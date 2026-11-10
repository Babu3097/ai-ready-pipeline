-- metrics_queries.sql : the questions a contract manager asks, answered in SQL.
-- Run them all with:  python src/run_queries.py
-- Plain-English reading guide:
--   SELECT   = which columns to show
--   FROM     = which table
--   JOIN     = bring in matching rows from another table
--   WHERE    = keep only rows that match a condition
--   GROUP BY = make one result row per group (e.g. per category)
--   COUNT, AVG, ROUND = count rows, average, round a number
-- "Best category" below = the cleaned category, or the AI's if the clean sheet had none.

-- Q1: How many enquiries do we get in each category?
SELECT COALESCE(e.category, t.category, 'Unknown') AS category,
       COUNT(*)                                     AS enquiries,
       ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM enquiries), 1) AS pct_of_total
FROM enquiries e
LEFT JOIN ai_triage t ON t.raw_row = e.raw_row
GROUP BY 1
ORDER BY enquiries DESC;

-- Q2: How many enquiries per month, and by which channel?
SELECT strftime('%Y-%m', received_date) AS month,
       channel,
       COUNT(*) AS enquiries
FROM enquiries
WHERE received_date IS NOT NULL AND channel IS NOT NULL
GROUP BY 1, 2
ORDER BY 1, 2;

-- Q3: Which urgent cases are still waiting (open and High urgency)?
SELECT e.case_ref,
       COALESCE(e.category, t.category, 'Unknown') AS category,
       COALESCE(t.urgency, e.urgency)              AS urgency,
       e.received_date,
       t.summary
FROM enquiries e
LEFT JOIN ai_triage t ON t.raw_row = e.raw_row
WHERE e.status = 'Open'
  AND COALESCE(t.urgency, e.urgency) = 'High'
ORDER BY e.received_date;

-- Q4: What is the average handling time per category? (closed cases, legacy times)
SELECT COALESCE(e.category, t.category, 'Unknown') AS category,
       COUNT(e.handling_mins)                      AS closed_cases,
       ROUND(AVG(e.handling_mins), 1)              AS avg_minutes
FROM enquiries e
LEFT JOIN ai_triage t ON t.raw_row = e.raw_row
WHERE e.status = 'Closed' AND e.handling_mins IS NOT NULL
GROUP BY 1
ORDER BY avg_minutes DESC;

-- Q5: Contract check - what share of closed cases met a handling target? (targets are ASSUMED: High 20, Medium 12, Low 8 minutes)
SELECT COALESCE(t.urgency, e.urgency) AS urgency,
       COUNT(*) AS closed_cases,
       SUM(CASE WHEN e.handling_mins <= CASE COALESCE(t.urgency, e.urgency)
                                           WHEN 'High' THEN 20 WHEN 'Medium' THEN 12 ELSE 8 END
                THEN 1 ELSE 0 END) AS within_target,
       ROUND(100.0 * SUM(CASE WHEN e.handling_mins <= CASE COALESCE(t.urgency, e.urgency)
                                           WHEN 'High' THEN 20 WHEN 'Medium' THEN 12 ELSE 8 END
                THEN 1 ELSE 0 END) / COUNT(*), 1) AS pct_within_target
FROM enquiries e
LEFT JOIN ai_triage t ON t.raw_row = e.raw_row
WHERE e.status = 'Closed' AND e.handling_mins IS NOT NULL AND COALESCE(t.urgency, e.urgency) IS NOT NULL
GROUP BY 1
ORDER BY CASE COALESCE(t.urgency, e.urgency) WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END;

-- Q6: How healthy is the data? (rows by quality status)
SELECT quality_status, COUNT(*) AS rows_
FROM enquiries
GROUP BY quality_status
ORDER BY rows_ DESC;

-- Q7: What did the clean-up do most often?
SELECT issue, action, COUNT(*) AS times
FROM data_quality_log
GROUP BY issue, action
ORDER BY times DESC
LIMIT 10;

-- Q8: Which enquiries look like repeats of an earlier one (flagged for a person)?
SELECT case_ref, possible_duplicate_of, received_date, SUBSTR(message, 1, 70) AS message_start
FROM enquiries
WHERE possible_duplicate_of IS NOT NULL
ORDER BY received_date
LIMIT 15;

-- Q9: How much does the AI send to a person, and how much has been decided?
SELECT COUNT(*)                                                        AS triaged,
       SUM(needs_human_review)                                         AS sent_to_review,
       ROUND(100.0 * SUM(needs_human_review) / COUNT(*), 1)            AS review_rate_pct,
       (SELECT COUNT(DISTINCT raw_row) FROM human_reviews)             AS decided_by_a_person
FROM ai_triage;
