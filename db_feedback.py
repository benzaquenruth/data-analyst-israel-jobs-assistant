# WHAT THIS FILE DOES
# This file saves one piece of feedback about a conversation into
# the "feedback" table.
#
# It's used for two different kinds of feedback:
#   - the LLM judge's verdict (source="judge", from judge.py)
#   - a real user's thumbs up/down (source="user", from app.py)
#
# Both share the same table — which kind a row is comes from the
# "source" column.
#
# Local / Docker:
#   -> saves to monitoring.db (SQLite), in the "feedback" table
#
# Streamlit Cloud:
#   -> saves to BigQuery, in rag_monitoring.feedback


import os
import uuid
from datetime import datetime, timezone

from db_init import get_db_connection


# save_feedback() writes one new row into the feedback table.
#   - conversation_id: which conversation this feedback is about (the id
#     returned earlier by save_conversation() in db_save.py)
#   - source: "judge" or "user"
#   - relevance / explanation: filled in for judge feedback
#     (RELEVANT / PARTLY_RELEVANT / NON_RELEVANT + why)
#   - score: filled in for user feedback (+1 for thumbs up, -1 for
#     thumbs down)
# Whichever fields don't apply are left as None / NULL.
def save_feedback(conversation_id, source, relevance=None,
                  explanation=None, score=None):

    # Streamlit Cloud uses BigQuery.
    # Local/Docker default to SQLite.
    backend = os.getenv("MONITORING_BACKEND", "sqlite")

    if backend == "bigquery":
        from bigquery_client import get_bigquery_client

        client = get_bigquery_client()

        row = {
            "id": str(uuid.uuid4()),
            "conversation_id": conversation_id,
            "source": source,
            "relevance": relevance,
            "explanation": explanation,
            "score": score,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        table_id = (
            "massive-bliss-481811-d8."
            "rag_monitoring.feedback"
        )

        errors = client.insert_rows_json(table_id, [row])

        if errors:
            raise RuntimeError(f"BigQuery insert failed: {errors}")

        return

    # -------------------------
    # LOCAL / DOCKER → SQLite
    # -------------------------

    timestamp = datetime.now().isoformat()

    conn = get_db_connection()
    try:
        conn.execute(
            """
            INSERT INTO feedback (
                conversation_id, source, relevance,
                explanation, score, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (conversation_id, source, relevance,
             explanation, score, timestamp),
        )
        conn.commit()
    finally:
        conn.close()