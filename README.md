# 🏏 IPL SQL Agent

A conversational AI agent that lets you query IPL cricket data (2008–2024) using plain English, Hindi, or broken English — no SQL knowledge needed.

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)
![Streamlit](https://img.shields.io/badge/Streamlit-1.57-red?logo=streamlit)
![Groq](https://img.shields.io/badge/LLM-Groq%20Llama3-orange)
![SQLite](https://img.shields.io/badge/Database-SQLite-lightgrey?logo=sqlite)

🚀 **[Live Demo → ipl-stats-ai.streamlit.app](https://ipl-stats-ai.streamlit.app)**

## Demo

> **You:** bumrah ne 2024 mein kitne wicket liye  
> **Agent:** Jasprit Bumrah took 15 wickets in IPL 2024.

> **You:** which team did he take most wickets against?  
> **Agent:** Bumrah took the most wickets against Royal Challengers Bangalore — 4 wickets.

> **You:** what was his economy in those matches?  
> **Agent:** Bumrah's economy rate against RCB in 2024 was 6.25.

## How It Works

The agent uses a 3-step pipeline:

```
Your question (any language/grammar)
        ↓
[Step 1] Intent Clarification — LLM cleans and understands your question
        ↓
[Step 2] SQL Generation — LLM writes the SQLite query
        ↓
[Step 3] Answer Generation — LLM converts raw results into a human response
```

## Features

- **Broken English & Hindi support** — ask in any way you naturally speak
- **Follow-up questions** — resolves pronouns like "him", "same season", "that team"
- **Natural language answers** — no raw tables, just clean conversational responses
- **SQL transparency** — click "View SQL" on any answer to see the exact query
- **Per-match breakdowns** — ask for match-by-match stats for any player

## Tech Stack

| Component | Technology |
|-----------|-----------|
| LLM | Groq API (Llama 3.3 70B) |
| UI | Streamlit |
| Database | SQLite |
| Data | IPL 2008–2024 (Kaggle) |
| Language | Python 3.11 |

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

**5. Download IPL dataset**

Download from Kaggle: [IPL Complete Dataset 2008–2024](https://www.kaggle.com/datasets/patrickb1912/ipl-complete-dataset-20082020)

Place `matches.csv` and `deliveries.csv` in the project folder.

**6. Set up the database**
```bash
python setup_db.py
```

**7. Run the app**
```bash
streamlit run app.py
```

## Sample Questions

```
Who hit the most sixes in IPL history?
Shami ne 2022 mein kitne wicket liye?
Which team won the most IPL titles?
Top 5 run scorers of 2024 IPL
What was Kohli's strike rate in 2016?
MI ne kitne finals jeete hain?
```
