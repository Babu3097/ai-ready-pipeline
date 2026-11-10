"""
review_queue.py - Phase 5 (local version): the human-in-the-loop step.

This does in Python what the n8n workflow does with Google Sheets:
  export    write the REVIEW QUEUE (data/review/review_queue.csv) - open it in Excel or Google Sheets
  simulate  fill in the decision column with a STAND-IN reviewer (clearly labelled SIMULATED)
  apply     read the decisions back, save them, write a draft reply ONLY for approved/edited cases,
            and record every step in the audit log
  all       export + simulate + apply (the quick demo)
  demo-one  push ONE brand-new test enquiry through the whole journey and print its audit trail

A real manager uses `export`, edits the decision columns by hand, then runs `apply`.
Nothing is ever really emailed: "sent" replies are text files in data/review/outbox/.
"""
import sys

import pandas as pd

import ai_client
import db
import pii
import triage

REVIEW_DIR = db.ROOT / "data" / "review"
QUEUE_FILE = REVIEW_DIR / "review_queue.csv"
OUTBOX = REVIEW_DIR / "outbox"
CATEGORIES = ["Housing Repairs", "Noise", "Waste", "Billing", "Complaints", "Safety"]
URGENCIES = ["High", "Medium", "Low"]

# Fictional response times for the fictional company
REPLY_TEMPLATES = {
    "Housing Repairs": "We have logged your repair request. An engineer will contact you to arrange a visit.",
    "Noise": "We have logged your noise report and our environmental team will look into it.",
    "Waste": "We have logged your waste and recycling report and passed it to the collections team.",
    "Billing": "We have passed your billing query to our accounts team, who will review your account.",
    "Complaints": "We are sorry you have had a poor experience. Your complaint has been logged and will be investigated.",
    "Safety": "Thank you for reporting this hazard. We take safety issues very seriously and are acting on it.",
}
TIMESCALES = {"High": "within 4 working hours", "Medium": "within 3 working days", "Low": "within 10 working days"}


def draft_reply(name, case_ref, category, urgency):
    text = f"Dear {name or 'resident'},\n\nRe: case {case_ref or '(reference pending)'}\n\n{REPLY_TEMPLATES[category]} "
    text += f"You can expect to hear from us {TIMESCALES[urgency]}.\n"
    if category == "Safety" or urgency == "High":
        text += "\nIf anyone is in immediate danger, please call 999.\n"
    return text + "\nKind regards,\nNorthfield Services (fictional)\n"


# ---------------- export ----------------

def export(conn):
    REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    rows = conn.execute("""
        SELECT e.raw_row, e.case_ref, e.received_date, e.channel, t.category AS ai_category, t.urgency AS ai_urgency,
               t.confidence, t.summary, t.requested_action,
               (SELECT detail FROM audit_log a WHERE a.raw_row = e.raw_row AND a.action = 'queued_for_review'
                ORDER BY a.id DESC LIMIT 1) AS why_flagged
        FROM ai_triage t JOIN enquiries e ON e.raw_row = t.raw_row
        WHERE t.needs_human_review = 1
          AND e.raw_row NOT IN (SELECT raw_row FROM human_reviews)
        ORDER BY CASE t.urgency WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END, e.received_date""").fetchall()
    df = pd.DataFrame([dict(r) for r in rows])
    for col in ["decision", "final_category", "final_urgency", "reviewer", "notes"]:
        df[col] = ""
    df.to_csv(QUEUE_FILE, index=False)
    print(f"Review queue: {len(df)} cases -> {QUEUE_FILE.relative_to(db.ROOT)}")
    print("Fill in 'decision' with approved / edited / rejected. For 'edited', also set final_category and final_urgency.")


# ---------------- simulate (stand-in manager) ----------------

