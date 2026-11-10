# Where the triage was wrong, and why

Three runs are described. **Run C (the real Claude API, Haiku 5.5) is the one to rely on.** Re-write this page from `docs/results.md` after any new run.

## Run C: Claude API (`claude-haiku-5-5`), 312 calls, about £0.41

Overall: category 84.3%, urgency 96.3%, 0 urgent cases missed without a person seeing them, 39% sent to a person.

| What | How many | Why | Was it caught? |
|---|---|---|---|
| **Safety** chosen for a High-urgency case the key files elsewhere: water through a ceiling (Housing Repairs), needles and glass in a play area (Waste), violent shouting with children at risk (Noise) | 32 | Claude treats real risk to people as "Safety". Reasonable people could agree; the single-label scheme forces a choice between overlapping categories. | Yes. Safety cases always go to a person. |
| "Confusing website / can't find the bulky-waste form" labelled Waste, key says Complaints | 7 | Genuinely ambiguous: part complaint, part waste request. Claude's confidence was 0.80-0.85, high for an ambiguous message. | **No.** Handled with only a skim. |
| Complaint about a repair with no follow-up labelled Housing Repairs | 5 | The message mentions a repair and complains about service. | 4 of 5 yes (low confidence or review); 1 slipped through. |
| Pothole with a cyclist fall rated High, key says Medium | 4 | Judgement call, safe side. | Yes. |
| Council-tax double charge rated Low (key: Medium); dumped sofa rated Low (key: Medium) | 2 | Claude judged them routine. | **No.** |
| Medium Waste cases rated High | 2 | Over-cautious. | Yes. |
| Empty messages | 3 | No text to triage. | Yes. |

**The number to worry about:** of the 184 enquiries handled with only a skim, 10 were wrong (5.4%). None was urgent. All were ambiguous or low-stakes, but Claude reported 0.80-0.95 confidence on them, so **confidence alone is not a reliable guard**. That is the argument for sampling un-reviewed cases every week.

**Possible fixes (not yet tried):** allow a secondary category for overlapping cases; add examples of the tricky cases to the prompt; send any message that touches two categories to a person; try a larger model on the ambiguous ones.

## Why run C is lower than runs A and B

- Run A (keyword stand-in) and run B (me, in a chat) both scored 97-99% on category. A was tuned to the same wording the templates use. B was not independent: the same assistant wrote the data and did the triage, and it read 35 distinct messages once rather than 312 one at a time. Real model, real API, no inside knowledge: 84%.
- Lesson: a score you can't separate from how the data was made isn't worth much. Quote the independent run.

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
