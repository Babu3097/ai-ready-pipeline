# Results

Mode: **real Claude API** (claude). Synthetic, template-based data is easier than real enquiries, so treat these as a best case.

## Accuracy against the answer key

| enquiries | category_right | category_accuracy_pct | urgency_right | urgency_accuracy_pct | both_right |
|---|---|---|---|---|---|
| 300 | 253 | 84.3 | 289 | 96.3 | 245 |

### By category

| category | enquiries | correct | accuracy_pct |
|---|---|---|---|
| Complaints | 37 | 25 | 67.6 |
| Waste | 58 | 44 | 75.9 |
| Housing Repairs | 79 | 64 | 81.0 |
| Noise | 48 | 42 | 87.5 |
| Billing | 48 | 48 | 100.0 |
| Safety | 30 | 30 | 100.0 |

### Urgency: what was true vs what the AI said

| true_urgency | ai_said_high | ai_said_medium | ai_said_low | ai_gave_none |
|---|---|---|---|---|
| High | 84 | 0 | 0 | 2 |
| Medium | 6 | 118 | 2 | 0 |
| Low | 0 | 0 | 87 | 1 |

## Urgent cases missed (the most important number)

| truly_urgent | ai_caught | missed_by_ai | missed_and_not_sent_to_a_person |
|---|---|---|---|
| 86 | 84 | 2 | 0 |

*"Missed by AI" includes enquiries with an empty message, which the AI could not read at all. Those are always sent to a person, so none were missed silently.*

## Does the human-review rule work?

| sent_to_person | enquiries | both_right_pct |
|---|---|---|
| 0 | 184 | 94.6 |
| 1 | 116 | 61.2 |

`sent_to_person = 1` are the cases routed to a person. The `0` row is what the AI handled with only a skim: that error rate is what a manager must be willing to accept.

## After human review

| enquiries | final_category_pct | final_urgency_pct | urgent_still_missed |
|---|---|---|---|
| 300 | 97.3 | 99.3 | 0 |

*The reviewer in this run is SIMULATED and knows the right answers, so this is a best case, not evidence about real managers.*

## Where the AI was wrong

| raw_row | true_category | ai_category | true_urgency | ai_urgency | reviewed | text_start |
|---|---|---|---|---|---|---|
| 1 | Housing Repairs | Safety | High | High | 1 | Hi, Water is pouring through my bedroom ceiling at [ADDRESS] from the flat above and it is |
| 7 | Housing Repairs | Safety | High | High | 1 | Water is pouring through my bedroom ceiling at [ADDRESS] from the flat above and it is get |
| 19 | Housing Repairs | Safety | High | High | 1 | Water is pouring through my bedroom ceiling at [ADDRESS] from the flat above and it is get |
| 20 | Waste | Safety | High | High | 1 | Fly-tipped rubbish including broken glass and needles has been left in the play area near  |
| 29 | Housing Repairs |  | High |  | 1 |  |
| 34 | Noise | Safety | High | High | 1 | Violent shouting and banging from the flat next to [ADDRESS] most nights. I am scared for  |
| 35 | Waste | Safety | High | High | 1 | Good morning, Fly-tipped rubbish including broken glass and needles has been left in the p |
| 46 | Waste | Safety | High | High | 1 | To whom it may concern, Fly-tipped rubbish including broken glass and needles has been lef |
| 54 | Housing Repairs | Safety | High | High | 1 | Water is pouring through my bedroom ceiling at [ADDRESS] from the flat above and it is get |
| 62 | Housing Repairs | Safety | High | High | 1 | Water is pouring through my bedroom ceiling at [ADDRESS] from the flat above and it is get |
| 72 | Waste | Safety | High | High | 1 | Fly-tipped rubbish including broken glass and needles has been left in the play area near  |
| 99 | Noise | Safety | High | High | 1 | Violent shouting and banging from the flat next to [ADDRESS] most nights. I am scared for  |
| 112 | Noise | Safety | High | High | 1 | Good morning, Violent shouting and banging from the flat next to [ADDRESS] most nights. I  |
| 114 | Noise | Safety | High | High | 1 | Hello, Violent shouting and banging from the flat next to [ADDRESS] most nights. I am scar |
| 135 | Housing Repairs | Safety | High | High | 1 | Hello, Water is pouring through my bedroom ceiling at [ADDRESS] from the flat above and it |

## Cost

| mode | model | enquiries | input_tokens | output_tokens | total_cost_gbp | cost_per_enquiry_gbp |
|---|---|---|---|---|---|---|
| claude | claude-haiku-5-5 | 312 | 140709 | 73171 | 0.4053 | 0.0013 |

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
| Sent to a person | 116 (39%) |
| Manual time | 20.0 h |
| With AI + review | 5.4 h |
| Time saved | 14.6 h (73%) |
| Staff cost saved | £262.39 |
| Scaled to 10,000 enquiries | about 487 h saved |

### How sensitive is the saving to the review-time assumption?

| Minutes per reviewed case | Hours saved | % saved |
|---|---|---|
| 1 min | 16.5 h | 83% |
| 2 min | 14.6 h | 73% |
| 3 min | 12.7 h | 63% |
| 4 min | 10.7 h | 54% |

The review rate is high because the rules send *every* High-urgency and Safety case to a person. That is deliberate (a human decides anything urgent), and it is the main thing that limits the saving.
