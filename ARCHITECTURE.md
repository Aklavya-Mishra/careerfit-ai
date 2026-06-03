# careerfit-ai — Architecture Documentation

## Overview

careerfit-ai is a locally-hosted, LLM-powered resume tailoring engine. Given a resume (PDF/DOCX) and a job description (PDF/DOCX or plain text), it semantically analyzes both documents, identifies gaps and alignment opportunities, and produces a professionally tailored resume that matches the target role — while preserving the original document's formatting, layout, fonts, colors, and visual identity.

The system runs with local Ollama by default, with no external LLM API dependency in the current codebase. It uses sentence-transformer embeddings for semantic gap scoring, an instruction-tuned local LLM for content rewriting, and WeasyPrint/python-docx for document generation.

---

## System Architecture

```mermaid
graph TB
    subgraph Client ["React SPA (Docker localhost:3000, Vite dev localhost:5173)"]
        UI[Upload UI]
        PROG[SSE Progress Stream]
        DIFF[Side-by-side Diff View]
        DL[Download DOCX + PDF]
    end

    subgraph API ["FastAPI Backend (port 8000)"]
        direction TB
        INGEST["/api/v1/tailor — POST"]
        STREAM["/api/v1/jobs/{id}/stream — SSE"]
        RESULT["/api/v1/jobs/{id}/result — GET"]
        JOB[Job Manager]

        subgraph Pipeline ["Tailoring Pipeline"]
            P1[1. Document Parser]
            P2[2. Semantic Analyzer]
            P3[3. Gap Scorer]
            P4[4. LLM Rewriter]
            P5[5. Document Generator]
        end
    end

    subgraph Models ["Local Model Layer"]
        OLLAMA[Ollama — llama3.1:8b]
        SBERT[sentence-transformers — all-MiniLM-L6-v2]
    end

    subgraph Storage ["File Storage"]
        UPLOADS[/tmp/careerfit_ai/uploads]
        OUTPUTS[/tmp/careerfit_ai/outputs]
    end

    UI -->|multipart/form-data| INGEST
    INGEST --> JOB
    JOB --> P1
    P1 --> P2
    P2 --> P3
    P3 --> P4
    P4 --> P5
    P5 --> OUTPUTS

    PROG -->|EventSource| STREAM
    STREAM --> JOB
    RESULT --> OUTPUTS

    P2 --> SBERT
    P4 --> OLLAMA

    P1 --> UPLOADS
```

---

## Component Architecture

```mermaid
graph LR
    subgraph parsers ["parsers/"]
        DP[docx_parser.py]
        PP[pdf_parser.py]
        TP[text_parser.py]
        OCR[ocr_fallback.py]
    end

    subgraph nlp ["nlp/"]
        EMB[embedder.py]
        GAP[gap_analyzer.py]
        EXT[jd_extractor.py]
    end

    subgraph generators ["generators/"]
        LLM[llm_rewriter.py]
        DG[docx_generator.py]
        PG[pdf_generator.py]
    end

    subgraph core ["core/"]
        CFG[config.py]
        JM[job_manager.py]
        MOD[models.py]
        PIPE[pipeline.py]
    end

    subgraph routes ["routes/"]
        TR[tailor.py]
        JR[jobs.py]
        HR[health.py]
    end

    PP --> OCR
    DP --> DG
    PP --> PG

    EMB --> GAP
    EXT --> GAP
    GAP --> LLM

    PIPE --> parsers
    PIPE --> nlp
    PIPE --> generators

    routes --> PIPE
    routes --> JM
    core --> CFG
```

---

## Data Flow — Full Pipeline

