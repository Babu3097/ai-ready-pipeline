"""
make_n8n_workflow.py - writes n8n/workflow.json (so the AI prompt is always identical to triage.py).

STATUS: drafted, NOT run. This computer has no Docker and no Google account connected, so the workflow has
not been imported into n8n. Import it, set the credentials, and expect to fix small things.
The same logic IS tested locally in review_queue.py.

Run:  python src/make_n8n_workflow.py
"""
import json

import db
import triage

MASK_JS = r"""// Hide personal details BEFORE anything is sent to Claude
const body = $input.first().json.body || $input.first().json;
let text = String(body.message || '');
const name = String(body.name || '');
text = text.replace(/[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/g, '[EMAIL]');
text = text.replace(/\b[A-Z]{2}\s?\d{2}\s?\d{2}\s?\d{2}\s?[A-D]\b/g, '[NI_NUMBER]');
text = text.replace(/\b[A-Z]{1,2}\d[A-Z\d]?\s?\d[A-Z]{2}\b/g, '[POSTCODE]');
text = text.replace(/\b\d{1,4}[A-Za-z]?\s+(?:[A-Z][a-z]+\s){1,2}(?:Street|Road|Avenue|Lane|Close|Drive|Way|Court|Gardens|Crescent|Terrace|Grove|Place)\b/g, '[ADDRESS]');
text = text.replace(/\+?\(?\d[\d\s\-().]{8,}\d/g, m => (m.replace(/\D/g, '').length >= 10 ? '[PHONE]' : m));
text = text.replace(/\b((?:kind regards|regards|many thanks|thanks|thank you|cheers|my name is)[, ]+)([A-Z][a-zA-Z'-]+(?:\s[A-Z][a-zA-Z'-]+){0,2})/gi, '$1[NAME]');
name.split(/[\s,]+/).filter(t => t.length >= 3).forEach(t => { text = text.split(t).join('[NAME]'); });
return [{ json: { case_ref: body.case_ref || ('NF-' + Date.now()), received: new Date().toISOString(), masked_message: text } }];
"""

VALIDATE_JS = r"""// Check Claude's JSON and let CODE (not the AI) decide whether a person must review it
const ctx = $('Mask personal details').first().json;
const reply = $input.first().json;
let parsed = null, error = '';
try {
  const raw = reply.content[0].text;
  parsed = JSON.parse(raw.slice(raw.indexOf('{'), raw.lastIndexOf('}') + 1));
  const cats = ['Housing Repairs','Noise','Waste','Billing','Complaints','Safety'];
  if (!cats.includes(parsed.category)) throw new Error('bad category');
  if (!['High','Medium','Low'].includes(parsed.urgency)) throw new Error('bad urgency');
  if (typeof parsed.confidence !== 'number' || parsed.confidence < 0 || parsed.confidence > 1) throw new Error('bad confidence');
} catch (e) { parsed = null; error = String(e); }
const reasons = [];
if (!parsed) reasons.push('AI output invalid: ' + error);
else {
  if (parsed.confidence < 0.7) reasons.push('low confidence');
  if (parsed.urgency === 'High') reasons.push('high urgency');
  if (parsed.category === 'Safety') reasons.push('safety issue');
}
return [{ json: {
  case_ref: ctx.case_ref, received: ctx.received,
  ai_category: parsed ? parsed.category : '', ai_urgency: parsed ? parsed.urgency : '',
  summary: parsed ? parsed.summary : '', requested_action: parsed ? parsed.requested_action : '',
  confidence: parsed ? parsed.confidence : '', why_flagged: reasons.join(', ') || 'routine - still needs manager sign-off in this pilot',
  decision: '', final_category: '', final_urgency: '', reviewer: '', notes: ''
} }];
"""

