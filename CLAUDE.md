# AI-Ready Operations Pipeline (Microsoft Edition): Portfolio Project

## The problem this project proves I can solve
A public-service provider handles thousands of enquiries from the public. Its data is messy (blanks, wrong formats, duplicates, details buried in free text), triage is slow and manual, and managers struggle to report performance against their contract. It wants to use AI, but its pilots stall because the data isn't ready, nobody trusts the outputs, and nobody can prove the savings.

**My claim, tested on synthetic data:** clean data + AI triage + human review + honest measurement can cut handling time while keeping people in control, built on the Microsoft tools most UK employers use.

It tackles the main UK AI problems: messy data, pilots that don't prove value, trust and governance, old systems, and cost.

My pitch: **"I make AI work in real organisations. I clean the data, keep humans in control, and prove the savings."**

## The scenario (all data is made up)
"Northfield Services" is a fictional company running a council contact centre (housing repairs, noise, waste, billing, complaints, safety). It has:
- ~300 public enquiries (emails and web forms) in free text
- A messy "legacy" case spreadsheet with the problems listed in my Messy Data Playbook
- Managers who need contract performance numbers

**Never use real company names, logos or real people's data. Everything is synthetic.**

## Two editions
1. **Local edition (free, no card needed), built first.** Python, a local SQL database (SQLite), Claude API, n8n, Power BI Desktop.
2. **Microsoft Fabric edition, the showcase.** The same pipeline moved into Microsoft Fabric (Lakehouse, notebooks, Warehouse/SQL, Power BI), using Fabric's free trial. This matches what UK job ads ask for most. Check the current trial terms before starting, and never leave paid resources running.

## What the pipeline does
```
Messy inputs → 1. Data quality check & clean-up (Python)
            → 2. Store clean data in SQL tables
            → 3. AI extraction & triage (Claude, validated JSON)
            → 4. Human review for urgent/low-confidence cases (n8n + Google Sheets)
            → 5. Audit log of every AI and human decision
            → 6. Evaluation with SQL: accuracy vs ground truth, cost, time saved
            → 7. Power BI report for contract managers
```

## Tech stack
- Python 3: pandas, faker, pydantic, anthropic, python-dotenv
- SQL: SQLite locally; Fabric Warehouse / SQL endpoint in the Fabric edition
- Claude API: `claude-haiku-5-5` by default. Only use `claude-sonnet-5-5` if quality is clearly poor, and tell me first.
- n8n self-hosted in Docker:
  `docker run -it --rm --name n8n -p 5678:5678 -v n8n_data:/home/node/.n8n docker.n8n.io/n8nio/n8n`
- Google Sheets (review queue and audit log)
- Power BI Desktop (Windows), or Power BI in Fabric
- Git + GitHub (public repo, no secrets)

## Folder structure
```
ai-ready-pipeline/
  CLAUDE.md
  README.md
  PROJECT_NOTES.md
  .env                    # ANTHROPIC_API_KEY (never committed)
  .gitignore
  requirements.txt
  data/
    raw/  clean/  ground_truth/
  src/
    generate_data.py      # Phase 1
    data_quality.py       # Phase 2
    load_sql.py           # Phase 3
    triage.py             # Phase 4
    evaluate.py           # Phase 6
  sql/
    create_tables.sql
    metrics_queries.sql   # the questions managers ask, answered in SQL
  n8n/
    workflow.json
  fabric/
    notebooks/            # Phase 8 exports
  powerbi/
    northfield_report.pbix
  docs/
    case_study.md
    screenshots/
```

## Build phases (hours, not days)

### Phase 0: Setup (2–4 hours)
- Install Python, Git, VS Code, Docker, Power BI Desktop; create a virtual environment and requirements.txt
- Create `.env` and `.gitignore` before anything else; set a monthly spend limit in the Claude Console
- **Done when:** a one-line test call to Claude works and the key is nowhere in the code

### Phase 1: Generate realistic messy data (4–6 hours)
- ~300 enquiries across 6 categories with urgency levels
- Seed the problems from my Messy Data Playbook: hidden blanks, blank rows, placeholder values, partial and mixed dates, swapped and shifted columns, exact and near duplicates, invalid postcodes/phones/emails, inconsistent categories, lost leading zeros, personal details in free text
- Save the correct answers to `data/ground_truth/`
- **Done when:** the raw data looks realistically messy and the ground truth matches every row

