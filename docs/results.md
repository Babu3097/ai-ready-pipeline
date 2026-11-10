# Results

> **READ THIS FIRST - these numbers come from DEMO MODE.** The "AI" here is a simple keyword matcher, not Claude.
> The synthetic enquiries were written from a small set of templates, so a keyword matcher scores very well on them.
> These figures prove the *pipeline and measurement work*. They do **not** show how Claude, or any AI, would do on real, messier enquiries.
> Re-run with a real API key (`python src/triage.py --redo`, then `python src/evaluate.py`) to get Claude's numbers.

## Accuracy against the answer key

| enquiries | category_right | category_accuracy_pct | urgency_right | urgency_accuracy_pct | both_right |
|---|---|---|---|---|---|
| 300 | 291 | 97.0 | 297 | 99.0 | 291 |

### By category

| category | enquiries | correct | accuracy_pct |
|---|---|---|---|
| Complaints | 37 | 31 | 83.8 |
| Waste | 58 | 56 | 96.6 |
| Housing Repairs | 79 | 78 | 98.7 |
| Billing | 48 | 48 | 100.0 |
| Noise | 48 | 48 | 100.0 |
| Safety | 30 | 30 | 100.0 |

### Urgency: what was true vs what the AI said

| true_urgency | ai_said_high | ai_said_medium | ai_said_low | ai_gave_none |
|---|---|---|---|---|
| High | 84 | 0 | 0 | 2 |
| Medium | 0 | 126 | 0 | 0 |
| Low | 0 | 0 | 87 | 1 |

## Urgent cases missed (the most important number)

| truly_urgent | ai_caught | missed_by_ai | missed_and_not_sent_to_a_person |
|---|---|---|---|
| 86 | 84 | 2 | 0 |

*"Missed by AI" includes enquiries with an empty message, which the AI could not read at all. Those are always sent to a person, so none were missed silently.*

## Does the human-review rule work?

| sent_to_person | enquiries | both_right_pct |
|---|---|---|
| 0 | 115 | 100.0 |
| 1 | 185 | 95.1 |

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
| 11 | Complaints | Housing Repairs | Medium | Medium | 1 | I reported a repair six weeks ago and nobody has been in touch. This is my second chaser.  |
| 22 | Complaints | Housing Repairs | Medium | Medium | 1 | Hi, I reported a repair six weeks ago and nobody has been in touch. This is my second chas |
| 37 | Waste |  | Low |  | 1 |  |
| 98 | Complaints | Housing Repairs | Medium | Medium | 1 | I reported a repair six weeks ago and nobody has been in touch. This is my second chaser.  |
| 185 | Complaints | Housing Repairs | Medium | Medium | 1 | Hi, I reported a repair six weeks ago and nobody has been in touch. This is my second chas |
| 232 | Complaints | Housing Repairs | Medium | Medium | 1 | Hi, I reported a repair six weeks ago and nobody has been in touch. This is my second chas |
| 320 | Complaints | Housing Repairs | Medium | Medium | 1 | Hello, I reported a repair six weeks ago and nobody has been in touch. This is my second c |

## Cost

| mode | model | enquiries | input_tokens | output_tokens | total_cost_gbp | cost_per_enquiry_gbp |
|---|---|---|---|---|---|---|
| demo | keyword-rules | 312 | 0 | 0 | 0.0 | 0.0 |

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
| Sent to a person | 185 (62%) |
| Manual time | 20.0 h |
| With AI + review | 7.1 h |
| Time saved | 12.9 h (64%) |
| Staff cost saved | £231.75 |
| Scaled to 10,000 enquiries | about 429 h saved |

### How sensitive is the saving to the review-time assumption?

| Minutes per reviewed case | Hours saved | % saved |
|---|---|---|
| 1 min | 16.0 h | 80% |
| 2 min | 12.9 h | 64% |
| 3 min | 9.8 h | 49% |
| 4 min | 6.7 h | 34% |

The review rate is high because the rules send *every* High-urgency and Safety case to a person. That is deliberate (a human decides anything urgent), and it is the main thing that limits the saving.
