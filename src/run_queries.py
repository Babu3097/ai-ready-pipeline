"""
run_queries.py - run every query in a .sql file and print the results as tables.

Run:  python src/run_queries.py                       (the manager questions)
      python src/run_queries.py sql/evaluation_queries.sql
"""
import sys
from pathlib import Path

import db


def show(title, cols, rows, limit=20):
    print(f"\n=== {title} ===")
    if not rows:
        print("(no rows)")
        return
    data = [[("" if v is None else str(v)) for v in r] for r in rows[:limit]]
    widths = [max(len(c), *(len(r[i]) for r in data)) for i, c in enumerate(cols)]
    widths = [min(w, 60) for w in widths]
    print("  ".join(c.ljust(w) for c, w in zip(cols, widths)))
    print("  ".join("-" * w for w in widths))
    for r in data:
        print("  ".join(v[:w].ljust(w) for v, w in zip(r, widths)))
    if len(rows) > limit:
        print(f"... {len(rows) - limit} more rows")


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else db.SQL_DIR / "metrics_queries.sql"
    for title, cols, rows, _ in db.run_sql_file(path):
        show(title, cols, rows)


if __name__ == "__main__":
    main()
