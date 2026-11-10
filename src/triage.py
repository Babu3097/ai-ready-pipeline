"""
triage.py - Phase 4: AI extraction and triage.

For each cleaned enquiry, Claude (or the demo stand-in) returns JSON:
  {category, urgency, summary, postcode, requested_action, confidence, needs_human_review, reason}

Safety rules built in:
  * only the MASKED message is sent (no names, phones, emails, addresses, postcodes)
  * pydantic checks the JSON; one retry on bad JSON; failures are logged and go to a person
  * CODE (not the AI) forces human review when confidence is low, urgency is High,
    or the category is Safety
  * cost is tracked; the run stops before passing £2

Run:  python src/triage.py              (demo mode if there is no API key)
      python src/triage.py --limit 20   (only the first 20 not yet done)
      python src/triage.py --redo       (wipe earlier triage results first)
      python src/triage.py --demo       (force demo mode even if a key exists)
      python src/triage.py --prompt v2  (choose a prompt version; see PROMPTS)
"""
import json
import sys
from typing import Literal, Optional

from pydantic import BaseModel, Field, ValidationError

import ai_client
import db
from ai_assist import KEYWORDS

CONFIDENCE_THRESHOLD = 0.70

PROMPT_V1 = """You triage enquiries for a UK council contact centre. The text has personal details removed
(shown as [NAME], [PHONE], [ADDRESS] and so on) - ignore those labels.

Return ONE JSON object and nothing else, with exactly these keys:
  category: one of "Housing Repairs", "Noise", "Waste", "Billing", "Complaints", "Safety"
  urgency: "High", "Medium" or "Low"
  summary: one plain sentence, under 25 words
  postcode: always "" (postcodes are not shared with you)
  requested_action: what the person wants done, in under 12 words
  confidence: number 0 to 1 for how sure you are of category and urgency
  needs_human_review: true or false
  reason: one short sentence explaining your category and urgency choice

Urgency guide: High = risk to health or safety, vulnerable people, a legal or court deadline, or a threat to escalate.
Medium = ongoing disruption or a clear problem that needs fixing soon. Low = routine request or minor issue.
Safety = hazards to people or property (gas, fire, electrics, structural, unlit or damaged public areas).
A person always makes the final decision; you only sort and summarise."""

PROMPT_V2 = """You triage enquiries for a UK council contact centre. The text has personal details removed
(shown as [NAME], [PHONE], [ADDRESS] and so on) - ignore those labels.

Return ONE JSON object and nothing else, with exactly these keys:
  category: the PRIMARY issue, one of "Housing Repairs", "Noise", "Waste", "Billing", "Complaints", "Safety"
  secondary_category: a second category that ALSO clearly applies, or null
  urgency: "High", "Medium" or "Low"
  summary: one plain sentence, under 25 words
  postcode: always "" (postcodes are not shared with you)
  requested_action: what the person wants done, in under 12 words
  confidence: number 0 to 1 for how sure you are of category and urgency
  needs_human_review: true or false
  reason: one short sentence explaining your category and urgency choice

CATEGORY GUIDE - choose by which team must act on the root problem:
- Housing Repairs: faults in or to a home or its building (leaks, flooding indoors, heating, boilers, damp and mould,
  doors, windows, lifts, pests inside), even when they are serious or an emergency.
- Noise: noise, and neighbour disputes or anti-social behaviour between residents, including shouting or threats.
- Waste: bins, recycling, collections, fly-tipping, dumped or hazardous rubbish (including needles and asbestos).
- Billing: council tax, rent, payments, refunds, arrears, benefits affecting payment, bailiffs, eviction for arrears.
- Complaints: the MAIN point is dissatisfaction with a service, process, website or staff member, a chaser about an
  earlier request, or feedback (including praise), even if the topic belongs to another category.
- Safety: hazards to the public or to shared and public spaces where no other category fits better: gas, fire safety,
  dangerous electrics, structural collapse risk, broken communal security, street lighting, pavements, roads, trees.
Seriousness is shown by URGENCY, not by category. Do not choose Safety just because a problem is serious: a serious fault
inside a home is Housing Repairs, serious neighbour behaviour is Noise, dangerous rubbish is Waste.
If a second category also clearly applies, name it in secondary_category; otherwise use null.

URGENCY GUIDE:
- High: immediate danger to someone's health or safety (gas, fire or electrical danger, water pouring in, threats or
  violence); a vulnerable person at risk (baby, child, elderly, disabled, seriously ill); an imminent legal or
  enforcement step (court date, bailiffs, eviction); or an explicit threat to escalate (Ombudsman, MP, press, solicitor).
- Medium: an ongoing problem or hazard needing action soon, but no immediate danger: repeated disruption, a repair
  affecting daily life, a hazard that could hurt someone, a billing error.
- Low: routine requests, questions, minor faults, a one-off annoyance, or general feedback.

If the message is too short or vague to classify, give your best guess, set confidence below 0.4 and say so in reason.
Use confidence below 0.7 whenever two categories are plausible. A person always makes the final decision; you only sort and summarise."""
PROMPTS = {"v1": PROMPT_V1, "v2": PROMPT_V2}
DEFAULT_PROMPT = "v2"
SYSTEM_PROMPT = PROMPT_V1  # kept so older code that imports SYSTEM_PROMPT still works


