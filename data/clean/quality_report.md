# Data quality report - Northfield Services (synthetic data)

Everything here is made-up data. Scores compare the raw legacy sheet with the cleaned table.

## Scores: before vs after

| Measure | Before | After | What it means |
|---|---|---|---|
| Completeness | 87.5% | 90.4% | Share of the 10 key fields that hold a real value |
| Uniqueness | 96.9% | 100.0% | Share of rows that are not exact repeats |
| Validity | 95.5% | 100.0% | Share of filled-in values that are real, readable values |
| Consistency | 64.9% | 100.0% | Share of filled-in values already in the one standard format |

**Read this honestly:** validity and consistency reach ~100% *by design*, because a value that cannot be trusted is emptied and flagged rather than guessed. The trade-off shows in completeness, which cannot return to 100% without inventing data.

## What happened to the rows

- Raw rows: **330**
- Blank rows removed: **8**
- Exact duplicate rows removed: **10** (found 10 literal repeats in the raw sheet)
- Cleaned rows: **312**
- Possible near-duplicates **flagged, not deleted**: **12** (a person decides)

Row status after clean-up:
- fixed: 231
- needs_review: 79
- clean: 2

## What the rules changed (from the log)

| Issue | Action | Count |
|---|---|---|
| date_format_standardised | fixed | 229 |
| status_format_standardised | fixed | 126 |
| urgency_format_standardised | fixed | 120 |
| phone_format_standardised | fixed | 106 |
| category_wording_standardised | fixed | 104 |
| channel_format_standardised | fixed | 99 |
| units_removed | fixed | 61 |
| extra_whitespace_trimmed | fixed | 49 |
| name_format_standardised | fixed | 41 |
| category_unresolved_by_rules | ai_suggested | 41 |
| email_found_in_message_text | filled_from_message | 28 |
| phone_found_in_message_text | filled_from_message | 26 |
| phone_placeholder | treated_as_missing | 25 |
| postcode_found_in_message_text | filled_from_message | 24 |
| phone_unreadable | cleared_invalid | 22 |
| lost_leading_zero_restored | fixed | 21 |
| email_unreadable | cleared_invalid | 19 |
| phone_hidden_blank | treated_as_missing | 18 |
| postcode_format_standardised | fixed | 18 |
| case_ref_format_standardised | fixed | 18 |
| category_hidden_blank | treated_as_missing | 15 |
| name_hidden_blank | treated_as_missing | 15 |
| email_placeholder | treated_as_missing | 13 |
| email_format_standardised | fixed | 12 |
| near_duplicate | flagged | 12 |
| postcode_placeholder | treated_as_missing | 12 |
| email_hidden_blank | treated_as_missing | 11 |
| category_unmappable | cleared_invalid | 10 |
| channel_hidden_blank | treated_as_missing | 10 |
| exact_duplicate | removed | 10 |
| postcode_hidden_blank | treated_as_missing | 10 |
| date_partial | cleared_invalid | 9 |
| name_placeholder | treated_as_missing | 9 |
| blank_row | removed | 8 |
| phone_and_postcode_swapped | fixed | 8 |
| name_and_email_swapped | fixed | 8 |
| postcode_unreadable | cleared_invalid | 7 |
| shifted_columns | fixed | 6 |
| status_hidden_blank | treated_as_missing | 6 |
| urgency_hidden_blank | treated_as_missing | 5 |
| date_placeholder | treated_as_missing | 4 |
| category_placeholder | treated_as_missing | 1 |

## The AI step

- Mode: **demo mode (keyword matcher, no API key)**
- Rows where rules could not set a category: **41**; AI suggested a category for **41**. Suggestions sit in their own column and are flagged for a human.
- Only the *masked* message (no names, phones, emails, addresses, postcodes) is ever sent.

## Checked against the answer key

Compared 300 cleaned rows with the known-correct data. "Wrong" is the number to watch: a cleaner that confidently writes bad data is worse than one that leaves a gap.

| Field | Correct | Left blank & flagged | Wrong |
|---|---|---|---|
| case_ref | 294 | 6 | 0 |
| received_date | 285 | 15 | 0 |
| channel | 278 | 22 | 0 |
| name | 270 | 30 | 0 |
| email | 271 | 29 | 0 |
| phone | 239 | 61 | 0 |
| postcode | 277 | 22 | 1 |
| category | 260 | 40 | 0 |
| urgency | 235 | 65 | 0 |
| status | 294 | 6 | 0 |
| handling_mins | 268 | 32 | 0 |

- Exact duplicates still in the data: **0**
- Near-duplicates caught: **12 of 12**; real enquiries wrongly flagged as duplicates: **0**
- Personal details leaking into the masked text: **0** 
- AI category suggestions that were right: **39 of 40**

## Assumptions and limits

- Dates like 04/11/2025 are read as **day/month** (UK).
- Names typed in all capitals or lower case are title-cased; names like McDonald can lose their inner capital.
- A phone/email/postcode found in the free text is used only if there is exactly one clear candidate. It is logged as `filled_from_message`.
- A postcode is accepted if its shape is right and its area (e.g. M, SK, OL) exists. We have no full postcode database, so a typo that still looks real would pass.
- Everything is synthetic; real data would need a data-protection review before any of this ran on it.
