# 🏏 IPL SQL Agent

A conversational AI agent that lets you query 17 years of IPL data (2008–2024) in plain English, Hindi, or broken English — no SQL knowledge needed.

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)
![Streamlit](https://img.shields.io/badge/Streamlit-1.57-red?logo=streamlit)
![Groq](https://img.shields.io/badge/LLM-Groq%20Llama3-orange)
![SQLite](https://img.shields.io/badge/Database-SQLite-lightgrey?logo=sqlite)

🚀 **[Live Demo → ipl-stats-ai.streamlit.app](https://ipl-stats-ai.streamlit.app)**

---

## Architecture

The agent uses a 3-step agentic pipeline with automatic error recovery and conversation memory:

```
User Input (any language/grammar)
        ↓
Step 1 — Intent Clarification
  Resolves nicknames, Hindi-English mix, typos, follow-up pronouns
  "Virat" → "V Kohli", "2020 IPL" → season = '2020/21'
  "what about him?" → resolved from conversation history
        ↓
Step 2 — SQL Generation
  Writes SQLite query against 900,000+ delivery records
  Auto-retry on failure — shows error to LLM, asks it to fix its own SQL
  Up to 2 retry attempts before giving up
        ↓
Step 3 — Answer Generation
  Converts raw query results into natural language
  Matches the user's input language (Hindi in → Hindi out)
  Structured format: bold key stat + bullet points for multi-row data
        ↓
Response displayed + query logged to JSONL
```

---

## Demo

> **You:** bumrah ne 2024 mein kitne wicket liye
> **Agent:** Jasprit Bumrah ne IPL 2024 mein 15 wicket liye.

> **You:** which team did he take most wickets against?
> **Agent:** Bumrah took the most wickets against Royal Challengers Bangalore — 4 wickets.

> **You:** what was his economy in those matches?
> **Agent:** Bumrah's economy rate against RCB in 2024 was 6.25.

---

## Features

- **Broken English & Hindi support** — ask in any way you naturally speak
- **Follow-up questions** — resolves pronouns like "him", "same season", "that team" using chat history
- **Auto-retry on SQL errors** — agent fixes its own mistakes without user intervention
- **Query logging** — every question, SQL, success/fail, retry count saved to JSONL for analysis
- **Natural language answers** — no raw tables, clean conversational responses
- **SQL transparency** — click "View SQL" on any answer to see the exact query generated
- **Per-match breakdowns** — ask for match-by-match stats for any player

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| LLM | Groq API (Llama 3.3 70B) |
| UI | Streamlit |
| Database | SQLite (900K+ rows) |
| Data | IPL 2008–2024 (Kaggle) |
| Language | Python 3.11 |

---

## Setup

**1. Clone the repo**
```bash
git clone https://github.com/Ashutosh0108/ipl-sql-agent.git
cd ipl-sql-agent
```

**2. Create virtual environment**
```bash
python -m venv venv
venv\Scripts\activate      # Windows
source venv/bin/activate   # Mac/Linux
```

**3. Install dependencies**
```bash
pip install -r requirements.txt
```

**4. Add your API key**

Create a `.env` file:
```
GROQ_API_KEY=your_groq_api_key_here
```
Get a free key at [console.groq.com](https://console.groq.com)

**5. Set up the database**
```bash
python setup_db.py
```

**6. Run the app**
```bash
streamlit run app.py
```

---

## Sample Questions

```
Who hit the most sixes in IPL history?
Shami ne 2022 mein kitne wicket liye?
Which team won the most IPL titles?
Top 5 run scorers of 2024 IPL
What was Kohli's strike rate in 2016?
List all players who scored 500+ runs in IPL 2024
Who made the fastest century in IPL history?
KKR ne 2024 mein kitne match jeete?
```