```mermaid
sequenceDiagram
    participant U as User (Browser)
    participant API as FastAPI
    participant JM as Job Manager
    participant PARSE as Parser
    participant NLP as NLP Engine
    participant LLM as Ollama LLM
    participant GEN as Doc Generator

    U->>API: POST /api/v1/tailor (resume + JD)
    API->>JM: create_job(id, files)
    API-->>U: { job_id: "abc123" }

    U->>API: GET /api/v1/jobs/abc123/stream (SSE)
    API-->>U: event: queued

    JM->>PARSE: parse_resume(file)
    PARSE-->>JM: ResumeDocument (sections, text, metadata)
    API-->>U: event: parsed_resume

    JM->>PARSE: parse_jd(file_or_text)
    PARSE-->>JM: JDDocument (requirements, skills, responsibilities)
    API-->>U: event: parsed_jd

    JM->>NLP: extract_jd_entities(jd)
    NLP-->>JM: { skills[], responsibilities[], keywords[] }

    JM->>NLP: embed_and_score(resume, jd)
    NLP-->>JM: GapReport { section_scores, missing_skills, weak_sections }
    API-->>U: event: gap_analysis_complete

    loop For each resume section
        JM->>LLM: rewrite_section(section, gap_context, jd_context)
        LLM-->>JM: rewritten_section
        API-->>U: event: section_rewritten (section_name)
    end

    JM->>GEN: generate_docx(tailored_resume, original_style)
    GEN-->>JM: tailored.docx

    JM->>GEN: generate_pdf(tailored_resume, layout_metadata)
    GEN-->>JM: tailored.pdf
    API-->>U: event: complete { docx_url, pdf_url, diff }

    U->>API: GET /api/v1/jobs/abc123/result
    API-->>U: { docx_url, pdf_url, diff, gap_report }
```

---

## Document Parsing Strategy

```mermaid
flowchart TD
    INPUT[Input File] --> TYPE{File Type?}

    TYPE -->|.docx| DOCX_PARSE[python-docx Parser]
    TYPE -->|.pdf| PDF_CHECK{Is PDF text-based?}
    TYPE -->|text| TEXT_PARSE[Plain Text Parser]

    PDF_CHECK -->|Yes| PDF_PARSE[pdfplumber Extraction]
    PDF_CHECK -->|No / Scanned| OCR[Tesseract OCR Fallback]

    DOCX_PARSE --> DOCX_META[Extract: paragraphs, runs, styles,\nfonts, colors, tables, spacing]
    PDF_PARSE --> PDF_META[Extract: text blocks, fonts,\nbbox coords, page layout]
    OCR --> PDF_META
    TEXT_PARSE --> BASIC[Basic section detection]

    DOCX_META --> STRUCT[Structured Resume Model]
    PDF_META --> STRUCT
    BASIC --> STRUCT

    STRUCT --> SECTIONS[Detected Sections:\nContact / Summary / Experience /\nEducation / Skills / Certifications]
```

---

## LLM Rewriting Strategy

```mermaid
flowchart LR
    subgraph INPUT ["Rewrite Inputs"]
        SEC[Original Section Text]
        GAP[Gap Score + Missing Skills]
        JDC[JD Requirements Context]
        INST[System Prompt + Rules]
    end

    subgraph PROMPT ["Prompt Construction"]
        SYS[System: professional resume writer,\nno keyword stuffing, preserve voice]
        CTX[Context: gap score, required skills,\nweak phrases identified]
        TASK[Task: rewrite this section to\nbetter match the JD]
    end

    subgraph OUTPUT ["Output Processing & Validation"]
        RAW[LLM Raw Output]
        CLEAN[_clean_markdown:\nstrip **, ##, *, url links,\nmeta-notes]
        VAL{Passes validation?\nlength, format, no hallucinations}
        RETRY[Retry with stricter prompt]
        FINAL[Final Rewritten Section]
    end

    INPUT --> PROMPT
    PROMPT --> OLLAMA[Ollama llama3.1:8b]
    OLLAMA --> RAW
    RAW --> CLEAN
    CLEAN --> VAL
    VAL -->|No| RETRY
    RETRY --> OLLAMA
    VAL -->|Yes| FINAL
```

---

## PDF Regeneration Strategy

```mermaid
flowchart TD
    ORIG[Original PDF] --> EXTRACT[pdfplumber: extract text + layout]
    EXTRACT --> META[Layout Metadata:\nfonts, sizes, colors, margins,\ncolumn structure, bbox coords]
    EXTRACT --> CONTENT[Section Content]

    CONTENT --> LLM_RW[LLM Rewritten Content]

    META --> TEMPLATE[HTML Template Engine]
    LLM_RW --> TEMPLATE

    TEMPLATE --> HTML[Styled HTML with\noriginal typography preserved]
    HTML --> WEASY[WeasyPrint PDF Renderer]
    WEASY --> WCHECK{WeasyPrint\nsucceeds?}
    WCHECK -->|Yes| PDF_OUT[tailored_resume.pdf]
    WCHECK -->|No — runtime error| FALLBACK[ReportLab fallback\nclean structured PDF]
    FALLBACK --> PDF_OUT
```

