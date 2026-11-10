"""
generate_data.py - Phase 1: make fake, realistically messy council enquiries.

Everything here is INVENTED. Names come from a fake-name library, emails use
reserved example domains, and "Northfield Services" is a fictional company.

It writes three files:
  data/raw/enquiries_raw.csv             the messy "legacy spreadsheet"
  data/ground_truth/enquiries_truth.csv  the correct answer for each real enquiry
  data/ground_truth/raw_row_map.csv      which raw row is which enquiry, and what we broke

Run:  python src/generate_data.py      (same result every time - the seed is fixed)
"""
import csv
import random
import re
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

from faker import Faker

ROOT = Path(__file__).resolve().parent.parent
RAW_FILE = ROOT / "data" / "raw" / "enquiries_raw.csv"
TRUTH_FILE = ROOT / "data" / "ground_truth" / "enquiries_truth.csv"
MAP_FILE = ROOT / "data" / "ground_truth" / "raw_row_map.csv"

SEED = 42  # fixed seed = the "random" data is identical on every run
N_ENQUIRIES = 300
N_NEAR_DUPES = 12   # same person re-sending the same enquiry (new case number)
N_EXACT_DUPES = 10  # the identical row pasted in twice
N_BLANK_ROWS = 8
N_SWAPPED = 8       # values in the wrong column
N_SHIFTED = 6       # whole row nudged one column across
START_DATE = date(2025, 10, 1)  # one fictional contract quarter
QUARTER_DAYS = 91

rng = random.Random(SEED)
fake = Faker("en_GB")
fake.seed_instance(SEED)

COLUMNS = ["case_ref", "received_date", "channel", "name", "email", "phone",
           "postcode", "category", "urgency", "message", "status", "handling_mins"]

CATEGORIES = ["Housing Repairs", "Noise", "Waste", "Billing", "Complaints", "Safety"]
CATEGORY_WEIGHTS = [28, 15, 20, 15, 12, 10]

# (urgency, message). {addr} becomes a made-up street address.
TEMPLATES = {
    "Housing Repairs": [
        ("Low", "The kitchen cabinet door at {addr} has come off its hinge. Could someone repair it when convenient?"),
        ("Low", "There is a small crack in the bathroom tiles at {addr}. It is not leaking but I would like it fixed."),
        ("Medium", "My boiler at {addr} stopped working two days ago and we have no hot water. Please send an engineer."),
        ("Medium", "The front door lock at {addr} is sticking and I'm worried it will jam shut."),
        ("High", "Water is pouring through my bedroom ceiling at {addr} from the flat above and it is getting worse."),
        ("High", "No heating or hot water at {addr} for four days. I have a baby and the temperature is dropping."),
    ],
    "Noise": [
        ("Low", "The neighbour near {addr} plays loud music most Saturday afternoons. Not late, but it is annoying."),
        ("Medium", "Dogs next door to {addr} bark for hours every day while the owners are out."),
        ("Medium", "Loud parties in the flat below {addr} go on past midnight, three nights this week."),
        ("Medium", "A drill starts at 6am every day at the building site by {addr}. I work nights and cannot sleep."),
        ("High", "Violent shouting and banging from the flat next to {addr} most nights. I am scared for the children living there."),
    ],
    "Waste": [
        ("Low", "Our recycling bin at {addr} was not emptied this week."),
        ("Low", "Could I order a replacement green bin for {addr}? Ours was damaged."),
        ("Medium", "An old sofa has been dumped in the alley behind {addr} for over a week."),
        ("Medium", "Missed bin collections three weeks in a row at {addr} and the bins are overflowing."),
        ("Medium", "Rats have been seen around the overflowing bins at {addr}."),
        ("High", "Fly-tipped rubbish including broken glass and needles has been left in the play area near {addr}."),
    ],
    "Billing": [
        ("Low", "I would like to set up a direct debit for my council tax at {addr}."),
        ("Low", "Can you send me a copy of my latest rent statement for {addr}?"),
        ("Medium", "I have been charged twice for my November council tax payment. Please refund the extra amount."),
        ("Medium", "My bill says I owe arrears but I paid in full last month. I have the receipt."),
        ("Medium", "I have lost my job and cannot pay my rent this month. What support is available?"),
        ("High", "I received a final demand and a court summons for council tax I already paid. The hearing is next week."),
    ],
    "Complaints": [
        ("Low", "The adviser I spoke to on Monday was rude. I would like this feedback passed on."),
        ("Low", "Your website is confusing and I could not find the form for bulky waste."),
        ("Medium", "I reported a repair six weeks ago and nobody has been in touch. This is my second chaser."),
        ("Medium", "I am unhappy with how my housing application was handled. Nobody explained the decision."),
        ("High", "This is my third formal complaint. If I do not get a reply within 48 hours I will go to the Ombudsman and my MP."),
    ],
    "Safety": [
        ("High", "I can smell gas in the communal hallway at {addr}."),
        ("High", "The handrail on the stairs at {addr} has come away from the wall and an elderly resident nearly fell."),
        ("High", "Exposed electrical wires are hanging from the ceiling in the stairwell at {addr}."),
        ("High", "A fire door at {addr} is propped open with a wedge and the fire alarm has been beeping for days."),
        ("Medium", "The street light outside {addr} has been out for a week and the pavement is very dark."),
        ("Medium", "There is a large pothole outside {addr}. A cyclist fell off this morning."),
    ],
}

