# WHAT THIS FILE DOES
# This is the MONITORING dashboard — a separate Streamlit page (not the
# one users ask questions in) for US to watch how the assistant is
# doing: how many questions have been asked, how much it's costing,
# how fast it answers, whether the LLM judge thinks the answers are
# relevant, and what real users thought (👍/👎).
#
# It never talks to the LLM or does any search itself — it only reads
# data that app.py already saved into monitoring.db, using the
# functions from db_query.py.
#
# HOW TO RUN THIS FILE (in a different terminal from app.py, and on a
# different port so both can run at the same time):
#   uv run streamlit run dashboard.py --server.port 8502

import streamlit as st
import pandas as pd

from db_query import (
    get_conversations,
    get_stats,
    get_relevance_stats,
    get_user_feedback_stats,
)

st.title("Jobs Assistant — Monitoring Dashboard")

# --- Summary numbers at the top ---
# get_stats() gives us four headline numbers across ALL conversations
# ever saved. st.columns(4) lays them out side by side, like a
# dashboard "scorecard" row.
stats = get_stats()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total conversations", stats.total)
col2.metric("Avg response time", f"{stats.avg_response_time:.2f}s")
col3.metric("Total cost", f"${stats.total_cost:.4f}")
col4.metric("Avg tokens", f"{stats.avg_tokens:.0f}")


# --- Cost and response time over time ---
# get_conversations() returns a list of {"id", "question", "record"}
# dicts (see db_query.py). To draw line charts we flatten that into a
# pandas DataFrame — basically a spreadsheet in memory — with one
# column per number we want to plot.
conversations = get_conversations(limit=100)

rows = []
for c in conversations:
    record = c["record"]
    rows.append({
        "timestamp": record.timestamp,
        "cost": record.cost,
        "response_time": record.response_time,
        "prompt_tokens": record.prompt_tokens,
        "completion_tokens": record.completion_tokens,
    })

df = pd.DataFrame(rows)

if not df.empty:
    # timestamps are saved as plain text (see db_save.py) — this turns
    # them into real datetime values so the charts below read them as a
    # proper time axis instead of alphabetically-sorted text, and so we
    # can sort oldest-to-newest for the line charts to read left-to-right.
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp")

    st.subheader("Cost over time")
    st.line_chart(df, x="timestamp", y="cost")

    st.subheader("Response time over time")
    st.line_chart(df, x="timestamp", y="response_time")

    st.subheader("Tokens per conversation over time")
    # Two lines on one chart: prompt tokens (the context we send in) vs
    # completion tokens (what the LLM generates back) — passing a list
    # of columns to y draws one line per column, both on the same axes.
    st.line_chart(df, x="timestamp", y=["prompt_tokens", "completion_tokens"])
else:
    st.write("No conversations yet — ask a question in app.py first.")


# --- Judge relevance distribution ---
# get_relevance_stats() returns something like
# {"RELEVANT": 8, "PARTLY_RELEVANT": 2} — st.bar_chart turns that
# straight into a bar chart, one bar per relevance category.
st.subheader("Judge relevance")
relevance = get_relevance_stats()

if relevance:
    st.bar_chart(relevance)
else:
    st.write("No judge feedback yet.")


# --- Real user feedback (👍/👎 from app.py) ---
# get_user_feedback_stats() returns two plain counts. The metric tiles
# below are a nice quick-glance summary, but st.bar_chart() underneath
# is the actual chart — turning those two counts into a small bar chart
# so this is a real visualization, not just numbers in boxes.
st.subheader("User feedback")
thumbs_up, thumbs_down = get_user_feedback_stats()

col1, col2 = st.columns(2)
col1.metric("👍 Thumbs up", thumbs_up)
col2.metric("👎 Thumbs down", thumbs_down)

feedback_counts = pd.DataFrame(
    {"count": [thumbs_up, thumbs_down]},
    index=["👍 Thumbs up", "👎 Thumbs down"],
)
st.bar_chart(feedback_counts)


# --- Recent conversations list ---
# A simple scrollable log of the last 20 questions asked, so we can
# spot-check what people are actually asking and what they got back.
# Placed last, after all the charts — the charts are the "at a glance"
# summary, this is the detail you scroll to if you want to dig in.
st.subheader("Recent conversations")
recent = get_conversations(limit=20)

for c in recent:
    record = c["record"]
    st.write(f"**{c['question'][:80]}**")
    st.write(f"{record.answer[:200]}...")
    st.write(f"Time: {record.response_time:.2f}s | Cost: ${record.cost:.4f}")
    st.divider()
