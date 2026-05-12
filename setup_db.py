import pandas as pd
import sqlite3

DB_PATH = "ipl.db"

def setup():
    conn = sqlite3.connect(DB_PATH)

    matches = pd.read_csv("matches.csv")
    deliveries = pd.read_csv("deliveries.csv")

    matches.to_sql("matches", conn, if_exists="replace", index=False)
    deliveries.to_sql("deliveries", conn, if_exists="replace", index=False)

    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    print("Tables:", cursor.fetchall())
    print("Matches columns:", matches.columns.tolist())
    print("Deliveries columns:", deliveries.columns.tolist())
    print("Sample match row:", matches.head(1).to_dict(orient="records"))

    conn.close()
    print("Done! ipl.db is ready.")

if __name__ == "__main__":
    setup()