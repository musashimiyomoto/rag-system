[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/release/python-3120/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336)](https://pycqa.github.io/isort/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Pyright](https://img.shields.io/badge/pyright-checked-informational.svg)](https://github.com/microsoft/pyright/)
[![CI/CD Pipeline](https://github.com/musashimiyomoto/rag-system/actions/workflows/ci.yml/badge.svg)](https://github.com/musashimiyomoto/rag-system/actions/workflows/ci.yml)

------------------------------------------------------------------------

# RAG System

## Requirements

- Python 3.11
- Poetry
- Docker and Docker Compose

## Quick Start with Makefile

This project includes a comprehensive Makefile that simplifies common development tasks. To see all available commands:

```bash
make help
```

### Docker Run

1. **Create .env file**:
```bash
cp .env.example .env
```

Add your API keys to the `.env` file. Open the file in a text editor and add the required variables in the format `KEY=value`. For example:
```bash
CORE_OPENAI_API_KEY=your_openai_api_key_here
CORE_GOOGLE_API_KEY=your_google_api_key_here
CORE_GITHUB_API_KEY=your_github_api_key_here
```

2. **Build and start the application**:
```bash
make build
```
This command will:
- Automatically copy `.env.example` to `.env` if it doesn't exist
- Build and start the application using Docker Compose

**Important**: After the `.env` file is created, you need to add your API keys for the chosen model provider. Edit the `.env` file and add the required API keys for your selected AI provider (OpenAI, Google, etc.).

3. **Stop the application**:
```bash
make stop
```

4. **Access the API documentation**:
   - Swagger UI: http://localhost:5000/docs
   - Prefect UI: http://localhost:4200
   - UI RAG Application: http://localhost:5000

## Development

### Setup

1. **Install all dependencies and setup pre-commit hooks**:
```bash
make install
```
This command will:
- Install all project dependencies including development and test dependencies
- Set up pre-commit hooks for code quality

### Available Makefile Commands

| Command | Description |
|---------|-------------|
| `make help` | Show all available commands with descriptions |
| `make install` | Install dependencies and setup pre-commit hooks |
| `make format` | Format code using black and isort |
| `make check` | Run code quality checks with ruff and pyright |
| `make test` | Run tests with coverage reporting |
| `make build` | Build and start the application with Docker Compose |
| `make stop` | Stop the Docker Compose services |

### Development Workflow

1. **Initial setup**:
```bash
make install
```

2. **Before committing code**:
```bash
make format    # Format your code
make check     # Run linting and type checks
make test      # Run tests
```

3. **Build and test the application**:
```bash
make build     # Start the application
# Test your changes
make stop      # Stop when done
```

## RAG System Features

The RAG (Retrieval-Augmented Generation) system provides intelligent document processing and chat capabilities:

1. **Document Upload**: Upload documents through the `/document` endpoint for processing and indexing
2. **Document Processing**: Documents are automatically processed, chunked, and stored in a vector database (ChromaDB)
3. **Streaming Responses**: Real-time streaming chat responses using FastAPI's StreamingResponse
4. **AI Integration**: Powered by PydanticAI with support for multiple AI providers (OpenAI, Google)
5. **Session Management**: Persistent chat sessions for better user experience
6. **Health Monitoring**: Built-in health checks for system monitoring

### API Endpoints

- **Health Check**:
  - `GET /health/liveness` - System liveness health status
  - `GET /health/readiness` - System readiness health status
- **Document Management**:
  - `POST /document` - Upload and process documents
  - `GET /document/list` - Get all documents
  - `GET /document/{document_id}` - Get a specific document
  - `GET /document/{document_id}/session/list` - Get all sessions for a specific document
  - `DELETE /document/{document_id}` - Delete a specific document
- **Chat Streaming**:
  - `POST /chat/stream` - Stream chat responses
- **Session Management**:
  - `POST /session` - Create chat sessions
  - `DELETE /session/{session_id}` - Delete a specific session
  - `GET /session/{session_id}/message/list` - Get all messages for a specific session
- **Web Interface**:
  - `GET /` - Main application interface
  - `GET /chat/{document_id}` - Chat interface for specific documents
