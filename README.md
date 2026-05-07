# CCMS-Sahayak ⚖️

> **From Court Judgments to Verified Action Plans — in minutes, not months.**

**🚀 Live Demo:** [`https://your-deployment-link-here.com`](https://your-deployment-link-here.com) ← _replace with deployed URL_

CCMS-Sahayak is an AI-powered decision-support layer built for Karnataka's Court Case Management System (CCMS). It converts raw Karnataka High Court judgment PDFs — digital or scanned — into structured, human-verified action plans that government departments can act on immediately.

> **AI extracts and drafts. Humans decide and verify. Only verified records reach the dashboard.**

---

## 📋 Table of Contents

- [Use Cases](#-use-cases)
- [System Architecture](#-system-architecture)
- [OCR Pipeline (Sarvam Document Intelligence)](#-ocr-pipeline-sarvam-document-intelligence)
- [Data Flow](#-data-flow)
- [Tech Stack](#-tech-stack)
- [Quick Start (Docker)](#-quick-start-docker)
- [Local Development](#-local-development)
- [Environment Variables](#-environment-variables)
- [API Reference](#-api-reference)
- [Test Suite](#-test-suite)
- [Project Structure](#-project-structure)
- [Screenshots](#-screenshots)

---

## 🎯 Use Cases

Karnataka government departments receive hundreds of High Court judgment PDFs every month. Tracking compliance deadlines, appeal windows, and contempt risks manually is error-prone and slow.

**CCMS-Sahayak solves this by:**

| Problem | Solution |
|---|---|
| Scanned PDFs are unreadable by computers | Sarvam Document Intelligence OCR pipeline extracts text from image-only pages |
| Extracting case numbers, dates, directives by hand | Dual extraction: rule-based regex + Gemini Flash 2.0 LLM, conflict-detected |
| Missing appeal deadlines | Automated urgency scoring: 🔴 RED (≤7 days), 🟡 AMBER (≤30 days), 🟢 GREEN |
| No audit trail for government decisions | Every field decision (approve/edit/reject) is logged with timestamp |
| English-only summaries hard to share | One-click Sarvam translation to Kannada (ಕನ್ನಡ) |
| Raw AI output without human check | Mandatory human review gate — unverified records never reach dashboard |

---

## 🏗️ System Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                          CCMS-Sahayak                                  │
│                                                                        │
│   ┌──────────────────────────────────────────────────────────────┐    │
│   │                    React Frontend (Vite)                      │    │
│   │                                                               │    │
│   │   ┌─────────────┐  ┌──────────────────┐  ┌───────────────┐  │    │
│   │   │ Upload Page │  │   Review Page    │  │ Dashboard Page│  │    │
│   │   │  (drag-drop │  │ (field-by-field  │  │ (verified     │  │    │
│   │   │   PDF zone) │  │  APPROVE/EDIT/   │  │  records +    │  │    │
│   │   │             │  │  REJECT + PDF    │  │  urgency +    │  │    │
│   │   │             │  │  side-by-side)   │  │  EN/KN + CSV) │  │    │
│   │   └──────┬──────┘  └────────┬─────────┘  └───────┬───────┘  │    │
│   └──────────┼──────────────────┼────────────────────┼───────────┘    │
│              │   REST API       │                    │                 │
│   ┌──────────▼──────────────────▼────────────────────▼───────────┐    │
│   │                   FastAPI Backend                             │    │
│   │                                                               │    │
│   │  POST /upload  GET /:id/review  PATCH /:id/fields/:fid       │    │
│   │  POST /:id/verify    GET /dashboard   GET /stats             │    │
│   │                                                               │    │
│   │  ┌─────────────┐  ┌────────────────┐  ┌──────────────────┐  │    │
│   │  │ PDF Parser  │  │  Rule Extractor│  │  LLM Extractor   │  │    │
│   │  │ (PyMuPDF)   │  │  (Regex rules  │  │  (Gemini Flash   │  │    │
│   │  │             │  │  case_number,  │  │   2.0 via        │  │    │
│   │  │ digital ──► │  │  date, court)  │  │   OpenRouter)    │  │    │
│   │  │ text pages  │  └───────┬────────┘  └────────┬─────────┘  │    │
│   │  │             │          │                     │            │    │
│   │  │ scanned ──► │          └──────────┬──────────┘            │    │
│   │  │ Sarvam OCR  │                     │                       │    │
│   │  └─────────────┘              Confidence Scorer              │    │
│   │                          HIGH(0.9) / MEDIUM(0.7)             │    │
│   │                          LOW/CONFLICT(0.35) / UNREADABLE(0)  │    │
│   │                                     │                        │    │
│   │                          ┌──────────▼──────────┐            │    │
│   │                          │   Action Planner     │            │    │
│   │                          │  (Gemini Flash 2.0)  │            │    │
│   │                          │  COMPLIANCE / APPEAL  │           │    │
│   │                          │  CONTEMPT / COST      │           │    │
│   │                          └──────────────────────┘            │    │
│   │                                                               │    │
│   │  ┌──────────────────────────────────────────────────────┐    │    │
│   │  │                   SQLite Database                     │    │    │
│   │  │  judgments → extractions → verifications             │    │    │
│   │  │  action_plans → verified_records                     │    │    │
│   │  └──────────────────────────────────────────────────────┘    │    │
│   └───────────────────────────────────────────────────────────────┘    │
│                                                                        │
│   ┌────────────────────────────────────────────────────────────┐       │
│   │               External AI Services                         │       │
│   │                                                            │       │
│   │  ┌─────────────────────┐    ┌─────────────────────────┐   │       │
│   │  │  Sarvam AI           │    │  OpenRouter              │   │       │
│   │  │  • Document Intel.  │    │  • Gemini Flash 2.0      │   │       │
│   │  │    (OCR pipeline)   │    │    (extraction + plan)   │   │       │
│   │  │  • Translate API    │    │                          │   │       │
│   │  │    (EN → ಕನ್ನಡ)      │    │                          │   │       │
│   │  └─────────────────────┘    └─────────────────────────┘   │       │
│   └────────────────────────────────────────────────────────────┘       │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 🔍 OCR Pipeline (Sarvam Document Intelligence)

Scanned judgment PDFs go through a **5-step asynchronous job pipeline** on Sarvam's Document Intelligence API:

```
PDF (scanned)
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 1 ─ Create Job                                            │
│  POST /doc-digitization/job/v1                                  │
│  → returns job_id (UUID)                                        │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 2 ─ Get Upload URL                                        │
│  POST /doc-digitization/job/v1/{job_id}/upload-files            │
│  → returns pre-signed Azure Blob Storage URL                    │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 3 ─ Upload PDF                                            │
│  PUT {presigned_url}  (Content-Type: application/pdf)           │
│  → PDF bytes sent directly to Azure Blob                        │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 4 ─ Start Job                                             │
│  POST /doc-digitization/job/v1/{job_id}/start                   │
│  → validates file (≤10 pages, ≤200 MB) and begins OCR          │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 5 ─ Poll Status  (every 5s, max 300s)                     │
│  GET /doc-digitization/job/v1/{job_id}/status                   │
│  → waits for: Completed | PartiallyCompleted                    │
│  → raises on: Failed | timeout                                  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 6 ─ Download Result                                       │
│  POST /doc-digitization/job/v1/{job_id}/download-files          │
│  GET  {presigned_download_url}                                  │
│  → returns Markdown text (or ZIP of .md files)                  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
                   Markdown text → extraction pipeline

  ⚠️  Sarvam limit: 10 pages per job
      PDFs > 10 pages are automatically split into 10-page chunks
      and results are concatenated.
```

---

## 🔄 Data Flow

```
User uploads PDF
       │
       ▼
  PyMuPDF reads pages
       │
       ├── page has text? ──YES──► collect text (digital path)
       │
       └── page is blank? ──YES──► flag as scanned → Sarvam OCR
                                         │
                                   Markdown text returned
                                         │
                                   ◄─────┘
       │
       ▼
  Full text assembled
       │
       ├──► Rule Extractor  ──────► case_number, date_of_order, court_name
       │      (regex, fast)
       │
       ├──► Gemini Flash 2.0 ────► all fields (JSON schema)
       │      (via OpenRouter)       directives, parties, limitation_period…
       │
       ▼
  Confidence Scorer compares rule vs LLM per field:
    BOTH + match  → HIGH   (0.9)
    LLM only      → MEDIUM (0.7)
    BOTH + differ → CONFLICT (0.35) ← flagged for human review
    Neither       → UNREADABLE (0.0)
       │
       ▼
  Action Planner (Gemini Flash 2.0)
    → generates directive-tagged action items:
      COMPLIANCE / APPEAL / CONTEMPT / COST / OTHER
    → assigns deadline_date, responsible_authority, priority_level
       │
       ▼
  Urgency Band:
    CONTEMPT directive                → 🔴 RED
    Deadline ≤ 7 days                 → 🔴 RED
    Deadline ≤ 30 days or APPEAL      → 🟡 AMBER
    Otherwise                         → 🟢 GREEN
       │
       ▼
  Saved to DB (judgment + extractions + action_plans)
       │
       ▼
  Human Reviewer (Review Page)
    → sees PDF side-by-side with each field
    → APPROVE / EDIT (corrected value) / REJECT (with reason)
    → keyboard shortcuts: A approve · E edit · R reject · Tab next
    → bulk-approve all HIGH-confidence fields in one click
       │
       ▼
  Submit (all fields must be reviewed — enforced by backend)
    → Sarvam translates action summary EN → ಕನ್ನಡ
    → VerifiedRecord created with audit trail
       │
       ▼
  Dashboard (verified records only)
    → urgency bands + appeal countdown
    → bilingual EN/KN toggle
    → department / action-type / urgency filters
    → CSV export
    → audit trail drawer per case
```

---

## 🛠️ Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Frontend** | React 18 + TypeScript | UI framework |
| | Vite 6 | Dev server & bundler |
| | Tailwind CSS | Utility-first styling (beige/saffron theme) |
| | TanStack Query | Server-state fetching & caching |
| | Zustand | Lightweight client state (active job ID) |
| | react-pdf / PDF.js | In-browser PDF rendering & field highlighting |
| **Backend** | FastAPI (Python 3.11) | REST API, async request handling |
| | SQLAlchemy 2.0 | ORM + SQLite persistence |
| | Pydantic v2 | Schema validation, settings management |
| | PyMuPDF (fitz) | PDF text extraction, page rendering, coordinate mapping |
| | httpx | Async HTTP client for external APIs |
| **AI — OCR** | Sarvam Document Intelligence | Async OCR job pipeline for scanned PDFs |
| **AI — LLM** | Google Gemini Flash 2.0 | Field extraction + action plan generation |
| | OpenRouter | LLM gateway / API routing |
| **AI — Translate** | Sarvam Translate API | EN → ಕನ್ನಡ action summaries |
| **Infra** | Docker + Docker Compose | One-command deployment |
| | SQLite | Zero-config database |
| **Testing** | pytest + pytest-asyncio | 60-test offline suite |
| | unittest.mock | Full HTTP mocking (no API key required) |

---

## 🚀 Quick Start (Docker)

**Prerequisites:** Docker Desktop installed and running.

```bash
# 1. Clone the repository
git clone https://github.com/your-org/ccms-sahayak.git
cd ccms-sahayak

# 2. Set your API keys
cp .env.example .env
# Edit .env — set SARVAM_API_KEY and OPENROUTER_API_KEY

# 3. Launch everything
docker compose up --build
```

| Service | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| Swagger Docs | http://localhost:8000/docs |
| Health Check | http://localhost:8000/health |

---

## 💻 Local Development

### Prerequisites

- Python 3.11+
- Node.js 18+
- Valid Sarvam AI and OpenRouter API keys

### Backend

```bash
# From project root
python -m venv .venv

# Windows
.\.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt

cd backend
uvicorn app.main:app --reload --port 8001
```

Backend is live at http://localhost:8001  
Swagger UI at http://localhost:8001/docs

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend is live at http://localhost:3000 (proxies API calls to port 8001)

---

## ⚙️ Environment Variables

Copy `.env.example` to `.env` and fill in the required values:

```env
# ── Required ──────────────────────────────────────────
SARVAM_API_KEY=your_sarvam_api_key_here
OPENROUTER_API_KEY=your_openrouter_api_key_here

# ── Optional (these are the defaults) ─────────────────
GEMINI_MODEL=google/gemini-2.0-flash-001
OCR_CONFIDENCE_THRESHOLD=0.55
DATABASE_URL=sqlite:///./ccms_sahayak.db
PDF_STORAGE_PATH=./storage/pdfs
```

| Variable | Required | Description |
|---|---|---|
| `SARVAM_API_KEY` | ✅ Yes | Sarvam AI key — used for OCR and translation |
| `OPENROUTER_API_KEY` | ✅ Yes | OpenRouter key — used to call Gemini Flash 2.0 |
| `GEMINI_MODEL` | No | LLM model identifier (default: Gemini Flash 2.0) |
| `OCR_CONFIDENCE_THRESHOLD` | No | Below this average confidence the job is FLAGGED (default: 0.55) |
| `DATABASE_URL` | No | SQLAlchemy connection string (default: local SQLite) |
| `PDF_STORAGE_PATH` | No | Directory where uploaded PDFs are saved |

> **Security:** `.env` is in `.gitignore`. Never commit API keys to version control.

---

## 📡 API Reference

All endpoints are prefixed with `/api/v1`.

### Judgments

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/judgments/upload` | Upload PDF, extract fields, generate action plan |
| `GET` | `/judgments/{id}/review` | Get all extracted fields + action plan for review |
| `PATCH` | `/judgments/{id}/fields/{field_id}` | Approve / edit / reject a single field |
| `POST` | `/judgments/{id}/verify` | Final submission — all fields must be reviewed |

### Dashboard

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/dashboard` | List verified records (filterable by dept / urgency / action type) |
| `GET` | `/dashboard/stats` | Aggregate counts (total, RED, AMBER, pending appeals) |
| `GET` | `/dashboard/export.csv` | Download filtered records as CSV |

### Upload Response Schema

```json
{
  "job_id": 42,
  "extraction_status": "EXTRACTED",
  "overall_confidence": 0.82,
  "ocr_used": false
}
```

`extraction_status` is `EXTRACTED` (confidence ≥ threshold) or `FLAGGED` (needs extra attention).

---

## 🧪 Test Suite

The project has **60 offline unit tests** (no API keys needed) plus a live integration suite.

### Run all offline tests

```bash
cd ccms-sahayak
python -m pytest backend/tests/ -v --ignore=backend/tests/test_live_integrations.py
```

Expected output: `60 passed`

### Test coverage by file

| Test file | What it covers |
|---|---|
| `test_sarvam_ocr_pipeline.py` | All 5 steps of the Document Intelligence pipeline (HTTP mocked) |
| `test_document_pipeline.py` | PDF parsing, rule extraction, confidence scoring, OCR path, action planner, upload endpoint |
| `test_confidence.py` | Score matrix, urgency bands, deadline calculation |
| `test_pdf_parser.py` | Digital text detection, scanned-page detection, base64 rendering |
| `test_rule_extractor.py` | Regex patterns for case numbers, dates, court names |
| `test_verification_gate.py` | All-fields-reviewed gate, dashboard only shows verified records |
| `test_live_integrations.py` | Real API calls (requires `RUN_LIVE_API_TESTS=1` and valid keys) |

### Run live API tests

```bash
# Windows PowerShell
$env:RUN_LIVE_API_TESTS="1"
python -m pytest backend/tests/test_live_integrations.py -v

# macOS / Linux
RUN_LIVE_API_TESTS=1 python -m pytest backend/tests/test_live_integrations.py -v
```

Live tests verify:
- Sarvam Translate returns non-empty Kannada text
- Sarvam Document Intelligence job is created and accepted
- Full OCR pipeline runs on a synthetic PDF
- Gemini Flash returns valid JSON
- End-to-end extraction on a text-based judgment PDF

### Linting

```bash
python -m ruff check backend/app backend/tests
```

---

## 📁 Project Structure

```
ccms-sahayak/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── judgments.py      # Upload, review, verify endpoints
│   │   │   └── dashboard.py      # Dashboard + stats + CSV export
│   │   ├── core/
│   │   │   ├── config.py         # Pydantic settings (reads .env)
│   │   │   └── database.py       # SQLAlchemy engine + session
│   │   ├── models/
│   │   │   └── entities.py       # ORM models: Judgment, Extraction, etc.
│   │   ├── schemas/
│   │   │   └── dto.py            # Pydantic request/response schemas
│   │   ├── services/
│   │   │   ├── sarvam_client.py  # Document Intelligence + Translate
│   │   │   ├── extractor.py      # Orchestrates PDF parse + rule + LLM
│   │   │   ├── pdf_parser.py     # PyMuPDF wrapper, scanned-page detection
│   │   │   ├── rule_extractor.py # Regex extraction (fast, no API)
│   │   │   ├── llm_client.py     # Gemini Flash via OpenRouter
│   │   │   ├── action_planner.py # LLM-generated action plan
│   │   │   └── confidence.py     # Score, urgency, deadline helpers
│   │   └── main.py               # FastAPI app, CORS, routers, startup
│   ├── prompts/
│   │   ├── extraction_system.txt # System prompt for field extraction
│   │   └── action_plan_system.txt# System prompt for action planning
│   └── tests/
│       ├── test_sarvam_ocr_pipeline.py
│       ├── test_document_pipeline.py
│       ├── test_confidence.py
│       ├── test_pdf_parser.py
│       ├── test_rule_extractor.py
│       ├── test_verification_gate.py
│       └── test_live_integrations.py
│
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── UploadPage.tsx    # Drag-drop PDF upload with file preview
│   │   │   ├── ReviewPage.tsx    # Field-by-field review + PDF viewer
│   │   │   └── DashboardPage.tsx # Verified records, urgency, EN/KN, CSV
│   │   ├── components/
│   │   │   ├── FieldCard.tsx     # Per-field APPROVE / EDIT / REJECT card
│   │   │   ├── PDFViewer.tsx     # PDF.js renderer with field highlight
│   │   │   └── ConfidenceBadge.tsx # HIGH / MEDIUM / LOW / CONFLICT badge
│   │   ├── api/client.ts         # Typed fetch wrappers (TanStack Query)
│   │   ├── store/reviewer.ts     # Zustand store (jobId, activeFieldId)
│   │   ├── types.ts              # TypeScript interfaces matching backend DTOs
│   │   ├── styles.css            # Tailwind base + beige/saffron theme
│   │   └── App.tsx               # Router + dark-brown header + nav tabs
│   ├── tailwind.config.js        # Beige + saffron colour tokens
│   └── vite.config.ts            # Proxy /api → backend
│
├── docker-compose.yml            # One-command full stack launch
├── requirements.txt              # Python dependencies
├── pytest.ini                    # Test paths, asyncio mode, markers
└── .env.example                  # Environment variable template
```

---

## 🖼️ Screenshots

> Upload a judgment — see the file name and size confirmed before submitting

The drop-zone switches from "choose a file" to a paperclip confirmation view with filename and size once a PDF is selected. The **Upload and Extract** button is disabled until a file is chosen.

> Review page — field cards + PDF side by side

Every extracted field shows its confidence badge (HIGH / MEDIUM / CONFLICT), extraction source (RULE / LLM / BOTH), and decision status. A saffron progress bar tracks how many fields have been reviewed. Keyboard shortcuts (A / E / R / Tab) allow rapid keyboard-only review.

> Dashboard — urgency at a glance

Verified records show colour-coded urgency badges, appeal countdowns, and bilingual EN/ಕನ್ನಡ summaries. One-click CSV export for any filtered view.

---

## 🔐 Security Notes

- API keys are loaded exclusively from `.env` (never hardcoded)
- `.env` is in `.gitignore`
- PDF files are stored server-side; never base64'd into responses
- All LLM prompts are server-side; the client never sees raw prompt text
- Verification gate enforced at backend level — frontend cannot bypass it

---

## 🏛️ Hackathon Compliance

This project was built for the **AI4Bharat Hackathon** targeting Karnataka CCMS integration.

- ✅ Working prototype on real Karnataka High Court judgment PDFs
- ✅ Sarvam AI used for OCR (Document Intelligence) and translation (EN → ಕನ್ನಡ)
- ✅ Human-in-the-loop review with audit trail
- ✅ Dashboard with verified action plans, urgency bands, bilingual summaries
- ✅ Complete repository with Docker Compose and setup documentation
- ✅ 60-test offline test suite (no API keys required to run)
- ✅ Live API integration tests for end-to-end pipeline verification
- ✅ No hardcoded credentials — `.env` driven configuration

---

## 📄 License

MIT — see [LICENSE](LICENSE) for details.
