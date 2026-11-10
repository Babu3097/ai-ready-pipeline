# CV line, LinkedIn text and interview notes

## The rule

Only claim what is true *today*. This project was **built with AI assistance**; Fabric, Power BI (.pbix), the n8n workflow and the real-Claude run are **not yet done**. Update the lines below as you complete each one.

## CV line (true today)

> Built an AI-assisted triage pipeline on synthetic council enquiries (Python, SQL, pandas, Claude API): cleaned 330 messy records to 312 (consistency 65% to 100%), masked personal data before AI use, and measured Claude's triage against a known answer key (84% category / 96% urgency accuracy; 0 of 86 urgent cases missed without human review; about £0.40 for 312 enquiries). Found and fixed two bugs in my own data masking and API handling. Built with AI assistance.

Keep "synthetic" and "Built with AI assistance". Do not write "on Microsoft Fabric" or "Power BI report" yet. A shorter version for a tight CV: "Built and evaluated an AI triage pipeline (Python, SQL, Claude API) on synthetic council data: 96% urgency accuracy, 0 urgent cases missed without human review, with a documented 5% silent-error rate and fixes proposed."

## Upgrade the line when each thing is true

| When you have... | You can add |
|---|---|
| Built and saved the Power BI report | "with a four-page Power BI report for contract managers" |
| Run it in a Fabric trial | "prepared and ran the pipeline on Microsoft Fabric (Lakehouse, notebooks, SQL endpoint, Power BI)" |
| Improved the prompt and re-measured | "improved category accuracy from 84% to X% by changing the prompt and label scheme" |
| Rebuilt the pieces yourself | "then rebuilt the data-cleaning script and key SQL queries from scratch" |

## LinkedIn "Featured" description (short)

"A portfolio project on a problem UK public-service providers face: AI pilots stall because the data is messy, nobody trusts the output, and the savings aren't proven. Using synthetic data for a fictional council contact centre, I built a pipeline that cleans and scores the data, masks personal details, triages enquiries with AI, sends anything urgent or uncertain to a human, logs every decision, and measures accuracy and time saved against a known answer key. Built with AI assistance as part of learning Python, SQL and Power BI; honest limitations are in the README."

## What I can say honestly in an interview

**Can say:**
- "I used AI tools to build it, and I understand each step: what the clean-up rules do, why uncertain values are blanked, how the review rule works, and what the numbers do and don't prove."
- "I'm learning Python and SQL properly now and plan to rebuild the clean-up and some queries myself."

**Don't say:**
- That you wrote the code unaided.
- That the AI is "97%" or "99% accurate". Those were the keyword stand-in and a chat-session run. The real API result is 84% category / 96% urgency, on easy synthetic data.
- That it runs on Fabric or that a Power BI report exists, until it does.

## Talking points for phases 3 to 9

**Phase 3 - SQL**
1. "I designed five tables (enquiries, quality log, AI triage, human reviews, audit log) and wrote nine manager questions in SQL, such as urgent cases still open and share of closed cases within a target."
2. "I kept the answer key in separate tables the pipeline never reads, so evaluation stays honest."
3. "Writing the same queries for the Fabric SQL endpoint showed me where SQLite and T-SQL differ."

**Phase 4 - AI triage**
1. "The AI must return JSON in an exact shape. It's validated, retried once, and failures go to a person. The first real call crashed because the reply included a 'thinking' block my demo mode never produced, which is why I test with the real thing."
2. "Code, not the AI, decides when a human must review: low confidence, high urgency, or safety. The AI can't talk its way out of it."
3. "Only masked text is sent, and a cost guard stops the run before £2."

**Phase 5 - Human in the loop**
1. "Nothing is 'sent' until a person approves or edits. Rejected cases get no reply."
2. "Every step goes into an audit log: who (system, AI or human), what and when."
3. "I drafted the n8n workflow, but haven't run it; I tested the same logic in Python first."

**Phase 6 - Evaluation**
1. "The key number is urgent cases missed, not overall accuracy."
2. "Time saved depends on assumptions, so I show a sensitivity table: at 4 minutes per review the saving drops to about a third."
3. "I'm upfront that results came from a keyword stand-in on easy data."

**Phase 7 - Reporting**
1. "I designed a four-page report a contract manager can read in 30 seconds, with the DAX measures written out."
2. "Power BI Desktop is Windows-only and I'm on a Mac, so I previewed the pages in Python and documented how to build them."

**Phase 8 - Fabric**
1. "I checked the trial terms: 60 days, no card via the Fabric app, items removed after expiry, so I planned to export evidence and delete the workspace."
2. "The notebooks reuse the same Python files as the local edition, so only the plumbing is new."

**Phase 9 - Packaging**
1. "Status table in the README says what is tested and what isn't."
2. "One-page case study for non-technical readers."
3. "I'd rather show honest limits than an impressive number I can't defend."

## Likely questions (practise answering in your own words)

- Why mask personal details before sending text to an AI?
- Why blank an uncertain value instead of guessing?
- What does "human in the loop" mean here, and what does it cost?
- How would you know if the AI got worse over time?
- What would change with real data?