STREETS = ["Alder Street", "Brook Road", "Cedar Avenue", "Dale Lane", "Elm Close", "Foster Drive",
           "Grove Way", "Hawthorn Court", "Iris Gardens", "Juniper Crescent", "Kestrel Terrace",
           "Lime Grove", "Mill Place", "Orchard Road"]
OPENERS = ["Hi,", "Hello,", "To whom it may concern,", "Hello Northfield Services,", "Good morning,"]
SIGNOFFS = ["Regards, {name}", "Thanks, {name}", "Kind regards, {name}", "Many thanks, {name}",
            "My name is {name}."]
EMAIL_DOMAINS = ["example.com", "example.org", "example.net"]  # reserved for examples - never real
AREAS = ["M", "M", "M", "SK", "OL", "BL", "WA", "WN"]
INWARD_LETTERS = "ABDEFGHJLNPQRSTUWXYZ"

PLACEHOLDERS = ["N/A", "n/a", "TBC", "unknown", "-", "none", "xxx", "?"]
HIDDEN_BLANKS = [" ", "   ", " ", "\t", "​"]  # look empty, but are not

CATEGORY_VARIANTS = {
    "Housing Repairs": ["housing repairs", "Housing repair", "Repairs", "HOUSING", "Housing - Repairs"],
    "Noise": ["noise", "Noise complaint", "NOISE", "Noise Nuisance"],
    "Waste": ["waste & recycling", "Bins", "Waste and Recycling", "WASTE", "bin collection"],
    "Billing": ["Council Tax", "billing", "Rent/Billing", "Payments", "BILLING"],
    "Complaints": ["Complaint", "complaints", "COMPLAINT", "Customer complaint"],
    "Safety": ["Health & Safety", "safety", "H&S", "SAFETY", "Safety hazard"],
}
URGENCY_VARIANTS = {
    "High": ["high", "HIGH", "Urgent", "urgent", "P1", "1 - High"],
    "Medium": ["medium", "Med", "MEDIUM", "P2", "normal"],
    "Low": ["low", "LOW", "P3", "L"],
}
CHANNEL_VARIANTS = {
    "Email": ["email", "E-mail", "EMAIL", "e-mail"],
    "Web form": ["Webform", "web form", "WEB FORM", "Web Form", "web"],
}
STATUS_VARIANTS = {
    "Closed": ["closed", "CLOSED", "Complete", "Done"],
    "Open": ["open", "OPEN", "In progress", "Pending"],
}
UNMAPPABLE_CATEGORIES = ["Other", "General enquiry", "misc", "?"]


# ---------- small helpers ----------

def chance(p: float) -> bool:
    return rng.random() < p


def format_phone(d: str) -> str:
    """Standard format: 0161 123 4567 for Manchester, otherwise 07123 456789."""
    return f"{d[:4]} {d[4:7]} {d[7:]}" if d.startswith("0161") else f"{d[:5]} {d[5:]}"


