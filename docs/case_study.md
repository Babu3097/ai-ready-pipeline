# Case study: making AI triage safe to trust (one page)

*A portfolio project using entirely synthetic data. "Northfield Services" is fictional.*

## The problem

A company running a council contact centre gets thousands of public enquiries: broken boilers, noisy neighbours, missed bins, bills, complaints and safety hazards. People read each one and decide what it is and how urgent it is. That is slow. The records are also messy: blanks, repeated entries, phone numbers in five formats, dates typed three ways, and details buried in the message text.

The company wants to use AI to help, but similar pilots often stall for three reasons: the data isn't clean enough, nobody trusts what the AI says, and nobody can prove it saves money.

## What I built

A pipeline that deals with each of those three problems in turn:

1. **Clean the data first.** Rules fix what is certain (a date in the wrong format, a phone number missing its leading zero). Anything uncertain is left blank and flagged for a person, never guessed. Every change is logged.
2. **Protect people's details.** Names, phone numbers, emails, addresses and postcodes are hidden before any text goes to an AI.
3. **Let AI sort, but keep people in charge.** The AI reads each enquiry and suggests a category, an urgency and a summary. Software rules, not the AI, send every urgent or safety-related case, and anything the AI is unsure about, to a person. Only after a person approves does a reply get drafted.
4. **Record everything.** A diary logs each AI answer and each human decision.
5. **Measure honestly.** I made up the data, so I knew the right answers and could check the AI against them, including how many urgent cases it missed.

## What the numbers say

I tested several ways of doing the triage on the same 300 enquiries, scored against the known answers:

| | Keyword matcher | Claude in a chat | Claude API, first prompt | **Claude API, improved prompt** |
|---|---|---|---|---|
| Category right | 97% | 99% | 84% | **98%** |
| Urgency right | 99% | 98% | 96% | **93%** |
| Urgent enquiries missed without a person seeing them | 0 of 86 | 0 of 86 | 0 of 86 | **0 of 86** |
| Sent to a person | 62% | 34% | 39% | **36%** |
| Estimated triage time saved | 64% | 75% | 73% | **74%** |

The two real-API columns are the ones that count. The first prompt got the category wrong 16% of the time, mostly by calling serious home repairs and neighbour disputes "Safety". I rewrote the prompt with clearer rules and added a rule that sends two-category cases to a person. Category accuracy rose to 98%, but I tuned it on the same 300 enquiries, so I also tested both prompts on 60 new messages I'd written and labelled in advance: 87.5% to 96.4%. The improvement held up, though that set is small and I wrote it myself.

The improved prompt did **not** improve urgency (it slipped from 96% to 93%), mostly by mixing up Low and Medium, which is a matter of policy more than prompting. None of the real-API runs missed an urgent case without a person seeing it.

Data quality: consistency rose from 65% to 100%, and the clean-up introduced 1 wrong value in about 3,300 cells.

**Cautions.** The enquiries are synthetic and template-based, so real ones will be harder. The "human reviewer" is simulated and knows the answers. The time saving rests on assumptions (4 minutes manual triage, 2 minutes to review an AI suggestion, £18 an hour) and falls sharply if review takes longer. The real runs cost about £1.3 in total on assumed prices.

## What I learned

- Clean data matters more than clever AI. Most of the effort went into making the data trustworthy.
- "Human in the loop" has a cost. Sending every urgent case to a person is the safe choice, and it is also what limits the saving.
- A result without its assumptions is just a claim. Every figure here comes with the assumption behind it.
- Testing against a known answer key found real flaws: a mistyped postcode that still looked valid slipped through, and my own leak check had missed a street name left unmasked in lower-case text until I widened it, the first real AI call crashed on a response format my demo mode could never have shown, and tuning a prompt on the same data I scored it on gave a flattering number until I tested on messages it hadn't seen.

## What I would do next

Test on a harder dataset written by someone else, try a larger model on the ambiguous cases, finish the Power BI report, and run the whole thing on Microsoft Fabric, which many UK employers use. Then repeat with real (properly protected) data under a data-protection review.

## How it was built

Built with AI assistance (Claude Code) while I was learning to code. I am now learning Python, SQL and Power BI properly and will rebuild key parts myself.
