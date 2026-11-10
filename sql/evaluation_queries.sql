-- evaluation_queries.sql : how good is the AI triage, checked against the answer key?
-- Only the 300 "original" enquiries are scored (repeat submissions and blank rows are left out).
-- Run with:  python src/run_queries.py sql/evaluation_queries.sql   (or python src/evaluate.py)
-- Reading guide: g = ground truth (the right answer), t = the AI's answer, h = a person's decision.

-- Q1: Overall accuracy - how often did the AI get it right?
SELECT COUNT(*)                                                                   AS enquiries,
       SUM(t.category = g.category)                                               AS category_right,
       ROUND(100.0 * SUM(t.category = g.category) / COUNT(*), 1)                  AS category_accuracy_pct,
       SUM(t.urgency = g.urgency)                                                 AS urgency_right,
       ROUND(100.0 * SUM(t.urgency = g.urgency) / COUNT(*), 1)                    AS urgency_accuracy_pct,
       SUM(t.category = g.category AND t.urgency = g.urgency)                     AS both_right
FROM raw_row_map m
JOIN ground_truth g ON g.enquiry_id = m.enquiry_id
JOIN ai_triage t    ON t.raw_row = m.raw_row
WHERE m.row_type = 'original';

-- Q2: Accuracy per category (of all enquiries that truly belong to it, how many did the AI label correctly?)
SELECT g.category,
       COUNT(*)                                                     AS enquiries,
       SUM(t.category = g.category)                                 AS correct,
       ROUND(100.0 * SUM(t.category = g.category) / COUNT(*), 1)    AS accuracy_pct
FROM raw_row_map m
JOIN ground_truth g ON g.enquiry_id = m.enquiry_id
JOIN ai_triage t    ON t.raw_row = m.raw_row
WHERE m.row_type = 'original'
GROUP BY g.category
ORDER BY accuracy_pct;

-- Q3: Urgency confusion table (rows = true urgency, columns = what the AI said)
SELECT g.urgency AS true_urgency,
       SUM(t.urgency = 'High')   AS ai_said_high,
       SUM(t.urgency = 'Medium') AS ai_said_medium,
       SUM(t.urgency = 'Low')    AS ai_said_low,
       SUM(t.urgency IS NULL)    AS ai_gave_none
FROM raw_row_map m
JOIN ground_truth g ON g.enquiry_id = m.enquiry_id
JOIN ai_triage t    ON t.raw_row = m.raw_row
WHERE m.row_type = 'original'
GROUP BY g.urgency
ORDER BY CASE g.urgency WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END;

-- Q4: THE KEY NUMBER - urgent cases missed. (true High urgency, but the AI did not say High)
SELECT COUNT(*)                                                              AS truly_urgent,
       SUM(t.urgency = 'High')                                               AS ai_caught,
       SUM(t.urgency IS NOT 'High')                                          AS missed_by_ai,
       SUM(t.urgency IS NOT 'High' AND t.needs_human_review = 0)             AS missed_and_not_sent_to_a_person
FROM raw_row_map m
JOIN ground_truth g ON g.enquiry_id = m.enquiry_id
JOIN ai_triage t    ON t.raw_row = m.raw_row
WHERE m.row_type = 'original' AND g.urgency = 'High';

-- Q5: Workload and trust - how many go to a person, and how accurate are the ones that do NOT?
SELECT t.needs_human_review                                                   AS sent_to_person,
       COUNT(*)                                                               AS enquiries,
       ROUND(100.0 * SUM(t.category = g.category AND t.urgency = g.urgency) / COUNT(*), 1) AS both_right_pct
FROM raw_row_map m
JOIN ground_truth g ON g.enquiry_id = m.enquiry_id
JOIN ai_triage t    ON t.raw_row = m.raw_row
WHERE m.row_type = 'original'
GROUP BY t.needs_human_review;

-- Q6: After the human review step - final answers (a person's if they decided, otherwise the AI's)
-- NOTE: in the demo the reviewer is a SIMULATED stand-in who knows the answers, so this is a best case.
SELECT COUNT(*)                                                                       AS enquiries,
       ROUND(100.0 * SUM(COALESCE(h.final_category, t.category) = g.category) / COUNT(*), 1) AS final_category_pct,
       ROUND(100.0 * SUM(COALESCE(h.final_urgency, t.urgency) = g.urgency) / COUNT(*), 1)   AS final_urgency_pct,
       SUM(g.urgency = 'High' AND COALESCE(h.final_urgency, t.urgency) IS NOT 'High')       AS urgent_still_missed
FROM raw_row_map m
JOIN ground_truth g ON g.enquiry_id = m.enquiry_id
JOIN ai_triage t    ON t.raw_row = m.raw_row
LEFT JOIN human_reviews h ON h.raw_row = m.raw_row AND h.decision IN ('approved', 'edited')
WHERE m.row_type = 'original';

-- Q7: Where was the AI wrong? (first 15)
SELECT m.raw_row, g.category AS true_category, t.category AS ai_category,
       g.urgency AS true_urgency, t.urgency AS ai_urgency, t.needs_human_review AS reviewed,
       SUBSTR(e.message_masked, 1, 90) AS text_start
FROM raw_row_map m
JOIN ground_truth g ON g.enquiry_id = m.enquiry_id
JOIN ai_triage t    ON t.raw_row = m.raw_row
JOIN enquiries e    ON e.raw_row = m.raw_row
WHERE m.row_type = 'original'
  AND (t.category IS NOT g.category OR t.urgency IS NOT g.urgency)
ORDER BY g.urgency = 'High' DESC, m.raw_row
LIMIT 15;

-- Q8: What did the AI cost?
SELECT mode, model,
       COUNT(*)                         AS enquiries,
       SUM(input_tokens)                AS input_tokens,
       SUM(output_tokens)               AS output_tokens,
       ROUND(SUM(cost_gbp), 4)          AS total_cost_gbp,
       ROUND(SUM(cost_gbp) / COUNT(*), 5) AS cost_per_enquiry_gbp
FROM ai_triage
GROUP BY mode, model;
