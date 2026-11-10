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

## What the numbers say (demo mode)

| | |
|---|---|
| Data completeness / consistency before clean-up | 88% / 65% |
| After clean-up | 90% / 100% |
| Wrong values introduced by the clean-up | 1 in about 3,300 cells |
| Urgent enquiries missed without a person seeing them | 0 of 86 |
| Enquiries sent to a person | 62% |
| Estimated triage time saved | about 64% (20.0 h -> 7.1 h on 300 enquiries) |

**An important caution.** These results come from a simple keyword matcher standing in for the AI, tested on easy, template-based enquiries. They show the pipeline and the measurement work; they do not show how a real AI would perform on real enquiries. The time saving depends on assumptions (4 minutes manual triage, 2 minutes to review an AI suggestion, £18 an hour). If review takes 4 minutes instead of 2, the saving falls to about a third.

## What I learned

- Clean data matters more than clever AI. Most of the effort went into making the data trustworthy.
- "Human in the loop" has a cost. Sending every urgent case to a person is the safe choice, and it is also what limits the saving.
- A result without its assumptions is just a claim. Every figure here comes with the assumption behind it.
- Testing against a known answer key found a real flaw: a mistyped postcode that still looked valid slipped through.

## What I would do next

Run the same pipeline with a real AI model on a harder test set, compare it to the baseline, finish the Power BI report, and run the whole thing on Microsoft Fabric, which many UK employers use. Then repeat with real (properly protected) data under a data-protection review.

## How it was built

Built with AI assistance (Claude Code) while I was learning to code. I am now learning Python, SQL and Power BI properly and will rebuild key parts myself.
