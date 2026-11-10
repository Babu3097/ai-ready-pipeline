# Results

> **READ THIS FIRST - the triage here was done by Claude in a Claude Code chat session, NOT by the Claude API.**
> Claude read each *distinct* masked message once and its answer was applied to every copy of that wording.
> Limits: (1) the same assistant wrote the synthetic data and the triage, so this is **not an independent test**; (2) the API code path in `src/triage.py` is still unproven;
> (3) the synthetic enquiries come from about 34 templates, which is far easier than real enquiries. Treat these as a best case.

## Accuracy against the answer key

| enquiries | category_right | category_accuracy_pct | urgency_right | urgency_accuracy_pct | both_right |
|---|---|---|---|---|---|
| 300 | 297 | 99.0 | 294 | 98.0 | 294 |

### By category

| category | enquiries | correct | accuracy_pct |
|---|---|---|---|
| Waste | 58 | 56 | 96.6 |
| Housing Repairs | 79 | 78 | 98.7 |
| Billing | 48 | 48 | 100.0 |
| Complaints | 37 | 37 | 100.0 |
| Noise | 48 | 48 | 100.0 |
| Safety | 30 | 30 | 100.0 |

### Urgency: what was true vs what the AI said

| true_urgency | ai_said_high | ai_said_medium | ai_said_low | ai_gave_none |
|---|---|---|---|---|
| High | 84 | 0 | 0 | 2 |
| Medium | 3 | 123 | 0 | 0 |
| Low | 0 | 0 | 87 | 1 |

## Urgent cases missed (the most important number)

| truly_urgent | ai_caught | missed_by_ai | missed_and_not_sent_to_a_person |
|---|---|---|---|
| 86 | 84 | 2 | 0 |

*"Missed by AI" includes enquiries with an empty message, which the AI could not read at all. Those are always sent to a person, so none were missed silently.*

## Does the human-review rule work?

| sent_to_person | enquiries | both_right_pct |
|---|---|---|
| 0 | 199 | 100.0 |
| 1 | 101 | 94.1 |

`sent_to_person = 1` are the cases routed to a person. The `0` row is what the AI handled with only a skim: that error rate is what a manager must be willing to accept.

## After human review

| enquiries | final_category_pct | final_urgency_pct | urgent_still_missed |
|---|---|---|---|
| 300 | 100.0 | 100.0 | 0 |

*The reviewer in this run is SIMULATED and knows the right answers, so this is a best case, not evidence about real managers.*

## Where the AI was wrong

| raw_row | true_category | ai_category | true_urgency | ai_urgency | reviewed | text_start |
|---|---|---|---|---|---|---|
| 29 | Housing Repairs |  | High |  | 1 |  |
| 284 | Waste |  | High |  | 1 |  |
| 37 | Waste |  | Low |  | 1 |  |
| 48 | Safety | Safety | Medium | High | 1 | There is a large pothole outside [ADDRESS]. A cyclist fell off this morning. Many thanks,  |
| 75 | Safety | Safety | Medium | High | 1 | To whom it may concern, There is a large pothole outside [ADDRESS], [POSTCODE]. A cyclist  |
| 283 | Safety | Safety | Medium | High | 1 | There is a large pothole outside [ADDRESS]. A cyclist fell off this morning. My number is  |

## Cost

| mode | model | enquiries | input_tokens | output_tokens | total_cost_gbp | cost_per_enquiry_gbp |
|---|---|---|---|---|---|---|
| claude-code-session | claude-sonnet-5-5 (Claude Code session, not the API) | 312 |  |  | 0.0 | 0.0 |

## Time and money saved

**Assumptions (all stated, all changeable at the top of `src/evaluate.py`):**

- Manual triage: **4.0 min** per enquiry (from the project brief)
- With AI, not sent for review: **0.5 min** quick skim
- With AI, sent for review: **2.0 min** to read the summary and decide
- Staff cost: **£18.0/hour** fully loaded
- Triage time only. It does not count the time to actually fix the issue.

| Measure | Value |
|---|---|
| Enquiries | 300 |
| Sent to a person | 101 (34%) |
| Manual time | 20.0 h |
| With AI + review | 5.0 h |
| Time saved | 15.0 h (75%) |
| Staff cost saved | £269.55 |
| Scaled to 10,000 enquiries | about 499 h saved |

### How sensitive is the saving to the review-time assumption?

| Minutes per reviewed case | Hours saved | % saved |
|---|---|---|
| 1 min | 16.7 h | 83% |
| 2 min | 15.0 h | 75% |
| 3 min | 13.3 h | 66% |
| 4 min | 11.6 h | 58% |

The review rate is high because the rules send *every* High-urgency and Safety case to a person. That is deliberate (a human decides anything urgent), and it is the main thing that limits the saving.
