import streamlit as st
from dataclasses import asdict
import pandas as pd
from db_query import get_conversations, get_stats, get_relevance_stats, get_user_feedback_stats

st.title("Course Assistant Dashboard")

stats = get_stats()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total conversations", stats.total)
col2.metric("Avg response time", f"{stats.avg_response_time:.2f}s")
col3.metric("Total cost", f"${stats.total_cost:.4f}")
col4.metric("Avg tokens", f"{stats.avg_tokens:.0f}")


records = get_conversations(limit=100)
df = pd.DataFrame([asdict(r) for r in records])

st.subheader("Cost over time")
st.line_chart(df, x="timestamp", y="cost")

st.subheader("Response time over time")
st.line_chart(df, x="timestamp", y="response_time")


st.subheader("Recent conversations")
records = get_conversations(limit=20)

for record in records:
    st.write(f"**{record.prompt[:80]}...**")
    st.write(f"{record.answer[:200]}...")
    st.write(f"Time: {record.response_time:.2f}s | Cost: ${record.cost:.4f}")
    st.divider()
    
# Judge relevance distribution
st.subheader("Judge relevance")
relevance = get_relevance_stats()
st.bar_chart(relevance)

# User feedback distribution
st.subheader("User feedback")
thumbs_up, thumbs_down = get_user_feedback_stats()
col1, col2 = st.columns(2)
col1.metric("Thumbs up", int(thumbs_up or 0))
col2.metric("Thumbs down", int(thumbs_down or 0))
    
# if we want to run this dashboard, we can use the command:
# cd /workspaces/LLM-zoomcamp-2026
# uv run --project 01-agentic-rag-and-02-vector-search streamlit run 05-monitoring/dashboard.py --server.port 8502

