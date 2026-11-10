"""
load_sql.py - Phase 3: build the SQLite database and load the clean data into it.

Run:  python src/load_sql.py
This REBUILDS the database from scratch, so run triage.py again afterwards
(run_all.py does every step in the right order).
"""
import pandas as pd

import db

CLEAN = db.ROOT / "data" / "clean"
TRUTH = db.ROOT / "data" / "ground_truth"


def read(path):
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def main():
    db.DB_FILE.parent.mkdir(parents=True, exist_ok=True)
    conn = db.connect()
    conn.executescript((db.SQL_DIR / "create_tables.sql").read_text(encoding="utf-8"))

    enq = read(CLEAN / "enquiries_clean.csv")
    enq["raw_row"] = enq["raw_row"].astype(int)
    enq["handling_mins"] = pd.to_numeric(enq["handling_mins"], errors="coerce").astype("Int64")
    enq["category_ai_confidence"] = pd.to_numeric(enq["category_ai_confidence"], errors="coerce")
    enq = enq.replace("", None)  # empty text becomes a proper NULL in SQL
    enq.to_sql("enquiries", conn, if_exists="append", index=False)

    log = read(CLEAN / "data_quality_log.csv").replace("", None)
    log["raw_row"] = log["raw_row"].astype(int)
    log.to_sql("data_quality_log", conn, if_exists="append", index=False)

    scores = pd.read_csv(CLEAN / "quality_scores.csv")
    scores.rename(columns={"metric": "metric"}).to_sql("quality_scores", conn, if_exists="append", index=False)

    read(TRUTH / "enquiries_truth.csv").to_sql("ground_truth", conn, if_exists="append", index=False)
    rmap = read(TRUTH / "raw_row_map.csv")
    rmap["raw_row"] = rmap["raw_row"].astype(int)
    rmap.to_sql("raw_row_map", conn, if_exists="append", index=False)

    db.audit(conn, None, "system", "database_loaded", f"{len(enq)} enquiries, {len(log)} log lines")
    conn.commit()

    for table in ["enquiries", "data_quality_log", "quality_scores", "ground_truth", "raw_row_map", "audit_log"]:
        n = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"  {table:<18}{n:>5} rows")
    print(f"Database written to {db.DB_FILE.relative_to(db.ROOT)}")
    conn.close()


if __name__ == "__main__":
    main()
