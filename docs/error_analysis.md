# Where the triage was wrong, and why (demo-mode run)

These notes describe the run in `docs/results.md`, which used the **keyword stand-in, not Claude**. If you re-run with a real key the errors will be different; update this page from the new `results.md`.

## What went wrong

| What | How many | Why | Was it caught? |
|---|---|---|---|
| Complaints about an unanswered repair labelled "Housing Repairs" | 6 of 37 complaints | The message mentions both "repair" and "chaser". The keyword matcher saw one hit for each category and the tie was settled by list order, not meaning. | Yes. A tie lowers confidence below 0.70, so all 6 went to a person. |
| Enquiries with an empty message | 3 | There was no text to triage (the message was blank in the legacy sheet). | Yes. They are routed to a person with the reason "AI triage failed: empty message". |

## What did not go wrong (and why to be cautious about that)

- Of the 115 enquiries handled with only a skim (not sent to a person), **all 115 were right**.
- No urgent case was missed *silently*: every true "High" case was either labelled High or sent to a person.

This looks excellent, but it is mostly a property of the data. The 300 enquiries were generated from about 35 message templates, and the keyword rules were written by looking at the same kinds of sentences. Real enquiries are vaguer, longer, mix topics and contain typos. Expect real accuracy to be lower and the number of silent mistakes to be higher. That is exactly why the project keeps the confidence threshold, the forced review of urgent and safety cases, and the evaluation against a known answer key.

## What I would do next with real data

1. Run the same pipeline with Claude and compare the two sets of numbers side by side.
2. Add a harder test set: typos, two problems in one message, very short messages, messages in other languages.
3. Review a sample of the cases the AI handled *without* review every week, to catch drift.
4. Tune the confidence threshold using the cost of a missed urgent case versus the cost of a reviewer's time.