def make_phone() -> str:
    if chance(0.7):
        d = "07" + str(rng.randint(100, 999)) + str(rng.randint(100000, 999999))
    else:
        d = "0161" + str(rng.randint(2000000, 9999999))
    return format_phone(d)


def make_postcode() -> str:
    outward = rng.choice(AREAS) + str(rng.randint(1, 30))
    inward = str(rng.randint(1, 9)) + "".join(rng.choice(INWARD_LETTERS) for _ in range(2))
    return f"{outward} {inward}"


def make_ni_number() -> str:
    """'QQ' prefixes are never issued to real people, so this can't be anyone's number."""
    return f"QQ{rng.randint(10, 99)}{rng.randint(10, 99)}{rng.randint(10, 99)}{rng.choice('ABCD')}"


# ---------- step 1: the correct (ground truth) records ----------

def make_message(template_text: str, rec: dict, buried: set) -> str:
    addr = f"{rng.randint(1, 120)} {rng.choice(STREETS)}"
    if chance(0.12):
        addr += f", {rec['postcode']}"
    parts = []
    if chance(0.35):
        parts.append(rng.choice(OPENERS))
    parts.append(template_text.format(addr=addr))
    if "phone" in buried or chance(0.10):
        parts.append(rng.choice(["You can ring me on {p}.", "My number is {p}."]).format(p=rec["phone"]))
    if "email" in buried or chance(0.06):
        parts.append(f"My email is {rec['email']}.")
    if "postcode" in buried:
        parts.append(f"My postcode is {rec['postcode']}.")
    if chance(0.03):
        parts.append(f"My National Insurance number is {make_ni_number()}.")
    if chance(0.45):
        parts.append(rng.choice(SIGNOFFS).format(name=rec["name"]))
    return " ".join(parts)


def make_truth(i: int) -> dict:
    category = rng.choices(CATEGORIES, weights=CATEGORY_WEIGHTS)[0]
    urgency, template = rng.choice(TEMPLATES[category])
    first, last = fake.first_name(), fake.last_name()
    local = re.sub(r"[^a-z0-9.]", "", f"{first}.{last}".lower())
    rec = {
        "enquiry_id": f"NF-2025-{i:04d}",
        "received_date": START_DATE + timedelta(days=rng.randint(0, QUARTER_DAYS - 1)),
        "channel": rng.choice(["Email", "Web form"]),
        "name": f"{first} {last}",
        "email": f"{local}@{rng.choice(EMAIL_DOMAINS)}",
        "phone": make_phone(),
        "postcode": make_postcode(),
        "category": category,
        "urgency": urgency,
    }
    buried = {f for f in ("email", "phone", "postcode") if chance(0.07)}
    rec["message"] = make_message(template, rec, buried)
    rec["_buried"] = buried  # remembered only so we can blank those columns later
    if chance(0.85):
        rec["status"] = "Closed"
        ranges = {"Low": (3, 9), "Medium": (6, 16), "High": (10, 35)}
        rec["handling_mins"] = rng.randint(*ranges[urgency])
    else:
        rec["status"], rec["handling_mins"] = "Open", ""
    return rec


def make_near_duplicate(rec: dict, new_number: int) -> dict:
    """Same person sends the same enquiry again, with a new case number."""
    dup = dict(rec)
    dup["enquiry_id"] = f"NF-2025-{new_number:04d}"
    dup["_source_id"] = rec["enquiry_id"]
    dup["received_date"] = rec["received_date"] + timedelta(days=rng.randint(0, 3))
    dup["message"] = rng.choice([
        rec["message"].lower(),
        rec["message"] + " Please reply ASAP.",
        rec["message"] + " Any update?",
        rec["message"].replace(".", "!", 1),
    ])
    return dup


# ---------- step 2: break the data like a real legacy system ----------

