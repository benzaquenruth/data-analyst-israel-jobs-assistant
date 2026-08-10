# Container for the Streamlit app (app.py). docker-compose.yaml reuses this
# same image for the dashboard (dashboard.py) too, just with a different
# command - see docker-compose.yaml.
FROM python:3.12-slim

# uv is how this project installs/runs its Python deps (see pyproject.toml /
# uv.lock) - grab the uv binary itself from its own image instead of pip
# installing it.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app
# so `streamlit`/`python` resolve to the venv uv creates below, without
# needing "uv run" in front of every command
ENV PATH="/app/.venv/bin:$PATH"

# copy just the dependency files first so this layer (the slow one) is
# cached and only reruns when dependencies actually change, not on every
# code edit
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --locked

# now copy the rest of the project (app.py, dashboard.py, rag_helper.py, etc.)
COPY . .

# default command: run the user-facing app on port 8501.
# --server.address=0.0.0.0 is required so Streamlit accepts connections
# from outside the container, not just from localhost inside it.
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
