# loading data and building the search index
# This file handles data loading and index creation - everything we need before we can search

# job listings ingested from rag_jobs.csv (exported from BigQuery so anyone
# cloning the repo can run the assistant without needing our BigQuery credentials)
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI, RateLimitError
from sqlitesearch import TextSearchIndex

load_dotenv()

CSV_PATH = "rag_jobs.csv"
DB_PATH = "jobs.db"

KEYWORD_FIELDS = ["Platform", "Company_Name", "City", "experience_bucket", "Date"]
TEXT_FIELDS = ["Title", "Job_Description", "experience_reasoning", "skills"]

# fields combined into one string per job for embedding
VECTOR_TEXT_FIELDS = [
    "Title", "Company_Name", "City", "Job_Description", "Date",
    "Platform", "experience_bucket", "experience_reasoning", "skills",
]
EMBEDDING_MODEL = "text-embedding-3-small"
VECTOR_DIR = Path("data")
VECTOR_EMBEDDINGS_PATH = VECTOR_DIR / "vector_embeddings.npy"
VECTOR_DOCUMENTS_PATH = VECTOR_DIR / "vector_documents.json"
# OpenAI's embeddings endpoint caps how many inputs one request can hold
# (also caps total tokens per request at 300k - keep batches small enough to stay under that)
EMBEDDING_BATCH_SIZE = 150


# use load_jobs_data() to load the job listings from rag_jobs.csv
def load_jobs_data():
    df = pd.read_csv(CSV_PATH)
    # CSV has no nulls to speak of, but a job missing e.g. skills or a city
    # should end up as "" (searchable/joinable text), not the string "nan"
    df = df.fillna("")

    documents = df.to_dict(orient="records")
    print(f"Loaded {len(documents)} job listings")
    return documents


# reload the documents we already indexed, straight from jobs.db
# useful so notebooks don't have to hit BigQuery again on every rerun
def load_documents_from_db(db_path=DB_PATH):
    import sqlite3

    conn = sqlite3.connect(db_path)
    rows = conn.execute("SELECT doc_json FROM docs").fetchall()
    conn.close()

    return [json.loads(row[0]) for row in rows]


# create the sqlitesearch keyword index and save it to a .db file on disk
def build_keyword_index(documents):
    index = TextSearchIndex(
        text_fields=TEXT_FIELDS,
        keyword_fields=KEYWORD_FIELDS,
        # Save the SQLite search database in a file called jobs.db
        db_path=DB_PATH
    )

    for doc in documents:
        index.add(doc)
    
    print("Keyword index saved to jobs.db")

    index.close()


# with ~4,600 jobs to embed, we can burn through OpenAI's tokens-per-minute
# limit mid-run and get a RateLimitError back - retry with exponential
# backoff (same pattern the course covers) instead of letting the whole
# ingest crash partway through
MAX_EMBEDDING_RETRIES = 5


def embed_with_retry(client, batch):
    for attempt in range(MAX_EMBEDDING_RETRIES):
        try:
            return client.embeddings.create(model=EMBEDDING_MODEL, input=batch)
        except RateLimitError:
            if attempt == MAX_EMBEDDING_RETRIES - 1:
                raise
            wait = 2 ** attempt  # 1s, 2s, 4s, 8s, 16s
            print(f"Rate limited, retrying in {wait}s...")
            time.sleep(wait)


# embed each job with OpenAI and save the vectors + matching documents to disk
def build_vector_index(documents):
    client = OpenAI()

    texts = [
        " ".join(str(doc.get(field) or "") for field in VECTOR_TEXT_FIELDS)
        for doc in documents
    ]

    embeddings = []
    for i in range(0, len(texts), EMBEDDING_BATCH_SIZE):
        batch = texts[i:i + EMBEDDING_BATCH_SIZE]
        response = embed_with_retry(client, batch)
        embeddings.extend(item.embedding for item in response.data)

    VECTOR_DIR.mkdir(parents=True, exist_ok=True)
    np.save(VECTOR_EMBEDDINGS_PATH, np.array(embeddings, dtype=np.float32))

    with open(VECTOR_DOCUMENTS_PATH, "w") as f:
        json.dump(documents, f)


if __name__ == "__main__":
    documents = load_jobs_data()
    build_keyword_index(documents)
    build_vector_index(documents)
    
    print(f"Vector embeddings saved to {VECTOR_EMBEDDINGS_PATH}")
    print(f"Vector documents saved to {VECTOR_DOCUMENTS_PATH}")