def mess_date(d: date):
    r = rng.random()
    if r < 0.25: return d.strftime("%Y-%m-%d"), None
    if r < 0.65: return d.strftime("%d/%m/%Y"), "date:uk_slash_format"
    if r < 0.72: return d.strftime("%d/%m/%y"), "date:two_digit_year"
    if r < 0.82: return d.strftime("%d-%b-%Y"), "date:text_month"
    if r < 0.89: return d.strftime("%d %B %Y"), "date:long_text_month"
    if r < 0.94: return str((d - date(1899, 12, 30)).days), "date:excel_serial_number"
    if r < 0.97: return rng.choice([d.strftime("%b %Y"), str(d.year)]), "date:partial"
    if r < 0.99: return rng.choice(["00/00/0000", "TBC"]), "date:placeholder"
    return "", "date:blank"


def mess_phone(p: str):
    d = p.replace(" ", "")
    r = rng.random()
    if r < 0.05: return "", "phone:blank"
    if r < 0.08: return rng.choice(HIDDEN_BLANKS), "phone:hidden_blank"
    if r < 0.14: return rng.choice(["0000000000", "N/A", "unknown", "TBC", "01234567890"]), "phone:placeholder"
    if r < 0.18: return rng.choice([d[:7], d[:-3], "123", d + "9"]), "phone:invalid"
    if r < 0.24: return d[1:], "phone:lost_leading_zero"
    if r < 0.34: return d, "phone:no_spaces"
    if r < 0.42: return f"+44 {d[1:5]} {d[5:]}", "phone:plus44"
    if r < 0.48: return f"+44{d[1:]}", "phone:plus44_no_spaces"
    if r < 0.54: return f"{d[:5]}-{d[5:]}", "phone:dashes"
    if r < 0.60: return f"({d[:4]}) {d[4:7]} {d[7:]}", "phone:brackets"
    return p, None


def mess_email(e: str):
    r = rng.random()
    if r < 0.03: return "", "email:blank"
    if r < 0.05: return rng.choice(HIDDEN_BLANKS), "email:hidden_blank"
    if r < 0.08: return rng.choice(["N/A", "none", "test@test.com", "noemail@noemail.com"]), "email:placeholder"
    if r < 0.13: return rng.choice([e.replace("@", ""), e.split("@")[0] + "@", e.rsplit(".", 1)[0]]), "email:invalid"
    if r < 0.20: return (e.upper() if chance(0.5) else f" {e} "), "email:case_or_spaces"
    return e, None


def mess_postcode(pc: str):
    r = rng.random()
    if r < 0.03: return "", "postcode:blank"
    if r < 0.05: return rng.choice(HIDDEN_BLANKS), "postcode:hidden_blank"
    if r < 0.08: return rng.choice(["N/A", "unknown", "TBC", "ZZ99 9ZZ"]), "postcode:placeholder"
    if r < 0.12: return rng.choice([pc[:-1], pc.split()[0], pc.replace(" ", "")[1:]]), "postcode:invalid"
    if r < 0.20: return rng.choice([pc.lower(), pc.replace(" ", ""), pc.lower().replace(" ", ""), f" {pc} "]), "postcode:case_or_spacing"
    return pc, None


def mess_name(n: str):
    r = rng.random()
    if r < 0.03: return rng.choice(PLACEHOLDERS), "name:placeholder"
    if r < 0.06: return "", "name:blank"
    if r < 0.10: return rng.choice(HIDDEN_BLANKS), "name:hidden_blank"
    if r < 0.16: return (n.upper() if chance(0.5) else n.lower()), "name:case"
    if r < 0.20 and " " in n:
        first, last = n.split(" ", 1)
        return f"{last}, {first}", "name:surname_first"
    if r < 0.25: return "  " + n.replace(" ", "  ") + " ", "name:extra_spaces"
    return n, None


def mess_from_variants(value: str, variants: dict, field: str, blank_p: float, odd_p: float = 0.35):
    r = rng.random()
    if r < blank_p: return "", f"{field}:blank"
    if r < blank_p + 0.02: return rng.choice(HIDDEN_BLANKS), f"{field}:hidden_blank"
    if r < blank_p + 0.02 + odd_p: return rng.choice(variants[value]), f"{field}:inconsistent_wording"
    return value, None


