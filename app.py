import os
import sqlite3
import pandas as pd
import streamlit as st
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

CLARIFY_PROMPT = """You are an IPL cricket expert. The user is having a conversation about IPL stats.
Given the conversation history and the latest message, rewrite the latest question as a single
clean, self-contained, precise English question. Resolve any pronouns or references using the history.

Rules:
- Fix grammar and spelling
- Expand short forms: 'RCB' -> 'Royal Challengers Bangalore', 'MI' -> 'Mumbai Indians',
  'CSK' -> 'Chennai Super Kings', 'KKR' -> 'Kolkata Knight Riders', 'SRH' -> 'Sunrisers Hyderabad'
- Expand player nicknames: 'Virat' -> 'Virat Kohli', 'Mahi'/'Dhoni' -> 'MS Dhoni',
  'Rohit' -> 'Rohit Sharma', 'Bumrah' -> 'Jasprit Bumrah', 'Sachin' -> 'Sachin Tendulkar'
- Resolve follow-up references: if user says 'what about him', 'same season', 'that team',
  use the conversation history to figure out who/what they mean
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
- Common mappings: Kohli -> LIKE '%Kohli%', Rohit Sharma -> LIKE '%Sharma%' AND batting_team = 'Mumbai Indians', Dhoni -> LIKE '%Dhoni%', Bumrah -> LIKE '%Bumrah%'

Joins: deliveries has NO team1, team2, date, venue, city, season columns — those are all in matches.
To get match details alongside delivery stats, always JOIN:
  SELECT m.date, m.team1, m.team2, ... FROM deliveries d JOIN matches m ON d.match_id = m.id WHERE ...

Counting fours and sixes scored off a bowler:
- Fours: SUM(CASE WHEN batsman_runs = 4 THEN 1 ELSE 0 END)
- Sixes: SUM(CASE WHEN batsman_runs = 6 THEN 1 ELSE 0 END)
Never use total_runs = 4 or total_runs = 6 as that includes extras.

Counting overs bowled: COUNT(DISTINCT over) gives number of overs a bowler bowled in a match.
Economy rate: ROUND(SUM(total_runs) * 1.0 / COUNT(DISTINCT over), 2)

Counting wickets: ALWAYS add AND is_wicket = 1 when counting wickets taken by a bowler.
Wrong: SELECT COUNT(*) FROM deliveries WHERE bowler LIKE '%Shami%'
Right: SELECT COUNT(*) FROM deliveries WHERE bowler LIKE '%Shami%' AND is_wicket = 1

When answering "most/least X against which team" questions, always include both the team name AND the count in SELECT.
Example: SELECT batting_team, COUNT(*) as wickets FROM deliveries WHERE bowler LIKE '%Shami%' AND is_wicket = 1 GROUP BY batting_team ORDER BY wickets DESC LIMIT 1

Season format in the database (exact values):
- '2007/08', '2009', '2009/10', '2011', '2012', '2013', '2014', '2015', '2016', '2017', '2018', '2019', '2020/21', '2021', '2022', '2023', '2024'
- When user says '2020 IPL', use season = '2020/21'
- Single years map directly: '2016' -> season = '2016'
"""

ANSWER_PROMPT = """You are a cricket analyst. Given a question and its data results,
write a clean, structured answer.

Format rules:
- Always start with one bold line that directly answers the question, e.g. **Mohammed Shami took 19 wickets in IPL 2022**
- Only add bullet points if the data has MULTIPLE rows with different values worth highlighting (e.g. top 5 list, season-wise breakdown)
- If the data has only 1 row or 1 number — just the bold line, NO bullets
- If you add bullets, each bullet must contain a DIFFERENT fact from the data, not a rephrasing of the bold line
- Never write bullets like "He took wickets in the 2022 season" or "The wickets were taken in the IPL" — these add zero value
- Use ONLY names and numbers from the data — never add facts from your own knowledge
- If data is empty, write: **No results found.**
- Never say 'Based on the data' or 'According to the results'
- Always respond in the same language the user asked the question in. If they asked in Hindi, answer in Hindi. If English, answer in English.
"""

def clarify_question(raw: str, history: list) -> str:
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

def generate_answer(question: str, df: pd.DataFrame) -> str:
    data_str = df.to_string(index=False) if not df.empty else "No data found."
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": ANSWER_PROMPT},
            {"role": "user", "content": f"Question: {question}\n\nData:\n{data_str}"}
        ]
    )
    return response.choices[0].message.content.strip()

def run_query(sql: str) -> pd.DataFrame:
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(sql, conn)
    conn.close()
    return df

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(page_title="IPL SQL Agent", page_icon="🏏", layout="centered")
st.title("🏏 IPL SQL Agent")
st.caption("Ask anything about IPL 2008–2024 in plain English, Hindi, or broken English.")

SUGGESTIONS = [
    "Who hit the most sixes in IPL history?",
    "Which team won the most IPL titles?",
    "Bumrah ka best bowling performance kya hai?",
    "Top 5 run scorers of 2024 IPL",
]

if "messages" not in st.session_state:
    st.session_state.messages = []

# Show suggestion chips only on first load
if not st.session_state.messages:
    st.markdown("**Try asking:**")
    cols = st.columns(2)
    for i, suggestion in enumerate(SUGGESTIONS):
        if cols[i % 2].button(suggestion, use_container_width=True):
            st.session_state.pending_prompt = suggestion
            st.rerun()

# Render chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "dataframe" in msg:
            with st.expander("View full table"):
                st.dataframe(msg["dataframe"], use_container_width=True)
        if "sql" in msg:
            with st.expander("View SQL"):
                st.code(msg["sql"], language="sql")

# Handle suggestion button clicks
prompt = st.chat_input("Ask about IPL stats...")
if not prompt and "pending_prompt" in st.session_state:
    prompt = st.session_state.pop("pending_prompt")

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            history = [
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state.messages[:-1]
                if m["role"] in ("user", "assistant")
            ]
            clarified = clarify_question(prompt, history)
            sql = generate_sql(clarified)

        try:
            df = run_query(sql)
            answer = generate_answer(clarified, df)
            st.markdown(answer)

            if not df.empty and len(df) > 1:
                with st.expander("View full table"):
                    st.dataframe(df, use_container_width=True)

            with st.expander("View SQL"):
                st.code(sql, language="sql")

            st.session_state.messages.append({
                "role": "assistant",
                "content": answer,
                "dataframe": df,
                "sql": sql
            })

        except Exception as e:
            error_msg = f"Sorry, I couldn't answer that. Try rephrasing. *(Error: {e})*"
            st.markdown(error_msg)
            with st.expander("View SQL"):
                st.code(sql, language="sql")
            st.session_state.messages.append({
                "role": "assistant",
                "content": error_msg,
                "sql": sql
            })
