# AI-Ready Operations Pipeline (Microsoft Edition)

A portfolio project showing how to make AI work in a real public-service setting: **clean the data, keep humans in control, and prove the savings.**

> **All data is synthetic.** "Northfield Services" is a fictional council contact centre. No real people, companies or logos are used.

## The problem

A public-service provider receives thousands of enquiries. The data is messy (blanks, wrong formats, duplicates, details buried in free text), triage is slow, and managers struggle to report contract performance. AI pilots stall because the data isn't ready, nobody trusts the output, and nobody can prove the savings.

## Status

| Phase | What | State |
|---|---|---|
| 0 | Setup, Git, demo mode | Done |
| 1 | Generate messy synthetic data + answer key | Done |
| 2 | Data quality clean-up (rules + AI help) | Done |
| 3 | SQL tables and manager queries | Next |
| 4-9 | AI triage, human review (n8n), evaluation, Power BI, Microsoft Fabric edition, packaging | Planned |

## Run it (no API key needed)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python src/generate_data.py     # makes data/raw and data/ground_truth
python src/data_quality.py      # cleans it, writes data/clean and a report
```

**Demo mode:** with no `ANTHROPIC_API_KEY` in `.env`, the AI step uses a simple keyword matcher instead of Claude. Nothing is sent anywhere and nothing costs money. To use the real thing, copy `.env.example` to `.env` and paste your key in. Check the connection with `python src/ai_client.py`.

## Phase 2 results (demo mode, seed 42)

Raw legacy sheet: 330 rows. Cleaned table: 312 rows.

| Measure | Before | After |
|---|---|---|
| Completeness | 87.5% | 90.4% |
| Uniqueness | 96.9% | 100.0% |
| Validity | 95.5% | 100.0% |
| Consistency | 64.9% | 100.0% |

Checked against the answer key (300 real enquiries): **1 wrong value out of about 3,300 cleaned cells**; everything the rules couldn't trust was left blank and flagged. All 10 exact duplicates were removed, all 12 near-duplicates were flagged for a human (none wrongly), and no personal details leaked into the text prepared for AI.

Honest limits: validity and consistency reach 100% by design, because untrustworthy values are emptied rather than guessed, so completeness can't return to 100%. The one wrong value is a mistyped postcode that still looks real; catching that needs a full postcode database. Full detail in [data/clean/quality_report.md](data/clean/quality_report.md).

## How the clean-up works

1. **Realign:** repair rows where values sit in the wrong column or a row is shifted.
2. **Standardise by rules:** dates, phones, postcodes, emails, names, categories, urgency. Only when the fix is certain.
3. **Never invent:** unreadable values are emptied and flagged; the original stays in `data_quality_log.csv`.
4. **Duplicates:** exact repeats removed; near-duplicates flagged for a person.
5. **Mask personal details** before any text goes near an AI.
6. **AI suggestion** for the few rows where the category can't be worked out. Stored as a suggestion, flagged for review.

## Project layout

```
src/        generate_data.py, data_quality.py, pii.py, ai_assist.py, ai_client.py
data/       raw/ (messy), clean/ (outputs), ground_truth/ (answer key)
sql/ n8n/ powerbi/ fabric/ docs/   filled in as later phases are built
```

## Built with AI assistance

This was built with Claude Code as a learn-by-building project. The plan is to learn the underlying skills afterwards and rebuild key parts (the clean-up script, the Claude call, SQL queries, one report page) from scratch.
