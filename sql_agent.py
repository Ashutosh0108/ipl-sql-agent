import os
import json
import sqlite3
from datetime import datetime
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

def _get_groq_key():
    try:
        import streamlit as st
        return st.secrets["GROQ_API_KEY"]
    except Exception:
        return os.getenv("GROQ_API_KEY")

client = Groq(api_key=_get_groq_key())
DB_PATH = "ipl.db"
LOG_FILE = "query_log.jsonl"

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

Joins: deliveries has NO team1, team2, date, venue, city, season columns — those are all in matches.
To get match details alongside delivery stats, always JOIN:
  SELECT m.date, m.team1, m.team2, ... FROM deliveries d JOIN matches m ON d.match_id = m.id WHERE ...

Counting fours and sixes scored off a bowler:
- Fours: SUM(CASE WHEN batsman_runs = 4 THEN 1 ELSE 0 END)
- Sixes: SUM(CASE WHEN batsman_runs = 6 THEN 1 ELSE 0 END)

Counting overs bowled: COUNT(DISTINCT over) gives number of overs a bowler bowled in a match.
Economy rate: ROUND(SUM(total_runs) * 1.0 / COUNT(DISTINCT over), 2)

Counting wickets taken by a bowler: ALWAYS add AND is_wicket = 1.
Wrong: SELECT COUNT(*) FROM deliveries WHERE bowler LIKE '%Shami%'
Right: SELECT COUNT(*) FROM deliveries WHERE bowler LIKE '%Shami%' AND is_wicket = 1

Wicket-keeper dismissals (catches + stumpings by keeper like Dhoni):
- ALWAYS use COUNT(*) — never SELECT match details for a "how many" question
- Right: SELECT COUNT(*) as dismissals FROM deliveries WHERE fielder LIKE '%Dhoni%' AND is_wicket = 1
- If asking for all-time, do NOT filter by season unless the user specifies a season

Highest individual score in a single innings:
Sum batsman_runs per batter per match, then find the max.
Example: SELECT batter, SUM(batsman_runs) as score FROM deliveries WHERE match_id = X GROUP BY batter ORDER BY score DESC LIMIT 1
For all time highest: SELECT batter, match_id, SUM(batsman_runs) as score FROM deliveries GROUP BY batter, match_id ORDER BY score DESC LIMIT 1

Counting innings batted: count DISTINCT match_id values where the batter appeared.
Example: SELECT COUNT(DISTINCT match_id) as innings FROM deliveries WHERE batter LIKE '%Dhoni%'

When answering "most/least X against which team" questions, always include both the team name AND the count in SELECT.
Example: SELECT batting_team, COUNT(*) as wickets FROM deliveries WHERE bowler LIKE '%Shami%' AND is_wicket = 1 GROUP BY batting_team ORDER BY wickets DESC LIMIT 1

Player name format in the database:
- Names are stored as initials + last name: 'V Kohli', 'MS Dhoni', 'RG Sharma', 'AB de Villiers'
- ALWAYS use LIKE for name matching: batter LIKE '%Kohli%', batter LIKE '%Dhoni%'
- Common mappings: Kohli -> LIKE '%Kohli%', Rohit Sharma -> LIKE '%Sharma%' AND batting_team = 'Mumbai Indians', Dhoni -> LIKE '%Dhoni%', Bumrah -> LIKE '%Bumrah%'

Home matches: the database has no explicit home/away column. In IPL data, team1 is the home team.
So "home wins" = matches where winner = team1.
Example: SELECT team1, COUNT(*) as home_wins FROM matches WHERE season = '2016' AND winner = team1 GROUP BY team1 ORDER BY home_wins DESC LIMIT 1

Super overs: the matches table has a super_over column with values 'Y' or 'N'.
To count super overs: SELECT COUNT(*) FROM matches WHERE super_over = 'Y'

When counting centuries (100+ runs in an innings):
SELECT batter, SUM(batsman_runs) as score FROM deliveries GROUP BY batter, match_id HAVING score >= 100

Fastest century (fewest balls faced to reach 100 runs in one innings):
Each row in deliveries is one ball. COUNT(*) per batter per match = balls faced.
Use this pattern:
SELECT batter, match_id, COUNT(*) as balls_faced, SUM(batsman_runs) as runs
FROM deliveries
GROUP BY batter, match_id
HAVING SUM(batsman_runs) >= 100
ORDER BY balls_faced ASC
LIMIT 1

