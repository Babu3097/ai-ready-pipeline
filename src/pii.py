"""
pii.py - find and hide personal details in free text.

PII = "personally identifiable information": names, phone numbers, emails,
addresses, postcodes, National Insurance numbers.

Rule for this project: personal details are MASKED before any text goes to an AI.
The same patterns are also used to *find* a phone/email/postcode that someone
typed into the message but left out of its proper column.
"""
import re

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
NI_RE = re.compile(r"\b[A-Z]{2}\s?\d{2}\s?\d{2}\s?\d{2}\s?[A-D]\b")
POSTCODE_RE = re.compile(r"\b[A-Z]{1,2}\d[A-Z\d]?\s?\d[A-Z]{2}\b")
POSTCODE_ANYCASE_RE = re.compile(r"\b[A-Z]{1,2}\d[A-Z\d]?\s?\d[A-Z]{2}\b", re.IGNORECASE)  # for masking: text may be lower case
STREET_WORDS = "Street|Road|Avenue|Lane|Close|Drive|Way|Court|Gardens|Crescent|Terrace|Grove|Place"
ADDRESS_RE = re.compile(rf"\b\d{{1,4}}[A-Za-z]?\s+(?:[A-Za-z]+\s){{1,2}}(?:{STREET_WORDS})\b", re.IGNORECASE)
# a run of digits, spaces, dashes, brackets - we then check it has 10+ digits
PHONE_LIKE_RE = re.compile(r"\+?\(?\d[\d\s\-().]{8,}\d")
# "Regards, Jane Smith" / "My name is Jane Smith" - hides the name that follows
# Sign-offs ("Regards, jane smith") and "my name is ..." hide the name that follows, in any letter case.
SIGNOFF_RE = re.compile(
    r"\b((?i:kind regards|regards|many thanks|thanks|thank you|cheers|sincerely|my name is)"
    r",?\s+)([A-Za-z'’-]+(?:\s[A-Za-z'’-]+){0,1})"
)
# Weaker lead-ins only count when the name is capitalised, so "this is my third complaint" is left alone.
WEAK_SIGNOFF_RE = re.compile(
    r"\b((?i:this is|i am|i'm)\s+)([A-Z][a-zA-Z'’-]+(?:\s[A-Z][a-zA-Z'’-]+){0,1})"
)


def find_emails(text: str) -> list:
    return sorted(set(EMAIL_RE.findall(text or "")))


def find_postcodes(text: str) -> list:
    return sorted(set(POSTCODE_RE.findall(text or "")))


def find_phone_candidates(text: str) -> list:
    """Return the digit-only version of every phone-looking run (10+ digits)."""
    found = []
    for m in PHONE_LIKE_RE.finditer(text or ""):
        digits = re.sub(r"\D", "", m.group())
        if len(digits) >= 10:
            found.append(digits)
    return sorted(set(found))


def mask_pii(text: str, name: str = "") -> str:
    """Replace personal details with labels like [EMAIL] so an AI never sees them."""
    if not text:
        return ""
    out = EMAIL_RE.sub("[EMAIL]", text)
    out = NI_RE.sub("[NI_NUMBER]", out)
    out = POSTCODE_ANYCASE_RE.sub("[POSTCODE]", out)
    out = ADDRESS_RE.sub("[ADDRESS]", out)
    out = PHONE_LIKE_RE.sub(lambda m: "[PHONE]" if len(re.sub(r"\D", "", m.group())) >= 10 else m.group(), out)
    out = SIGNOFF_RE.sub(lambda m: m.group(1) + "[NAME]", out)
    out = WEAK_SIGNOFF_RE.sub(lambda m: m.group(1) + "[NAME]", out)
    for token in re.split(r"[\s,]+", name or ""):  # the name we already know, wherever it appears
        if len(token) >= 3:
            out = re.sub(rf"\b{re.escape(token)}\b", "[NAME]", out, flags=re.IGNORECASE)
    return out


if __name__ == "__main__":
    demo = ("Hi, my name is Jane Doe and the boiler at 14 Alder Street, M14 5HD is broken. "
            "Call 07123 456789 or email jane.doe@example.com. NI QQ123456C.")
    print(demo)
    print(mask_pii(demo, "Jane Doe"))
