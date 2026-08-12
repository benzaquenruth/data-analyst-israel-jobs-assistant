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

## From where the data comes from?

I extracted the job postings myself from the internet and processed them
with a pipeline I built. This pipeline is part of a bigger project, and
you're welcome to take a look at it here: [data_analyst_job_seeker_automation](https://github.com/benzaquenruth/data_analyst_job_seeker_automation).

[`rag_jobs.csv`](rag_jobs.csv) is the full dataset. If you want to see what
the data looks like, check [`rag_jobs_sample.csv`](rag_jobs_sample.csv),
which has a sample of 100 rows (job descriptions truncated for readability)
and renders as a table right here on GitHub.

## Evaluation

Retrieval was evaluated on 25 ground-truth question/job pairs (`data/ground_truth.csv`).

### Conclusion: keyword search vs. hybrid search

We compared three retrieval setups on the same 25 ground-truth questions:

| Search method | boost_dict | hit_rate | mrr |
|---|---|---|---|
| Keyword only | `{"Title": 3.0, "skills": 0.5}` | 0.28 | 0.159 |
| Keyword only (production weights) | `{"skills": 4.0, "Title": 3.0, "Job_Description": 3.0}` | 0.28 | 0.159 |
| **Hybrid (keyword + vector)** | `{"skills": 4.0, "Title": 3.0, "Job_Description": 3.0}` | **0.76** | **0.435** |

**Keyword search alone is weak here.** Only 28% of the time did it return the
correct job in the top 5 — and changing which fields get boosted didn't
meaningfully help. That's expected: our ground-truth questions were written
to avoid reusing the listing's exact words (to mimic how people actually
search), which is exactly the kind of paraphrasing keyword search struggles
with.

**Hybrid search fixes most of that.** Adding vector search on top of keyword
search almost triples the hit rate (0.28 → 0.76) and nearly triples the MRR
(0.159 → 0.435). This makes sense: vector search matches on *meaning*, not
exact words, so it can find the right job even when the question doesn't
share vocabulary with the listing.

**Takeaway:** hybrid search is clearly the right choice for this assistant,
confirming the current production setup (`RAGBase.rag()` already uses
`hybrid_search()`, not keyword search alone).

**Caveat:** these numbers come from a small sample — 25 questions generated
from just 5 job listings. They show a clear direction, not a precise,
final score. Worth re-running on a larger ground-truth sample before citing
these numbers as final.

### LLM-as-a-judge evaluation

Beyond retrieval metrics, we also scored the assistant's final answers with
an LLM-as-a-judge, run twice against the same 25 questions — once for each
boost_dict — to see whether the retrieval tuning above actually improved the
answers a user receives, not just the search hit rate:

| boost_dict | good answers |
|---|---|
| `{"Title": 3.0, "skills": 0.5}` | 19/25 |
| **`{"skills": 4.0, "Title": 3.0, "Job_Description": 3.0}`** | **23/25** |

The tuned weights produced more "good" answers (23/25) than the original
weights (19/25), so we chose the tuned boost_dict for production — it's the
same one used above in the hybrid search row, and it's what `RAGBase.rag()`
uses today. For more details check the notebook [`04-evaluation-notebook.ipynb`](04-evaluation-notebook.ipynb) in the repository.

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
