#We're saving conversations now, so the next step is reading them back.
#Connect to the same database

from dataclasses import dataclass

from db_init import get_db_connection
from metrics import LLMCallRecord

@dataclass
class Stats:
    total: int
    avg_response_time: float
    total_cost: float
    avg_tokens: float

# A helper to convert a database row into an LLMCallRecord
def row_to_record(row):
    return LLMCallRecord(
        model=row[4],
        prompt=row[6],
        instructions=row[5],
        answer=row[2],
        prompt_tokens=row[7],
        completion_tokens=row[8],
        total_tokens=row[9],
        response_time=row[10],
        cost=row[11],
        timestamp=row[12],
    )
    
# Now update get_conversations to use it
# This gets the latest 10 saved conversations from the database
def get_conversations(limit=10):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, question, answer, course, model,
                       instructions, prompt,
                       prompt_tokens, completion_tokens, total_tokens,
                       response_time, cost, timestamp
                FROM conversations
                ORDER BY timestamp DESC
                LIMIT %s
                """,
                (limit,),
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    return [row_to_record(row) for row in rows]

# get_stats() asks PostgreSQL: “Give me the main monitoring numbers for all conversations.”
def get_stats():
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    COUNT(*),
                    AVG(response_time),
                    SUM(cost),
                    AVG(total_tokens)
                FROM conversations
            """)
            row = cur.fetchone()
    finally:
        conn.close()

    return Stats(
        total=row[0],
        avg_response_time=row[1],
        total_cost=row[2],
        avg_tokens=row[3],
    )

# Get judge relevance distribution
def get_relevance_stats():
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT relevance, COUNT(*)
                FROM feedback
                WHERE source = 'judge'
                GROUP BY relevance
            """)
            rows = cur.fetchall()
    finally:
        conn.close()
    return dict(rows)

# Get user feedback stats
def get_user_feedback_stats():
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    SUM(CASE WHEN score > 0 THEN 1 ELSE 0 END),
                    SUM(CASE WHEN score < 0 THEN 1 ELSE 0 END)
                FROM feedback
                WHERE source = 'user'
            """)
            row = cur.fetchone()
    finally:
        conn.close()
    return row

# this is just for testing from the terminal
if __name__ == "__main__":
    records = get_conversations()
    for record in records:
        print(record)
        
# command line to run it, in my case : 
# pyproject.toml = inside 01-agentic-rag-and-02-vector-search
# db_query.py = inside 05-monitoring
        