### Phase 2: Data quality and clean-up (6–8 hours)
- Before/after report: completeness, duplicates, validity, consistency
- Fix by rules what's safe; flag the rest; never invent data; log every change; mask personal details before anything goes to AI
- **Done when:** quality scores before vs after are in numbers

### Phase 3: Store it in SQL (6–8 hours)
- Design simple tables: `enquiries`, `data_quality_log`, `ai_triage`, `human_reviews`, `audit_log`
- `load_sql.py` loads the clean data; `metrics_queries.sql` answers manager questions (volumes by category, urgent cases waiting, average handling time)
- **Done when:** I can run each query and explain in plain English what it does

### Phase 4: AI extraction and triage (8–10 hours)
- Claude returns JSON: `{category, urgency, summary, postcode, requested_action, confidence, needs_human_review, reason}`
- Validate with pydantic; retry once on bad JSON; log failures
- `needs_human_review = true` if confidence is low, urgency is high, or it's a safety issue
- Track tokens and cost; small batches; stop and warn if cost would go over £2
- **Done when:** all 300 are triaged, stored in SQL, with a review queue and a cost total

### Phase 5: Human in the loop with n8n (8–10 hours)
- New enquiry → Claude → review queue (Google Sheet) → a manager approves, edits or rejects → only then a drafted reply is "sent" (to my own email)
- Every step written to the audit log
- **Done when:** a test enquiry goes through AI, a human decision and the audit log end to end

### Phase 6: Evaluation, proving the value (4–6 hours)
- Compare with ground truth using SQL and Python: overall accuracy, per category, **urgent cases missed** (most important)
- Time saved, with clearly stated assumptions (e.g. 4 minutes manual per enquiry); cost per enquiry
- **Done when:** honest numbers exist, including where the AI was wrong and why

### Phase 7: Power BI report (6–8 hours)
- Pages: Overview · Data quality before/after · AI performance (accuracy, review rate, missed urgent) · Value (hours and cost saved)
- Readable by a contract manager in 30 seconds
- **Done when:** screenshots are saved and the .pbix is in the repo

### Phase 8: Microsoft Fabric edition (8–12 hours)
- Start the Fabric free trial; create a workspace
- Upload raw data to a **Lakehouse**; run the clean-up and triage as **Fabric notebooks**
- Store results in a **Warehouse** (or the Lakehouse SQL endpoint) and run the same SQL queries
- Build the Power BI report on the Fabric data
- Export notebooks to `fabric/notebooks/`, take screenshots, and record what's different from the local edition
- **Done when:** the whole pipeline runs in Fabric and the report updates from it

### Phase 9: Package it for publication (6–8 hours)
- README.md: the problem, architecture, results in numbers, how to run it, the Fabric edition, what I'd do next with real data
- `docs/case_study.md`: one plain-English page for non-technical readers
- A 2-minute video: messy data → clean → AI → human approval → Power BI
- CV line, e.g.: "Built an AI triage pipeline on Microsoft Fabric and Power BI: cleaned 300 messy records, auto-triaged enquiries at X% accuracy with human review of urgent cases, cutting estimated handling time by Y%"
- **Done when:** the repo is public, the video is uploaded and the CV is updated

## Rules (always follow)
- **Secrets:** the API key lives only in `.env` (or Fabric's secure settings). Never print, log or commit it.
- **Synthetic data only.** No real people, no real company names or logos.
- **A human decides** anything urgent, safety-related or low-confidence. The AI only sorts, extracts and drafts.
- **Honest results:** report mistakes and limitations; state every assumption.
- **Keep costs low:** Haiku by default, small batches, warn me before anything likely to cost over £2, and remind me to stop or delete cloud resources when finished.
- **Document as we go:** after each phase, update `PROJECT_NOTES.md` (new terms, what each part does, 3 interview talking points).
- **Describe the project honestly:** it was built with AI assistance; say which results are real API runs and which are demo mode or a chat session.

## Next steps
- Rebuild key parts by hand: `data_quality.py`, the Claude call in `triage.py`, three SQL metric queries, one Power BI page.
- Record the 2-minute video; test on a dataset written by someone else.
- Polish the Power BI report in Power BI Desktop (custom DAX); run the Fabric edition if an account that can start the trial becomes available.

## Where things stand
Phases 0-9 built (see README "Honest status"). Real Claude API runs done (claude-haiku-5-5; prompt v2 is the default). Power BI report built in the Power BI service. Fabric edition prepared but not run. Notes and interview talking points live in `PROJECT_NOTES.md`.
