import pandas as pd
import sqlite3

conn = sqlite3.connect("ipl.db")

matches = pd.read_csv("matches.csv")
deliveries = pd.read_csv("deliveries.csv")

matches.to_sql("matches", conn, if_exists="replace", index=False)
deliveries.to_sql("deliveries", conn, if_exists="replace", index=False)

cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
print("Tables:", cursor.fetchall())
print("\nMatches columns:", matches.columns.tolist())
print("\nDeliveries columns:", deliveries.columns.tolist())
print("\nSample match row:")
print(matches.head(1).to_dict(orient="records"))

conn.close()
print("\nDone! ipl.db is ready.")
