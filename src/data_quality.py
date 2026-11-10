"""
data_quality.py - Phase 2: check the messy data, clean what is SAFE, flag the rest.

The golden rules:
  1. Fix by simple rules only when the fix is certain (e.g. "14/10/2025" -> "2025-10-14").
  2. NEVER invent data. If a value can't be trusted it is emptied, flagged, and
     the original is kept in the log.
  3. Log every change in data_quality_log.csv.
  4. Mask personal details before anything goes to an AI.

Run:  python src/data_quality.py            (AI suggestions on; demo mode if no key)
      python src/data_quality.py --no-ai    (rules only)

Outputs (in data/clean/):
  enquiries_clean.csv      the cleaned table (one row per real enquiry)
  data_quality_log.csv     every change, flag and removal
  quality_scores.csv       before vs after scores (feeds Power BI later)
  ground_truth_check.csv   how right the clean-up was, using the answer key
  quality_report.md        the same story in plain English
"""
import csv
import difflib
import re
import sys
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

import ai_assist
import ai_client
from pii import find_emails, find_phone_candidates, find_postcodes, mask_pii

ROOT = Path(__file__).resolve().parent.parent
RAW_FILE = ROOT / "data" / "raw" / "enquiries_raw.csv"
TRUTH_FILE = ROOT / "data" / "ground_truth" / "enquiries_truth.csv"
MAP_FILE = ROOT / "data" / "ground_truth" / "raw_row_map.csv"
OUT = ROOT / "data" / "clean"

HEADER = ["case_ref", "received_date", "channel", "name", "email", "phone",
          "postcode", "category", "urgency", "message", "status", "handling_mins"]
IDX = {name: i for i, name in enumerate(HEADER)}
KEY_FIELDS = HEADER[:10]  # the ten fields a case worker needs
VALID_FIELDS = ["case_ref", "received_date", "channel", "email", "phone", "postcode", "category", "urgency"]
CONSISTENCY_FIELDS = VALID_FIELDS + ["name"]

CATEGORIES = ["Housing Repairs", "Noise", "Waste", "Billing", "Complaints", "Safety"]
# Real UK postcode areas. Lets us reject shapes that look right but cannot exist (e.g. "K24 1YW").
UK_POSTCODE_AREAS = set("""AB AL B BA BB BD BH BL BN BR BS BT CA CB CF CH CM CO CR CT CV CW DA DD DE DG DH DL DN
DT DY E EC EH EN EX FK FY G GL GU GY HA HD HG HP HR HS HU HX IG IM IP IV JE KA KT KW KY L LA LD LE LL LN LS LU M ME
MK ML N NE NG NN NP NR NW OL OX PA PE PH PL PO PR RG RH RM S SA SE SG SK SL SM SN SO SP SR SS ST SW SY TA TD TF TN
TQ TR TS TW UB W WA WC WD WF WN WR WS WV YO ZE""".split())

PLACEHOLDERS = {"n/a", "na", "tbc", "unknown", "-", "--", "none", "xxx", "?", "null", "nil",
                "test@test.com", "noemail@noemail.com", "zz99 9zz", "00/00/0000",
                "0000000000", "00000000000", "01234567890", "1234567890"}
ZERO_WIDTH = dict.fromkeys(map(ord, "​‌‍﻿"), None)

# Flags that mean "a human should look at this row"
REVIEW_FLAGS = {"case_ref_missing", "case_ref_invalid", "date_missing", "date_partial", "date_invalid",
                "no_contact_details", "message_missing", "possible_duplicate",
                "category_unresolved", "category_ai_suggested"}


# ======================================================================
# Part 1 - small rule functions. Each one takes messy text and returns
# the clean standard version, or None when it can't be trusted.
# ======================================================================

def tidy(value) -> str:
    """Remove invisible characters and extra spaces."""
    if value is None:
        return ""
    return " ".join(str(value).translate(ZERO_WIDTH).split())


def missing_kind(value):
    """None if there is a real value; otherwise how it is 'missing'."""
    raw = "" if value is None else str(value)
    t = tidy(raw)
    if raw == "":
        return "blank"
    if t == "":
        return "hidden_blank"  # spaces, tabs, zero-width characters
    if t.lower() in PLACEHOLDERS:
        return "placeholder"
    return None


