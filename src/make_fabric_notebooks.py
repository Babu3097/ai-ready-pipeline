"""
make_fabric_notebooks.py - writes the three Microsoft Fabric notebooks into fabric/notebooks/.

STATUS: NOT RUN in Fabric. This needs your own Fabric free-trial workspace. The notebooks reuse the same
Python files as the local edition (src/*.py), uploaded to the Lakehouse, so the logic is identical.

Run:  python src/make_fabric_notebooks.py
"""
import json

import db

OUT = db.ROOT / "fabric" / "notebooks"


def md(text):
    return {"cell_type": "markdown", "metadata": {}, "source": text.strip("\n").splitlines(True)}


def code(text):
    return {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [],
            "source": text.strip("\n").splitlines(True)}


def notebook(cells):
    return {"cells": cells, "nbformat": 4, "nbformat_minor": 5,
            "metadata": {"language_info": {"name": "python"}, "kernelspec": {"name": "synapse_pyspark", "display_name": "Synapse PySpark"}}}


SETUP = '''
import sys
ROOT = "/lakehouse/default/Files"          # the attached Lakehouse's Files area
sys.path.insert(0, f"{ROOT}/src")          # so we can import the same .py files as the local edition
%pip install -q anthropic python-dotenv pydantic faker
'''

NB1 = notebook([
    md("""
# 01 - Clean the data (Phase 2 in Fabric)
**Before you run:** create a Lakehouse, attach it as this notebook's default Lakehouse, and upload into its **Files** area:
- the `src/` folder (all `.py` files)
- `data/raw/enquiries_raw.csv`
- `data/ground_truth/` (both CSV files)

This notebook runs the same `data_quality.py` as the local edition, then saves the results as Lakehouse (Delta) tables.
"""),
    code(SETUP),
    code("""
# Optional: regenerate the synthetic data instead of uploading it
# import generate_data; generate_data.main()
"""),
    code("""
import data_quality
data_quality.main()     # reads Files/data/raw, writes Files/data/clean (no API key = demo mode)
"""),
    code("""
print(open(f"{ROOT}/data/clean/quality_report.md").read()[:2500])
"""),
    md("## Save the cleaned data as Delta tables (these appear in the SQL analytics endpoint)"),
    code("""
def csv_to_table(path, table):
    df = (spark.read.option("header", True).option("inferSchema", True)
          .option("multiLine", True).option("escape", '"').csv(path))
    df.write.mode("overwrite").format("delta").saveAsTable(table)
    print(table, df.count(), "rows")

csv_to_table("Files/data/clean/enquiries_clean.csv", "enquiries")
csv_to_table("Files/data/clean/data_quality_log.csv", "data_quality_log")
csv_to_table("Files/data/clean/quality_scores.csv", "quality_scores")
"""),
])

NB2 = notebook([
    md("""
# 02 - AI triage (Phase 4 in Fabric)
Reads the `enquiries` table, triages each **masked** message, and writes `ai_triage` and `audit_log` tables.

**API key:** leave it out and this runs in **demo mode** (free, keyword stand-in). To use Claude, store the key in Azure Key Vault
and read it with `notebookutils.credentials.getSecret(...)`. Never paste a key into a cell. Remember Key Vault and API usage can cost money: delete them when you are finished.
"""),
    code(SETUP),
    code("""
import os
# OPTIONAL real-Claude mode (uncomment, fill in YOUR vault URL and secret name):
# os.environ["ANTHROPIC_API_KEY"] = notebookutils.credentials.getSecret("https://YOUR-VAULT.vault.azure.net/", "anthropic-api-key")

import ai_client, triage
print("DEMO MODE" if ai_client.is_demo() else f"Real Claude: {ai_client.MODEL}")
"""),
    code("""
import pandas as pd
from datetime import datetime

enq = spark.table("enquiries").toPandas()
tracker = ai_client.CostTracker()
triage_rows, audit_rows = [], []
now = lambda: datetime.now().replace(microsecond=0).isoformat(sep=" ")

for _, r in enq.iterrows():
    masked = r["message_masked"] if isinstance(r["message_masked"], str) else ""
    result, error = None, "empty message"
    if masked.strip():
        if ai_client.is_demo():
            result, error = triage.demo_triage(masked), ""
        else:
            result, error = triage.claude_triage(masked, tracker)
    if result is None:
        triage_rows.append(dict(raw_row=int(r["raw_row"]), needs_human_review=1, reason=f"AI triage failed: {error}"))
        audit_rows.append(dict(ts=now(), raw_row=int(r["raw_row"]), actor="ai", action="triage_failed", detail=error))
        continue
    needs, why = triage.apply_review_rules(result)
    triage_rows.append(dict(raw_row=int(r["raw_row"]), category=result["category"], urgency=result["urgency"],
        summary=result["summary"], postcode=r["postcode"], requested_action=result["requested_action"],
        confidence=float(result["confidence"]), needs_human_review=int(needs), reason=result["reason"],
        mode="demo" if ai_client.is_demo() else "claude"))
    audit_rows.append(dict(ts=now(), raw_row=int(r["raw_row"]), actor="ai", action="triaged",
        detail=f"category={result['category']}; urgency={result['urgency']}; confidence={result['confidence']}"))
    if needs:
        audit_rows.append(dict(ts=now(), raw_row=int(r["raw_row"]), actor="system", action="queued_for_review", detail=why))

spark.createDataFrame(pd.DataFrame(triage_rows)).write.mode("overwrite").format("delta").saveAsTable("ai_triage")
spark.createDataFrame(pd.DataFrame(audit_rows)).write.mode("overwrite").format("delta").saveAsTable("audit_log")
print(len(triage_rows), "triaged;", sum(t["needs_human_review"] for t in triage_rows), "sent to review")
print(f"Claude cost so far: about GBP {tracker.cost_gbp:.4f}")
"""),
])

