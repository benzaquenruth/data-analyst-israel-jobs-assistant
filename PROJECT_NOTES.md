# Project working notes — data-analyst-israel-jobs-assistant

> Working doc for Claude and Ruth to track progress across sessions.
> Not the final README — see README.md for the user-facing doc, built up as we go.

## What this is
RAG assistant over data-analyst job listings for Israel — Ruth's final project for the LLM Zoomcamp course. Follows the course's FAQ-assistant pattern, adapted: BigQuery instead of a static JSON dataset, `sqlitesearch` instead of in-memory `minsearch` (matches the pattern from the course notebook Ruth learned from).

## Data source
BigQuery table `massive-bliss-481811-d8.job_listings_analysis.rag_jobs`.
Key fields: `Title`, `Job_Description`, `Platform`, `Link` (used as de-facto id), `Date`, `Rating`, `Fit_for_the_job`, `Reasoning`, `experience_reasoning`, `experience_bucket`, `skills` (repeated), `Company_Name`, `City`, `Status`, `Expired`, `Remote`.

## Indexing decisions
- `text_fields`: `Title`, `Job_Description`, `experience_reasoning`, `skills`
- `keyword_fields`: `Platform`, `Company_Name`, `City`, `Status`, `experience_bucket`
- Index ALL rows, no `Expired` filter.
- `Reasoning` excluded — personal fit-score justification, not useful to other users.

## BigQuery
- Key file gitignored, wired via `GOOGLE_APPLICATION_CREDENTIALS` in `.env`. Connection tested — 4,255 rows.
- Later: export to CSV for the published repo, so others don't need Ruth's GCP access.