---

## DOCX Modification Strategy

```mermaid
flowchart TD
    ORIG[Original DOCX] --> COPY[shutil.copy2 → output DOCX]
    COPY --> SCAN[Scan all paragraphs]

    SCAN --> TYPE{Para type?}

    TYPE -->|Section heading\nHeading style or bold < 60 chars| SKIP1[Skip — section boundary marker]
    TYPE -->|Structural para\nJob title / company / date / location\nShort line ≤ 80 chars, no list style| SKIP2[Skip — preserve as-is]
    TYPE -->|Content para\nList/bullet style\nStarts with bullet char •\nLong descriptive line > 80 chars| REPLACE[Replace text via _set_para_text]

    REPLACE --> FORMAT[Preserve: font, size, color,\nbold/italic from first run]
    FORMAT --> NEWTEXT[Insert clean LLM line\nmarkdown already stripped]

    SKIP1 --> SAVE
    SKIP2 --> SAVE
    NEWTEXT --> SAVE[doc.save → tailored.docx]
```

**Key design decisions:**
- Only `_is_content_para()` paragraphs are ever touched — job titles, company names, dates, and locations survive unchanged regardless of resume format
- `_set_para_text()` clears all runs except the first, then sets the first run's text — character formatting (font family, size, colour) is preserved; inline bold within a bullet is intentionally collapsed (acceptable tradeoff for structural fidelity)
- Summary sections with a single content slot join all LLM output lines into one paragraph instead of mapping line-by-line
- If the LLM produces fewer lines than original bullets, excess slots are cleared; if more, extra lines are silently dropped to avoid inserting paragraphs with wrong styles

---

## Semantic Gap Analysis

```mermaid
flowchart LR
    RES[Resume Text\nby section] --> SBERT1[sentence-transformers\nall-MiniLM-L6-v2]
    JD[Job Description\nfull text] --> SBERT2[sentence-transformers\nall-MiniLM-L6-v2]

    SBERT1 --> RE[Resume Embeddings\nvector per section]
    SBERT2 --> JE[JD Embeddings\nvector per requirement]

    RE --> COS[Cosine Similarity\nMatrix]
    JE --> COS

    COS --> SCORE[Section Alignment Scores\n0.0 — 1.0]
    SCORE --> GAP[Gap Report:\n- Missing skills\n- Weak sections score < 0.6\n- Strong sections score > 0.8\n- Recommended additions]

    GAP --> PROMPT[LLM Rewrite Prompt\nwith structured gap context]
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/tailor` | Submit resume + JD, returns `job_id` |
| `GET` | `/api/v1/jobs/{id}/stream` | SSE stream of pipeline progress events |
| `GET` | `/api/v1/jobs/{id}/result` | Final result with download URLs + diff |
| `DELETE` | `/api/v1/jobs/{id}` | Cleanup job files |
| `GET` | `/api/v1/health` | Health check + Ollama connectivity status |

---

## SSE Event Schema

```json
{ "event": "queued",              "data": { "job_id": "abc123", "position": 1 } }
{ "event": "parsing_resume",      "data": { "progress": 10 } }
{ "event": "parsing_jd",          "data": { "progress": 20 } }
{ "event": "analyzing_gaps",      "data": { "progress": 35 } }
{ "event": "rewriting_summary",   "data": { "progress": 45, "section": "summary" } }
{ "event": "rewriting_experience","data": { "progress": 60, "section": "experience" } }
{ "event": "rewriting_skills",    "data": { "progress": 75, "section": "skills" } }
{ "event": "generating_docx",     "data": { "progress": 85 } }
{ "event": "generating_pdf",      "data": { "progress": 95 } }
{ "event": "complete",            "data": { "progress": 100, "docx_url": "...", "pdf_url": "...", "gap_report": {} } }
{ "event": "error",               "data": { "message": "..." } }
```

---

