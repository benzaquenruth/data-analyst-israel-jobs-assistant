# WHAT THIS FILE DOES
# This file saves one finished conversation (a question + its answer +
# all the metrics from metrics.py) into monitoring.db, as one new row
# in the "conversations" table we created in db_init.py.
#
# app.py will call save_conversation() right after getting an answer
# from the assistant.




from datetime import datetime

from db_init import get_db_connection


# save_conversation() takes:
#   - record: an LLMCallRecord from metrics.py (has answer, model,
#     tokens, cost, response_time, etc.)
#   - question: the raw text the user typed in
# and writes one new row into the conversations table.
#
# It returns the new row's id, so app.py can remember "this is
# conversation #17" and later attach feedback to that same row.
def save_conversation(record, question):
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
