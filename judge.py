# WHAT THIS FILE DOES
# This file grades an answer automatically, using a separate LLM call as
# a "judge." Given the user's question and the assistant's answer, it
# asks: does this answer actually address the question? The judge
# replies with one of three verdicts (RELEVANT / PARTLY_RELEVANT /
# NON_RELEVANT) plus a short explanation.
#
# This is the same LLM-as-judge idea used in 04-evaluation-notebook.ipynb
# for offline evaluation on 25 ground-truth questions — here we run it
# live, on every real question asked in the app, so we can watch answer
# quality over time on the monitoring dashboard (built in a later step).

from pydantic import BaseModel
from typing import Literal
from openai import OpenAI

from evaluation_utils import llm_structured_retry


# Pydantic model describing exactly what shape we want the judge's
# answer in. Passing this to llm_structured_retry() (below) forces the
# LLM's response to match this structure, instead of free-form text we'd
# have to parse ourselves.
class RelevanceVerdict(BaseModel):
    relevance: Literal["NON_RELEVANT", "PARTLY_RELEVANT", "RELEVANT"]
    explanation: str


judge_instructions = """
You are an expert evaluator for a RAG-based job matching assistant.
The assistant recommends data analyst job listings in Israel in response
to a user's question.

Analyze whether the generated answer actually addresses the user's
question, based only on the question and answer text (you do not see
the underlying job listings).

Classify the answer as:
- RELEVANT: the answer addresses the question (e.g. it recommends jobs
  that match what was asked, or correctly explains it found nothing).
- PARTLY_RELEVANT: the answer partially addresses the question.
- NON_RELEVANT: the answer does not address the question at all.
""".strip()

judge_prompt = """
Question: {question}
Generated Answer: {answer}
""".strip()


# evaluate_relevance() sends one question/answer pair to the judge and
# returns (relevance, explanation). A client is created automatically if
# none is passed in, so callers (like app.py) don't need to build one
# just to use this function.
def evaluate_relevance(question, answer, client=None):
    if client is None:
        client = OpenAI()

    prompt = judge_prompt.format(
        question=question,
        answer=answer
    )

    result, usage = llm_structured_retry(
        client,
        judge_instructions,
        prompt,
        RelevanceVerdict,
    )

    return result.relevance, result.explanation
