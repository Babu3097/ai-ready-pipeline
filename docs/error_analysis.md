# Where the triage was wrong, and why

Two runs are described. Neither is the Claude API. Re-write this page from `docs/results.md` after any new run.

## Run B: Claude in a Claude Code chat session (current `docs/results.md`)

Claude read each distinct masked message once, from the text only, and its answer was applied to every copy of that wording. The answer key was not looked at.

| What | How many | Why | Was it caught? |
|---|---|---|---|
| Enquiries with an empty message | 3 | No text to triage (the message was blank in the legacy sheet). | Yes. Routed to a person with the reason "AI triage failed: empty message". |
| Pothole enquiries ("a cyclist fell off this morning") labelled **High** urgency; the answer key says **Medium** | 3 | A hazard that has already hurt someone fits the "risk to health or safety" definition. This is a judgement call, and the error is on the safe side. | Yes. Safety cases always go to a person. |

Everything else matched the answer key. Of the 199 enquiries handled with only a skim, **all 199 were right**; of the 101 sent to a person, 94% were fully right before the person looked.

### Why this is not a strong result

- **Not independent.** The same assistant wrote the synthetic data and did the triage, so it knew the kinds of sentences to expect. A fair test needs someone else's data.
- **Easy data.** About 34 templates. Real enquiries are vaguer, longer, contain typos and mix topics.
- **Identical wording got an identical answer.** 35 distinct messages stood in for 312 rows, so 'accuracy' is really a verdict on 34 judgements.
- **The API path is untested.** This used none of the retry, validation or cost code in `src/triage.py`.

## Run A: keyword stand-in (demo mode)

| What | How many | Why | Was it caught? |
|---|---|---|---|
| Complaints about an unanswered repair labelled "Housing Repairs" | 6 of 37 complaints | The message mentions both "repair" and "chaser". One keyword hit each, and the tie was settled by list order, not meaning. | Yes. A tie lowers confidence below 0.70, so a person saw all 6. |
| Enquiries with an empty message | 3 | As above. | Yes. |

The stand-in sent 62% of enquiries to a person; run B sent 34%. The difference is mostly confidence: the keyword rules produce low confidence whenever they are unsure, while run B reported high confidence on clear messages.

## What I would do next with real data

1. Run the API (`python src/triage.py`) and compare it with both runs above.
2. Use a harder test set written by someone else: typos, two problems in one message, very short messages, other languages.
3. Check a weekly sample of the cases handled *without* review to catch drift.
4. Tune the confidence threshold using the cost of a missed urgent case versus the cost of a reviewer's time.