def is_missing(value) -> bool:
    return missing_kind(value) is not None


def normalise_case_ref(v):
    m = re.fullmatch(r"NF[- ]?(\d{4})[- ]?(\d{4})", tidy(v).upper())
    return f"NF-{m.group(1)}-{m.group(2)}" if m else None


def parse_date(v):
    t = tidy(v)
    if re.fullmatch(r"\d{5}", t):  # Excel stores dates as a count of days
        d = date(1899, 12, 30) + timedelta(days=int(t))
    else:
        d = None
        # We assume UK order (day first). "04/11/2025" means 4 November.
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d/%m/%y", "%d-%b-%Y", "%d %B %Y", "%d %b %Y", "%d-%m-%Y"):
            try:
                d = datetime.strptime(t, fmt).date()
                break
            except ValueError:
                continue
    if d is None or not (date(2020, 1, 1) <= d <= date.today()):
        return None
    return d


def normalise_email(v):
    t = tidy(v).lower()
    ok = re.fullmatch(r"[a-z0-9._%+-]+@[a-z0-9-]+(\.[a-z0-9-]+)*\.[a-z]{2,}", t)
    return t if ok else None


def format_phone(d: str) -> str:
    return f"{d[:4]} {d[4:7]} {d[7:]}" if d.startswith("0161") else f"{d[:5]} {d[5:]}"


def normalise_phone(v):
    digits = re.sub(r"\D", "", tidy(v))
    if len(digits) == 12 and digits.startswith("44"):
        digits = "0" + digits[2:]  # +44 7123... -> 07123...
    elif len(digits) == 10 and not digits.startswith("0"):
        digits = "0" + digits      # a spreadsheet dropped the leading zero
    if len(digits) != 11 or digits[:2] not in ("01", "02", "03", "07") or len(set(digits)) <= 2:
        return None
    return format_phone(digits)


def normalise_postcode(v):
    t = re.sub(r"\s", "", tidy(v).upper())
    outward, inward = t[:-3], t[-3:]
    if not re.fullmatch(r"[A-Z]{1,2}\d[A-Z\d]?", outward) or not re.fullmatch(r"\d[A-Z]{2}", inward):
        return None
    if re.match(r"[A-Z]+", outward).group() not in UK_POSTCODE_AREAS:
        return None
    return f"{outward} {inward}"


def normalise_name(v):
    t = tidy(v)
    if "," in t:  # "Smith, John" -> "John Smith"
        last, first = [p.strip() for p in t.split(",", 1)]
        t = f"{first} {last}"
    if t.isupper() or t.islower():
        t = t.title()
    return t or None


def map_category(v):
    t = tidy(v).lower()
    if "noise" in t: return "Noise"
    if any(k in t for k in ("waste", "bin", "recycl")): return "Waste"
    if "safety" in t or t in ("h&s", "hs"): return "Safety"
    if any(k in t for k in ("bill", "council tax", "payment", "rent")): return "Billing"
    if any(k in t for k in ("housing", "repair")): return "Housing Repairs"
    if "complain" in t: return "Complaints"
    return None  # e.g. "Other", "misc" - rules can't know


def map_urgency(v):
    t = tidy(v).lower()
    if any(k in t for k in ("urgent", "high", "crit", "p1")): return "High"
    if any(k in t for k in ("med", "normal", "p2")): return "Medium"
    if "low" in t or t in ("l", "p3"): return "Low"
    return None


def map_channel(v):
    t = tidy(v).lower()
    if "mail" in t: return "Email"
    if "web" in t or "form" in t: return "Web form"
    return None


def map_status(v):
    t = tidy(v).lower()
    if any(k in t for k in ("closed", "complete", "done")): return "Closed"
    if any(k in t for k in ("open", "progress", "pending")): return "Open"
    return None


def parse_minutes(v):
    m = re.fullmatch(r"(\d+(?:\.\d+)?)\s*(m|min|mins|minutes?|h|hr|hrs|hours?)?", tidy(v).lower())
    if not m:
        return None
    value = float(m.group(1))
    if m.group(2) and m.group(2).startswith("h"):
        value *= 60
    return int(round(value))


