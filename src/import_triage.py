"""
import_triage.py - load triage answers written by a Claude Code SESSION (no API call).

WHY THIS EXISTS: with no API key, the project can only run the keyword stand-in. As a stop-gap, Claude (in a
Claude Code chat) read each DISTINCT masked message once, using the same instructions as triage.py's prompt,
and wrote its answer to data/triage_session/triage_answers.json. This script applies those answers to every
enquiry with the same wording, then runs the SAME validation and review rules as triage.py.

HONEST LIMITS:
  * This is NOT the Claude API code path. The API call in triage.py is still untested.
  * The test data was written by the same assistant that triaged it, so the result is not independent.
  * Identical wording gets an identical answer, because each distinct message was read once.
  * Only masked text was read. The answer key was not looked at.

Run:  python src/import_triage.py          (after load_sql.py)
"""
import json
import re

import db
import triage

ANSWERS = db.ROOT / "data" / "triage_session" / "triage_answers.json"
MODE = "claude-code-session"
MODEL = "claude-sonnet-5-5 (Claude Code session, not the API)"


def core(masked: str) -> str:
    """Strip greetings, sign-offs and contact sentences so identical wording matches."""
    t = (masked or "").replace("\n", " ")
    t = re.sub(r"(?i)\b(my name is|kind regards,|many thanks,|regards,|thanks,)\s*\[NAME\]\.?", "", t)
    t = re.sub(r"(You can ring me on|My number is) \[PHONE\]\.?", "", t)
    t = re.sub(r"My email is \[EMAIL\]\.?", "", t)
    t = re.sub(r"My postcode is \[POSTCODE\]\.?", "", t)
    t = re.sub(r"My National Insurance number is \[NI_NUMBER\]\.?", "", t)
    t = re.sub(r"(?i)^(hi|hello northfield services|hello|good morning|to whom it may concern),?\s*", "", t.strip())
    t = re.sub(r"(?i)(please reply asap|any update)[.!?]*$", "", t.strip())
    t = re.sub(r"\[ADDRESS\](, \[POSTCODE\])?", "[ADDRESS]", t)
    t = re.sub(r"[^a-z\[\] ]", "", t.lower())
    return re.sub(r"\s+", " ", t).strip()


def main():
    answers = json.loads(ANSWERS.read_text(encoding="utf-8"))
    conn = db.connect()
    for sql in ("DELETE FROM ai_triage", "DELETE FROM human_reviews",
                "DELETE FROM audit_log WHERE actor = 'ai' OR action IN ('queued_for_review', 'triage_failed')"):
        conn.execute(sql)

    done = failed = review = 0
    for row in conn.execute("SELECT raw_row, message_masked, postcode FROM enquiries ORDER BY raw_row").fetchall():
        raw_row, masked, postcode = row["raw_row"], row["message_masked"] or "", row["postcode"]
        key = core(masked)
        answer = answers.get(key) if key else None
        result, error = None, "empty message" if not key else "no answer recorded for this wording"
        if answer:
            result = triage.Triage(**answer).model_dump()  # same shape check as the API path
        if result is None:
            failed += 1
            conn.execute("""INSERT INTO ai_triage (raw_row, needs_human_review, reason, mode, model, created_at)
                            VALUES (?, 1, ?, ?, ?, ?)""", (raw_row, f"AI triage failed: {error}", MODE, MODEL, db.now()))
            db.audit(conn, raw_row, "ai", "triage_failed", error)
            db.audit(conn, raw_row, "system", "queued_for_review", "triage failed")
            review += 1
            continue
        needs, why = triage.apply_review_rules(result)
        conn.execute("""INSERT INTO ai_triage (raw_row, category, urgency, summary, postcode, requested_action, confidence,
                        needs_human_review, reason, mode, model, input_tokens, output_tokens, cost_gbp, created_at)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,NULL,NULL,0,?)""",
                     (raw_row, result["category"], result["urgency"], result["summary"], postcode,
                      result["requested_action"], result["confidence"], int(needs), result["reason"],
                      MODE, MODEL, db.now()))
        db.audit(conn, raw_row, "ai", "triaged",
                 f"category={result['category']}; urgency={result['urgency']}; confidence={result['confidence']}; mode={MODE}")
        if needs:
            review += 1
            db.audit(conn, raw_row, "system", "queued_for_review", why)
        done += 1
    conn.commit()
    print(f"Imported {done} triage answers ({len(answers)} distinct messages), {failed} could not be triaged.")
    print(f"Sent to human review: {review} ({100 * review / max(1, done + failed):.0f}%). Cost: £0.00 (no API call).")
    conn.close()


if __name__ == "__main__":
    main()
