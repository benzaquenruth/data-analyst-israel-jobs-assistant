# WHAT THIS FILE DOES
# This file saves one piece of feedback about a conversation into
# monitoring.db, as one new row in the "feedback" table we created in
# db_init.py. It's used for two different kinds of feedback:
#   - the LLM judge's verdict (source="judge", from judge.py)
#   - a real user's thumbs up/down (source="user", from app.py)
# Both share the same table — which kind a row is comes from the
# "source" column.

from datetime import datetime

from db_init import get_db_connection


# save_feedback() writes one new row into the feedback table.
#   - conversation_id: which conversation this feedback is about (the id
#     returned earlier by save_conversation() in db_save.py)
#   - source: "judge" or "user"
#   - relevance / explanation: filled in for judge feedback
#     (RELEVANT / PARTLY_RELEVANT / NON_RELEVANT + why)
#   - score: filled in for user feedback (+1 for thumbs up, -1 for
#     thumbs down)
# Whichever fields don't apply are just left as None (SQLite stores
# that as NULL).
def save_feedback(conversation_id, source, relevance=None,
                   explanation=None, score=None):
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
