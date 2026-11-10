# Building the Power BI report (Phase 7)

**Status:** the data and the design are ready, but **no `.pbix` file exists yet**. Power BI Desktop only runs on Windows and this project was built on a Mac. Pictures of the four pages (drawn with Python from the same data) are in `docs/screenshots/`; they show what to build. They are not Power BI screenshots.

Do this on a Windows PC, or in the Power BI service (app.powerbi.com) using a free/trial account, which also works from a Mac browser. Save the finished file as `powerbi/northfield_report.pbix` and take real screenshots into `docs/screenshots/`.

## 1. Load the data

Get data -> Text/CSV, load these from `powerbi/data/` (run `python src/evaluate.py` first to refresh them):

| File | What it is |
|---|---|
| `triage_facts.csv` | One row per enquiry: dates, channel, AI answer, human decision, true answer, correct flags |
| `quality_scores.csv` | Before/after data quality scores |
| `eval_summary.csv` | Headline numbers (accuracy, review rate, time saved, cost) |
| `value_sensitivity.csv` | Time saved if review takes 1-4 minutes |
| `audit_log.csv` | Every AI and human step |

In Power Query, set `received_date` to Date, `confidence` and `cost_gbp` to Decimal, `needs_human_review` to Whole number.

## 2. Measures (DAX)

Create these in a table called `_Measures` (Home -> Enter data -> empty table, then New measure).

```
Enquiries = COUNTROWS(triage_facts)

Scored Enquiries = CALCULATE([Enquiries], triage_facts[row_type] = "original")

Review Rate = DIVIDE(CALCULATE([Enquiries], triage_facts[needs_human_review] = 1), [Enquiries])

Category Accuracy =
    DIVIDE(CALCULATE(SUM(triage_facts[category_correct]), triage_facts[row_type] = "original"), [Scored Enquiries])

Urgency Accuracy =
    DIVIDE(CALCULATE(SUM(triage_facts[urgency_correct]), triage_facts[row_type] = "original"), [Scored Enquiries])

Truly Urgent = CALCULATE([Enquiries], triage_facts[row_type] = "original", triage_facts[true_urgency] = "High")

Urgent Missed Silently =
    CALCULATE([Enquiries], triage_facts[row_type] = "original", triage_facts[true_urgency] = "High",
              triage_facts[ai_urgency] <> "High", triage_facts[needs_human_review] = 0)

Urgent Open = CALCULATE([Enquiries], triage_facts[status] = "Open", triage_facts[urgency_final] = "High")

Avg Handling Mins = CALCULATE(AVERAGE(triage_facts[handling_mins]), triage_facts[status] = "Closed")

Hours Saved = LOOKUPVALUE(eval_summary[value], eval_summary[metric], "Time saved")

Cost Saved GBP = LOOKUPVALUE(eval_summary[value], eval_summary[metric], "Staff cost saved")
```

(`ai_urgency <> "High"` is true for blanks in DAX only if you handle them; if the numbers look off, compare with `Q4` in `sql/evaluation_queries.sql`, which is the reference answer.)

## 3. The four pages

Keep each page readable in 30 seconds: big numbers on top, two charts underneath, plain titles.

| Page | Top row (cards) | Charts |
|---|---|---|
| **1 Overview** | Enquiries, Review Rate, Urgent Open, Avg Handling Mins | Bar: enquiries by `category_final`. Stacked column: enquiries by `month` and `channel` |
| **2 Data quality** | (none) | Clustered column from `quality_scores` (before vs after per metric). A text box: "Values we can't trust are blanked, never guessed" |
| **3 AI performance** | Category Accuracy, Urgency Accuracy, Review Rate, Urgent Missed Silently (turn the number green at 0) | Matrix of `true_urgency` (rows) vs `ai_urgency` (columns) with count. Column chart: accuracy for `needs_human_review` 0 vs 1 |
| **4 Value** | Hours Saved, Cost Saved GBP, AI cost | Column: manual vs AI+review hours (from `eval_summary`). Line: `value_sensitivity` pct_saved by review_minutes. Text box listing the assumptions |

Add a **slicer** for `month` and `channel` on page 1.

## 4. Honest labelling

- If the data came from demo mode, put a visible label on pages 3 and 4: "Demo mode: keyword stand-in, not Claude".
- Show the assumptions on the value page. A number without its assumption is a claim, not a result.

## 5. Fabric edition

In the Fabric edition, connect the same report to the Lakehouse/Warehouse tables instead of CSV files (Get data -> OneLake catalog). The measures stay the same.
