-- metrics_queries_tsql.sql : the same manager questions in T-SQL (Fabric Lakehouse SQL analytics endpoint / Warehouse).
-- STATUS: translated by hand from sql/metrics_queries.sql, NOT run in Fabric.
-- Main differences from the SQLite version:
--   strftime(...)          -> LEFT(received_date, 7)
--   SUBSTR / LIMIT n       -> LEFT(...) / SELECT TOP (n)
--   SUM(a = b)             -> SUM(CASE WHEN a = b THEN 1 ELSE 0 END)   (T-SQL has no true/false numbers)
--   x IS NOT 'High'        -> (x IS NULL OR x <> 'High')

-- Q1: Enquiries per category
SELECT COALESCE(NULLIF(e.category, ''), t.category, 'Unknown') AS category,
       COUNT(*) AS enquiries,
       ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM enquiries), 1) AS pct_of_total
FROM enquiries e
LEFT JOIN ai_triage t ON t.raw_row = e.raw_row
GROUP BY COALESCE(NULLIF(e.category, ''), t.category, 'Unknown')
ORDER BY enquiries DESC;

-- Q2: Enquiries per month and channel
SELECT LEFT(received_date, 7) AS month, channel, COUNT(*) AS enquiries
FROM enquiries
WHERE received_date IS NOT NULL AND channel IS NOT NULL
GROUP BY LEFT(received_date, 7), channel
ORDER BY month, channel;

-- Q3: Urgent cases still open
SELECT e.case_ref,
       COALESCE(NULLIF(e.category, ''), t.category, 'Unknown') AS category,
       COALESCE(t.urgency, e.urgency) AS urgency,
       e.received_date, t.summary
FROM enquiries e
LEFT JOIN ai_triage t ON t.raw_row = e.raw_row
WHERE e.status = 'Open' AND COALESCE(t.urgency, e.urgency) = 'High'
ORDER BY e.received_date;

-- Q4: Average handling time per category (closed cases)
SELECT COALESCE(NULLIF(e.category, ''), t.category, 'Unknown') AS category,
       COUNT(e.handling_mins) AS closed_cases,
       ROUND(AVG(CAST(e.handling_mins AS FLOAT)), 1) AS avg_minutes
FROM enquiries e
LEFT JOIN ai_triage t ON t.raw_row = e.raw_row
WHERE e.status = 'Closed' AND e.handling_mins IS NOT NULL
GROUP BY COALESCE(NULLIF(e.category, ''), t.category, 'Unknown')
ORDER BY avg_minutes DESC;

-- Q5: Review load
SELECT COUNT(*) AS triaged,
       SUM(needs_human_review) AS sent_to_review,
       ROUND(100.0 * SUM(needs_human_review) / COUNT(*), 1) AS review_rate_pct
FROM ai_triage;

-- E1: Urgent cases missed (evaluation; needs the ground_truth and raw_row_map tables)
SELECT COUNT(*) AS truly_urgent,
       SUM(CASE WHEN t.urgency = 'High' THEN 1 ELSE 0 END) AS ai_caught,
       SUM(CASE WHEN t.urgency IS NULL OR t.urgency <> 'High' THEN 1 ELSE 0 END) AS missed_by_ai,
       SUM(CASE WHEN (t.urgency IS NULL OR t.urgency <> 'High') AND t.needs_human_review = 0 THEN 1 ELSE 0 END) AS missed_and_not_reviewed
FROM raw_row_map m
JOIN ground_truth g ON g.enquiry_id = m.enquiry_id
JOIN ai_triage t    ON t.raw_row = CAST(m.raw_row AS INT)
WHERE m.row_type = 'original' AND g.urgency = 'High';
