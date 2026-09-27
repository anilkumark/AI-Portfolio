-- Phase 4 dashboard queries. QuickSight itself is a managed AWS BI tool,
-- not something to build in Python -- what a codebase actually owns is
-- the views QuickSight (or any BI tool) points at. Three real views,
-- matching what the design names explicitly: trend, distribution,
-- comparison, plus the regulatory-deadline visibility the design calls
-- for separately from the analytics views.

-- Trend: monthly case volume by source, so a spike is visible at a glance.
CREATE OR REPLACE VIEW omop.v_monthly_case_volume AS
SELECT
    date_trunc('month', COALESCE(de.exposure_start_date, co.condition_start_date)) AS month,
    de.source_type,
    COUNT(DISTINCT de.person_id) AS case_count
FROM omop.drug_exposure de
LEFT JOIN omop.condition_occurrence co ON co.person_id = de.person_id
GROUP BY 1, 2
ORDER BY 1 DESC, 2;

-- Distribution: which suspect products carry the most reports, and how
-- many are serious -- pulled from the operational schema's seriousness
-- result since that's the source of truth for it, joined via source_record_id.
CREATE OR REPLACE VIEW omop.v_product_report_distribution AS
SELECT
    de.drug_source_value AS suspect_product,
    COUNT(DISTINCT de.person_id) AS total_reports,
    COUNT(DISTINCT de.person_id) FILTER (
        WHERE cr.seriousness_result = 'serious'
    ) AS serious_reports
FROM omop.drug_exposure de
LEFT JOIN operational.case_records cr ON cr.case_id::text = de.source_record_id
WHERE de.is_suspect_product = true
GROUP BY 1
ORDER BY total_reports DESC;

-- Comparison: reporting rate for a product's top events against its own
-- historical baseline (same product, prior 12 months vs. most recent month)
-- -- a simple within-product comparison, distinct from the cross-product
-- PRR/ROR signal detection in src/analytics/signal_detection.py.
CREATE OR REPLACE VIEW omop.v_product_event_month_over_month AS
WITH monthly_counts AS (
    SELECT
        de.drug_source_value AS suspect_product,
        co.condition_source_value AS event,
        date_trunc('month', co.condition_start_date) AS month,
        COUNT(DISTINCT de.person_id) AS report_count
    FROM omop.drug_exposure de
    JOIN omop.condition_occurrence co ON co.person_id = de.person_id
    WHERE de.is_suspect_product = true
    GROUP BY 1, 2, 3
)
SELECT
    suspect_product,
    event,
    month,
    report_count,
    LAG(report_count) OVER (
        PARTITION BY suspect_product, event ORDER BY month
    ) AS prior_month_count
FROM monthly_counts
ORDER BY suspect_product, event, month DESC;

-- Regulatory-deadline visibility: cases within the alert window, computed
-- directly (mirrors src/evaluation/deadline_monitor.py's date math, kept
-- here too since a dashboard should be queryable without running the
-- scheduled job first).
CREATE OR REPLACE VIEW operational.v_cases_approaching_deadline AS
SELECT
    case_id,
    received_at,
    (received_at + INTERVAL '15 days')::date AS regulatory_deadline,
    (received_at + INTERVAL '15 days')::date - CURRENT_DATE AS days_remaining,
    submission_status
FROM operational.case_records
WHERE submission_status != 'submitted'
  AND (received_at + INTERVAL '15 days')::date - CURRENT_DATE <= 3
ORDER BY days_remaining ASC;