NORMALISERS = {  # field -> function used by the scoring section too
    "case_ref": normalise_case_ref,
    "received_date": lambda v: (parse_date(v).isoformat() if parse_date(v) else None),
    "channel": map_channel, "name": normalise_name, "email": normalise_email,
    "phone": normalise_phone, "postcode": normalise_postcode,
    "category": map_category, "urgency": map_urgency,
}


# ======================================================================
# Part 2 - clean one row
# ======================================================================

def row_score(cells) -> int:
    """How many cells look right in their column? Used to repair shifted rows."""
    checks = [("case_ref", normalise_case_ref), ("received_date", parse_date), ("channel", map_channel),
              ("email", normalise_email), ("phone", normalise_phone), ("postcode", normalise_postcode),
              ("category", map_category), ("urgency", map_urgency), ("status", map_status)]
    return sum(1 for field, fn in checks if fn(cells[IDX[field]]) is not None)


def realign(cells, raw_row, log):
    """Rows with an extra cell have been shifted: find the blank cell to remove."""
    width = len(HEADER)
    cells = list(cells)
    if len(cells) < width:
        log.append(dict(raw_row=raw_row, field="(whole row)", issue="row_too_short", action="padded",
                        old_value="|".join(cells), new_value=""))
        return cells + [""] * (width - len(cells))
    if len(cells) == width:
        return cells
    blanks = [i for i, c in enumerate(cells) if tidy(c) == ""]
    if len(cells) - width == 1 and blanks:
        best = max(blanks, key=lambda i: (row_score(cells[:i] + cells[i + 1:]), -i))
        fixed = cells[:best] + cells[best + 1:]
        log.append(dict(raw_row=raw_row, field="(whole row)", issue="shifted_columns", action="fixed",
                        old_value=f"extra empty cell at position {best + 1}", new_value="removed it"))
        return fixed
    log.append(dict(raw_row=raw_row, field="(whole row)", issue="row_too_long", action="truncated",
                    old_value="|".join(cells[width:]), new_value=""))
    return cells[:width]


