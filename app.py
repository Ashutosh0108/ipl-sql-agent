import os
import streamlit as st
from datetime import datetime
from setup_db import setup as build_db
from sql_agent import (

    clarify_question,
    generate_sql,
    generate_answer,
    run_query_with_retry,
    log_query,
)

if not os.path.exists("ipl.db"):
    with st.spinner("Setting up database..."):
        build_db()

SUGGESTIONS = [
    "Who hit the most sixes in IPL history?",
    "Which team won the most IPL titles?",
    "Bumrah ka best bowling performance kya hai?",
    "Top 5 run scorers of 2024 IPL",
]

st.set_page_config(page_title="IPL SQL Agent", page_icon="🏏", layout="centered")
st.title("🏏 IPL SQL Agent")
st.caption("Ask anything about IPL 2008–2024 in plain English, Hindi, or broken English.")

if "messages" not in st.session_state:
    st.session_state.messages = []

if not st.session_state.messages:
    st.markdown("**Try asking:**")
    cols = st.columns(2)
    for i, suggestion in enumerate(SUGGESTIONS):
        if cols[i % 2].button(suggestion, use_container_width=True):
            st.session_state.pending_prompt = suggestion
            st.rerun()

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "dataframe" in msg:
            with st.expander("View full table"):
                st.dataframe(msg["dataframe"], use_container_width=True)
        if "sql" in msg:
            with st.expander("View SQL"):
                st.code(msg["sql"], language="sql")

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

        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "question": prompt,
            "clarified": clarified,
            "sql": sql,
            "success": False,
            "retries": 0,
            "rows_returned": 0,
            "error": None
        }

        try:
            df, final_sql, retries = run_query_with_retry(clarified, sql)
            answer = generate_answer(clarified, df)

            log_entry.update({
                "success": True,
                "retries": retries,
                "rows_returned": len(df),
                "sql": final_sql
            })

            st.markdown(answer)

            if not df.empty and len(df) > 1:
                with st.expander("View full table"):
                    st.dataframe(df, use_container_width=True)

            with st.expander("View SQL" + (" (auto-fixed)" if retries > 0 else "")):
                st.code(final_sql, language="sql")

            st.session_state.messages.append({
                "role": "assistant",
                "content": answer,
                "dataframe": df,
                "sql": final_sql
            })

        except Exception as e:
            log_entry["error"] = str(e)
            error_msg = f"Sorry, I couldn't answer that. Try rephrasing. *(Error: {e})*"
            st.markdown(error_msg)
            with st.expander("View SQL"):
                st.code(sql, language="sql")
            st.session_state.messages.append({
                "role": "assistant",
                "content": error_msg,
                "sql": sql
            })

        finally:
            log_query(log_entry)