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

I tested three ways of doing the triage on the same 300 enquiries, scored against the known answers:

| | Keyword matcher | Claude in a chat | **Claude API (real run)** |
|---|---|---|---|
| Category right | 97% | 99% | **84%** |
| Urgency right | 99% | 98% | **96%** |
| Urgent enquiries missed without a person seeing them | 0 of 86 | 0 of 86 | **0 of 86** |
| Sent to a person | 62% | 34% | **39%** |
| Estimated triage time saved | 64% | 75% | **73%** |

The real run is the one that counts, and it scored lower than my earlier tests. That is useful: the earlier tests were not independent, and they flattered the result. Of the cases the AI handled without a person, about 5% were wrong. None were urgent, but the AI was confident about them, which shows why you cannot trust the AI's confidence on its own.

Data quality: consistency rose from 65% to 100%, and the clean-up introduced 1 wrong value in about 3,300 cells.

**Cautions.** The enquiries are synthetic and template-based, so real ones will be harder. The "human reviewer" is simulated and knows the answers. The time saving rests on assumptions (4 minutes manual triage, 2 minutes to review an AI suggestion, £18 an hour) and falls sharply if review takes longer. The real run cost about £0.41 on assumed prices.

## What I learned

- Clean data matters more than clever AI. Most of the effort went into making the data trustworthy.
- "Human in the loop" has a cost. Sending every urgent case to a person is the safe choice, and it is also what limits the saving.
- A result without its assumptions is just a claim. Every figure here comes with the assumption behind it.
- Testing against a known answer key found real flaws: a mistyped postcode that still looked valid slipped through, and my own leak check had missed a street name left unmasked in lower-case text until I widened it, and the first real AI call crashed on a response format my demo mode could never have shown.

## What I would do next

Improve the prompt and the category scheme (a second label for overlapping cases), test on a harder dataset written by someone else, finish the Power BI report, and run the whole thing on Microsoft Fabric, which many UK employers use. Then repeat with real (properly protected) data under a data-protection review.

## How it was built

Built with AI assistance (Claude Code) while I was learning to code. I am now learning Python, SQL and Power BI properly and will rebuild key parts myself.
