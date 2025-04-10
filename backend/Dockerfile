FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && \
    apt-get install -y curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="/root/.local/bin:${PATH}"
COPY pyproject.toml poetry.lock ./
RUN poetry install --no-root
COPY . .
ENTRYPOINT ["poetry", "run"]

# CMD ["uvicorn", "src.app:app"] TODO: investigate why it doesn't work
CMD ["python", "-m", "src.app"]