def clean_row(cells, raw_row, log):
    d = dict(zip(HEADER, cells))
    raw = dict(d)
    flags = []

    def record(field, issue, action, new=""):
        log.append(dict(raw_row=raw_row, field=field, issue=issue, action=action,
                        old_value=raw[field], new_value=new))

    # --- values sitting in the wrong column ---
    if (not is_missing(d["email"]) and normalise_email(d["email"]) is None
            and normalise_email(d["name"]) is not None):
        d["name"], d["email"] = d["email"], d["name"]
        record("name", "name_and_email_swapped", "fixed", d["name"])
        record("email", "name_and_email_swapped", "fixed", d["email"])
    if normalise_postcode(d["phone"]) is not None and normalise_phone(d["postcode"]) is not None:
        d["phone"], d["postcode"] = d["postcode"], d["phone"]
        record("phone", "phone_and_postcode_swapped", "fixed", d["phone"])
        record("postcode", "phone_and_postcode_swapped", "fixed", d["postcode"])

    out = {"raw_row": raw_row}

    def handle(field, normaliser, label, optional=False):
        """Shared logic: missing -> empty+flag; unreadable -> empty+flag; else standardise."""
        kind = missing_kind(d[field])
        if kind:
            if kind != "blank":
                record(field, f"{label}_{kind}", "treated_as_missing")
            flags.append(f"{label}_missing" if not optional else f"{label}_missing_info")
            return ""
        value = normaliser(d[field])
        if value is None:
            record(field, f"{label}_unreadable", "cleared_invalid")
            flags.append(f"{label}_invalid_cleared")
            return ""
        if value != d[field]:
            issue = "extra_whitespace_trimmed" if tidy(d[field]) == value else f"{label}_format_standardised"
            if field == "phone" and len(re.sub(r"\D", "", d[field])) == 10 and not tidy(d[field]).startswith("0"):
                issue = "lost_leading_zero_restored"
            record(field, issue, "fixed", value)
        return value

    out["case_ref"] = handle("case_ref", normalise_case_ref, "case_ref")
    kind = missing_kind(d["received_date"])
    if kind:
        if kind != "blank":
            record("received_date", f"date_{kind}", "treated_as_missing")
        flags.append("date_missing")
        out["received_date"] = ""
    else:
        parsed = parse_date(d["received_date"])
        if parsed is None:
            partial = re.fullmatch(r"\d{4}|[A-Za-z]{3,9}\.? \d{4}", tidy(d["received_date"]))
            record("received_date", "date_partial" if partial else "date_unreadable", "cleared_invalid")
            flags.append("date_partial" if partial else "date_invalid")
            out["received_date"] = ""
        else:
            out["received_date"] = parsed.isoformat()
            if out["received_date"] != d["received_date"]:
                record("received_date", "date_format_standardised", "fixed", out["received_date"])
    out["channel"] = handle("channel", map_channel, "channel", optional=True)
    out["name"] = handle("name", normalise_name, "name", optional=True)
    out["email"] = handle("email", normalise_email, "email", optional=True)
    out["phone"] = handle("phone", normalise_phone, "phone", optional=True)
    out["postcode"] = handle("postcode", normalise_postcode, "postcode", optional=True)
    out["urgency"] = handle("urgency", map_urgency, "urgency", optional=True)
    out["status"] = handle("status", map_status, "status", optional=True)

    # category: unmappable text becomes empty and goes to the AI/human step later
    kind = missing_kind(d["category"])
    if kind:
        if kind != "blank":
            record("category", f"category_{kind}", "treated_as_missing")
        out["category"] = ""
    else:
        out["category"] = map_category(d["category"]) or ""
        if out["category"] == "":
            record("category", "category_unmappable", "cleared_invalid")
        elif out["category"] != d["category"]:
            record("category", "category_wording_standardised", "fixed", out["category"])

    # message
    out["message"] = tidy(d["message"])
    if out["message"] == "":
        flags.append("message_missing")
    elif out["message"] != d["message"]:
        record("message", "extra_whitespace_trimmed", "fixed", out["message"])

    # handling time
    kind = missing_kind(d["handling_mins"])
    if kind:
        out["handling_mins"] = ""
    else:
        mins = parse_minutes(d["handling_mins"])
        out["handling_mins"] = "" if mins is None else mins
        if mins is None:
            record("handling_mins", "handling_time_unreadable", "cleared_invalid")
        elif str(mins) != d["handling_mins"]:
            record("handling_mins", "units_removed", "fixed", str(mins))

    # details typed only in the free text: use them ONLY if exactly one clear candidate exists
    finders = {
        "email": lambda m: {normalise_email(x) for x in find_emails(m)} - {None},
        "phone": lambda m: {normalise_phone(x) for x in find_phone_candidates(m)} - {None},
        "postcode": lambda m: {normalise_postcode(x) for x in find_postcodes(m)} - {None},
    }
    for field, finder in finders.items():
        if out[field] == "":
            candidates = finder(out["message"])
            if len(candidates) == 1:
                out[field] = candidates.pop()
                record(field, f"{field}_found_in_message_text", "filled_from_message", out[field])
                flags = [f for f in flags if not f.startswith(field + "_")]
                flags.append(f"{field}_filled_from_message")

    if out["email"] == "" and out["phone"] == "":
        flags.append("no_contact_details")

    out["_flags"] = flags
    out["_changed"] = any(e["raw_row"] == raw_row and e["action"] in ("fixed", "filled_from_message") for e in log)
    return out


# ======================================================================
# Part 3 - duplicates
# ======================================================================

def message_key(text: str) -> str:
    return re.sub(r"\W+", " ", text.lower()).strip()


def remove_exact_duplicates(rows, log):
    seen, kept = {}, []
    for r in rows:
        key = (r["case_ref"], r["received_date"], message_key(r["message"]))
        if key in seen:
            log.append(dict(raw_row=r["raw_row"], field="(whole row)", issue="exact_duplicate", action="removed",
                            old_value="", new_value=f"same as raw row {seen[key]}"))
        else:
            seen[key] = r["raw_row"]
            kept.append(r)
    return kept


