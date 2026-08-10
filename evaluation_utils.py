# time is a built-in Python module
# That means: "wait a little bit before trying again."
import time

# tqdm is a library that shows a progress bar
from tqdm.auto import tqdm
from rag_helper import RAGBase


# This calculates the price of one LLM call.
def calc_price(usage):
    input_price_per_million = 0.75
    output_price_per_million = 4.50

    input_cost = (usage.input_tokens / 1_000_000) * input_price_per_million
    output_cost = (usage.output_tokens / 1_000_000) * output_price_per_million
    total_cost = input_cost + output_cost

    return {
        "input_cost": input_cost,
        "output_cost": output_cost,
        "total_cost": total_cost
    }


# This calculates the total cost for many LLM calls
def calc_total_price(usages):
    total_cost = 0.0

    for usage in usages:
        cost = calc_price(usage)
        total_cost += cost["total_cost"]

    return total_cost


# This function calls the LLM and asks for a structured output.
def llm_structured(client, instructions, user_prompt, output_type, model="gpt-5.4-mini"):
    messages = [
        {"role": "developer", "content": instructions},
        {"role": "user", "content": user_prompt}
    ]

    # This asks the model to return something that matches output_type
    response = client.responses.parse(
        model=model,
        input=messages,
        text_format=output_type
    )
    # It returns two things: 1. The parsed structured response & 2. The token usage
    return response.output_parsed, response.usage


# This is the safer version of llm_structured
# It tries to call the LLM. If it fails, it tries again.
def llm_structured_retry(
    client,
    instructions,
    user_prompt,
    output_type,
    model="gpt-5.4-mini",
    max_retries=3,
):
    for attempt in range(max_retries):
        try:
            return llm_structured(
                client,
                instructions,
                user_prompt,
                output_type,
                model=model,
            )
        except Exception:
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)


# This creates a new RAG class based on RAGBase
# It adds the ability to track usage and calculate costs.
class RAGWithUsage(RAGBase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.usages = []
        self.last_usage = None

    def reset_usage(self):
        self.usages = []
        self.last_usage = None

    # Same boost weights as the production RAGBase.search() in rag_helper.py.
    # We tested keyword vs. hybrid search with these weights in the notebook
    # (hybrid clearly won), so this evaluation should use the same weights
    # the real assistant uses, not a separate experimental set.
    def search(self, query, num_results=5):
        boost_dict = {"skills": 4.0, "Title": 3.0, "Job_Description": 3.0}

        return self.index.search(
            query,
            num_results=num_results,
            boost_dict=boost_dict
        )

    def llm(self, prompt):
        input_messages = [
            {"role": "developer", "content": self.instructions},
            {"role": "user", "content": prompt}
        ]

        response = self.llm_client.responses.create(
            model=self.model,
            input=input_messages
        )

        self.last_usage = response.usage
        self.usages.append(response.usage)

        return response.output_text

    def total_cost(self):
        return calc_total_price(self.usages)

# progress bar
def map_progress(pool, seq, f):
    results = []

    with tqdm(total=len(seq)) as progress:
        futures = []

        for el in seq:
            future = pool.submit(f, el)
            future.add_done_callback(lambda p: progress.update())
            futures.append(future)

        for future in futures:
            result = future.result()
            results.append(result)

    return results
