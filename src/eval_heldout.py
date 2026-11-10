"""
eval_heldout.py - test a triage prompt on a NEW set of 60 messages that was written and labelled
BEFORE the improved prompt was written (data/heldout/heldout_messages.csv).

Why: tuning a prompt on the same 300 enquiries it is scored on inflates the score. This set checks the
change on messages the prompt was not tuned on. (It is still written by the same assistant that wrote the
prompt, and it is only 60 messages, so treat the result as a signal, not proof.)

Run:  python src/eval_heldout.py v1        (baseline prompt)
      python src/eval_heldout.py v2        (improved prompt)
Needs an API key in .env. Cost: about £0.09 per run (price figures assumed).
"""
import csv
import sys

import ai_client
import pii
import triage

HELDOUT = ai_client.ROOT / "data" / "heldout" / "heldout_messages.csv"
OUT_DIR = ai_client.ROOT / "data" / "heldout"


def main():
    version = sys.argv[1] if len(sys.argv) > 1 else triage.DEFAULT_PROMPT
    if ai_client.is_demo():
        raise SystemExit("This needs a real API key in .env (it tests a real prompt).")
    if version not in triage.PROMPTS:
        raise SystemExit(f"Unknown prompt version {version}. Available: {list(triage.PROMPTS)}")
    rows = list(csv.DictReader(open(HELDOUT, newline="", encoding="utf-8")))
    tracker = ai_client.CostTracker()
    out = []
    for r in rows:
        masked = pii.mask_pii(r["message"])
        result, error = triage.claude_triage(masked, tracker, version)
        if result is None:
            out.append({**r, "ai_category": "", "ai_urgency": "", "confidence": "", "secondary": "", "review": 1, "why": error})
            continue
        needs, why = triage.apply_review_rules(result)
        out.append({**r, "ai_category": result["category"], "ai_urgency": result["urgency"], "confidence": result["confidence"],
                    "secondary": result.get("secondary_category") or "", "review": int(needs), "why": why})

    path = OUT_DIR / f"results_{version}.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader(); w.writerows(out)

    normal = [o for o in out if o["tag"] == "normal"]
    cat_ok = sum(o["ai_category"] == o["true_category"] for o in normal)
    urg_ok = sum(o["ai_urgency"] == o["true_urgency"] for o in normal)
    urgent = [o for o in normal if o["true_urgency"] == "High"]
    missed = [o for o in urgent if o["ai_urgency"] != "High"]
    missed_silent = [o for o in missed if not o["review"]]
    skimmed = [o for o in normal if not o["review"]]
    silent = [o for o in skimmed if o["ai_category"] != o["true_category"] or o["ai_urgency"] != o["true_urgency"]]
    hard = [o for o in out if o["tag"] != "normal"]
    hard_routed = [o for o in hard if o["review"]]

    print(f"\nPrompt {version} on {len(normal)} clear + {len(hard)} ambiguous/unclear held-out messages")
    print(f"  Category accuracy        {cat_ok}/{len(normal)} = {100 * cat_ok / len(normal):.1f}%")
    print(f"  Urgency accuracy         {urg_ok}/{len(normal)} = {100 * urg_ok / len(normal):.1f}%")
    print(f"  Urgent cases missed      {len(missed)}/{len(urgent)}  (missed AND not sent to a person: {len(missed_silent)})")
    print(f"  Sent to a person         {sum(o['review'] for o in normal)}/{len(normal)} clear messages")
    print(f"  Silent errors            {len(silent)}/{len(skimmed)} of the skimmed (not reviewed) clear messages")
    print(f"  Ambiguous/unclear routed to a person: {len(hard_routed)}/{len(hard)}")
    print(f"  Cost about £{tracker.cost_gbp:.3f} ({tracker.calls} calls)  ->  {path.relative_to(ai_client.ROOT)}")
    wrong = [o for o in normal if o["ai_category"] != o["true_category"] or o["ai_urgency"] != o["true_urgency"]]
    print("\n  Disagreements with my labels (id: true -> AI, reviewed?):")
    for o in wrong:
        print(f"   {o['id']}: {o['true_category']}/{o['true_urgency']} -> {o['ai_category']}/{o['ai_urgency']}  reviewed={o['review']}  | {o['message'][:60]}")


if __name__ == "__main__":
    main()
