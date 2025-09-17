import sqlite3, os
DB_PATH = os.environ.get("SOCP_DB", "/mnt/data/socp.sqlite3")

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(schema_path: str):
    conn = get_conn()
    with open(schema_path, "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db(os.path.join(os.path.dirname(__file__), "schema.sql"))
    print("DB initialized at", DB_PATH)