def corrupt_record(rec: dict):
    """Turn one correct record into one messy row. Returns (12 cells, list of tags)."""
    tags = []

    def note(tag):
        if tag:
            tags.append(tag)

    cells = {}
    cells["case_ref"], t = (rec["enquiry_id"], None)
    r = rng.random()
    if r < 0.03: cells["case_ref"], t = rec["enquiry_id"].lower(), "case_ref:lowercase"
    elif r < 0.05: cells["case_ref"], t = rec["enquiry_id"].replace("-", " "), "case_ref:spaces"
    elif r < 0.07: cells["case_ref"], t = "", "case_ref:blank"
    note(t)
    cells["received_date"], t = mess_date(rec["received_date"]); note(t)
    cells["channel"], t = mess_from_variants(rec["channel"], CHANNEL_VARIANTS, "channel", 0.03, 0.30); note(t)
    cells["name"], t = mess_name(rec["name"]); note(t)
    cells["email"], t = mess_email(rec["email"]); note(t)
    cells["phone"], t = mess_phone(rec["phone"]); note(t)
    cells["postcode"], t = mess_postcode(rec["postcode"]); note(t)

    r = rng.random()
    if r < 0.04: cells["category"], t = "", "category:blank"
    elif r < 0.07: cells["category"], t = rng.choice(UNMAPPABLE_CATEGORIES), "category:unmappable"
    elif r < 0.09: cells["category"], t = rng.choice(HIDDEN_BLANKS), "category:hidden_blank"
    else: cells["category"], t = mess_from_variants(rec["category"], CATEGORY_VARIANTS, "category", 0.0, 0.35)
    note(t)
    cells["urgency"], t = mess_from_variants(rec["urgency"], URGENCY_VARIANTS, "urgency", 0.22, 0.35); note(t)

    msg = rec["message"]
    r = rng.random()
    if r < 0.01: msg, t = "", "message:blank"
    elif r < 0.09: msg, t = msg.replace(". ", ".\n", 1) + "  ", "message:stray_whitespace"
    else: t = None
    cells["message"] = msg; note(t)

    cells["status"], t = mess_from_variants(rec["status"], STATUS_VARIANTS, "status", 0.0, 0.35); note(t)
    mins = rec["handling_mins"]
    if mins != "":
        r = rng.random()
        if r < 0.15: mins, t = f"{mins} mins", "handling_mins:has_units"
        elif r < 0.20: mins, t = f"{mins}min", "handling_mins:has_units"
        else: t = None
        note(t)
    cells["handling_mins"] = str(mins)

    # Details that exist ONLY inside the free-text message (column left empty)
    for f in rec["_buried"]:
        cells[f] = rng.choice(["", "", rng.choice(HIDDEN_BLANKS), "N/A"])
        tags[:] = [x for x in tags if not x.startswith(f + ":")]
        tags.append(f"{f}:only_in_message_text")

    return [cells[c] for c in COLUMNS], tags


# ---------- step 3: put it all together ----------