NB3 = notebook([
    md("""
# 03 - Evaluate (Phase 6 in Fabric)
Loads the answer key and runs the key evaluation queries in Spark SQL. The same questions in T-SQL (for the Lakehouse SQL analytics endpoint or a Warehouse) are in `fabric/sql/metrics_queries_tsql.sql`.
"""),
    code("""
def csv_to_table(path, table):
    df = spark.read.option("header", True).option("multiLine", True).option("escape", '"').csv(path)
    df.write.mode("overwrite").format("delta").saveAsTable(table)

csv_to_table("Files/data/ground_truth/enquiries_truth.csv", "ground_truth")
csv_to_table("Files/data/ground_truth/raw_row_map.csv", "raw_row_map")
"""),
    md("### Overall accuracy and urgent cases missed"),
    code("""
display(spark.sql('''
SELECT COUNT(*) AS enquiries,
       SUM(CASE WHEN t.category = g.category THEN 1 ELSE 0 END) AS category_right,
       SUM(CASE WHEN t.urgency  = g.urgency  THEN 1 ELSE 0 END) AS urgency_right
FROM raw_row_map m
JOIN ground_truth g ON g.enquiry_id = m.enquiry_id
JOIN ai_triage t    ON t.raw_row = CAST(m.raw_row AS INT)
WHERE m.row_type = 'original'
'''))
"""),
    code("""
display(spark.sql('''
SELECT COUNT(*) AS truly_urgent,
       SUM(CASE WHEN t.urgency = 'High' THEN 1 ELSE 0 END) AS ai_caught,
       SUM(CASE WHEN t.urgency IS NULL OR t.urgency <> 'High' THEN 1 ELSE 0 END) AS missed_by_ai,
       SUM(CASE WHEN (t.urgency IS NULL OR t.urgency <> 'High') AND t.needs_human_review = 0 THEN 1 ELSE 0 END) AS missed_and_not_reviewed
FROM raw_row_map m
JOIN ground_truth g ON g.enquiry_id = m.enquiry_id
JOIN ai_triage t    ON t.raw_row = CAST(m.raw_row AS INT)
WHERE m.row_type = 'original' AND g.urgency = 'High'
'''))
"""),
    md("""
### Then: Power BI
In the Lakehouse, choose **New semantic model** (select the tables above), then build the report from `powerbi/BUILD_GUIDE.md`. The `human_reviews` step runs locally in this project; in Fabric you would add a Data Pipeline plus a Power Automate or n8n approval step.
"""),
])

for name, nb in [("01_clean_data", NB1), ("02_ai_triage", NB2), ("03_evaluate", NB3)]:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{name}.ipynb").write_text(json.dumps(nb, indent=1), encoding="utf-8")
    print("wrote", f"fabric/notebooks/{name}.ipynb")