def flag_near_duplicates(rows, log):
    """Same person + similar message within a week. We FLAG these; a human decides."""
    for j, b in enumerate(rows):
        for a in rows[:j]:
            same_person = (
                (a["email"] and a["email"] == b["email"]) or (a["phone"] and a["phone"] == b["phone"])
                or (a["name"] and a["name"].casefold() == b["name"].casefold() and a["postcode"] and a["postcode"] == b["postcode"])
            )
            if not same_person:
                continue
            if a["received_date"] and b["received_date"]:
                gap = abs((date.fromisoformat(a["received_date"]) - date.fromisoformat(b["received_date"])).days)
                if gap > 7:
                    continue
            ratio = difflib.SequenceMatcher(None, message_key(a["message"]), message_key(b["message"])).ratio()
            if ratio >= 0.8:
                b["possible_duplicate_of"] = a["case_ref"] or f"raw row {a['raw_row']}"
                b["_flags"].append("possible_duplicate")
                log.append(dict(raw_row=b["raw_row"], field="(whole row)", issue="near_duplicate", action="flagged",
                                old_value="", new_value=f"looks like raw row {a['raw_row']} (similarity {ratio:.2f})"))
                break


# ======================================================================
# Part 4 - scoring: how good is the data, before and after?
# ======================================================================

def score_table(rows):
    """rows = list of dicts keyed by HEADER names. Returns completeness/validity/consistency %."""
    n = len(rows)
    missing = sum(is_missing(r.get(f, "")) for r in rows for f in KEY_FIELDS)
    completeness = 1 - missing / (n * len(KEY_FIELDS))

    valid = present = 0
    for r in rows:
        for f in VALID_FIELDS:
            if not is_missing(r.get(f, "")):
                present += 1
                valid += NORMALISERS[f](r[f]) is not None
    validity = valid / present

    consistent = present2 = 0
    for r in rows:
        for f in CONSISTENCY_FIELDS:
            if not is_missing(r.get(f, "")):
                present2 += 1
                consistent += NORMALISERS[f](r[f]) == tidy(r[f]) and str(r[f]) == tidy(r[f])
    consistency = consistent / present2
    return {"completeness": completeness, "validity": validity, "consistency": consistency}


def count_literal_duplicates(raw_cells):
    seen, dups = set(), 0
    for cells in raw_cells:
        if all(tidy(c) == "" for c in cells):
            continue
        key = tuple(cells)
        dups += key in seen
        seen.add(key)
    return dups


# ======================================================================
# Part 5 - check ourselves against the answer key
# ======================================================================

