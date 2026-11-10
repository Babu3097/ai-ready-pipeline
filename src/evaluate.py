"""
evaluate.py - Phase 6: prove the value, honestly.

1. Runs sql/evaluation_queries.sql (accuracy vs the answer key, urgent cases missed, review rate, cost)
2. Works out time and money saved from clearly stated ASSUMPTIONS
3. Writes docs/results.md and the CSV files Power BI reads (powerbi/data/)

Run:  python src/evaluate.py
"""
import pandas as pd

import db

# ---------- ASSUMPTIONS (change these and re-run; nothing is hidden) ----------
MANUAL_MINUTES = 4.0        # a person reads, categorises and prioritises one enquiry by hand (from the project brief)
SKIM_MINUTES = 0.5          # with AI, an enquiry NOT sent for review still gets a quick skim
REVIEW_MINUTES = 2.0        # with AI, a flagged enquiry: read the summary, check, decide
HOURLY_COST_GBP = 18.0      # assumed fully-loaded cost of a contact-centre worker per hour
SCALE_VOLUME = 10_000       # illustrative yearly volume for the scaled example
# -------------------------------------------------------------------------------

OUT = db.ROOT / "powerbi" / "data"


def md_table(cols, rows):
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for r in rows:
        out.append("| " + " | ".join("" if v is None else str(v) for v in r) + " |")
    return "\n".join(out)


def build_fact_table(conn):
    return pd.read_sql_query("""
        SELECT e.raw_row, e.case_ref, e.received_date, SUBSTR(e.received_date, 1, 7) AS month, e.channel, e.status,
               e.handling_mins, e.quality_status, e.possible_duplicate_of,
               t.category AS ai_category, t.urgency AS ai_urgency, t.confidence, t.needs_human_review, t.mode AS ai_mode,
               t.cost_gbp, h.decision AS human_decision, h.final_category, h.final_urgency, h.simulated AS decision_simulated,
               m.row_type, g.category AS true_category, g.urgency AS true_urgency,
               COALESCE(h.final_category, t.category, e.category) AS category_final,
               COALESCE(h.final_urgency, t.urgency, e.urgency)    AS urgency_final,
               CASE WHEN t.category = g.category THEN 1 ELSE 0 END AS category_correct,
               CASE WHEN t.urgency  = g.urgency  THEN 1 ELSE 0 END AS urgency_correct
        FROM enquiries e
        LEFT JOIN ai_triage t ON t.raw_row = e.raw_row
        LEFT JOIN human_reviews h ON h.raw_row = e.raw_row
        LEFT JOIN raw_row_map m ON m.raw_row = e.raw_row
        LEFT JOIN ground_truth g ON g.enquiry_id = m.enquiry_id AND m.row_type = 'original'
        ORDER BY e.raw_row""", conn)


