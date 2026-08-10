# WHAT THIS FILE DOES
# This file adds monitoring on top of our RAG assistant. It defines
# RAGWithMetrics, a version of RAGBase (from rag_helper.py) that works
# exactly the same way — same search, same prompt, same answers — but
# every time it calls the LLM, it also records: how long the call took,
# how many tokens were used, and how much it cost. That record gets
# saved on the object as `self.last_call`, so app.py can read it right
# after asking a question and display/save it.
#
# We reuse calc_price() from evaluation_utils.py for the cost math,
# instead of writing pricing numbers again here — that function is
# already our one source of truth for "how much does an LLM call cost"
# (it's what the evaluation notebook uses too), so both places always
# agree on the price.

import time
from dataclasses import dataclass, field
from datetime import datetime

from rag_helper import RAGBase
from evaluation_utils import calc_price


# One LLMCallRecord = a snapshot of everything worth knowing about a
# single question-answer exchange. A dataclass is just a simple
# container for these fields — no extra logic, just organized storage.
@dataclass
class LLMCallRecord:
    model: str
    prompt: str
    instructions: str
    answer: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    response_time: float
    cost: float
    timestamp: datetime = field(default_factory=datetime.now)


# RAGWithMetrics inherits everything from RAGBase (search, vector_search,
# hybrid_search, build_context, build_prompt, rag) and only changes one
# thing: the llm() method, which is where the actual call to OpenAI
# happens. That's the one place we need to measure time and read token
# usage, so that's the one method we override.
class RAGWithMetrics(RAGBase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # last_call holds the LLMCallRecord for the most recent question.
        # Starts as None until the first question is asked.
        self.last_call: LLMCallRecord = None

    def llm(self, prompt):
        start_time = time.time()
        response = self._call_llm(prompt)
        response_time = time.time() - start_time

        self._log_response(prompt, response, response_time)

        return response.output_text

    # _call_llm() is the actual API call to OpenAI — split out from llm()
    # so we can time it cleanly (start the clock, call this, stop the
    # clock) without the timing code and the API-call code tangled up.
    def _call_llm(self, prompt):
        input_messages = [
            {"role": "developer", "content": self.instructions},
            {"role": "user", "content": prompt}
        ]

        return self.llm_client.responses.create(
            model=self.model,
            input=input_messages
        )

    # _log_response() takes the raw API response and turns it into an
    # LLMCallRecord, then stores it as self.last_call so app.py can read
    # it right after calling .rag(). Note: this is "good enough" for one
    # person using the app at a time — it's not built to handle many
    # simultaneous users safely, but that's fine for our project.
    def _log_response(self, prompt, response, response_time):
        usage = response.usage
        cost = calc_price(usage)["total_cost"]

        call_record = LLMCallRecord(
            model=self.model,
            prompt=prompt,
            instructions=self.instructions,
            answer=response.output_text,
            prompt_tokens=usage.input_tokens,
            completion_tokens=usage.output_tokens,
            total_tokens=usage.total_tokens,
            response_time=response_time,
            cost=cost,
        )

        self.last_call = call_record