def ground_truth_check(clean_df):
    if not (TRUTH_FILE.exists() and MAP_FILE.exists()):
        return None
    truth = pd.read_csv(TRUTH_FILE, dtype=str, keep_default_na=False).set_index("enquiry_id")
    rmap = pd.read_csv(MAP_FILE, dtype=str, keep_default_na=False)
    rmap["raw_row"] = rmap["raw_row"].astype(int)
    merged = clean_df.merge(rmap, on="raw_row", how="left")
    originals = merged[merged["row_type"] == "original"]

    rows = []
    for field in ["case_ref", "received_date", "channel", "name", "email", "phone",
                  "postcode", "category", "urgency", "status", "handling_mins"]:
        correct = blank = wrong = 0
        for _, r in originals.iterrows():
            expected = r["enquiry_id"] if field == "case_ref" else truth.loc[r["enquiry_id"], field]
            got = "" if pd.isna(r[field]) else str(r[field])
            if got.endswith(".0"):
                got = got[:-2]
            if got == "":
                blank += 1
            elif got.casefold() == str(expected).casefold():  # names ignore capital letters
                correct += 1
            else:
                wrong += 1
        rows.append(dict(field=field, correct=correct, left_blank_and_flagged=blank, wrong=wrong))

    # personal-detail leak check on the masked message
    leaks = Counter()
    known = merged[merged["enquiry_id"].fillna("") != ""]  # every row we know the owner of, incl. repeats
    for _, r in known.iterrows():
        t, masked = truth.loc[r["enquiry_id"]], r["message_masked"]
        if t["email"].lower() in masked.lower(): leaks["email"] += 1
        if t["phone"] in masked or t["phone"].replace(" ", "") in masked.replace(" ", ""): leaks["phone"] += 1
        if t["postcode"].lower() in masked.lower(): leaks["postcode"] += 1
        if any(len(tok) >= 3 and re.search(rf"\b{re.escape(tok)}\b", masked, re.I) for tok in t["name"].split()): leaks["name"] += 1
        if re.search(r"\b\d{1,4} [A-Za-z]+ (Street|Road|Avenue|Lane|Close|Drive|Way|Court|Gardens|Crescent|Terrace|Grove|Place)\b", masked, re.I): leaks["address"] += 1
        if re.search(r"\bQQ\s?\d{2}\s?\d{2}\s?\d{2}\s?[A-D]\b", masked, re.I): leaks["ni_number"] += 1

    types = merged["row_type"].value_counts().to_dict()
    flagged = merged[merged["possible_duplicate_of"].fillna("") != ""]
    summary = {
        "exact_duplicates_left_in_data": int(types.get("exact_duplicate", 0)),
        "near_duplicates_flagged_correctly": int((flagged["row_type"] == "near_duplicate").sum()),
        "near_duplicates_in_data": int(types.get("near_duplicate", 0)),
        "originals_wrongly_flagged_as_duplicate": int((flagged["row_type"] == "original").sum()),
        "pii_leaks": dict(leaks),
        "n_original_rows_checked": len(originals), "n_rows_leak_checked": len(known),
    }
    sugg = originals[originals["category_ai_suggestion"].fillna("") != ""]
    if len(sugg):
        right = sum(truth.loc[r["enquiry_id"], "category"] == r["category_ai_suggestion"] for _, r in sugg.iterrows())
        summary["ai_suggestions"] = len(sugg)
        summary["ai_suggestions_correct"] = int(right)
    return pd.DataFrame(rows), summary


# ======================================================================
# Part 6 - run everything
# ======================================================================

def pct(x):
    return f"{x * 100:.1f}%"