## Vector search
- Uses OpenAI embeddings (`text-embedding-3-small`), not ONNX — simpler, no local model/tokenizer needed. Decided against the course's ONNX approach (`download.py`/`embedder.py`, `sqlitesearch.VectorSearchIndex`) for this reason.
- `build_vector_index()` in `ingest.py`: for each job, joins `Title`, `Company_Name`, `City`, `Job_Description`, `Platform`, `experience_bucket`, `experience_reasoning`, `skills` into one text string, embeds in batches of 500 (OpenAI's per-request input cap), and saves:
  - vectors → `data/vector_embeddings.npy`
  - matching documents → `data/vector_documents.json`
- Kept separate from `jobs.db` on purpose: `TextSearchIndex` owns `jobs.db` for keyword search; embeddings are numpy arrays, simpler as `.npy` + `.json` than forced into the same SQLite file.

## Status log
- 2026-07-28: kickoff (`uv init`, base deps, `.env`, `.gitignore`).
- 2026-07-28: `ingest.py` written (BigQuery → `sqlitesearch.TextSearchIndex` → `jobs.db`).
- 2026-07-28: memory/notes setup redone (had been announced but never executed earlier).
- 2026-07-28: BigQuery connection installed + tested. `Reasoning` dropped from index.
- 2026-07-28: Vector search implemented with OpenAI embeddings (not ONNX) — `build_keyword_index()` + `build_vector_index()` both in `ingest.py`, separate storage (`jobs.db` vs `data/`).
- 2026-08-04: `rag_helper.py` (production RAG: keyword/vector/hybrid search + `rag()` flow) and `evaluation_utils.py` (cost tracking, LLM-judge helpers, parallel eval) written. Eval work started in `04-evaluation-notebook.ipynb`.
- 2026-08-04: Retrieval eval — keyword-only `boost_dict = {"Title": 3.0, "skills": 0.5}` → hit_rate 0.28 / mrr 0.159, vs hybrid (keyword+vector) with `boost_dict = {"skills": 4.0, "Title": 3.0, "Job_Description": 3.0}` → hit_rate 0.76 / mrr 0.435 → confirmed hybrid search for production. LLM-judge eval on final answers: same tuned weights → 23/25 good answers (up from 19/25 with the earlier `{"Title": 3.0, "skills": 0.5}` weights).
- 2026-08-04: Started monitoring (final project step). Pulled 9 PostgreSQL-based course reference files (`app.py`, `assistant.py`, `dashboard.py`, `db_init.py`, `db_query.py`, `db_save.py`, `db_feedback.py`, `judge.py`, `metrics.py`) into `course-reference/` — kept as pattern reference, not used directly. Building SQLite equivalents step by step instead of Postgres. **Step 1 done:** `app.py` + `assistant.py` — minimal Streamlit app, ask a question, get an answer from `RAGBase.rag()`, no monitoring saved yet. Verified working end to end. `streamlit` added as a real dependency via `uv add streamlit` (in `pyproject.toml`/`uv.lock`). **Step 2 done:** `db_init.py` — creates `monitoring.db` (SQLite, gitignored like `jobs.db`) with `conversations` and `feedback` tables (adapted from the course's Postgres schema: no `course` column since this is a single-purpose assistant, `TEXT` timestamps instead of Postgres `TIMESTAMP WITH TIME ZONE`). Verified schema via `sqlite3 monitoring.db ".schema"`.

## Monitoring plan (staged, one file at a time)
1. ✅ `app.py` + `assistant.py` — ask → answer only
2. ✅ `db_init.py` — SQLite schema (`conversations`, `feedback`)
3. ✅ `metrics.py` — `RAGWithMetrics`, tracks tokens/cost/response time per call (reuses `evaluation_utils.calc_price`, not a separate pricing table like the course had — one source of truth for cost). Verified: `last_call` correctly captured model/time/tokens/cost on a real question.
4. ✅ `db_save.py` — `save_conversation(record, question)` (no `course` param — course version had one, dropped since this is a single-purpose assistant). Verified: real conversation saved and confirmed correct in `monitoring.db` (conversation id 1).
5. ✅ `assistant.py`/`app.py` updated to use `RAGWithMetrics` + display metrics (response time/tokens/cost) + save each conversation via `save_conversation()`. Fully verified by Ruth in her own terminal: asked a real question in the browser, confirmed the answer + metrics displayed, and confirmed the row actually landed in `monitoring.db`.
6. ✅ `judge.py` — `evaluate_relevance(question, answer)`, LLM-as-judge (reuses `evaluation_utils.llm_structured_retry`). Instructions adapted to job-matching context (not generic course FAQ). Verified: correctly flagged a hybrid-vs-remote mismatch as `PARTLY_RELEVANT`.
7. ✅ `db_feedback.py` — `save_feedback(conversation_id, source, relevance=None, explanation=None, score=None)`. Verified: saved a judge-style row and a user-style row, both landed correctly with the right fields filled/blank.
8. ✅ `app.py` updated — after each answer, calls `judge.evaluate_relevance()` + `save_feedback(..., "judge", ...)`, and shows 👍/👎 buttons that call `save_feedback(..., "user", score=...)`. Ruth confirmed the flow works but noticed the answer/metrics disappeared from screen after clicking 👍/👎 (Streamlit rerun quirk). **Fixed:** moved the display code into its own block that reads from `st.session_state` (`last_answer`, `last_record`, `last_relevance`, `last_explanation`) instead of local variables, so the answer/metrics/judge verdict stay visible across reruns — only clear on a new question or a real page refresh. Ruth explicitly wants to keep showing tokens/cost in the app (not just the dashboard) — deliberate choice, not an oversight. Ruth confirmed in her own terminal: answer/metrics/judge verdict now stay on screen after clicking 👍/👎.
9. ✅ `db_query.py` — `get_conversations()`, `get_stats()`, `get_relevance_stats()`, `get_user_feedback_stats()`, plus `row_to_record()` helper (reuses `LLMCallRecord` from `metrics.py`). Verified against real data from Ruth's testing: 7 conversations, avg response time ~2s, total cost ~$0.017, judge relevance counts, 3 thumbs-up/0 thumbs-down.
10. ✅ `dashboard.py` written — summary stats row, cost/response-time line charts (timestamps parsed to datetime for a real time axis), recent conversations list, judge relevance bar chart, user thumbs up/down counts. All reads go through `db_query.py`, no direct SQL in this file. Syntax verified; Ruth to confirm in browser (`uv run streamlit run dashboard.py --server.port 8502`, separate terminal/port from `app.py`).

Ruth confirmed `dashboard.py` in browser — charts render correctly against real data.

**Evaluation criteria check (course rubric: 2 points = user feedback collected AND dashboard with ≥5 charts):** Original dashboard had only 3 real charts (2 line charts + judge relevance bar chart) — the 4 `st.metric()` KPI tiles and thumbs up/down tiles don't count as charts for grading purposes. Added 2 more real charts using data already being collected (no new instrumentation needed): "Tokens per conversation over time" (line chart, prompt vs completion tokens) and a bar chart version of user feedback counts (in addition to the metric tiles, not replacing them). Now at 5 real charts. Data-prep logic smoke-tested against real `monitoring.db` data.

Reordered `dashboard.py` sections per Ruth's request: "Recent conversations" moved from the middle to the very end, after all charts — charts (the at-a-glance summary) now come first, detail list last.

**Monitoring plan: DONE.** All 10 steps code-complete and verified end-to-end in the browser by Ruth, including the 5-chart rubric fix and final section ordering. Meets course rubric's 2-point bar (user feedback collected + dashboard with ≥5 real charts).

Files not yet committed to git as of this writing — ask Ruth before committing (she hasn't asked for it yet).

## Evaluation criteria scorecard (as of 2026-08-05)

Full rubric reviewed against actual code (not just memory) — verified `04-evaluation-notebook.ipynb` markdown cells directly for the two evaluation criteria.

| Criterion | Points | Notes |
|---|---|---|
| Problem description | 0 / 2 ⚠️ | `README.md` is still just the title — needs real content |
| Retrieval flow | 2 / 2 | Knowledge base (`jobs.db` + vector embeddings) + LLM both in the flow |
| Retrieval evaluation | 2 / 2 | 3 retrieval setups compared via hit_rate/mrr (keyword ×2, hybrid) — hybrid picked for production |
| LLM evaluation | 2 / 2 | LLM-as-judge on final answers, 2 setups compared (19/25 vs 23/25 good), best one adopted |
| Interface | 2 / 2 | Streamlit (`app.py`) |
| Ingestion pipeline | 1 / 2 | `ingest.py` is a plain script — no orchestration tool (Kestra/Airflow/Prefect/dlt); would need one for 2 pts |
| Monitoring | 2 / 2 | Feedback collected + 5-chart dashboard |
| Containerization | 0 / 2 | Not started — planned next (after CSV export + README) |
| Reproducibility | 0 / 2 ⚠️ | No README run instructions yet; data not accessible to others without Ruth's BigQuery creds (CSV export not done yet) |
| Best practice: hybrid search | 1 / 1 ✅ | Free point — already built + evaluated |
| Best practice: document re-ranking | 0 / 1 | Not implemented (optional) |
| Best practice: query rewriting | 0 / 1 | Not implemented (optional) |
| Bonus: cloud deployment | 0 / 2 | Not done (optional). Discussed: Streamlit Community Cloud is the easiest path and doesn't need a Dockerfile; deploying is much safer/easier now that the plan is CSV-based (no BigQuery credential to protect). Containerization and cloud deployment are complementary, not either/or — a container can *be* what gets deployed, or Streamlit Cloud can deploy straight from the repo without Docker at all. |

**Current: 12/21 core+practices points (23 incl. bonus).** The two real gaps (Problem description, Reproducibility) are cheap fixes and share a dependency: both need the CSV export + a written README.

**Decision confirmed with Ruth: staying with CSV export, not a live BigQuery connection, for the published project.** Reasoning discussed at length: no way to give a program BigQuery access without that access being extractable by whoever runs the code locally — GitHub Secrets don't solve this (they only protect Ruth's own CI, not strangers running the code on their own machines). The only way to keep live BigQuery + hidden credentials would be Ruth hosting her own proxy API server indefinitely (real ongoing infra cost, zero extra rubric points) — not worth it. CSV export removes the problem entirely and directly fixes the Reproducibility rubric gap too.

## ⏸️ Paused (2026-08-05) — blocked on an upstream data fix

Ruth is switching to a **separate session/repo for "the job seeker app"** (the n8n scraping + BigQuery ingestion pipeline that populates the `rag_jobs` table this project reads from — a different codebase, not part of this repo) to fix a data quality issue before we do the CSV export here:

**The problem:** job postings from roughly the last 1.5 months have an empty/missing `skills` column in BigQuery. Why: skills extraction was originally done as a post-processing step *after* scraping — run once over already-ingested BigQuery data using Claude Code — rather than being built into the n8n scraping workflow itself. Ruth was still evaluating the best way to do it before wiring it permanently into n8n, so newer postings never got the skills extraction step applied.

**Why this matters here:** `skills` is one of our most important fields — it's in both `text_fields` and gets the highest boost weight (4.0) in production search (see Indexing decisions above). Exporting to CSV *before* this is fixed would bake the gap into the published dataset.

**Next steps when resuming this project:**
1. (Elsewhere) Ruth fixes the `skills` column gap in BigQuery via the job-seeker-app session.
2. Come back here and export the corrected BigQuery data to a CSV; update `ingest.py` to build from the CSV instead of live BigQuery.
3. Write `README.md` (problem description + run instructions) — closes both the Problem description and Reproducibility rubric gaps.
4. Containerization (Dockerfile + docker-compose).
5. Optional stretch, time permitting: document re-ranking, query rewriting, cloud deployment (each worth 1-2 rubric points, discussed above).
6. Also still open: whether to keep `onnxruntime`/`tokenizers`/`huggingface-hub` deps (added early on, now unused since vector search uses OpenAI embeddings not ONNX).

## For README (later)
- Setup: `uv sync`.
- Data source: BigQuery live for dev; CSV export planned for the published version so others don't need GCP credentials.
- Mention the LLM Zoomcamp course origin, and note vector search uses OpenAI embeddings rather than the course's local ONNX approach.
- Evaluation: retrieval tested via hit_rate/mrr on 25 ground-truth Q&A pairs — hybrid search (`{"skills": 4.0, "Title": 3.0, "Job_Description": 3.0}`) nearly triples keyword-only performance (0.28→0.76 hit_rate, 0.159→0.435 mrr). Final answers scored by an LLM-as-judge: 23/25 "good" with tuned weights, up from 19/25 with the original `{"Title": 3.0, "skills": 0.5}` weights.