Top scorer for a specific team in a season — ALWAYS select batter name AND use subquery (not JOIN) to avoid row duplication:
SELECT batter, SUM(batsman_runs) as runs FROM deliveries
WHERE match_id IN (SELECT id FROM matches WHERE season = '2023')
AND batting_team = 'Chennai Super Kings'
GROUP BY batter ORDER BY runs DESC LIMIT 1

IMPORTANT: When aggregating deliveries stats (SUM, COUNT), prefer subquery over JOIN to avoid inflated numbers due to row multiplication.
Wrong: SELECT SUM(d.batsman_runs) FROM deliveries d JOIN matches m ON d.match_id = m.id WHERE m.season = '2023'
Right: SELECT SUM(batsman_runs) FROM deliveries WHERE match_id IN (SELECT id FROM matches WHERE season = '2023')

For "top scorer" questions always SELECT both the player name AND the runs together:
SELECT batter, SUM(batsman_runs) as runs FROM deliveries ... GROUP BY batter ORDER BY runs DESC LIMIT 1

Season format in the database (exact values):
- '2007/08', '2009', '2009/10', '2011', '2012', '2013', '2014', '2015', '2016', '2017', '2018', '2019', '2020/21', '2021', '2022', '2023', '2024'
- When user says '2020 IPL', use season = '2020/21'
- Single years map directly: '2016' -> season = '2016'
"""

FIX_SQL_PROMPT = """You are a SQL expert. A SQL query failed with an error.
Fix the query so it works correctly.

Rules:
- Return ONLY the fixed SQL query, nothing else
- No markdown, no explanation, no code blocks
"""

def log_query(entry: dict):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

def clarify_question(raw: str, history: list = None) -> str:
    if history is None:
        history = []
    messages = [{"role": "system", "content": CLARIFY_PROMPT}]
    for h in history[-6:]:
        messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": raw})
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages
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

def fix_sql(question: str, bad_sql: str, error: str) -> str:
    prompt = f"""Question: {question}

Failed SQL:
{bad_sql}

Error:
{error}

Database schema:
{SCHEMA}

Write a corrected SQL query."""
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": FIX_SQL_PROMPT},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content.strip()

ANSWER_PROMPT = """You are a cricket analyst. Given a question and its data results,
write a clean, structured answer.

Format rules:
- Always start with one bold line that directly answers the question, e.g. **Mohammed Shami took 19 wickets in IPL 2022**
- Only add bullet points if the data has MULTIPLE rows with different values worth highlighting
- If the data has only 1 row or 1 number — just the bold line, NO bullets
- If you add bullets, each bullet must contain a DIFFERENT fact from the data, not a rephrasing of the bold line
- Use ONLY names and numbers from the data — never add facts from your own knowledge
- If data is empty or all values are NULL/0, say **0** for "how many" questions rather than "No results found"
- Never say 'Based on the data' or 'According to the results'
- Always respond in the same language the user asked the question in
"""

def generate_answer(question: str, df) -> str:
    import pandas as pd
    data_str = df.to_string(index=False) if not df.empty else "No data found."
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": ANSWER_PROMPT},
            {"role": "user", "content": f"Question: {question}\n\nData:\n{data_str}"}
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

def run_query_with_retry(question: str, sql: str, max_retries: int = 2):
    import pandas as pd
    current_sql = sql
    for attempt in range(max_retries + 1):
        try:
            conn = sqlite3.connect(DB_PATH)
            df = pd.read_sql_query(current_sql, conn)
            conn.close()
            return df, current_sql, attempt
        except Exception as e:
            if attempt < max_retries:
                print(f"  [retry {attempt + 1}] fixing SQL: {e}")
                current_sql = fix_sql(question, current_sql, str(e))
            else:
                raise Exception(f"Failed after {max_retries} retries. Last error: {e}")

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

    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "question": question,
        "clarified": clarified,
        "sql": sql,
        "success": False,
        "retries": 0,
        "rows_returned": 0,
        "error": None
    }

    try:
        df, final_sql, retries = run_query_with_retry(clarified, sql)
        log_entry["success"] = True
        log_entry["retries"] = retries
        log_entry["rows_returned"] = len(df)
        log_entry["sql"] = final_sql
        if retries > 0:
            print(f"Fixed SQL: {final_sql}\n")
        columns = list(df.columns)
        rows = df.values.tolist()
        print(format_results(columns, rows))
    except Exception as e:
        log_entry["error"] = str(e)
        print(f"Query error: {e}")
        print("Try rephrasing your question.")
    finally:
        log_query(log_entry)

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