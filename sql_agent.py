import os
import sqlite3
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
DB_PATH = "ipl.db"

SCHEMA = """
Table: matches
Columns: id, season, city, date, match_type, player_of_match, venue, team1, team2,
         toss_winner, toss_decision, winner, result, result_margin, target_runs,
         target_overs, super_over, method, umpire1, umpire2

Table: deliveries
Columns: match_id, inning, batting_team, bowling_team, over, ball, batter, bowler,
         non_striker, batsman_runs, extra_runs, total_runs, extras_type, is_wicket,
         player_dismissed, dismissal_kind, fielder
"""

CLARIFY_PROMPT = """You are an IPL cricket expert. The user will ask a question in broken English,
Hindi-English mix, slang, or informal language.
Rewrite it as a single clean, precise English question about IPL cricket stats.

Rules:
- Fix grammar and spelling
- Expand short forms: 'RCB' -> 'Royal Challengers Bangalore', 'MI' -> 'Mumbai Indians', 'CSK' -> 'Chennai Super Kings', 'KKR' -> 'Kolkata Knight Riders', 'SRH' -> 'Sunrisers Hyderabad'
- Expand player nicknames: 'Virat' -> 'Virat Kohli', 'Mahi' or 'Dhoni' -> 'MS Dhoni', 'Rohit' -> 'Rohit Sharma', 'Bumrah' -> 'Jasprit Bumrah'
- Return ONLY the rewritten question, nothing else
"""

SYSTEM_PROMPT = f"""You are a SQL expert. Given a user question, write a single SQLite SQL query to answer it.

Database schema:
{SCHEMA}

Rules:
- Return ONLY the SQL query, nothing else
- No markdown, no explanation, no code blocks
- Use only the tables and columns listed above
- matches.id joins with deliveries.match_id

CRITICAL — the deliveries table has NO season, city, venue, date, or winner columns.
To filter deliveries by season, you MUST use a subquery like this:
  WHERE match_id IN (SELECT id FROM matches WHERE season = '2020/21')
Never write: WHERE season = '...' directly on deliveries. It will always fail.

Player name format in the database:
- Names are stored as initials + last name: 'V Kohli', 'MS Dhoni', 'RG Sharma', 'AB de Villiers'
- ALWAYS use LIKE for name matching: batter LIKE '%Kohli%', batter LIKE '%Dhoni%'
- Never use full first names like 'Virat Kohli' or 'Rohit Sharma' — the DB won't have them
- Common mappings: Kohli -> LIKE '%Kohli%', Rohit Sharma -> LIKE '%Sharma%' AND batting_team = 'Mumbai Indians', Dhoni -> LIKE '%Dhoni%', Bumrah -> LIKE '%Bumrah%'

Season format in the database (exact values):
- '2007/08', '2009', '2009/10', '2011', '2012', '2013', '2014', '2015', '2016', '2017', '2018', '2019', '2020/21', '2021', '2022', '2023', '2024'
- When user says '2020 IPL', use season = '2020/21'
- When user says '2021 IPL', use season = '2021'
- Single years map directly: '2016' -> season = '2016'
"""

def clarify_question(raw: str) -> str:
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": CLARIFY_PROMPT},
            {"role": "user", "content": raw}
        ]
    )
    return response.choices[0].message.content.strip()

def generate_sql(question: str) -> str:
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question}
        ]
    )
    return response.choices[0].message.content.strip()

def run_query(sql: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(sql)
    rows = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    conn.close()
    return columns, rows

def format_results(columns, rows):
    if not rows:
        return "No results found."
    col_header = " | ".join(columns)
    divider = "-" * len(col_header)
    lines = [col_header, divider]
    for row in rows[:15]:
        lines.append(" | ".join(str(v) for v in row))
    if len(rows) > 15:
        lines.append(f"... ({len(rows) - 15} more rows)")
    return "\n".join(lines)

def ask(question: str):
    clarified = clarify_question(question)
    print(f"\nUnderstood: {clarified}")
    sql = generate_sql(clarified)
    print(f"SQL: {sql}\n")
    try:
        columns, rows = run_query(sql)
        print(format_results(columns, rows))
    except Exception as e:
        print(f"Query error: {e}")
        print("Try rephrasing your question.")

def main():
    print("IPL SQL Agent — ask anything about IPL data.")
    print("Type 'exit' to quit.\n")
    while True:
        question = input("You: ").strip()
        if not question:
            continue
        if question.lower() in ("exit", "quit"):
            print("Bye!")
            break
        ask(question)

if __name__ == "__main__":
    main()
