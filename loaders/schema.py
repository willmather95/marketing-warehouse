"""Create the warehouse tables (idempotent)."""
import duckdb
from config import DB_PATH


DDL = """
CREATE TABLE IF NOT EXISTS gsc_page_query (
  property VARCHAR NOT NULL,
  brand VARCHAR NOT NULL,
  date DATE NOT NULL,
  page VARCHAR NOT NULL,
  query VARCHAR NOT NULL,
  clicks DOUBLE NOT NULL,
  impressions DOUBLE NOT NULL,
  ctr DOUBLE NOT NULL,
  position DOUBLE NOT NULL,
  pulled_at TIMESTAMP NOT NULL,
  PRIMARY KEY (property, date, page, query)
);

CREATE TABLE IF NOT EXISTS gsc_load_meta (
  property VARCHAR PRIMARY KEY,
  brand VARCHAR NOT NULL,
  min_date DATE,
  max_date DATE,
  row_count BIGINT,
  last_pulled_at TIMESTAMP,
  notes VARCHAR
);
"""


def connect(read_only: bool = False):
    from config import DB_PATH  # read at call time so tests can point WAREHOUSE_DB elsewhere
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(DB_PATH), read_only=read_only)


def init_schema():
    con = connect()
    try:
        con.execute(DDL)
    finally:
        con.close()


if __name__ == "__main__":
    init_schema()
    print(f"schema ready at {DB_PATH}")
