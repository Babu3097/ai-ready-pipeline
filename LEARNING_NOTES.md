# Learning Notes

Updated after each phase. Plain English, my words to grow into.

## Time tracking

| Session | Date | Hours | Running total |
|---|---|---|---|
| Phases 0-2 build | 2026-11-10 | _to fill in_ | _to fill in_ |

Estimates: project 58-80 hours, learning 70-90, rebuild 15-20.

---

## Phases 0-2

### New words

- **Terminal**: a text window where you type commands to the computer.
- **Python**: the programming language we write the project in.
- **Virtual environment (`.venv`)**: a private box of tools for this project, so it doesn't clash with anything else on the computer.
- **Package / `pip`**: ready-made code written by others (e.g. pandas); `pip` installs it. `requirements.txt` lists what the project needs.
- **Git / commit**: Git is a save-history for a project. A commit is one labelled save point.
- **`.gitignore`**: a list of files Git must never save or share. Our `.env` (secret key) is on it.
- **`.env` file**: where the secret API key lives, outside the code.
- **API / API key**: a way for one program to ask another for something (here, asking Claude). The key is the password.
- **Demo mode**: the project runs without a key, using a simple stand-in for Claude.
- **Synthetic data**: invented data that looks real. No real people involved.
- **Seed**: a starting number that makes "random" data come out the same every time.
- **Ground truth**: the answer key. We know the correct values, so we can check how well the clean-up did.
- **CSV**: a plain-text spreadsheet; one row per line, values separated by commas.
- **pandas / DataFrame**: a Python tool for working with tables of data.
- **Data quality dimensions**: completeness (is it filled in?), uniqueness (no repeats?), validity (is it a real value?), consistency (same format everywhere?).
- **PII**: personally identifiable information (names, phones, emails, addresses). Masked before AI sees anything.
- **Masking**: replacing personal details with labels like `[PHONE]`.
- **Pydantic**: a tool that checks data is the shape we expect (used on the AI's answers).
- **Token**: a chunk of text an AI reads or writes. Cost is counted in tokens.
- **Regex**: a pattern for finding text, e.g. "something that looks like an email".
- **Logging**: writing down every change so it can be checked later.

### What each part does

- `src/ai_client.py`: the one place that talks to Claude. Works in demo mode without a key, and counts cost.
- `src/generate_data.py`: invents 300 enquiries, then deliberately breaks them the way old systems do. Saves the correct answers separately.
- `src/pii.py`: finds and hides personal details in free text.
- `src/ai_assist.py`: asks for a category suggestion on the few rows rules can't fix (masked text only; stored as a suggestion).
- `src/data_quality.py`: the clean-up. Fixes what is certain, flags the rest, logs every change, scores before vs after, and checks itself against the answer key.

### 3 interview talking points

1. **"I measured data quality before and after, in numbers"**: consistency went from about 65% to 100%, and I explained why completeness couldn't (I refuse to invent data).
2. **"I tested my clean-up against an answer key"**: I generated synthetic data with known correct values, so I could show 1 wrong value in about 3,300 cells instead of just claiming it worked, and I can name the one mistake and why it happened.
3. **"Personal details are masked before anything goes to an AI, and AI output is a suggestion, not a decision"**: that is the trust and governance story public-sector employers worry about.

### Honest description of my part

Built with AI assistance (Claude Code). I have not yet written this code myself; that comes in the rebuild stage. What I can say today: I understand what each step does and why, and I can explain the results.

### Quiz (answer in your own words)

1. Why does the clean-up empty a bad phone number instead of guessing the right one?
2. What is the ground truth, and why can we only have it because the data is synthetic?
3. What gets sent to the AI, and what never does?

---

## Phases 3-9 (built in one go)

> **Quizzes still owed.** You asked to finish the project first, so the end-of-phase quizzes were skipped. Before you list this on a CV, be able to answer the questions at the bottom of this file in your own words.

### New words

- **Database / table / row / column**: a database holds tables (like sheets); each row is one record.
- **SQLite**: a small database stored in one file. **SQL**: the language for asking a database questions.
- **Primary key**: the column that identifies each row. **Foreign key**: a column pointing at a row in another table.
- **SELECT / WHERE / GROUP BY / JOIN**: choose columns / filter rows / one result row per group / combine tables.
- **Schema**: the design of the tables. `create_tables.sql` is ours.
- **JSON**: a text format for structured data, like `{"category": "Noise"}`. **Pydantic** checks a JSON answer has the right shape.
- **Confidence**: how sure the AI says it is (0 to 1). We don't trust it alone.
- **Human in the loop**: a person must approve before something happens.
- **Audit log**: a diary of who did what and when.
- **Ground truth / accuracy / recall**: the right answers; share correct; share of true cases found.
- **Confusion table**: shows what was true against what the AI said.
- **Sensitivity analysis**: re-running a result with different assumptions to see how much it changes.
- **Demo mode / stand-in**: a simple substitute that lets everything run without the real AI.
- **n8n**: a tool that connects steps (web form -> AI -> sheet -> email) with boxes and arrows. **Webhook**: a web address that starts a workflow when something posts to it.
- **DAX / measure**: Power BI's formula language; a measure is a calculation like "review rate".
- **Semantic model**: the tables and measures Power BI reports use.
- **Microsoft Fabric**: Microsoft's all-in-one data platform. **Lakehouse**: files + tables in OneLake. **Delta table**: the table format Fabric stores. **Notebook**: a document mixing code and results. **SQL analytics endpoint**: lets you query Lakehouse tables with T-SQL. **Capacity**: the compute you use (the trial gives 60 days free).
- **T-SQL**: Microsoft's flavour of SQL.

### What each new part does

- `sql/create_tables.sql`, `src/load_sql.py`, `src/db.py`: design the database and load the clean data.
- `sql/metrics_queries.sql`, `src/run_queries.py`: the questions managers ask, answered in SQL.
- `src/triage.py`: asks the AI (or the demo stand-in) for category, urgency and summary; validates it; code decides which cases need a person.
- `src/review_queue.py`: the human review loop: queue, decisions, draft replies, audit log. `src/make_n8n_workflow.py` + `n8n/`: the same idea as an n8n workflow (drafted, not run).
- `sql/evaluation_queries.sql`, `src/evaluate.py`: checks the AI against the answer key and works out time and money saved from stated assumptions.
- `src/make_report_images.py`, `powerbi/BUILD_GUIDE.md`: previews of the four report pages and instructions to build them in Power BI.
- `fabric/`: notebooks, T-SQL and a guide for running it in Microsoft Fabric (not run).
- `src/run_all.py`: runs everything in order.
- `docs/`: results, error analysis, case study, video script, CV notes.

### 3 interview talking points per phase

See [docs/cv_and_interview.md](docs/cv_and_interview.md).

### What is and isn't done (don't overclaim)

- Done and tested: phases 0-3 and 6, plus the local review loop.
- Tested only in demo mode: AI triage. The real Claude call is untested.
- Drafted, not run: n8n workflow, Fabric notebooks.
- Not built: the Power BI `.pbix`, real screenshots, the video.

### Questions you owe (answer in your own words)

Phase 2:
1. Why does the clean-up empty a bad phone number instead of guessing the right one?
2. What is the ground truth, and why can we only have it because the data is synthetic?
3. What gets sent to the AI, and what never does?

Phases 3-6:
4. What does `GROUP BY category` do in plain English?
5. Why does code, not the AI, decide when a person must review a case?
6. Why is "urgent cases missed" a better headline than overall accuracy?
7. The results say about 64% time saved. Which assumption would you challenge first, and why?
8. Why can't the demo-mode accuracy be quoted as the AI's accuracy?

### Time tracking

Add your real hours in the table at the top of this file. Time so far on this project (your hours, not mine): _to fill in_.

### Next: learn from scratch, then rebuild

Order from CLAUDE.md: terminal and VS Code -> Python basics -> pandas -> SQL -> APIs/JSON/Claude -> n8n -> Power BI/DAX/Fabric. Then rewrite `data_quality.py`, the Claude call in `triage.py`, three SQL queries and one Power BI page yourself.


---

## Update: the real Claude API run

- **What happened:** ran `src/triage.py` against the real Claude API (Haiku 5.5) on all 312 enquiries. About £0.41 on assumed prices (check the Console for the real figure).
- **Result:** 84% category, 96% urgency, 0 of 86 urgent cases missed without a person seeing them. About 5% of the cases handled without review were wrong.
- **Lesson:** the keyword stand-in and my chat-session run both scored 97-99%. Neither was a fair test. Always report the independent run.
- **Bugs the real run found:** the API reply can start with a "thinking" block (my code crashed until I read only the text blocks); earlier, the personal-detail masking missed lower-case text.
- **New words:** *thinking block* (the model's reasoning, returned before the answer); *silent error* (a mistake nobody reviewed); *label ambiguity* (the category scheme itself overlaps, e.g. Safety vs Housing Repairs).
- **New questions to answer in your own words:** (9) Why is Claude's confidence not enough to decide who reviews a case? (10) Why did the real run score lower than the chat-session run? (11) What would you change to reduce the "Safety" over-use?
