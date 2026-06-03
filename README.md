# careerfit-ai

> Local AI resume tailoring app for the `careerfit-ai` repository.

careerfit-ai accepts a resume and a target job description, analyzes their semantic fit, and generates a tailored DOCX/PDF resume with a diff view and gap report. The current implementation is designed for local Docker Compose usage with Ollama, sentence-transformers, FastAPI, and React/Vite.

## Features

- Semantic gap analysis with `sentence-transformers` and cosine similarity.
- Local LLM rewriting through Ollama, defaulting to `llama3.1:8b`.
- Resume input support for PDF and DOCX.
- Job description input support for PDF, DOCX, or pasted plain text.
- OCR fallback for scanned/image-based PDFs.
- DOCX output with style-aware paragraph replacement.
- PDF output through WeasyPrint with ReportLab fallback.
- Real-time progress updates over Server-Sent Events.
- Downloadable DOCX and PDF outputs.
- Side-by-side diff and gap report in the web UI.

## Privacy Model

The app is built around local processing. In the default Docker Compose setup, resume and job description content is sent to the local FastAPI service, saved under `/tmp/careerfit_ai/uploads`, processed by local Ollama and local embedding models, and written to `/tmp/careerfit_ai/outputs`.

No external LLM API is used by the current codebase. Docker images and Python/Node dependencies are still downloaded during setup/build, and uploaded/output files persist in the configured Docker volumes until the job is deleted or the periodic TTL cleanup removes expired in-memory jobs and their files.

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Optional, for GPU inference: NVIDIA Container Toolkit

### Clone and Configure

```bash
git clone https://github.com/Aklavya-Mishra/careerfit-ai.git
cd careerfit-ai
cp .env.example .env
```

### Pull the Ollama Model

```bash
# GPU or higher-memory local setup
docker compose -f docker-compose.yml -f docker-compose.gpu.yml run --rm ollama ollama pull llama3.1:8b

# CPU-only alternative
docker compose run --rm ollama ollama pull qwen2.5:3b
```

### Start the Stack

```bash
# GPU-enabled Ollama
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up --build

# CPU-only
docker compose up --build
```

Open the Docker-hosted app at:

```text
http://localhost:3000
```

The Vite development server, when run directly from `web/`, uses:

```text
http://localhost:5173
```

## CPU-Only Setup

For CPU-only machines, use a smaller Ollama model and keep embeddings on CPU:

```env
OLLAMA_MODEL=qwen2.5:3b
EMBEDDING_DEVICE=cpu
```

Expected runtime depends heavily on resume length and CPU speed. LLM rewriting can take several minutes per request on CPU.

## Architecture

See [ARCHITECTURE.md](./ARCHITECTURE.md) for system diagrams, data flow, API schema, and component details.

## Stack

| Layer | Technology |
| --- | --- |
| API | FastAPI, Uvicorn |
| Frontend | React, Vite, Nginx in Docker |
| LLM | Ollama |
| Default LLM model | `llama3.1:8b` |
| CPU fallback model | `qwen2.5:3b` |
| Embeddings | `sentence-transformers`, `all-MiniLM-L6-v2` |
| PDF parsing | `pdfplumber`, `pdf2image`, `pytesseract` |
| PDF generation | WeasyPrint, ReportLab fallback |
| DOCX parsing/generation | `python-docx` |
| Deployment | Docker Compose |

## API Reference

### `POST /api/v1/tailor`

Submit a resume and job description for tailoring.

Form fields:

- `resume`: required PDF or DOCX file.
- `jd_file`: optional PDF or DOCX job description file.
- `jd_text`: optional plain-text job description.

At least one of `jd_file` or `jd_text` is required.

Response:

```json
{ "job_id": "abc123", "status": "queued" }
```

### `GET /api/v1/jobs/{id}/stream`

Server-Sent Events stream for pipeline progress.

### `GET /api/v1/jobs/{id}/result`

Returns the final result when complete, including download URLs, diff, and gap report.

### `GET /api/v1/jobs/{id}/download/docx`

Downloads the tailored resume as DOCX.

### `GET /api/v1/jobs/{id}/download/pdf`

Downloads the tailored resume as PDF.

### `DELETE /api/v1/jobs/{id}`

Deletes the in-memory job record and associated uploaded/output files.

### `GET /api/v1/health`

Returns service health and Ollama connectivity status.

## Development Without Docker

### Backend

```bash
cd api
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

ollama serve
ollama pull llama3.1:8b

uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd web
npm install
npm run dev
```

Open:

```text
http://localhost:5173
```

## Configuration

All settings can be overridden with environment variables or `.env`.

| Variable | Default | Description |
| --- | --- | --- |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL outside Docker |
| `OLLAMA_MODEL` | `llama3.1:8b` | Ollama model used for rewriting |
| `OLLAMA_TIMEOUT` | `120` | Ollama request timeout in seconds |
| `OLLAMA_MAX_RETRIES` | `2` | Retry count for LLM rewriting |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence-transformer model |
| `EMBEDDING_DEVICE` | `cpu` | `cpu` or `cuda` |
| `UPLOAD_DIR` | `/tmp/careerfit_ai/uploads` | Uploaded file storage |
| `OUTPUT_DIR` | `/tmp/careerfit_ai/outputs` | Generated file storage |
| `MAX_FILE_SIZE_MB` | `20` | Configured maximum file size value |
| `JOB_TTL_SECONDS` | `3600` | Job expiration window |
| `WEAK_SECTION_THRESHOLD` | `0.55` | Score below which sections are rewritten |
| `STRONG_SECTION_THRESHOLD` | `0.78` | Score above which sections are considered strong |
| `CORS_ORIGINS` | `["http://localhost:5173","http://localhost:3000"]` | Allowed browser origins |
| `LOG_LEVEL` | `INFO` | Logging level |
| `LOG_FORMAT` | `json` | `json` or `console` |

## Tests

Backend:

```bash
cd api
pytest
```

Frontend:

```bash
cd web
npm test
```

## Project Structure

```text
careerfit-ai/
|-- api/
|   |-- core/
|   |-- generators/
|   |-- nlp/
|   |-- parsers/
|   |-- routes/
|   |-- tests/
|   |-- utils/
|   |-- Dockerfile
|   |-- main.py
|   |-- pytest.ini
|   `-- requirements.txt
|-- docs/
|   `-- prompts.md
|-- scripts/
|   `-- start.sh
|-- web/
|   |-- src/
|   |-- Dockerfile
|   |-- index.html
|   |-- nginx.conf
|   |-- package.json
|   `-- vite.config.js
|-- .env.example
|-- .gitignore
|-- ARCHITECTURE.md
|-- docker-compose.gpu.yml
|-- docker-compose.yml
`-- README.md
```

## License

MIT
