# WHAT THIS FILE DOES
# This is a small "factory" file: its only job is to build a ready-to-use
# RAG assistant object, so app.py (and later, other files) don't have to
# repeat the setup steps every time. It builds a RAGWithMetrics (from
# metrics.py) instead of a plain RAGBase — same search, same answers,
# but every call also records tokens/cost/response time on
# assistant.last_call, so app.py can display and save it.

from dotenv import load_dotenv
from openai import OpenAI

from rag_helper import load_index
from metrics import RAGWithMetrics


def create_assistant():
    # load_dotenv() reads the .env file so OPENAI_API_KEY is available
    # to the OpenAI() client below.
    load_dotenv()

    # load_index() opens the keyword search index we already built into
    # jobs.db with ingest.py — it does NOT rebuild anything, just connects.
    index = load_index()

    # RAGWithMetrics (from metrics.py) already knows how to do hybrid
    # search, build the prompt, and call the LLM (it inherits all of
    # that from RAGBase) — we just need to give it the index and an
    # OpenAI client to use.
    return RAGWithMetrics(
        index=index,
        llm_client=OpenAI()
    )


# This block only runs if you execute `python assistant.py` directly
# (not when app.py imports create_assistant from this file). Handy for a
# quick sanity check from the terminal without starting Streamlit.
if __name__ == "__main__":
    assistant = create_assistant()

    query = "What data analyst jobs are available in Tel Aviv?"
    answer = assistant.rag(query)
    print(answer)