def main():
    use_ai = "--no-ai" not in sys.argv
    OUT.mkdir(parents=True, exist_ok=True)

    with open(RAW_FILE, newline="", encoding="utf-8-sig") as f:
        all_rows = list(csv.reader(f))
    raw_cells = all_rows[1:]
    print(f"Read {len(raw_cells)} raw rows from {RAW_FILE.relative_to(ROOT)}")

    # BEFORE scores: the sheet exactly as a person would see it (first 12 columns)
    before_rows = [dict(zip(HEADER, (c + [""] * 12)[:12])) for c in raw_cells]
    non_blank_before = [r for r in before_rows if any(tidy(v) for v in r.values())]
    before = score_table(before_rows)
    before_dups = count_literal_duplicates(raw_cells)
    before["uniqueness"] = 1 - before_dups / len(non_blank_before)

    # CLEAN
    log, rows = [], []
    for n, cells in enumerate(raw_cells, start=1):
        if all(tidy(c) == "" for c in cells):
            log.append(dict(raw_row=n, field="(whole row)", issue="blank_row", action="removed", old_value="", new_value=""))
            continue
        rows.append(clean_row(realign(cells, n, log), n, log))
    n_before_dedupe = len(rows)
    rows = remove_exact_duplicates(rows, log)
    for r in rows:
        r["possible_duplicate_of"] = ""
    flag_near_duplicates(rows, log)

    # AI help for categories the rules could not work out (masked text only)
    tracker = ai_client.CostTracker()
    mode = "demo mode (keyword matcher, no API key)" if ai_client.is_demo() else f"Claude {ai_client.MODEL}"
    for r in rows:
        r["category_ai_suggestion"], r["category_ai_confidence"], r["category_ai_note"] = "", "", ""
        r["message_masked"] = mask_pii(r["message"], r["name"])
        if r["category"] == "" and use_ai:
            try:
                suggestion, note = ai_assist.suggest_category(r["message_masked"], tracker)
            except ai_client.BudgetExceeded as e:
                print(e)
                break
            r["category_ai_note"] = note
            if suggestion:
                r["category_ai_suggestion"], r["category_ai_confidence"] = suggestion.category, suggestion.confidence
                r["_flags"].append("category_ai_suggested")
                log.append(dict(raw_row=r["raw_row"], field="category", issue="category_unresolved_by_rules",
                                action="ai_suggested", old_value="", new_value=f"{suggestion.category} ({suggestion.confidence:.2f}) - needs human check"))
                continue
        if r["category"] == "":
            r["_flags"].append("category_unresolved")

    # final status per row
    for r in rows:
        r["quality_flags"] = "; ".join(dict.fromkeys(r["_flags"]))
        if set(r["_flags"]) & REVIEW_FLAGS:
            r["quality_status"] = "needs_review"
        else:
            r["quality_status"] = "fixed" if r["_changed"] else "clean"

    cols = ["raw_row"] + HEADER[:10] + ["message_masked", "status", "handling_mins", "category_ai_suggestion",
            "category_ai_confidence", "category_ai_note", "possible_duplicate_of", "quality_flags", "quality_status"]
    clean_df = pd.DataFrame(rows)[cols]
    clean_df.to_csv(OUT / "enquiries_clean.csv", index=False, encoding="utf-8")
    log_df = pd.DataFrame(log, columns=["raw_row", "field", "issue", "action", "old_value", "new_value"])
    log_df.to_csv(OUT / "data_quality_log.csv", index=False, encoding="utf-8")

    # AFTER scores
    after = score_table([{k: ("" if pd.isna(v) else v) for k, v in rec.items()} for rec in clean_df.to_dict("records")])
    after_dups = len(clean_df) - len(clean_df.drop_duplicates(subset=["case_ref", "received_date", "message"]))
    after["uniqueness"] = 1 - after_dups / len(clean_df)
    near_flagged = int((clean_df["possible_duplicate_of"].fillna("") != "").sum())

    scores = pd.DataFrame([
        dict(metric="Completeness", before=before["completeness"], after=after["completeness"],
             meaning="Share of the 10 key fields that hold a real value"),
        dict(metric="Uniqueness", before=before["uniqueness"], after=after["uniqueness"],
             meaning="Share of rows that are not exact repeats"),
        dict(metric="Validity", before=before["validity"], after=after["validity"],
             meaning="Share of filled-in values that are real, readable values"),
        dict(metric="Consistency", before=before["consistency"], after=after["consistency"],
             meaning="Share of filled-in values already in the one standard format"),
    ])
    scores.to_csv(OUT / "quality_scores.csv", index=False)

    gt = ground_truth_check(clean_df)
    if gt:
        gt[0].to_csv(OUT / "ground_truth_check.csv", index=False)

    write_report(scores, clean_df, log_df, before_dups, near_flagged, n_before_dedupe, len(raw_cells), gt, tracker, mode, use_ai)

    print("\nQuality scores (before -> after):")
    for _, s in scores.iterrows():
        print(f"  {s['metric']:<13}{pct(s['before']):>8}  ->  {pct(s['after'])}")
    print(f"\nRows: {len(raw_cells)} raw -> {len(clean_df)} cleaned "
          f"({len(raw_cells) - n_before_dedupe} blank removed, {n_before_dedupe - len(clean_df)} exact duplicates removed)")
    print("Row status:", clean_df["quality_status"].value_counts().to_dict())
    if gt:
        print("\nChecked against the answer key (original rows only):")
        print(gt[0].to_string(index=False))
        print(gt[1])
    print(f"\nAI step: {mode}" + (f", {tracker.calls} calls, about £{tracker.cost_gbp:.4f}" if not ai_client.is_demo() else ""))
    print(f"Full report: {(OUT / 'quality_report.md').relative_to(ROOT)}")