class Triage(BaseModel):
    """The exact shape we accept back. Anything else is rejected."""
    category: Literal["Housing Repairs", "Noise", "Waste", "Billing", "Complaints", "Safety"]
    urgency: Literal["High", "Medium", "Low"]
    summary: str = Field(max_length=300)
    postcode: str = ""
    requested_action: str = Field(max_length=200)
    confidence: float = Field(ge=0, le=1)
    needs_human_review: bool
    reason: str = Field(max_length=400)
    secondary_category: Optional[Literal["Housing Repairs", "Noise", "Waste", "Billing", "Complaints", "Safety"]] = None


# ---------------- demo stand-in (NOT an AI; simple keyword rules) ----------------

HIGH_WORDS = ["gas", "pouring", "baby", "needles", "summons", "court", "scared", "violent", "ombudsman",
              "nearly fell", "wires", "fire door", "alarm", "broken glass"]
MEDIUM_WORDS = ["no hot water", "two days", "midnight", "every day", "weeks", "dumped", "charged twice",
                "arrears", "lost my job", "sticking", "unhappy", "chaser", "street light", "pothole",
                "rats", "drill", "overflowing", "refund"]
ACTIONS = {
    "Housing Repairs": "Arrange a repair visit", "Noise": "Investigate the noise complaint",
    "Waste": "Arrange a bin or waste collection", "Billing": "Review the account or bill",
    "Complaints": "Log and respond to the complaint", "Safety": "Inspect the hazard urgently",
}


def demo_triage(masked: str) -> dict:
    text = masked.lower()
    scores = {cat: sum(w in text for w in words) for cat, words in KEYWORDS.items()}
    best = max(scores, key=scores.get)
    top = scores[best]
    runner_up = sorted(scores.values())[-2]
    if top == 0:
        best, confidence = "Complaints", 0.30
    else:
        confidence = min(0.92, 0.55 + 0.12 * top - 0.15 * (runner_up == top))
    urgency = "High" if any(w in text for w in HIGH_WORDS) else "Medium" if any(w in text for w in MEDIUM_WORDS) else "Low"
    first_sentence = masked.replace("\n", " ").split(". ")[0].strip()
    return dict(
        category=best, urgency=urgency, summary=first_sentence[:200] or "No message text",
        postcode="", requested_action=ACTIONS[best], confidence=round(confidence, 2),
        needs_human_review=False, reason="Demo stand-in: keyword rules, not an AI model.",
    )


# ---------------- real Claude call ----------------

def claude_triage(masked: str, tracker, prompt: str = None):
    """Ask Claude; validate; retry once. Returns (dict or None, error text)."""
    last_error = ""
    for attempt in (1, 2):
        try:
            reply = ai_client.ask_claude(masked, system=PROMPTS[prompt or DEFAULT_PROMPT], max_tokens=600, tracker=tracker)
            start, end = reply.find("{"), reply.rfind("}") + 1
            return Triage(**json.loads(reply[start:end])).model_dump(), ""
        except (json.JSONDecodeError, ValidationError, ValueError) as e:
            last_error = f"attempt {attempt}: {type(e).__name__}"
    return None, last_error


def apply_review_rules(result: dict):
    """The human-review decision is made by CODE, so the AI can't talk its way out of it."""
    reasons = []
    if result["confidence"] < CONFIDENCE_THRESHOLD: reasons.append("low confidence")
    if result["urgency"] == "High": reasons.append("high urgency")
    if result["category"] == "Safety": reasons.append("safety issue")
    sec = result.get("secondary_category")
    if sec and sec != result["category"]: reasons.append(f"two possible categories ({result['category']} / {sec})")
    if result["needs_human_review"] and not reasons: reasons.append("AI asked for review")
    return bool(reasons), ", ".join(reasons)