DRAFT_JS = r"""// Draft the reply (only reached for approved/edited cases)
const r = $input.first().json;
const cat = r.decision === 'edited' ? r.final_category : r.ai_category;
const urg = r.decision === 'edited' ? r.final_urgency : r.ai_urgency;
const times = { High: 'within 4 working hours', Medium: 'within 3 working days', Low: 'within 10 working days' };
const lines = {
  'Housing Repairs': 'We have logged your repair request. An engineer will contact you to arrange a visit.',
  'Noise': 'We have logged your noise report and our environmental team will look into it.',
  'Waste': 'We have logged your waste and recycling report and passed it to the collections team.',
  'Billing': 'We have passed your billing query to our accounts team.',
  'Complaints': 'We are sorry you have had a poor experience. Your complaint has been logged.',
  'Safety': 'Thank you for reporting this hazard. We are acting on it.'
};
let text = `Dear resident,\n\nRe: case ${r.case_ref}\n\n${lines[cat]} You can expect to hear from us ${times[urg]}.\n`;
if (cat === 'Safety' || urg === 'High') text += '\nIf anyone is in immediate danger, please call 999.\n';
text += '\nKind regards,\nNorthfield Services (fictional)';
return [{ json: { ...r, reply_text: text, final_category_used: cat, final_urgency_used: urg } }];
"""


def sheets_node(name, pos, sheet, columns, node_id):
    return {
        "id": node_id, "name": name, "type": "n8n-nodes-base.googleSheets", "typeVersion": 4.5, "position": pos,
        "parameters": {
            "resource": "sheet", "operation": "append",
            "documentId": {"__rl": True, "value": "REPLACE_WITH_YOUR_GOOGLE_SHEET_ID", "mode": "id"},
            "sheetName": {"__rl": True, "value": sheet, "mode": "name"},
            "columns": {"mappingMode": "defineBelow", "value": columns, "matchingColumns": [], "schema": []},
            "options": {},
        },
        "credentials": {"googleSheetsOAuth2Api": {"id": "REPLACE_ME", "name": "Google Sheets account"}},
    }


def code_node(name, pos, js, node_id):
    return {"id": node_id, "name": name, "type": "n8n-nodes-base.code", "typeVersion": 2, "position": pos,
            "parameters": {"jsCode": js}}


def link(*names):
    return [{"node": n, "type": "main", "index": 0} for n in names]


