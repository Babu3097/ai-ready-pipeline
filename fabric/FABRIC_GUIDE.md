# Microsoft Fabric edition (Phase 8)

**Status: prepared, NOT run.** Fabric needs your own Microsoft account and trial workspace, so none of this has been executed. The notebooks reuse the exact same Python files as the local edition, so the logic is already tested; what is untested is the Fabric-specific plumbing (file paths, Delta tables, SQL endpoint).

## Trial terms (checked on 10 Nov 2026 against Microsoft Learn)

- The Fabric trial lasts **60 days** and gives a trial capacity of 64 capacity units and up to 1 TB of OneLake storage. It does not extend if you enlarge it.
- Starting it from the Fabric app (app.fabric.microsoft.com -> Account manager -> Start trial) needs **no credit card**. If you sign up with a personal email, Microsoft's guide says an Azure account is needed first, and Azure may ask for a phone number and payment method for verification. Read the prompts before you continue.
- When the trial ends, workspace items other than Power BI ones **stop working and are removed**; you have about 7 days after expiry to save things. So export your notebooks and screenshots before day 60.
- Terms change. Re-check https://learn.microsoft.com/en-us/fabric/fundamentals/fabric-trial before you start.

## Cost safety (read before clicking anything)

- Do **not** buy a Fabric capacity or an Azure subscription tier. The trial is enough.
- Run it in **demo mode** (no API key). That costs nothing. Only add Claude if you want real numbers.
- If you use Azure Key Vault for the key, delete the vault when finished.
- Final step: delete the workspace (or cancel the trial from Account manager) and confirm no Azure resources remain in the Azure portal.

## Steps

1. **Start the trial** and create a workspace named `northfield-pipeline`, with the trial capacity assigned.
2. **Create a Lakehouse** called `northfield_lakehouse`.
3. **Upload files** into the Lakehouse **Files** area, keeping this layout:
   ```
   Files/src/            (all .py files from this repo's src/ folder)
   Files/data/raw/enquiries_raw.csv
   Files/data/ground_truth/enquiries_truth.csv
   Files/data/ground_truth/raw_row_map.csv
   ```
   (Or run `generate_data.main()` in the first notebook to create the data inside Fabric.)
4. **Import the notebooks** from `fabric/notebooks/` (Workspace -> Import -> Notebook), open each, and attach `northfield_lakehouse` as the default Lakehouse.
5. **Run them in order:** `01_clean_data` -> `02_ai_triage` -> `03_evaluate`.
6. **Check the tables:** open the Lakehouse and confirm `enquiries`, `data_quality_log`, `quality_scores`, `ai_triage`, `audit_log`, `ground_truth`, `raw_row_map` exist.
7. **Run the SQL:** switch to the **SQL analytics endpoint** and run the queries in `fabric/sql/metrics_queries_tsql.sql`. (Optional: create a Warehouse and copy the tables across; the queries are the same.)
8. **Build the report:** in the Lakehouse choose **New semantic model**, select the tables, then build the four pages from `powerbi/BUILD_GUIDE.md` (the measures work unchanged).
9. **Capture evidence:** screenshots of the workspace, the notebook runs, the tables and the report into `docs/screenshots/fabric_*.png`. Export the notebooks again if you edited them.
10. **Clean up:** delete the workspace or cancel the trial. Delete any Key Vault.

## What is different from the local edition

| Local edition | Fabric edition |
|---|---|
| Files on your laptop | OneLake: the Lakehouse Files area, at `/lakehouse/default/Files` |
| SQLite database file | Delta tables in the Lakehouse, queried through the SQL analytics endpoint (T-SQL) or Spark SQL |
| `python src/...` in a terminal | Notebooks, which can be scheduled with a Data Pipeline |
| `.env` file for the key | Azure Key Vault read with `notebookutils.credentials.getSecret` (or demo mode) |
| CSV files into Power BI Desktop | A semantic model on the Lakehouse tables (Direct Lake), so the report updates when the notebooks re-run |
| SQLite SQL (`strftime`, `LIMIT`) | T-SQL (`LEFT`, `TOP`); see the notes at the top of `metrics_queries_tsql.sql` |
| Human review via a CSV or n8n + Google Sheets | Not rebuilt in Fabric; a real deployment would use Power Automate or n8n with an approval step |

## If something fails

- **`ModuleNotFoundError` for a project file:** the `src/` folder is not at `Files/src/`, or no default Lakehouse is attached.
- **Permission or write errors under `/lakehouse/default/Files`:** make sure the Lakehouse is attached as the default one.
- **`spark` is not defined:** the notebook is running with the Python kernel instead of PySpark; switch the kernel.
- Tell Claude the exact error text and which notebook cell it came from.
