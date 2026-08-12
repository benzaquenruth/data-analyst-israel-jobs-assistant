# Data Analyst Israel Jobs RAG Assistant

A RAG (Retrieval-Augmented Generation) assistant that helps you find data analyst jobs in Israel. Built as the final project for the [LLM Zoomcamp](https://github.com/DataTalksClub/llm-zoomcamp) course.

## What this is

This project is built on top of real data analyst job postings scraped from Israel (LinkedIn, Indeed). Instead of scrolling through job boards yourself, you ask a question in plain English, and the assistant searches through the job postings and recommends the ones that actually match, explaining why.

It's a job matching and recommendation assistant, not a statistics tool — it can find and explain relevant jobs, but it won't answer dataset-level questions like "how many jobs are open in Tel Aviv" or "what's the average salary."

**Good questions to ask:**
- "What data analyst jobs are available in Tel Aviv?"
- "Find me a junior-level BI role that doesn't need SQL experience yet."
- "Any remote data analyst jobs for someone with Python and Excel skills?"
- "Show me product analytics jobs at tech companies in Herzliya."

## Quickstart

The easiest way to run this project is with Docker Compose.

1. Clone the repo and go into it:
   ```
   git clone https://github.com/benzaquenruth/data-analyst-israel-jobs-assistant
   cd data-analyst-israel-jobs-assistant
   ```

2. Create a `.env` file with your OpenAI API key:
   ```
   OPENAI_API_KEY=your-key-here
   ```

3. Install the Python dependencies (needed for the next step, which runs on your machine, not in Docker):
   ```
   uv sync
   ```

4. Build the search index and the monitoring database. This reads `rag_jobs.csv` (already included in the repo, no credentials needed) and only needs to be run once:
   ```
   uv run python ingest.py
   uv run python db_init.py
   ```

5. Start the app and the dashboard:
   ```
   docker-compose up
   ```

The assistant runs at http://localhost:8501, and the monitoring dashboard at http://localhost:8502.

## Prerequisites
- Python 3.12
- [uv](https://docs.astral.sh/uv/) for dependency management
- Docker and Docker Compose
- An OpenAI API key

## How it works

`ingest.py` reads ~4,600 real job postings from `rag_jobs.csv` and builds two search indexes:
- a **keyword index** (`sqlitesearch.TextSearchIndex`, saved to `jobs.db`)
- a **vector index** (OpenAI `text-embedding-3-small` embeddings, saved to `data/`)

When you ask a question, the assistant (`rag_helper.py`) runs both searches and combines their results with reciprocal rank fusion (hybrid search), then passes the best-matching job postings to an LLM, which writes the final answer.

## Evaluation

Retrieval was evaluated on 25 ground-truth question/job pairs (`data/ground_truth.csv`), comparing keyword-only search against hybrid search:

| Search type | Hit rate | MRR |
|---|---|---|
| Keyword-only | 0.28 | 0.159 |
| Hybrid (keyword + vector) | 0.76 | 0.435 |

Hybrid search nearly triples retrieval quality, so it's what the app uses in production.

The final answers were also scored by an LLM-as-a-judge for relevance: 23 out of 25 were rated "good" with the tuned search weights, up from 19/25 with the original weights. Full evaluation details are in `04-evaluation-notebook.ipynb`.

## Monitoring

Every question asked in the app is logged to `monitoring.db`, along with:
- the LLM's response time, token usage, and cost
- an LLM-as-a-judge relevance score for the answer
- optional 👍/👎 feedback from the user

The dashboard (`dashboard.py`) reads this data and shows cost, response time, and token usage over time, the judge's relevance scores, user feedback counts, and a list of recent conversations.

## Tech stack
- **LLM + embeddings:** OpenAI (`gpt-5.4-mini` for answers, `text-embedding-3-small` for embeddings)
- **Search:** `sqlitesearch` (keyword) + OpenAI embeddings (vector), combined via hybrid search
- **Interface & dashboard:** Streamlit
- **Storage:** SQLite (`jobs.db` for the search index, `monitoring.db` for monitoring data)
- **Dependency management:** uv
- **Containerization:** Docker / Docker Compose
