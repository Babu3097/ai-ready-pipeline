"""
ai_assist.py - AI help for the few rows the clean-up RULES cannot fix.

When the "category" cell is blank or says something like "Other", rules can't
know the answer. This file asks for a SUGGESTION based on the message text.

Safety rules:
  * only the MASKED message is ever sent (no names, phones, emails, addresses)
  * the answer is stored as a suggestion, never written over the real category
  * a person checks it later (rows are flagged for review)

No API key? Demo mode uses a simple keyword matcher instead, so it still runs.
"""
import json
from typing import Literal, Optional, Tuple

from pydantic import BaseModel, Field, ValidationError

import ai_client

CATEGORIES = ["Housing Repairs", "Noise", "Waste", "Billing", "Complaints", "Safety"]

SYSTEM_PROMPT = (
    "You sort UK council enquiries. Choose exactly one category from: "
    + ", ".join(CATEGORIES)
    + '. Reply with JSON only, like {"category": "Noise", "confidence": 0.8}. '
    "confidence is a number from 0 to 1. The text has personal details removed; ignore the [LABELS]."
)


class Suggestion(BaseModel):
    """The shape we expect back. pydantic rejects anything that doesn't fit."""
    category: Literal["Housing Repairs", "Noise", "Waste", "Billing", "Complaints", "Safety"]
    confidence: float = Field(ge=0, le=1)


# --- demo mode: simple keywords instead of AI ---
KEYWORDS = {
    "Safety": ["gas", "fire", "handrail", "wires", "electrical", "pothole", "street light", "unsafe", "fell"],
    "Noise": ["noise", "loud", "music", "bark", "party", "parties", "shouting", "drill"],
    "Waste": ["bin", "rubbish", "recycl", "sofa", "fly-tip", "rats", "collection"],
    "Billing": ["council tax", "rent", "direct debit", "refund", "arrears", "charged", "bill", "summons"],
    "Housing Repairs": ["boiler", "heating", "ceiling", "leak", "lock", "tiles", "cabinet", "repair", "hot water"],
    "Complaints": ["complaint", "rude", "unhappy", "ombudsman", "website", "chaser"],
}


def _demo_suggest(masked_text: str) -> Optional[Suggestion]:
    text = masked_text.lower()
    scores = {cat: sum(word in text for word in words) for cat, words in KEYWORDS.items()}
    best = max(scores, key=scores.get)
    if scores[best] == 0:
        return None
    return Suggestion(category=best, confidence=min(0.9, 0.5 + 0.15 * scores[best]))


def suggest_category(masked_text: str, tracker: ai_client.CostTracker = None) -> Tuple[Optional[Suggestion], str]:
    """Return (suggestion or None, note about how it went)."""
    if not masked_text.strip():
        return None, "no message text"
    if ai_client.is_demo():
        s = _demo_suggest(masked_text)
        return s, ("demo keyword match" if s else "demo: no keywords matched")

    for attempt in (1, 2):  # one retry if the answer isn't valid JSON
        try:
            reply = ai_client.ask_claude(masked_text, system=SYSTEM_PROMPT, max_tokens=60, tracker=tracker)
            start, end = reply.find("{"), reply.rfind("}") + 1
            return Suggestion(**json.loads(reply[start:end])), f"claude {ai_client.MODEL}"
        except (json.JSONDecodeError, ValidationError, ValueError):
            if attempt == 2:
                return None, "claude answer was not valid JSON (logged, no suggestion)"
    return None, "unknown failure"


if __name__ == "__main__":
    sample = "The handrail on the stairs at [ADDRESS] has come away from the wall."
    print(suggest_category(sample))
