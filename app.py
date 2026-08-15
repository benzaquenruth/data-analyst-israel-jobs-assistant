# WHAT THIS FILE DOES
# This is the Streamlit app the USER interacts with: a simple web page
# where someone types a question (e.g. "jobs for a junior data analyst
# in Tel Aviv") and gets back an answer from our RAG assistant.
#
# STEP 8 of the monitoring plan: on top of "ask -> answer" (step 1) and
# saving metrics (step 5), this version also:
#   - asks the LLM judge (judge.py) to grade the answer's relevance
#   - saves that judge verdict as feedback (db_feedback.py)
#   - shows two buttons (+1 / -1) so a real user can rate the answer,
#     which also gets saved as feedback
#
# HOW TO RUN THIS FILE:
#   uv run streamlit run app.py

import streamlit as st

from assistant import create_assistant
from db_save import save_conversation
from db_feedback import save_feedback
from judge import evaluate_relevance

# create_assistant() builds our RAG object (search index + OpenAI client).
# Streamlit re-runs this whole script top-to-bottom every time the user
# clicks something on the page, so this line runs again each time too —
# that's fine for now (matches how we learned it in the course); we can
# optimize it later with @st.cache_resource if it turns out to be slow.
assistant = create_assistant()

st.title("Data Analyst Job Seeker Assistant")

st.markdown("""
This project is built on top of real data analyst job postings scraped from Israel (LinkedIn, Indeed). Instead of scrolling through job boards yourself, you ask a question in plain English, and the assistant searches through the job postings and recommends the ones that actually match, explaining why.

It's a job matching and recommendation assistant, not a statistics tool — it can find and explain relevant jobs, but it won't answer dataset-level questions like "how many jobs are open in Tel Aviv" or "what's the average salary."
""")

st.markdown("### Try one of these questions:")

example_questions = [
    "What data analyst jobs are available in Tel Aviv?",
    "Any remote data analyst jobs?",
    "Best matches for a data / business analyst background",
    "Best maches for someone with SQL and python skills"
]

selected_question = None

for question in example_questions:
    if st.button(question, use_container_width=True):
        st.session_state["question"] = question
        selected_question = question

# A single text box where the user types their question.
user_input = st.text_input(
    "Ask about data analyst jobs in Israel:",
    key="question"
)


# typed_question = st.text_input("Ask about data analyst jobs in Israel:")
# user_input = selected_question or typed_question

# The app only does anything once the user clicks "Ask".
if selected_question or st.button("Ask"):
    user_input = selected_question or user_input
    
    with st.spinner("Searching job listings and thinking..."):
        # assistant.rag() is the full pipeline from rag_helper.py:
        # hybrid search (keyword + vector) -> build prompt -> call the LLM.
        answer = assistant.rag(user_input)

    # Because assistant is a RAGWithMetrics (see metrics.py), the call
    # above also filled in assistant.last_call with everything about
    # this one exchange: response time, token counts, and cost.
    record = assistant.last_call

    # Save this question + answer + metrics as one row in monitoring.db.
    conversation_id = save_conversation(record, user_input)

    # Ask the LLM judge (judge.py) to grade this answer's relevance to
    # the question, then save that verdict as a "judge" feedback row
    # linked to the conversation we just saved.
    relevance, explanation = evaluate_relevance(user_input, answer)
    save_feedback(
            conversation_id,
            "judge",
            relevance=relevance,
            explanation=explanation
        )

    # Stash everything needed to redraw this answer on screen into
    # st.session_state, instead of just local variables. Streamlit
    # re-runs this whole file top-to-bottom on every click (e.g. the
    # 👍/👎 buttons below) — a plain local variable would be lost on
    # that rerun, but st.session_state survives across reruns within
    # the same browser tab. This is what keeps the answer visible after
    # giving feedback, instead of it vanishing.
    st.session_state.conversation_id = conversation_id
    st.session_state.last_answer = answer
    st.session_state.last_record = record
    st.session_state.last_relevance = relevance
    st.session_state.last_explanation = explanation


# This block redraws the most recent answer + metrics + judge verdict on
# EVERY rerun (not only right after clicking "Ask"), by reading them back
# from st.session_state instead of local variables. That's what makes the
# answer stay on screen when you click 👍/👎 below — it only changes when
# a new question is asked (session_state gets overwritten above) or the
# page is actually refreshed in the browser (a fresh page load starts a
# new Streamlit session, so session_state is empty again).
if "last_answer" in st.session_state:
    record = st.session_state.last_record

    st.success("Done!")
    st.write(st.session_state.last_answer)
    # st.write(f"Response time: {record.response_time:.2f}s")
    # st.write(f"Prompt tokens: {record.prompt_tokens}")
    # st.write(f"Completion tokens: {record.completion_tokens}")
    # st.write(f"Cost: ${record.cost:.4f}")
    # st.write(f"Judge relevance: {st.session_state.last_relevance}")
    # st.write(f"Judge explanation: {st.session_state.last_explanation}")


# These two buttons live outside both blocks above, so they stay on the
# page across reruns. They only work once a question has been asked at
# least once (i.e. once st.session_state.conversation_id exists) —
# that's what "conversation_id" in st.session_state checks.
st.divider()
col1, col2 = st.columns(2)

with col1:
    if st.button("👍 Helpful"):
        if "conversation_id" in st.session_state:
            save_feedback(st.session_state.conversation_id, "user", score=1)
            st.write("Thanks for the feedback!")
        else:
            st.write("Ask a question first.")

with col2:
    if st.button("👎 Not helpful"):
        if "conversation_id" in st.session_state:
            save_feedback(st.session_state.conversation_id, "user", score=-1)
            st.write("Thanks for the feedback!")
        else:
            st.write("Ask a question first.")