def simulate(conn):
    """A pretend reviewer who KNOWS the right answer. This shows what the loop does when the human is
    careful - it is an upper bound, not proof about real managers."""
    q = pd.read_csv(QUEUE_FILE, dtype=str, keep_default_na=False)
    truth = {r["raw_row"]: r for r in conn.execute("""
        SELECT m.raw_row, m.row_type, g.category, g.urgency FROM raw_row_map m
        LEFT JOIN ground_truth g ON g.enquiry_id = m.enquiry_id""")}
    for i, r in q.iterrows():
        t = truth[int(r["raw_row"])]
        q.loc[i, "reviewer"] = "SIMULATED-REVIEWER"
        if t["row_type"] == "near_duplicate":
            q.loc[i, ["decision", "notes"]] = ["rejected", "Looks like a repeat of an earlier enquiry"]
        elif r["ai_category"] == t["category"] and r["ai_urgency"] == t["urgency"]:
            q.loc[i, "decision"] = "approved"
        else:
            q.loc[i, ["decision", "final_category", "final_urgency", "notes"]] = [
                "edited", t["category"], t["urgency"], "Corrected AI category/urgency"]
    q.to_csv(QUEUE_FILE, index=False)
    print(f"Simulated reviewer filled in {len(q)} decisions (labelled SIMULATED-REVIEWER).")


# ---------------- apply ----------------

def apply(conn):
    q = pd.read_csv(QUEUE_FILE, dtype=str, keep_default_na=False)
    OUTBOX.mkdir(parents=True, exist_ok=True)
    counts = {"approved": 0, "edited": 0, "rejected": 0, "skipped": 0}
    for _, r in q.iterrows():
        raw_row, decision = int(r["raw_row"]), r["decision"].strip().lower()
        if decision == "":
            counts["skipped"] += 1  # not decided yet - stays in the queue
            continue
        if conn.execute("SELECT 1 FROM human_reviews WHERE raw_row = ?", (raw_row,)).fetchone():
            continue
        cat, urg = r["ai_category"], r["ai_urgency"]
        if decision == "edited":
            cat, urg = r["final_category"], r["final_urgency"]
            if cat not in CATEGORIES or urg not in URGENCIES:
                print(f"  row {raw_row}: 'edited' needs a valid final_category and final_urgency - skipped")
                counts["skipped"] += 1
                continue
        elif decision not in ("approved", "rejected"):
            print(f"  row {raw_row}: unknown decision '{decision}' - skipped")
            counts["skipped"] += 1
            continue
        if decision == "rejected":
            cat = urg = None
        elif not cat or not urg:
            print(f"  row {raw_row}: AI gave no category, so it cannot be 'approved' - use 'edited'")
            counts["skipped"] += 1
            continue
        reviewer = r["reviewer"] or "unknown"
        conn.execute("""INSERT INTO human_reviews (raw_row, decision, final_category, final_urgency, reviewer, reviewed_at, notes, simulated)
                        VALUES (?,?,?,?,?,?,?,?)""",
                     (raw_row, decision, cat, urg, reviewer, db.now(), r["notes"], int(reviewer.startswith("SIMULATED"))))
        db.audit(conn, raw_row, "human", f"decision_{decision}", f"reviewer={reviewer}; category={cat}; urgency={urg}; notes={r['notes']}")
        counts[decision] += 1
        if decision == "rejected":
            db.audit(conn, raw_row, "system", "no_reply_sent", "rejected by reviewer - back to manual handling")
            continue
        e = conn.execute("SELECT case_ref, name FROM enquiries WHERE raw_row = ?", (raw_row,)).fetchone()
        text = draft_reply(e["name"], e["case_ref"], cat, urg)
        (OUTBOX / f"reply_row{raw_row:04d}.txt").write_text(f"To: (demo - saved locally, not emailed)\n\n{text}", encoding="utf-8")
        db.audit(conn, raw_row, "system", "reply_sent", f"draft saved to outbox/reply_row{raw_row:04d}.txt (demo: not emailed)")
    conn.commit()
    print(f"Applied decisions: {counts}")
    waiting = conn.execute("SELECT COUNT(*) FROM ai_triage WHERE needs_human_review = 1 AND raw_row NOT IN (SELECT raw_row FROM human_reviews)").fetchone()[0]
    print(f"Still waiting for a person: {waiting}")


