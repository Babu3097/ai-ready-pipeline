"""
run_all.py - run the whole local pipeline, in order, from a clean start.

  1 generate_data   make the messy synthetic data and the answer key
  2 data_quality    clean it, score it, mask personal details
  3 load_sql        build the SQLite database
  4 triage          AI triage (demo mode if there is no API key)
  5 review_queue    export the review queue, simulated reviewer decides, replies drafted, audit log written
  6 evaluate        accuracy vs the answer key, time and money saved, CSVs for Power BI
  7 report images   draw the four report pages

Run:  python src/run_all.py            (keyword stand-in if no API key)
      python src/run_all.py --session  (use the saved Claude-in-chat triage answers)
"""
import subprocess
import sys
import time
from pathlib import Path

SRC = Path(__file__).resolve().parent

STEPS = [
    ("1. Generate messy data", ["generate_data.py"]),
    ("2. Clean the data", ["data_quality.py"]),
    ("3. Build the SQL database", ["load_sql.py"]),
    ("4. AI triage", ["triage.py"]),
    ("5. Human review loop (simulated reviewer)", ["review_queue.py", "all"]),
    ("6. Evaluate", ["evaluate.py"]),
    ("7. Draw report pages", ["make_report_images.py"]),
]

if __name__ == "__main__":
    start = time.time()
    steps = list(STEPS)
    if "--session" in sys.argv:  # use the Claude-in-chat answers instead of the keyword stand-in
        steps[3] = ("4. AI triage (answers from a Claude Code chat session)", ["import_triage.py"])
    for title, cmd in steps:
        print(f"\n{'=' * 8} {title} {'=' * 8}")
        result = subprocess.run([sys.executable, str(SRC / cmd[0])] + cmd[1:], cwd=SRC)
        if result.returncode != 0:
            raise SystemExit(f"Step failed: {title}")
    print(f"\nAll done in {time.time() - start:.0f} seconds. See docs/results.md and docs/screenshots/.")
