# Results

Mode: **real Claude API** (claude, prompt v2). Synthetic, template-based data is easier than real enquiries, so treat these as a best case.

## Accuracy against the answer key

| enquiries | category_right | category_accuracy_pct | urgency_right | urgency_accuracy_pct | both_right |
|---|---|---|---|---|---|
| 300 | 294 | 98.0 | 279 | 93.0 | 276 |

### By category

| category | enquiries | correct | accuracy_pct |
|---|---|---|---|
| Safety | 30 | 27 | 90.0 |
| Waste | 58 | 56 | 96.6 |
| Housing Repairs | 79 | 78 | 98.7 |
| Billing | 48 | 48 | 100.0 |
| Complaints | 37 | 37 | 100.0 |
| Noise | 48 | 48 | 100.0 |

### Urgency: what was true vs what the AI said

| true_urgency | ai_said_high | ai_said_medium | ai_said_low | ai_gave_none |
|---|---|---|---|---|
| High | 83 | 1 | 0 | 2 |
| Medium | 3 | 112 | 11 | 0 |
| Low | 0 | 3 | 84 | 1 |

## Urgent cases missed (the most important number)

| truly_urgent | ai_caught | missed_by_ai | missed_and_not_sent_to_a_person |
|---|---|---|---|
| 86 | 83 | 3 | 0 |

*"Missed by AI" includes enquiries with an empty message, which the AI could not read at all. Those are always sent to a person, so none were missed silently.*

## Does the human-review rule work?

| sent_to_person | enquiries | both_right_pct |
|---|---|---|
| 0 | 191 | 92.7 |
| 1 | 109 | 90.8 |

`sent_to_person = 1` are the cases routed to a person. The `0` row is what the AI handled with only a skim: that error rate is what a manager must be willing to accept.

## After human review

| enquiries | final_category_pct | final_urgency_pct | urgent_still_missed |
|---|---|---|---|
| 300 | 100.0 | 95.3 | 0 |

*The reviewer in this run is SIMULATED and knows the right answers, so this is a best case, not evidence about real managers.*

## Where the AI was wrong

| raw_row | true_category | ai_category | true_urgency | ai_urgency | reviewed | text_start |
|---|---|---|---|---|---|---|
| 29 | Housing Repairs |  | High |  | 1 |  |
| 58 | Safety | Housing Repairs | High | High | 1 | The handrail on the stairs at [ADDRESS] has come away from the wall and an elderly residen |
| 155 | Safety | Housing Repairs | High | High | 1 | The handrail on the stairs at [ADDRESS] has come away from the wall and an elderly residen |
| 277 | Safety | Housing Repairs | High | High | 1 | Hello, The handrail on the stairs at [ADDRESS] has come away from the wall and an elderly  |
| 284 | Waste |  | High |  | 1 |  |
| 323 | Waste | Waste | High | Medium | 1 | Hi, Fly-tipped rubbish including broken glass and needles has been left in the play area n |
| 2 | Waste | Waste | Medium | Low | 0 | An old sofa has been dumped in the alley behind [ADDRESS] for over a week. Regards, [NAME] |
| 37 | Waste |  | Low |  | 1 |  |
| 38 | Complaints | Complaints | Medium | Low | 0 | I am unhappy with how my housing application was handled. Nobody explained the decision. Y |
| 43 | Complaints | Complaints | Medium | Low | 0 | I am unhappy with how my housing application was handled. Nobody explained the decision. |
| 48 | Safety | Safety | Medium | High | 1 | There is a large pothole outside [ADDRESS]. A cyclist fell off this morning. Many thanks,  |
| 75 | Safety | Safety | Medium | High | 1 | To whom it may concern, There is a large pothole outside [ADDRESS], [POSTCODE]. A cyclist  |
| 109 | Noise | Noise | Low | Medium | 0 | The neighbour near [ADDRESS] plays loud music most Saturday afternoons. Not late, but it i |
| 150 | Waste | Waste | Medium | Low | 0 | Hi, An old sofa has been dumped in the alley behind [ADDRESS] for over a week. |
| 214 | Waste | Waste | Medium | Low | 0 | An old sofa has been dumped in the alley behind [ADDRESS] for over a week. My postcode is  |

## Cost

| mode | model | enquiries | input_tokens | output_tokens | total_cost_gbp | cost_per_enquiry_gbp |
|---|---|---|---|---|---|---|
| claude | claude-haiku-5-5 | 312 | 359517 | 85411 | 0.6293 | 0.00202 |

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
| Sent to a person | 109 (36%) |
| Manual time | 20.0 h |
| With AI + review | 5.2 h |
| Time saved | 14.8 h (74%) |
| Staff cost saved | £265.32 |
| Scaled to 10,000 enquiries | about 493 h saved |

### How sensitive is the saving to the review-time assumption?

| Minutes per reviewed case | Hours saved | % saved |
|---|---|---|
| 1 min | 16.6 h | 83% |
| 2 min | 14.8 h | 74% |
| 3 min | 13.0 h | 65% |
| 4 min | 11.1 h | 56% |

The review rate is high because the rules send *every* High-urgency and Safety case to a person. That is deliberate (a human decides anything urgent), and it is the main thing that limits the saving.
