# AGENTS.md

Guidelines for coding agents working in this repository.

## Project Scope

This project provides:
- FastAPI backend for sources, sessions, providers, and chat streaming
- Prefect flow for asynchronous source indexing/summarization
- Qdrant for vector retrieval
- Streamlit UI for manual workflows

## Architecture Notes

- API entrypoint: `main.py`
- Routers: `api/routers/*.py`
- Business logic: `usecases/*.py`
- Data layer: `db/models` and `db/repositories`
- Source processing flow: `flows/process_source.py`
- UI: `ui/*`

When implementing changes, preserve this layering:
- router: HTTP boundary only
- usecase: business behavior
- repository: DB persistence

## Local Commands

- Install: `make install`
- Format: `make format`
- Lint/type-check: `make check`
- Tests: `make test`
- Full stack up: `make build`
- Full stack down: `make stop`

## API and Behavior Constraints

- Chat endpoint `/chat/stream` accepts `provider_id`, `model_name`, and tool configuration in request body.
- Providers are managed in DB (`/provider` endpoints), not `.env` keys.
- Source upload supports `.pdf`, `.txt`, `.md`, `.docx`, `.rtf`, `.odt`, `.epub`, `.html`, `.htm`, `.pptx`, `.xlsx`, and `.eml`.
- Source processing is async and status-driven (`created -> processed -> completed` or `failed`).

## Editing Rules for Agents

- Keep changes minimal and scoped to the request.
- Do not refactor unrelated modules in the same patch.
- Prefer the simplest implementation that satisfies the requirement.
- Avoid unnecessary abstractions, overengineering, and premature optimization.
- Keep code clean and readable: clear naming, small focused functions, and consistent style.
- Add concise docstrings for new or changed public modules, classes, and functions.
- Avoid breaking public endpoint contracts unless explicitly requested.
- If contract changes are required, update:
  - request/response schemas
  - router behavior
  - README examples
  - tests

## Validation Checklist

Before finishing, run (or explain why not run):

```bash
make format
make check
make test
```

If tests are skipped, clearly state the reason and likely impact.

## Documentation Expectations

When behavior changes, update docs in the same task:
- `README.md` for user-facing usage
- this `AGENTS.md` if agent workflow/constraints changed
