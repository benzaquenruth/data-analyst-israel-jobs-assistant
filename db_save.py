# WHAT THIS FILE DOES
# Saves monitoring conversations.
# This file saves one finished conversation (a question + its answer + all the metrics from metrics.py 
# into conversactions table 
# It is called from app.py after the assistant answers a question.

# Local / Docker:
#   -> saves to monitoring.db (SQLite) -  in the "conversations" table we created in db_init.py.
#
# Streamlit Cloud:
#   -> saves to BigQuery - in BigQuery rag_monitoring dataset, in conversations table



import os
import uuid
from datetime import datetime, timezone

from db_init import get_db_connection


# save_conversation() takes:
#   - record: an LLMCallRecord from metrics.py (has answer, model,
#     tokens, cost, response_time, etc.)
#   - question: the raw text the user typed in
# and writes one new row into the table of saved conversations.
#
# It returns the new row's id, so app.py can remember "this is
# conversation #17" and later attach feedback to that same row.
def save_conversation(record, question):
    
    # Streamlit Cloud has:
    # MONITORING_BACKEND = "bigquery"
    #
    # Local/Docker don't, so they default to SQLite.
    
    backend = os.getenv("MONITORING_BACKEND", "sqlite")

    if backend == "bigquery":
        from bigquery_client import get_bigquery_client

        client = get_bigquery_client()

        conversation_id = str(uuid.uuid4())  
    
        row = {
            "id": conversation_id,
            "question": question,
            "answer": record.answer,
            "model": record.model,
            "instructions": record.instructions,
            "prompt": record.prompt,
            "prompt_tokens": record.prompt_tokens,
            "completion_tokens": record.completion_tokens,
            "total_tokens": record.total_tokens,
            "response_time": record.response_time,
            "cost": record.cost,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        table_id = (
            "massive-bliss-481811-d8."
            "rag_monitoring.conversations"
        )
        
        errors = client.insert_rows_json(table_id, [row])

        if errors:
            raise RuntimeError(f"BigQuery insert failed: {errors}")

        return conversation_id
    
    # -------------------------
    # LOCAL / DOCKER → SQLite
    # -------------------------
    
    # SQLite stores timestamps as plain text, so we convert the
    # datetime to an ISO-format string (e.g. "2026-08-04T22:35:19").
    timestamp = datetime.now().isoformat()

    conn = get_db_connection()
    try:
        cursor = conn.execute(
            """
            INSERT INTO conversations (
                question, answer, model, instructions, prompt,
                prompt_tokens, completion_tokens, total_tokens,
                response_time, cost, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                question,
                record.answer,
                record.model,
                record.instructions,
                record.prompt,
                record.prompt_tokens,
                record.completion_tokens,
                record.total_tokens,
                record.response_time,
                record.cost,
                timestamp,
            ),
        )
        conn.commit()
        # lastrowid is SQLite's way of telling us the id of the row we
        # just inserted (the auto-incrementing "id" column).
        conversation_id = cursor.lastrowid
        
    finally:
        conn.close()

    return conversation_id