def main():
    conn = db.connect()
    mode = [r[0] for r in conn.execute("SELECT DISTINCT mode FROM ai_triage")]
    prompts = [r[0] for r in conn.execute("SELECT DISTINCT prompt_version FROM ai_triage WHERE prompt_version IS NOT NULL")]
    demo = mode == ["demo"]
    session = mode == ["claude-code-session"]
    results = db.run_sql_file(db.SQL_DIR / "evaluation_queries.sql", conn)
    R = {title.split(":")[0]: (cols, rows) for title, cols, rows, _ in results}

    q1 = dict(zip(*[R["Q1"][0], R["Q1"][1][0]]))
    q4 = dict(zip(*[R["Q4"][0], R["Q4"][1][0]]))
    q6 = dict(zip(*[R["Q6"][0], R["Q6"][1][0]]))
    q8 = R["Q8"][1]
    n = q1["enquiries"]
    flagged = conn.execute("""SELECT COUNT(*) FROM ai_triage t JOIN raw_row_map m ON m.raw_row = t.raw_row
                              WHERE m.row_type = 'original' AND t.needs_human_review = 1""").fetchone()[0]
    unflagged = n - flagged
    ai_cost = sum(r[5] or 0 for r in q8)

    # ---- value ----
    manual_total = n * MANUAL_MINUTES
    ai_total = unflagged * SKIM_MINUTES + flagged * REVIEW_MINUTES
    saved = manual_total - ai_total
    saved_pct = 100 * saved / manual_total
    money_saved = saved / 60 * HOURLY_COST_GBP - ai_cost
    scale = SCALE_VOLUME / n
    sens = []
    for rm in (1.0, 2.0, 3.0, 4.0):
        t = unflagged * SKIM_MINUTES + flagged * rm
        sens.append((f"{rm:.0f} min", f"{(manual_total - t) / 60:.1f} h", f"{100 * (manual_total - t) / manual_total:.0f}%"))

    summary = [
        ("Enquiries scored", n, "count", "Original enquiries only"),
        ("Category accuracy", q1["category_accuracy_pct"], "%", "AI category = true category"),
        ("Urgency accuracy", q1["urgency_accuracy_pct"], "%", "AI urgency = true urgency"),
        ("Truly urgent enquiries", q4["truly_urgent"], "count", "True urgency = High"),
        ("Urgent missed by AI", q4["missed_by_ai"], "count", "AI did not say High (includes blank messages it could not read)"),
        ("Urgent missed AND not sent to a person", q4["missed_and_not_sent_to_a_person"], "count", "The dangerous kind"),
        ("Sent to human review", flagged, "count", "Low confidence, High urgency or Safety"),
        ("Review rate", round(100 * flagged / n, 1), "%", "Share of enquiries needing a person"),
        ("Accuracy after human review", q6["final_category_pct"], "%", "SIMULATED reviewer - best case"),
        ("Manual triage time", round(manual_total / 60, 1), "hours", f"{MANUAL_MINUTES} min per enquiry (assumed)"),
        ("Time with AI + human review", round(ai_total / 60, 1), "hours", f"{SKIM_MINUTES} min skim, {REVIEW_MINUTES} min review (assumed)"),
        ("Time saved", round(saved / 60, 1), "hours", "Over the scored enquiries"),
        ("Time saved %", round(saved_pct, 1), "%", "Triage time only, not fixing the problem"),
        ("Staff cost saved", round(money_saved, 2), "GBP", f"At £{HOURLY_COST_GBP}/hour (assumed), after AI cost"),
        ("AI cost", round(ai_cost, 4), "GBP", "Demo / chat-session modes = 0 (no API billing); API cost is estimated from assumed token prices"),
        (f"Hours saved per {SCALE_VOLUME:,} enquiries", round(saved * scale / 60), "hours", "Straight scaling - illustrative only"),
    ]

    # ---- exports for Power BI ----
    OUT.mkdir(parents=True, exist_ok=True)
    build_fact_table(conn).to_csv(OUT / "triage_facts.csv", index=False)
    pd.DataFrame(summary, columns=["metric", "value", "unit", "note"]).to_csv(OUT / "eval_summary.csv", index=False)
    pd.read_sql_query("SELECT * FROM quality_scores", conn).to_csv(OUT / "quality_scores.csv", index=False)
    pd.DataFrame([(f"{rm}", float(h.split()[0]), float(p.strip('%'))) for (rm, h, p) in sens],
                 columns=["review_minutes", "hours_saved", "pct_saved"]).to_csv(OUT / "value_sensitivity.csv", index=False)
    pd.read_sql_query("SELECT * FROM audit_log", conn).to_csv(OUT / "audit_log.csv", index=False)
    pd.read_sql_query("SELECT category, urgency, COUNT(*) AS n FROM ground_truth GROUP BY 1,2", conn).to_csv(OUT / "truth_mix.csv", index=False)

    # ---- results.md ----
    L = ["# Results\n"]
    if demo:
        L += ["> **READ THIS FIRST - these numbers come from DEMO MODE.** The \"AI\" here is a simple keyword matcher, not Claude.",
              "> The synthetic enquiries were written from a small set of templates, so a keyword matcher scores very well on them.",
              "> These figures prove the *pipeline and measurement work*. They do **not** show how Claude, or any AI, would do on real, messier enquiries.",
              "> Re-run with a real API key (`python src/triage.py --redo`, then `python src/evaluate.py`) to get Claude's numbers.\n"]
    elif session:
        L += ["> **READ THIS FIRST - the triage here was done by Claude in a Claude Code chat session, NOT by the Claude API.**",
              "> Claude read each *distinct* masked message once and its answer was applied to every copy of that wording.",
              "> Limits: (1) the same assistant wrote the synthetic data and the triage, so this is **not an independent test**; (2) the API code path in `src/triage.py` is still unproven;",
              "> (3) the synthetic enquiries come from about 34 templates, which is far easier than real enquiries. Treat these as a best case.\n"]
    else:
        L += [f"Mode: **real Claude API** ({', '.join(mode)}, prompt {', '.join(prompts) or 'unknown'}). Synthetic, template-based data is easier than real enquiries, so treat these as a best case.\n"]
    L += ["## Accuracy against the answer key\n", md_table(*R["Q1"]), "",
          "### By category\n", md_table(*R["Q2"]), "",
          "### Urgency: what was true vs what the AI said\n", md_table(*R["Q3"]), "",
          "## Urgent cases missed (the most important number)\n", md_table(*R["Q4"]), "",
          "*\"Missed by AI\" includes enquiries with an empty message, which the AI could not read at all. Those are always sent to a person, so none were missed silently.*\n",
          "## Does the human-review rule work?\n", md_table(*R["Q5"]), "",
          "`sent_to_person = 1` are the cases routed to a person. The `0` row is what the AI handled with only a skim: that error rate is what a manager must be willing to accept.\n",
          "## After human review\n", md_table(*R["Q6"]), "",
          "*The reviewer in this run is SIMULATED and knows the right answers, so this is a best case, not evidence about real managers.*\n",
          "## Where the AI was wrong\n", md_table(*R["Q7"]), "",
          "## Cost\n", md_table(*R["Q8"]), "",
          "## Time and money saved\n",
          "**Assumptions (all stated, all changeable at the top of `src/evaluate.py`):**\n",
          f"- Manual triage: **{MANUAL_MINUTES} min** per enquiry (from the project brief)",
          f"- With AI, not sent for review: **{SKIM_MINUTES} min** quick skim",
          f"- With AI, sent for review: **{REVIEW_MINUTES} min** to read the summary and decide",
          f"- Staff cost: **£{HOURLY_COST_GBP}/hour** fully loaded",
          "- Triage time only. It does not count the time to actually fix the issue.\n",
          md_table(["Measure", "Value"], [
              ("Enquiries", n), ("Sent to a person", f"{flagged} ({100 * flagged / n:.0f}%)"),
              ("Manual time", f"{manual_total / 60:.1f} h"), ("With AI + review", f"{ai_total / 60:.1f} h"),
              ("Time saved", f"{saved / 60:.1f} h ({saved_pct:.0f}%)"), ("Staff cost saved", f"£{money_saved:.2f}"),
              (f"Scaled to {SCALE_VOLUME:,} enquiries", f"about {saved * scale / 60:.0f} h saved")]), "",
          "### How sensitive is the saving to the review-time assumption?\n",
          md_table(["Minutes per reviewed case", "Hours saved", "% saved"], sens), "",
          "The review rate is high because the rules send *every* High-urgency and Safety case to a person. That is deliberate (a human decides anything urgent), "
          "and it is the main thing that limits the saving."]
    (db.ROOT / "docs" / "results.md").write_text("\n".join(L) + "\n", encoding="utf-8")

    print("Key results:")
    for m, v, u, _ in summary:
        print(f"  {m:<45}{v} {u}")
    print(f"\nWritten: docs/results.md and CSV files in {OUT.relative_to(db.ROOT)}/")
    conn.close()


if __name__ == "__main__":
    main()
