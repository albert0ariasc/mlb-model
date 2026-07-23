import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "mlb.db"
DB_PATH.parent.mkdir(exist_ok=True)

SCHEMA = """
CREATE TABLE IF NOT EXISTS players (
    mlbam_id    INTEGER PRIMARY KEY,
    name_full   TEXT NOT NULL,
    name_search TEXT NOT NULL,
    bats        TEXT,
    throws      TEXT
);
CREATE INDEX IF NOT EXISTS idx_name_search ON players(name_search);

CREATE TABLE IF NOT EXISTS batter_stats (
    mlbam_id    INTEGER,
    as_of       TEXT,
    split       TEXT,
    pa          INTEGER,
    k_rate      REAL,
    bb_rate     REAL,
    hbp_rate    REAL,
    single_rate REAL,
    double_rate REAL,
    triple_rate REAL,
    hr_rate     REAL,
    PRIMARY KEY (mlbam_id, as_of, split)
);

CREATE TABLE IF NOT EXISTS pitcher_stats (
    mlbam_id    INTEGER,
    as_of       TEXT,
    split       TEXT,
    bf          INTEGER,
    k_rate      REAL,
    bb_rate     REAL,
    hbp_rate    REAL,
    single_rate REAL,
    double_rate REAL,
    triple_rate REAL,
    hr_rate     REAL,
    PRIMARY KEY (mlbam_id, as_of, split)
);

CREATE TABLE IF NOT EXISTS league_baseline (
    as_of       TEXT,
    split       TEXT,
    k_rate      REAL,
    bb_rate     REAL,
    hbp_rate    REAL,
    single_rate REAL,
    double_rate REAL,
    triple_rate REAL,
    hr_rate     REAL,
    PRIMARY KEY (as_of, split)
);
"""

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA)
    print(f"DB lista en {DB_PATH}")

if __name__ == "__main__":
    init_db()