def write_report(scores, clean_df, log_df, before_dups, near_flagged, n_before_dedupe, n_raw, gt, tracker, mode, use_ai):
    L = []
    L.append("# Data quality report - Northfield Services (synthetic data)\n")
    L.append("Everything here is made-up data. Scores compare the raw legacy sheet with the cleaned table.\n")
    L.append("## Scores: before vs after\n")
    L.append("| Measure | Before | After | What it means |\n|---|---|---|---|")
    for _, s in scores.iterrows():
        L.append(f"| {s['metric']} | {pct(s['before'])} | {pct(s['after'])} | {s['meaning']} |")
    L.append("\n**Read this honestly:** validity and consistency reach ~100% *by design*, because a value that cannot be "
             "trusted is emptied and flagged rather than guessed. The trade-off shows in completeness, which cannot "
             "return to 100% without inventing data.\n")
    L.append("## What happened to the rows\n")
    L.append(f"- Raw rows: **{n_raw}**")
    L.append(f"- Blank rows removed: **{n_raw - n_before_dedupe}**")
    L.append(f"- Exact duplicate rows removed: **{n_before_dedupe - len(clean_df)}** (found {before_dups} literal repeats in the raw sheet)")
    L.append(f"- Cleaned rows: **{len(clean_df)}**")
    L.append(f"- Possible near-duplicates **flagged, not deleted**: **{near_flagged}** (a person decides)")
    L.append("\nRow status after clean-up:")
    for k, v in clean_df["quality_status"].value_counts().items():
        L.append(f"- {k}: {v}")
    L.append("\n## What the rules changed (from the log)\n")
    L.append("| Issue | Action | Count |\n|---|---|---|")
    for (issue, action), n in log_df.groupby(["issue", "action"]).size().sort_values(ascending=False).items():
        L.append(f"| {issue} | {action} | {n} |")
    L.append("\n## The AI step\n")
    if not use_ai:
        L.append("Skipped (`--no-ai`).")
    else:
        sug = int((clean_df["category_ai_suggestion"].fillna("") != "").sum())
        L.append(f"- Mode: **{mode}**")
        L.append(f"- Rows where rules could not set a category: **{int((clean_df['category'].fillna('') == '').sum())}**; "
                 f"AI suggested a category for **{sug}**. Suggestions sit in their own column and are flagged for a human.")
        L.append("- Only the *masked* message (no names, phones, emails, addresses, postcodes) is ever sent.")
        if not ai_client.is_demo():
            L.append(f"- Claude calls: {tracker.calls}; estimated cost about £{tracker.cost_gbp:.4f} (price figures are assumptions - check the Claude Console).")
    if gt:
        table, s = gt
        L.append("\n## Checked against the answer key\n")
        L.append(f"Compared {s['n_original_rows_checked']} cleaned rows with the known-correct data. "
                 "\"Wrong\" is the number to watch: a cleaner that confidently writes bad data is worse than one that leaves a gap.\n")
        L.append("| Field | Correct | Left blank & flagged | Wrong |\n|---|---|---|---|")
        for _, r in table.iterrows():
            L.append(f"| {r['field']} | {r['correct']} | {r['left_blank_and_flagged']} | {r['wrong']} |")
        L.append(f"\n- Exact duplicates still in the data: **{s['exact_duplicates_left_in_data']}**")
        L.append(f"- Near-duplicates caught: **{s['near_duplicates_flagged_correctly']} of {s['near_duplicates_in_data']}**; "
                 f"real enquiries wrongly flagged as duplicates: **{s['originals_wrongly_flagged_as_duplicate']}**")
        L.append(f"- Personal details leaking into the masked text: **{sum(s['pii_leaks'].values())}** {s['pii_leaks'] or ''}")
        if "ai_suggestions" in s:
            L.append(f"- AI category suggestions that were right: **{s['ai_suggestions_correct']} of {s['ai_suggestions']}**")
    L.append("\n## Assumptions and limits\n")
    L.append("- Dates like 04/11/2025 are read as **day/month** (UK).")
    L.append("- Names typed in all capitals or lower case are title-cased; names like McDonald can lose their inner capital.")
    L.append("- A phone/email/postcode found in the free text is used only if there is exactly one clear candidate. It is logged as `filled_from_message`.")
    L.append("- A postcode is accepted if its shape is right and its area (e.g. M, SK, OL) exists. We have no full postcode database, so a typo that still looks real would pass.")
    L.append("- Everything is synthetic; real data would need a data-protection review before any of this ran on it.")
    (OUT / "quality_report.md").write_text("\n".join(L) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
