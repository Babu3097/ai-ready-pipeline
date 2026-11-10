# 2-minute video script

**Goal:** show messy data -> clean -> AI -> human approval -> report, in plain English. **You record this yourself** (screen recording on a Mac: Cmd+Shift+5, or QuickTime). Don't read it word for word; say it in your own voice.

**Before you record:** run `python src/run_all.py` so everything is fresh. Have these open in tabs: `data/raw/enquiries_raw.csv`, `data/clean/quality_report.md`, `data/review/review_queue.csv`, `docs/example_audit_trail.txt`, and the four images in `docs/screenshots/`. If you have built the Power BI report or run Fabric, show those instead of the Python preview images and say so.

| Time | Show | Say (rough idea) |
|---|---|---|
| 0:00 | Title / README top | "Hi, I'm Ranjith. This project shows how I'd make AI work in a real organisation: clean the data, keep humans in control, and prove the savings. Everything is synthetic data for a fictional council contact centre." |
| 0:15 | Raw CSV, scroll the mess | "This is a legacy case sheet. Blank rows, dates in different formats, phone numbers missing their zero, categories typed five ways, details buried in the message." |
| 0:35 | quality_report.md scores table | "My clean-up fixes only what's certain and flags the rest. Consistency went from 65% to 100%. It never guesses: if it can't trust a value it leaves it blank. I checked it against an answer key: one wrong value in about 3,300." |
| 0:55 | Terminal: `python src/triage.py` finishing, then masked text sample | "Before AI sees any text, personal details are masked. The AI returns a category, urgency and summary, checked for the right shape. This run is in demo mode, a keyword stand-in, not Claude." |
| 1:15 | review_queue.csv, then example_audit_trail.txt | "Urgent, safety and low-confidence cases go to a person, decided by code, not by the AI. Only after approval is a reply drafted. Every step is in the audit log." |
| 1:35 | Screenshots 3 and 4 (or Power BI) | "Evaluation: zero urgent cases missed without a person seeing them. Time saved is about 64% on triage, but that rests on stated assumptions, and drops to a third if review takes longer." |
| 1:50 | README limitations | "Honest limits: synthetic easy data, a simulated reviewer, and the Claude path is still to be tested. Next: real Claude run, Power BI and Fabric. Thanks for watching." |

**Tips:** keep it under 2:10; zoom the terminal text; don't show your `.env`; mention it was built with AI assistance (it's in the README too).

**After recording:** upload (YouTube unlisted works) and add the link to the README.