def build():
    body = ("={{ JSON.stringify({ model: 'claude-haiku-5-5', max_tokens: 300, system: "
            + json.dumps(triage.SYSTEM_PROMPT) + ", messages: [{ role: 'user', content: $json.masked_message }] }) }}")
    audit_cols = lambda actor, action, detail: {"timestamp": "={{ $now.toISO() }}", "case_ref": "={{ $json.case_ref }}",
                                                "actor": actor, "action": action, "detail": detail}
    nodes = [
        {"id": "n1", "name": "New enquiry (webhook)", "type": "n8n-nodes-base.webhook", "typeVersion": 2, "position": [0, 0],
         "webhookId": "northfield-new-enquiry",
         "parameters": {"httpMethod": "POST", "path": "new-enquiry", "responseMode": "onReceived", "options": {}}},
        code_node("Mask personal details", [220, 0], MASK_JS, "n2"),
        {"id": "n3", "name": "Ask Claude", "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.2, "position": [440, 0],
         "parameters": {"method": "POST", "url": "https://api.anthropic.com/v1/messages",
                        "authentication": "genericCredentialType", "genericAuthType": "httpHeaderAuth",
                        "sendHeaders": True,
                        "headerParameters": {"parameters": [{"name": "anthropic-version", "value": "2023-06-01"},
                                                            {"name": "content-type", "value": "application/json"}]},
                        "sendBody": True, "specifyBody": "json", "jsonBody": body, "options": {}},
         "credentials": {"httpHeaderAuth": {"id": "REPLACE_ME", "name": "Anthropic API key (header x-api-key)"}}},
        code_node("Validate and decide review", [660, 0], VALIDATE_JS, "n4"),
        sheets_node("Add to review queue", [880, -80], "Review queue",
                    {k: f"={{{{ $json.{k} }}}}" for k in ["case_ref", "received", "ai_category", "ai_urgency", "summary",
                                                          "requested_action", "confidence", "why_flagged", "decision",
                                                          "final_category", "final_urgency", "reviewer", "notes"]}, "n5"),
        sheets_node("Audit: AI triaged", [880, 80], "Audit log",
                    audit_cols("ai", "triaged", "={{ 'category=' + $json.ai_category + '; urgency=' + $json.ai_urgency + '; confidence=' + $json.confidence }}"), "n6"),
        # ---- second flow: a manager fills in the sheet ----
        {"id": "n7", "name": "Manager updated a row", "type": "n8n-nodes-base.googleSheetsTrigger", "typeVersion": 1, "position": [0, 400],
         "parameters": {"pollTimes": {"item": [{"mode": "everyMinute"}]},
                        "documentId": {"__rl": True, "value": "REPLACE_WITH_YOUR_GOOGLE_SHEET_ID", "mode": "id"},
                        "sheetName": {"__rl": True, "value": "Review queue", "mode": "name"},
                        "event": "rowUpdate", "options": {}},
         "credentials": {"googleSheetsTriggerOAuth2Api": {"id": "REPLACE_ME", "name": "Google Sheets Trigger account"}}},
        {"id": "n8", "name": "Was it rejected?", "type": "n8n-nodes-base.if", "typeVersion": 1, "position": [220, 400],
         "parameters": {"conditions": {"string": [{"value1": "={{ $json.decision }}", "operation": "equals", "value2": "rejected"}]}}},
        sheets_node("Audit: rejected, no reply", [440, 520], "Audit log",
                    audit_cols("human", "decision_rejected", "={{ 'reviewer=' + $json.reviewer + '; notes=' + $json.notes }}"), "n9"),
        code_node("Draft the reply", [440, 320], DRAFT_JS, "n10"),
        {"id": "n11", "name": "Send reply (to my own email)", "type": "n8n-nodes-base.emailSend", "typeVersion": 2.1, "position": [660, 320],
         "parameters": {"fromEmail": "REPLACE_WITH_YOUR_EMAIL", "toEmail": "REPLACE_WITH_YOUR_EMAIL",
                        "subject": "={{ 'DEMO reply for case ' + $json.case_ref }}", "emailFormat": "text",
                        "text": "={{ $json.reply_text }}", "options": {}},
         "credentials": {"smtp": {"id": "REPLACE_ME", "name": "SMTP account"}}},
        sheets_node("Audit: human decision + reply", [880, 320], "Audit log",
                    audit_cols("human", "decision_" + "approved_or_edited",
                               "={{ 'reviewer=' + $json.reviewer + '; category=' + $json.final_category_used + '; urgency=' + $json.final_urgency_used + '; reply emailed (demo, to own address)' }}"), "n12"),
    ]
    connections = {
        "New enquiry (webhook)": {"main": [link("Mask personal details")]},
        "Mask personal details": {"main": [link("Ask Claude")]},
        "Ask Claude": {"main": [link("Validate and decide review")]},
        "Validate and decide review": {"main": [link("Add to review queue", "Audit: AI triaged")]},
        "Manager updated a row": {"main": [link("Was it rejected?")]},
        "Was it rejected?": {"main": [link("Audit: rejected, no reply"), link("Draft the reply")]},
        "Draft the reply": {"main": [link("Send reply (to my own email)")]},
        "Send reply (to my own email)": {"main": [link("Audit: human decision + reply")]},
    }
    return {"name": "Northfield - AI triage with human review (DRAFT, untested)", "nodes": nodes,
            "connections": connections, "active": False, "settings": {"executionOrder": "v1"}}


if __name__ == "__main__":
    out = db.ROOT / "n8n" / "workflow.json"
    out.write_text(json.dumps(build(), indent=2), encoding="utf-8")
    json.loads(out.read_text(encoding="utf-8"))  # proves it is valid JSON
    print(f"Wrote {out.relative_to(db.ROOT)} ({len(build()['nodes'])} nodes). Valid JSON, but not yet tested in n8n.")
