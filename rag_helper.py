# the RAG logic: search, prompt, LLM

from openai import OpenAI
from sqlitesearch import TextSearchIndex
import json
from pathlib import Path

import numpy as np

DB_PATH = "jobs.db"
EMBEDDING_MODEL = "text-embedding-3-small"

VECTOR_EMBEDDINGS_PATH = Path("data/vector_embeddings.npy")
VECTOR_DOCUMENTS_PATH = Path("data/vector_documents.json")

TEXT_FIELDS = ["Title", "Job_Description",  "skills"]
KEYWORD_FIELDS = ["Platform", "Company_Name", "City", "Status", "experience_bucket"]


INSTRUCTIONS = """
You are a job matching assistant for data analyst jobs in Israel.

Your task is to answer one user question at a time by recommending relevant jobs
from the provided job posting context.

The assistant is good for questions like:
- Recommend jobs for someone with specific skills.
- Find jobs that match a certain experience level.
- Find jobs in a specific city or location.
- Recommend jobs that match a product analytics, BI, or data analyst background.
- Explain why the retrieved jobs are relevant to the user's question.
- while recomendig specific jobs, always provide the link to the job posting.
- Don't add ideas for future questions or next steps in your answer. For example, don't add things like "You can also ask me about..." or "Next, you might want to..." ot "If you want, I can also rank these by..."

Do not answer dataset-level analytics questions such as counts, averages,
totals, percentages, or "most common" statistics.

If the user asks for aggregations, say:
"This assistant is designed for job matching and recommendations, not dataset-level statistics."

Use only the provided context.
If the answer is not found in the context, say:
"I don't know based on the available job data."
"""


PROMPT_TEMPLATE = """
QUESTION: {question}

CONTEXT:
{context}
""".strip()


# load the keyword search index we created in ingest.py
def load_index():
    index = TextSearchIndex(
        text_fields=TEXT_FIELDS,
        keyword_fields=KEYWORD_FIELDS,
        db_path=DB_PATH
    )

    return index

# load the vector index we created in ingest.py
def load_vector_index():
    embeddings = np.load(VECTOR_EMBEDDINGS_PATH)

    with open(VECTOR_DOCUMENTS_PATH, "r") as f:
        documents = json.load(f)

    return embeddings, documents


class RAGBase:

    def __init__(
        self,
        index,
        llm_client,
        instructions=INSTRUCTIONS,
        prompt_template=PROMPT_TEMPLATE,
        model="gpt-5.4-mini"
    ):
        self.index = index
        self.llm_client = llm_client
        self.instructions = instructions
        self.prompt_template = prompt_template
        self.model = model

    # search for relevant job postings
    def search(self, query, num_results=5):
        boost_dict = {
            "skills": 4.0,
            "Title": 3.0,
            "Job_Description": 3.0
        }

        return self.index.search(
            query,
            num_results=num_results,
            boost_dict=boost_dict
        )

    # turn search results into text context for the LLM
    def build_context(self, search_results):
        lines = []

        for doc in search_results:
            lines.append("Title: " + str(doc.get("Title", "")))
            lines.append("Company: " + str(doc.get("Company_Name", "")))
            lines.append("City: " + str(doc.get("City", "")))
            lines.append("Platform: " + str(doc.get("Platform", "")))
            lines.append("Experience level: " + str(doc.get("experience_bucket", "")))
            lines.append("Skills: " + str(doc.get("skills", "")))
            lines.append("Job description: " + str(doc.get("Job_Description", "")))
            lines.append("Link: " + str(doc.get("Link", "")))
            lines.append("")

        return "\n".join(lines).strip()

    # build the full prompt
    def build_prompt(self, query, search_results):
        context = self.build_context(search_results)

        return self.prompt_template.format(
            question=query,
            context=context
        )

    # send the prompt to the LLM
    def llm(self, prompt):
        input_messages = [
            {"role": "developer", "content": self.instructions},
            {"role": "user", "content": prompt}
        ]

        response = self.llm_client.responses.create(
            model=self.model,
            input=input_messages
        )

        return response.output_text
    
        # search using vector embeddings
    def vector_search(self, query, num_results=5):
        embeddings, documents = load_vector_index()

        # turn the user question into a vector
        response = self.llm_client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=query
        )

        query_embedding = np.array(response.data[0].embedding, dtype=np.float32)

        # normalize query vector
        query_embedding = query_embedding / np.linalg.norm(query_embedding)

        # normalize document vectors
        embeddings = embeddings / np.linalg.norm(
            embeddings,
            axis=1,
            keepdims=True
        )

        # calculate similarity between query and every job document
        scores = embeddings @ query_embedding

        # get the best matching documents
        best_indices = np.argsort(scores)[::-1][:num_results]

        results = []
        for idx in best_indices:
            doc = documents[idx]
            doc["score"] = float(scores[idx])
            results.append(doc)

        return results
    
        # search using both keyword search and vector search
    def hybrid_search(self, query, num_results=5):
        keyword_results = self.search(query, num_results=10)
        vector_results = self.vector_search(query, num_results=10)

        scores = {}
        documents = {}

        # add keyword search results
        for rank, doc in enumerate(keyword_results):
            key = doc.get("Link") or doc.get("Title")

            if key not in scores:
                scores[key] = 0
                documents[key] = doc

            # higher rank = higher score
            scores[key] += 1 / (rank + 1)

        # add vector search results
        for rank, doc in enumerate(vector_results):
            key = doc.get("Link") or doc.get("Title")

            if key not in scores:
                scores[key] = 0
                documents[key] = doc

            # higher rank = higher score
            scores[key] += 1 / (rank + 1)

        # sort by final hybrid score
        sorted_keys = sorted(scores, key=scores.get, reverse=True)

        results = []
        for key in sorted_keys[:num_results]:
            doc = documents[key]
            doc["hybrid_score"] = scores[key]
            results.append(doc)

        return results
    
    # full RAG flow
    def rag(self, query):
        search_results = self.hybrid_search(query)
        prompt = self.build_prompt(query, search_results)
        answer = self.llm(prompt)
    
        return answer