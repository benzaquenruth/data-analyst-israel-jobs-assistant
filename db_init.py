# WHAT THIS FILE DOES
# This file sets up our monitoring database: a separate SQLite file called
# monitoring.db (NOT jobs.db — that one holds the job listings for search,
# this one holds a log of every question asked, every answer given, and
# the feedback on those answers).
#
# In the course this used PostgreSQL (psycopg, a server you have to run
# separately). We're using SQLite instead: no server to start, it's just
# a single file that sqlite3 (built into Python) reads and writes.
#
# Run this file ONCE to create the tables before using app.py:
#   uv run python db_init.py

import sqlite3

DB_PATH = "monitoring.db"


# get_db_connection() opens (or creates, if it doesn't exist yet) the
# monitoring.db file and returns a connection to it. Every other file
# that needs to read or write monitoring data will call this same
# function, so they all talk to the same database file.
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)

    # SQLite does not enforce "foreign keys" (the rule that a feedback
    # row's conversation_id must point to a real conversation) unless we
    # turn it on explicitly. This line turns it on for this connection.
    conn.execute("PRAGMA foreign_keys = ON")

    return conn


# init_db() creates the "conversations" table: one row per question asked
# in the app, with the answer and all the metrics we care about
# (tokens, cost, response time). drop=True wipes it first — useful while
# we're still developing, but leave it False in normal use so we don't
# lose data by accident.
def init_db(drop=False):
    conn = get_db_connection()
    try:
        if drop:
            conn.execute("DROP TABLE IF EXISTS conversations")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                model TEXT NOT NULL,
                instructions TEXT NOT NULL,
                prompt TEXT NOT NULL,
                prompt_tokens INTEGER NOT NULL,
                completion_tokens INTEGER NOT NULL,
                total_tokens INTEGER NOT NULL,
                response_time REAL NOT NULL,
                cost REAL NOT NULL,
                timestamp TEXT NOT NULL
            )
        """)
        conn.commit()
    finally:
        conn.close()


# init_feedback() creates the "feedback" table: one row per piece of
# feedback on a conversation. A conversation can have TWO kinds of
# feedback rows:
#   - source="judge" -> an LLM judge's relevance verdict (from judge.py)
#   - source="user"  -> a real user's thumbs up (+1) / thumbs down (-1)
# conversation_id links each feedback row back to its conversation.
def init_feedback(drop=False):
    conn = get_db_connection()
    try:
        if drop:
            conn.execute("DROP TABLE IF EXISTS feedback")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER NOT NULL REFERENCES conversations(id),
                source TEXT NOT NULL,
                relevance TEXT,
                explanation TEXT,
                score INTEGER,
                timestamp TEXT NOT NULL
            )
        """)
        conn.commit()
    finally:
        conn.close()


# Running `python db_init.py` directly builds both tables. Safe to run
# more than once — CREATE TABLE IF NOT EXISTS just leaves existing
# tables (and their data) alone.
if __name__ == "__main__":
    init_db()
    init_feedback()
    print(f"Database initialized at {DB_PATH}")