## Docker Compose Services

```mermaid
graph TB
    subgraph DC ["docker-compose.yml"]
        WEB["web (Nginx-served React build)\nlocalhost:3000\nbuild: ./web"]
        API["api (FastAPI/uvicorn)\nport 8000\nbuild: ./api"]
        OLL["ollama\nport 11434\nimage: ollama/ollama\nvolume: ollama_data"]
    end

    WEB -->|/api proxy via nginx| API
    API -->|OLLAMA_BASE_URL=http://ollama:11434| OLL
    OLL -->|GPU pass-through\nnvidia runtime| GPU[RTX 5070 Ti]
```

---

## Project File Structure

```text
careerfit-ai/
|-- api/
|   |-- main.py                    # FastAPI app entrypoint
|   |-- requirements.txt
|   |-- Dockerfile
|   |-- core/
|   |   |-- config.py              # Settings via pydantic-settings
|   |   |-- models.py              # Pydantic data models
|   |   |-- pipeline.py            # Orchestrates the tailoring pipeline
|   |   `-- job_manager.py         # In-memory job state + SSE queue
|   |-- parsers/
|   |   |-- docx_parser.py         # python-docx resume parser
|   |   |-- pdf_parser.py          # pdfplumber layout-aware parser
|   |   |-- text_parser.py         # Plain text / JD text parser
|   |   `-- ocr_fallback.py        # Tesseract OCR for scanned PDFs
|   |-- nlp/
|   |   |-- embedder.py            # sentence-transformers wrapper
|   |   |-- gap_analyzer.py        # Cosine similarity + gap scoring
|   |   `-- jd_extractor.py        # Extract skills/requirements from JD
|   |-- generators/
|   |   |-- llm_rewriter.py        # Ollama LLM prompt orchestration
|   |   |-- docx_generator.py      # python-docx output with style preservation
|   |   `-- pdf_generator.py       # WeasyPrint PDF generation
|   |-- routes/
|   |   |-- tailor.py              # POST /api/v1/tailor
|   |   |-- jobs.py                # stream, result, download, delete endpoints
|   |   `-- health.py              # Health check
|   `-- utils/
|       `-- logger.py              # Structured logging setup
|-- web/
|   |-- index.html
|   |-- package.json
|   |-- vite.config.js
|   |-- Dockerfile
|   |-- nginx.conf
|   `-- src/
|-- docker-compose.yml
|-- docker-compose.gpu.yml          # GPU override for Ollama
|-- .env.example
|-- README.md
|-- ARCHITECTURE.md
`-- docs/
    `-- prompts.md
```

---

## Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| LLM (GPU) | `ollama` + `llama3.1:8b` | Resume rewriting, semantic analysis |
| LLM (CPU) | `ollama` + `qwen2.5:3b` | Fallback for CPU-only machines |
| Embeddings | `sentence-transformers` `all-MiniLM-L6-v2` | Semantic gap scoring |
| PDF parsing | `pdfplumber` | Layout-aware text + metadata extraction |
| PDF generation | `WeasyPrint` + `ReportLab` fallback | HTML → PDF with structured fallback |
| DOCX parsing | `python-docx` | Structure + style extraction |
| DOCX generation | `python-docx` | Format-preserving output |
| OCR | `pytesseract` + `pdf2image` | Scanned PDF fallback |
| API framework | `FastAPI` + `uvicorn` | Async HTTP + SSE |
| Frontend | `React` + `Vite` | SPA with diff view |
| Containerization | `Docker Compose` | Single-command local deployment |
| Config | `pydantic-settings` | Type-safe environment configuration |
| Logging | `structlog` | Structured JSON logging |

---

## Non-Functional Characteristics

- **Privacy-first default**: resume/JD processing uses local services in the Docker Compose setup; no external LLM API is called by the current codebase
- **Ephemeral job state**: job state is held in-memory; uploaded and generated files are removed when a job is deleted or when periodic TTL cleanup expires the job
- **Modular pipeline**: each stage is independently testable and replaceable
- **Graceful degradation**: OCR fallback for scanned PDFs; CPU model if GPU unavailable
- **Extensible**: JD URL scraping, multi-language support, and ATS scoring can be added as pipeline stages without architectural changes