def main():
    args = sys.argv[1:]
    force_demo = "--demo" in args
    prompt_name = args[args.index("--prompt") + 1] if "--prompt" in args else DEFAULT_PROMPT
    limit = int(args[args.index("--limit") + 1]) if "--limit" in args else None
    demo = force_demo or ai_client.is_demo()
    conn = db.connect()

    if "--redo" in args:
        conn.execute("DELETE FROM ai_triage")
        conn.execute("DELETE FROM human_reviews")
        conn.execute("DELETE FROM audit_log WHERE actor IN ('ai') OR action IN ('queued_for_review')")
        conn.commit()

    todo = conn.execute("""SELECT e.raw_row, e.message_masked, e.postcode FROM enquiries e
                           WHERE e.raw_row NOT IN (SELECT raw_row FROM ai_triage) ORDER BY e.raw_row""").fetchall()
    if limit:
        todo = todo[:limit]
    if not todo:
        print("Nothing to do: every enquiry is already triaged (use --redo to start again).")
        return

    mode, model = ("demo", "keyword-rules") if demo else ("claude", ai_client.MODEL)
    tracker = ai_client.CostTracker()
    if not demo:
        per_call_in = len(PROMPTS[prompt_name]) // 2.5 + 150  # rough: the prompt dominates the input
        est_in, est_out = len(todo) * per_call_in, len(todo) * 280  # ~280 output tokens per call was observed
        est = (est_in * ai_client.PRICE_IN_USD_PER_MILLION_TOKENS + est_out * ai_client.PRICE_OUT_USD_PER_MILLION_TOKENS) / 1e6 * ai_client.USD_TO_GBP
        print(f"Real Claude run: {len(todo)} enquiries with {model}. Estimated cost about £{est:.2f} (limit £{tracker.budget_gbp:.2f}).")
        if est >= tracker.budget_gbp:
            print("Estimate is over the limit - stopping. Use --limit to run a smaller batch.")
            return
    else:
        print(f"DEMO MODE: {len(todo)} enquiries triaged with keyword rules (no AI, no cost).")

    done = failed = review = 0
    for n, row in enumerate(todo, start=1):
        raw_row, masked, postcode = row["raw_row"], row["message_masked"] or "", row["postcode"]
        before_in, before_out = tracker.input_tokens, tracker.output_tokens
        result, error = None, ""
        if not masked.strip():
            error = "empty message"
        elif demo:
            result = demo_triage(masked)
        else:
            try:
                result, error = claude_triage(masked, tracker, prompt_name)
            except ai_client.BudgetExceeded as e:
                print(e)
                break

        if result is None:  # could not triage: a person must handle it
            failed += 1
            conn.execute("""INSERT INTO ai_triage (raw_row, needs_human_review, reason, mode, model, created_at)
                            VALUES (?, 1, ?, ?, ?, ?)""", (raw_row, f"AI triage failed: {error}", mode, model, db.now()))
            db.audit(conn, raw_row, "ai", "triage_failed", error)
            db.audit(conn, raw_row, "system", "queued_for_review", "triage failed")
            review += 1
            continue

        needs, why = apply_review_rules(result)
        in_t, out_t = tracker.input_tokens - before_in, tracker.output_tokens - before_out
        cost = ((in_t * ai_client.PRICE_IN_USD_PER_MILLION_TOKENS + out_t * ai_client.PRICE_OUT_USD_PER_MILLION_TOKENS)
                / 1e6 * ai_client.USD_TO_GBP)
        conn.execute("""INSERT INTO ai_triage (raw_row, category, urgency, summary, postcode, requested_action, confidence,
                        needs_human_review, reason, mode, model, input_tokens, output_tokens, cost_gbp, created_at,
                        secondary_category, prompt_version)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                     (raw_row, result["category"], result["urgency"], result["summary"], postcode,
                      result["requested_action"], result["confidence"], int(needs), result["reason"],
                      mode, model, in_t, out_t, cost, db.now(), result.get("secondary_category"),
                      None if demo else (prompt_name)))
        db.audit(conn, raw_row, "ai", "triaged",
                 f"category={result['category']}; urgency={result['urgency']}; confidence={result['confidence']}; mode={mode}")
        if needs:
            review += 1
            db.audit(conn, raw_row, "system", "queued_for_review", why)
        done += 1
        if n % 25 == 0:
            conn.commit()
            print(f"  ...{n}/{len(todo)} done")
    conn.commit()

    print(f"\nTriaged {done}, failed {failed}. Sent to human review: {review} ({100 * review / max(1, done + failed):.0f}%).")
    if not demo:
        print(f"Claude calls: {tracker.calls}; tokens: {tracker.input_tokens} in / {tracker.output_tokens} out; "
              f"cost about £{tracker.cost_gbp:.4f} (price figures are assumptions - check the Console).")
    else:
        print("Cost: £0.00 (demo mode).")
    conn.close()


if __name__ == "__main__":
    main()