def build():
    truths = [make_truth(i) for i in range(1, N_ENQUIRIES + 1)]

    near_sources = rng.sample(truths, N_NEAR_DUPES)
    near_dupes = [make_near_duplicate(src, N_ENQUIRIES + 1 + k) for k, src in enumerate(near_sources)]

    records = []  # every enquiry-like row we will break, oldest first
    for rec in truths:
        records.append({"rec": rec, "source": rec["enquiry_id"], "type": "original"})
    for rec in near_dupes:
        records.append({"rec": rec, "source": rec["_source_id"], "type": "near_duplicate"})
    records.sort(key=lambda r: (r["rec"]["received_date"], r["rec"]["enquiry_id"]))

    rows = []
    for r in records:
        cells, tags = corrupt_record(r["rec"])
        rows.append({"cells": cells, "enquiry_id": r["source"], "type": r["type"], "tags": tags})

    # values in the wrong column (only on rows where both columns were otherwise fine)
    def untouched(row, *fields):
        return not any(t.split(":")[0] in fields for t in row["tags"])

    ci = COLUMNS.index
    swap_name_email = [r for r in rows if r["type"] == "original" and untouched(r, "name", "email")]
    swap_phone_pc = [r for r in rows if r["type"] == "original" and untouched(r, "phone", "postcode")]
    for r in rng.sample(swap_name_email, N_SWAPPED // 2):
        a, b = ci("name"), ci("email")
        r["cells"][a], r["cells"][b] = r["cells"][b], r["cells"][a]
        r["tags"].append("structure:name_email_swapped")
    for r in rng.sample(swap_phone_pc, N_SWAPPED // 2):
        a, b = ci("phone"), ci("postcode")
        r["cells"][a], r["cells"][b] = r["cells"][b], r["cells"][a]
        r["tags"].append("structure:phone_postcode_swapped")

    # whole row shifted one column to the right (an extra empty cell appears)
    plain = [r for r in rows if "structure:name_email_swapped" not in r["tags"]
             and "structure:phone_postcode_swapped" not in r["tags"]]
    for r in rng.sample(plain, N_SHIFTED):
        r["cells"].insert(rng.randint(0, 3), "")
        r["tags"].append("structure:shifted_columns")

    # identical rows pasted in twice, a little further down
    for src in rng.sample(rows, N_EXACT_DUPES):
        copy = {"cells": list(src["cells"]), "enquiry_id": src["enquiry_id"],
                "type": "exact_duplicate", "tags": src["tags"] + ["structure:exact_duplicate"]}
        rows.insert(min(len(rows), rows.index(src) + rng.randint(1, 25)), copy)

    # completely empty rows (some look empty but hold spaces)
    for k in range(N_BLANK_ROWS):
        cells = [""] * len(COLUMNS) if k % 3 else [rng.choice(HIDDEN_BLANKS) for _ in COLUMNS]
        rows.insert(rng.randint(1, len(rows)), {"cells": cells, "enquiry_id": "", "type": "blank_row",
                                                "tags": ["structure:blank_row"]})
    return truths, rows


def write_files(truths, rows):
    for f in (RAW_FILE, TRUTH_FILE, MAP_FILE):
        f.parent.mkdir(parents=True, exist_ok=True)

    with open(RAW_FILE, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(COLUMNS)
        for r in rows:
            w.writerow(r["cells"])

    with open(TRUTH_FILE, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["enquiry_id"] + COLUMNS[1:])
        for t in sorted(truths, key=lambda x: x["enquiry_id"]):
            w.writerow([t["enquiry_id"], t["received_date"].isoformat()] + [t[c] for c in COLUMNS[2:]])

    with open(MAP_FILE, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["raw_row", "enquiry_id", "row_type", "issue_tags"])
        for n, r in enumerate(rows, start=1):
            w.writerow([n, r["enquiry_id"], r["type"], "|".join(r["tags"])])


def check_ground_truth(truths):
    """Re-read the files from disk and prove the answer key matches every raw row."""
    with open(RAW_FILE, newline="", encoding="utf-8-sig") as f:
        raw_rows = list(csv.reader(f))[1:]
    with open(MAP_FILE, newline="", encoding="utf-8") as f:
        mapping = list(csv.DictReader(f))
    truth_ids = {t["enquiry_id"] for t in truths}

    assert len(raw_rows) == len(mapping), "every raw row must have a map entry"
    for m in mapping:
        if m["row_type"] == "blank_row":
            assert m["enquiry_id"] == ""
        else:
            assert m["enquiry_id"] in truth_ids, f"row {m['raw_row']} points at an unknown enquiry"
    covered = {m["enquiry_id"] for m in mapping if m["row_type"] == "original"}
    assert covered == truth_ids, "every true enquiry must appear exactly once as an original row"
    print("Ground-truth check passed: every raw row is accounted for.")
    return mapping


def main():
    truths, rows = build()
    write_files(truths, rows)
    mapping = check_ground_truth(truths)

    types = Counter(m["row_type"] for m in mapping)
    print(f"\nWrote {len(rows)} raw rows to {RAW_FILE.relative_to(ROOT)}")
    for k, v in sorted(types.items()):
        print(f"  {k:<16}{v}")
    tag_counts = Counter(t for m in mapping for t in m["issue_tags"].split("|") if t)
    problems = Counter()
    for tag, n in tag_counts.items():
        problems[tag.split(":")[1] if ":" in tag else tag] += n
    print("\nProblems planted (so we can check the clean-up later):")
    for tag, n in sorted(problems.items(), key=lambda x: -x[1]):
        print(f"  {tag:<28}{n}")


if __name__ == "__main__":
    main()
