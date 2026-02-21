[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/release/python-3120/)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![ty](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ty/main/assets/badge/v0.json)](https://github.com/astral-sh/ty)
[![CI/CD Pipeline](https://github.com/musashimiyomoto/rag-system/actions/workflows/ci.yml/badge.svg)](https://github.com/musashimiyomoto/rag-system/actions/workflows/ci.yml)


# RAG System

RAG system built with `FastAPI` + `PydanticAI` + `Qdrant`, with asynchronous source processing via `Prefect` and a `Streamlit` UI.

## Stack

- API: `FastAPI` (`main.py`)
- UI: `Streamlit` (`ui/app.py`)
- Database: `PostgreSQL`
- Vector store: `Qdrant`
- Cache/broker: `Redis`
- Pipeline orchestration: `Prefect`

## Requirements

- Python `3.11`
- Poetry
- Docker + Docker Compose

## Quick Start (Docker)

1. Create `.env`:

```bash
cp .env.example .env
```

2. Start all services:

```bash
make build
```

3. Open:

- API docs: `http://localhost:5000/docs`
- Streamlit UI: `http://localhost:8501`
- Prefect UI: `http://localhost:4200`

4. Stop services:

```bash
make stop
```

## Local Development

Install tooling and dependencies:

```bash
make install
```

Useful commands:

```bash
make help
make format
make check
make test
```

## Environment Variables

Base variables are defined in `.env.example`.

## Tools

Chat supports runtime tool selection through query params.

- `provider_id` and `model_name` are required.
- `tool_ids` is optional and repeatable.
- Default behavior (when `tool_ids` is omitted): tools marked
  `enabled_by_default` are enabled (currently `retrieve` and `web_search`).

Example request:

```bash
curl -X POST "http://localhost:5000/chat/stream?provider_id=1&model_name=gpt-4.1&tool_ids=retrieve&tool_ids=web_search" \
  -H "Content-Type: application/json" \
  -d '{"session_id":1,"message":"What changed in EU AI Act this month?"}'
```

Available tools can be fetched via:

```bash
curl "http://localhost:5000/tool/list"
```

You can also switch model and tool set on every request within the same session.