# ---------------- one brand-new enquiry, end to end ----------------

def demo_one(conn):
    test_row = 9001
    message = ("Hello, I can smell gas in the corridor outside flat 3 at 22 Willow Court, M99 1ZZ. "
               "My name is Test Person and my number is 07700 900123. Please send someone today.")
    conn.execute("""INSERT INTO enquiries (raw_row, case_ref, received_date, channel, name, message, message_masked, status, quality_status)
                    VALUES (?,?,?,?,?,?,?,?,?)""",
                 (test_row, "NF-TEST-0001", db.now()[:10], "Web form", "Test Person", message,
                  pii.mask_pii(message, "Test Person"), "Open", "clean"))
    db.audit(conn, test_row, "system", "enquiry_received", "web form submission (synthetic test)")
    masked = pii.mask_pii(message, "Test Person")
    print("Text the AI sees:", masked)
    if ai_client.is_demo():
        result, tracker = triage.demo_triage(masked), None
    else:
        tracker = ai_client.CostTracker()
        result, err = triage.claude_triage(masked, tracker)
        if result is None:
            raise SystemExit(f"Claude triage failed: {err}")
    needs, why = triage.apply_review_rules(result)
    conn.execute("""INSERT INTO ai_triage (raw_row, category, urgency, summary, postcode, requested_action, confidence, needs_human_review,
                    reason, mode, model, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                 (test_row, result["category"], result["urgency"], result["summary"], "", result["requested_action"],
                  result["confidence"], int(needs), result["reason"], "demo" if ai_client.is_demo() else "claude",
                  "keyword-rules" if ai_client.is_demo() else ai_client.MODEL, db.now()))
    db.audit(conn, test_row, "ai", "triaged", f"category={result['category']}; urgency={result['urgency']}; confidence={result['confidence']}")
    db.audit(conn, test_row, "system", "queued_for_review", why)
    conn.execute("""INSERT INTO human_reviews (raw_row, decision, final_category, final_urgency, reviewer, reviewed_at, notes, simulated)
                    VALUES (?,?,?,?,?,?,?,1)""",
                 (test_row, "approved", result["category"], result["urgency"], "SIMULATED-REVIEWER", db.now(), "demo-one test"))
    db.audit(conn, test_row, "human", "decision_approved", "reviewer=SIMULATED-REVIEWER")
    reply = draft_reply("Test Person", "NF-TEST-0001", result["category"], result["urgency"])
    db.audit(conn, test_row, "system", "reply_sent", "demo: draft not emailed")
    trail = conn.execute("SELECT ts, actor, action, detail FROM audit_log WHERE raw_row = ? ORDER BY id", (test_row,)).fetchall()
    lines = ["Audit trail for one synthetic test enquiry", ""] + [f"{r['ts']}  {r['actor']:<7} {r['action']:<20} {r['detail']}" for r in trail]
    lines += ["", "Draft reply:", "", reply]
    out = db.ROOT / "docs" / "example_audit_trail.txt"
    out.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    # clean up so the test row does not pollute the real numbers
    for table in ("audit_log", "human_reviews", "ai_triage", "enquiries"):
        conn.execute(f"DELETE FROM {table} WHERE raw_row = ?", (test_row,))
    conn.commit()
    print(f"\n(Saved to {out.relative_to(db.ROOT)}; test row removed from the database.)")


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    conn = db.connect()
    if cmd in ("export", "all"): export(conn)
    if cmd in ("simulate", "all"): simulate(conn)
    if cmd in ("apply", "all"): apply(conn)
    if cmd == "demo-one": demo_one(conn)
    if cmd not in ("export", "simulate", "apply", "all", "demo-one"):
        print(__doc__)
    conn.close()


if __name__ == "__main__":
    main()
