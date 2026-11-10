# n8n workflow (Phase 5)

**Status: drafted, not run.** The machine this was built on has no Docker and no connected Google account, so `workflow.json` has never been imported into n8n. The same logic is tested in Python in `src/review_queue.py`. Treat this as a head start, not a finished product.

## What it does

Flow 1 (intake): web form POST -> mask personal details -> ask Claude -> check the JSON and let *code* decide human review -> add a row to the **Review queue** sheet and the **Audit log** sheet.

Flow 2 (decision): a manager edits a row in the Review queue sheet (`decision` = approved / edited / rejected) -> if rejected, log it and send nothing -> otherwise draft a reply, email it **to your own address only**, and log it.

## Set-up steps

1. Start n8n (needs Docker Desktop):
   ```bash
   docker run -it --rm --name n8n -p 5678:5678 -v n8n_data:/home/node/.n8n docker.n8n.io/n8nio/n8n
   ```
   Open http://localhost:5678.
2. Create a Google Sheet with two tabs.
   - **Review queue** columns: `case_ref, received, ai_category, ai_urgency, summary, requested_action, confidence, why_flagged, decision, final_category, final_urgency, reviewer, notes`
   - **Audit log** columns: `timestamp, case_ref, actor, action, detail`
3. In n8n: Workflows -> Import from file -> `n8n/workflow.json`.
4. Add credentials (never paste keys into the workflow itself):
   - Google Sheets OAuth2 (and the Sheets Trigger one)
   - HTTP Header Auth: name `x-api-key`, value = your Anthropic key
   - SMTP for the email node (a Gmail app password works)
5. Replace `REPLACE_WITH_YOUR_GOOGLE_SHEET_ID` and `REPLACE_WITH_YOUR_EMAIL` in the nodes.
6. Test with a synthetic enquiry:
   ```bash
   curl -X POST http://localhost:5678/webhook-test/new-enquiry \
     -H "Content-Type: application/json" \
     -d '{"case_ref":"NF-TEST-0001","name":"Test Person","message":"I can smell gas in the corridor at 22 Willow Court, M99 1ZZ. Call 07700 900123."}'
   ```
7. In the Review queue sheet, type `approved` in the `decision` column and watch the second flow run.

## Things to check when you first open it

- n8n node versions change; if a node shows a warning, open it and re-select its options.
- The Google Sheets "columns" mapping may need re-mapping in the UI.
- Keep the workflow **inactive** until the credentials are set.
- Use synthetic data only.
