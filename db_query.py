# WHAT THIS FILE DOES
# This is the "read" side of monitoring.db — the opposite of db_save.py
# and db_feedback.py (which write data in). These functions pull data
# back OUT, already shaped the way dashboard.py needs it: recent
# conversations, overall stats, judge-relevance counts, and user
# thumbs up/down counts. dashboard.py will just call these functions
# and plot the results — it won't write any SQL itself.

from dataclasses import dataclass

from db_init import get_db_connection
from metrics import LLMCallRecord


# Stats holds the four headline numbers shown at the top of the
# dashboard. A dataclass here is just a simple named container, same
# idea as LLMCallRecord in metrics.py.
@dataclass
class Stats:
    total: int
    avg_response_time: float
    total_cost: float
    avg_tokens: float


# row_to_record() converts one raw row from the "conversations" table
# (a plain tuple of values, in column order) into an LLMCallRecord —
# the same object shape metrics.py uses. That way dashboard.py can work
# with conversations the same way whether they just came from a live
# LLM call or were loaded back from the database.
def row_to_record(row):
    return LLMCallRecord(
        model=row[3],
        instructions=row[4],
        prompt=row[5],
        answer=row[2],
        prompt_tokens=row[6],
        completion_tokens=row[7],
        total_tokens=row[8],
        response_time=row[9],
        cost=row[10],
        timestamp=row[11],
    )


# get_conversations() returns the most recent `limit` conversations,
# newest first — used for the "recent conversations" list on the
# dashboard. Each row becomes an LLMCallRecord (via row_to_record), plus
# we return the question text separately since LLMCallRecord doesn't
# have a "question" field (only "prompt", the full text sent to the LLM).
def get_conversations(limit=10):
    conn = get_db_connection()
    try:
        rows = conn.execute(
            """
            SELECT id, question, answer, model,
                   instructions, prompt,
                   prompt_tokens, completion_tokens, total_tokens,
                   response_time, cost, timestamp
            FROM conversations
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    finally:
        conn.close()

    results = []
    for row in rows:
        record = row_to_record(row)
        results.append({"id": row[0], "question": row[1], "record": record})

    return results


# get_stats() answers: "give me the main monitoring numbers across ALL
# conversations" — shown as the summary metrics at the top of the
# dashboard.
def get_stats():
    conn = get_db_connection()
    try:
        row = conn.execute("""
            SELECT
                COUNT(*),
                AVG(response_time),
                SUM(cost),
                AVG(total_tokens)
            FROM conversations
        """).fetchone()
    finally:
        conn.close()

    return Stats(
        total=row[0],
        avg_response_time=row[1] or 0.0,
        total_cost=row[2] or 0.0,
        avg_tokens=row[3] or 0.0,
    )


# get_relevance_stats() returns how many judge verdicts fall into each
# relevance category, e.g. {"RELEVANT": 8, "PARTLY_RELEVANT": 2}. Used
# for the judge-relevance bar chart on the dashboard.
def get_relevance_stats():
    conn = get_db_connection()
    try:
        rows = conn.execute("""
            SELECT relevance, COUNT(*)
            FROM feedback
            WHERE source = 'judge'
            GROUP BY relevance
        """).fetchall()
    finally:
        conn.close()

    return dict(rows)


# get_user_feedback_stats() returns (thumbs_up_count, thumbs_down_count)
# from real user feedback (score = +1 or -1).
def get_user_feedback_stats():
    conn = get_db_connection()
    try:
        row = conn.execute("""
            SELECT
                SUM(CASE WHEN score > 0 THEN 1 ELSE 0 END),
                SUM(CASE WHEN score < 0 THEN 1 ELSE 0 END)
            FROM feedback
            WHERE source = 'user'
        """).fetchone()
    finally:
        conn.close()

    return row[0] or 0, row[1] or 0


# This lets us do a quick sanity check from the terminal:
#   uv run python db_query.py
if __name__ == "__main__":
    print("Stats:", get_stats())
    print("Relevance stats:", get_relevance_stats())
    print("User feedback (up, down):", get_user_feedback_stats())
    print("Recent conversations:")
    for c in get_conversations(limit=5):
        print(" -", c["id"], c["question"])
