# Manufacturing SOP Copilot

A retrieval-augmented generation (RAG) application that helps manufacturing personnel find answers to operational questions from supplied Standard Operating Procedures (SOPs) and maintenance manuals.

The application retrieves relevant passages from PDF documents, generates an answer grounded in those passages, and displays the source document, revision, page number and supporting excerpt. If the supplied documents do not contain sufficient information, the application returns an explicit insufficient-information response instead of attempting to invent an answer.

## Features

- PDF text extraction using PyMuPDF.
- Text chunking with overlap to preserve context.
- Document metadata extraction, including document number, revision and effective date.
- Revision handling for explicitly superseded documents.
- Gemini embeddings for document and query vectorization.
- FAISS similarity search for local retrieval.
- Gemini Flash for evidence-grounded answer generation.
- Source references with document name, revision and page number.
- Supporting excerpts to help users verify answers.
- Explicit abstention when relevant evidence is unavailable.
- Retry handling for temporary Gemini API failures.
- Responsive web interface accessible from a laptop or phone on the same Wi-Fi network.

## Technology Stack

| Component | Technology |
|---|---|
| Backend | Python, FastAPI |
| Frontend | HTML, CSS, JavaScript |
| PDF processing | PyMuPDF |
| Embeddings | Gemini `gemini-embedding-001` |
| Vector database | FAISS CPU |
| Answer generation | Gemini Flash |
| Configuration | python-dotenv |
| API validation | Pydantic |

## Architecture

1. **Document ingestion:** PDFs are read from the `documents/` directory. Text is extracted page by page.
2. **Metadata extraction:** Document number, revision, effective date, source filename and page number are captured.
3. **Chunking:** Extracted text is divided into overlapping chunks to retain context.
4. **Revision management:** Explicitly superseded document revisions are excluded from the active retrieval set.
5. **Embedding generation:** Gemini converts document chunks into 768-dimensional vectors.
6. **Indexing:** FAISS stores normalized vectors for similarity search.
7. **Question retrieval:** A user's question is embedded and compared against indexed document chunks. Results below the configured similarity threshold of `0.60` are discarded.
8. **Answer generation:** Gemini receives the question and retrieved evidence and is instructed to answer only from that evidence.
9. **Evidence validation:** Returned evidence identifiers and supporting excerpts are checked against retrieved content.
10. **Presentation:** The frontend displays the answer, source references and supporting excerpt, or an insufficient-information response.

### High-level flow

```text
PDF Documents
     |
     v
PyMuPDF Extraction
     |
     v
Metadata + Text Chunking
     |
     v
Revision Filtering
     |
     v
Gemini Embeddings
     |
     v
FAISS Vector Index
     |
     v
User Question
     |
     v
Question Embedding
     |
     v
FAISS Similarity Retrieval
     |
     v
Gemini Answer Generation
     |
     v
Evidence Validation
     |
     v
Answer + Sources / Abstention
```

## Project Structure

```text
Manufacturing_SOP_Copilot/
|
├── app/
│   ├── main.py
│   ├── services/
│   │   ├── answer_generator.py
│   │   ├── embeddings.py
│   │   ├── pdf_processor.py
│   │   ├── retriever.py
│   │   └── version_manager.py
│   ├── static/
│   │   ├── script.js
│   │   └── style.css
│   └── templates/
│       └── index.html
│
├── documents/
│   ├── MNT-MAN-CNC-02_TX-200_Preventive_Maintenance.pdf
│   ├── QC-SOP-014_Rev03_Incoming_Material_Inspection.pdf
│   ├── QC-SOP-014_Rev04_Incoming_Material_Inspection.pdf
│   └── SAF-SOP-003_Lockout_Tagout_Procedure.pdf
│
├── tests/
│   └── test_version_manager.py
│
├── vector_store/
│   ├── document_chunks.json
│   ├── document_metadata.json
│   ├── indexed_chunks.json
│   └── sop_index.faiss
│
├── .env.example
├── .gitignore
└── requirements.txt
```

## Prerequisites

- Python 3.12
- A Gemini API key
- Internet connectivity for Gemini embedding and generation requests

The PDF extraction, FAISS indexing and similarity search run locally. Gemini API calls require internet connectivity and are subject to the API account's quotas and rate limits.

## Setup and Installation

### 1. Clone the repository

```bash
git clone https://github.com/Sknda/Manufacturing_SOP_Copilot.git
cd Manufacturing_SOP_Copilot
```

### 2. Create and activate a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root.

```env
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-3.5-flash-lite
GEMINI_EMBEDDING_MODEL=gemini-embedding-001
EMBEDDING_DIMENSION=768
```

Replace the API key placeholder with your own Gemini API key. Use a Gemini Flash model available to your account if the example model is unavailable.

**Do not commit `.env` or expose your API key.** The `.gitignore` file excludes environment files.

### 5. Process the PDF documents

```bash
python -m app.services.pdf_processor
```

This extracts PDF text, generates metadata and chunks, and saves the outputs under `vector_store/`.

### 6. Generate the vector index

```bash
python -m app.services.embeddings
```

This generates embeddings for the active document chunks and builds the FAISS index.

The repository includes generated vector-store files from the current document set. Re-run the processing and indexing steps if the source PDFs or revision configuration change.

### 7. Run the application

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Open the application on the computer running the server:

`http://localhost:8000`

FastAPI API documentation:

`http://localhost:8000/docs`

### 8. Access from a phone on the same Wi-Fi network

Find the computer's local IPv4 address:

```powershell
ipconfig
```

Use the IPv4 address in the phone browser:

`http://YOUR_LOCAL_IP:8000`

For example:

`http://192.168.0.141:8000`

The computer and phone must be connected to the same Wi-Fi network. Allow Python through Windows Firewall on a private network if prompted.

## API

### Health check

`GET /health`

Returns the application health status.

### Ask a question

`POST /api/ask`

Example request:

```json
{
  "question": "What is the recommended coolant concentration for the TX-200?"
}
```

The response includes:

- `status` — answer status.
- `answer` — generated answer or insufficient-information message.
- `sources` — source document, revision, page and related metadata.
- `supporting_excerpt` — evidence excerpt from the retrieved content.

The application also exposes an HTTP 503 response when Gemini is temporarily unavailable or rate-limited.

## Question Evaluation

The following questions cover the five questions supplied with the assignment and five additional questions selected to test retrieval, revision handling and abstention.

A. Supplied questions

1. What is the recommended coolant concentration for the TX-200?

Expected answer: Maintain coolant concentration between 6% and 8%, using a refractometer with a factor of 1.0.

Source: MNT-MAN-CNC-02, Revision 02, page 1.

2. What does alarm AL-104 indicate, and what action should be taken?

Expected answer: AL-104 indicates low way lube oil. Top up with ISO VG 68 oil to the MAX level and press RESET. Operation can continue after the reset.

Source: MNT-MAN-CNC-02, Revision 02, page 2.

3. Who is permitted to remove a Lockout/Tagout lock?

Expected answer: Each authorized person must remove their own lock. If the lock owner is absent, the exceptional procedure requires attempting to contact the owner. If unreachable, both the Production Manager and Safety Officer must authorize removal after physically inspecting the equipment for safety. The action must be recorded using SF-12 and the owner informed.

Source: SAF-SOP-003, Revision 05, pages 1–2.

4. What is the acceptable outer diameter tolerance for BH-220?

Expected answer: The BH-220 outer diameter is 90.000 ± 0.050 mm, measured using a digital caliper. The characteristic is classified as Major.

Source: QC-SOP-014, Revision 04, page 2.

5. How frequently should spindle runout be checked, and what is the acceptable limit?

Expected answer: Maintenance personnel must check spindle runout monthly. The maximum permitted runout is 0.005 mm at the chuck face, using a dial indicator.

Source: MNT-MAN-CNC-02, Revision 02, page 1.

B. Additional questions

6. For an incoming material lot of 200 pieces, how many samples should QC inspect?

Expected answer: Inspect 13 samples, as a lot size between 91 and 500 requires a sample size of 13.

Source: QC-SOP-014, Revision 04, page 1.

7. What should QC do if the supplier Material Test Certificate (MTC) is missing?

Expected answer: The MTC is mandatory under the current incoming material inspection procedure. The material must be placed on hold until the required certificate is available.

Source: QC-SOP-014, Revision 04, page 1.

8. Can an operator remove another employee's LOTO lock?

Expected answer: No. Each authorized person removes only their own lock. The absent-owner exception requires the specific authorization, safety inspection and documentation procedure described in the SOP.

Source: SAF-SOP-003, Revision 05, pages 1–2.

9. Which revision of the incoming material inspection SOP should be used?

Expected answer: Revision 04 is the applicable revision in the supplied documents. It explicitly supersedes Revision 03 and has an effective date of 01-Jul-2026.

Source: QC-SOP-014, Revision 04, page 1.

10. What is the company's employee leave policy?

Expected answer: The supplied documents do not contain the company's employee leave policy. The copilot should respond that it does not have sufficient information rather than inventing a policy.

Expected behavior: insufficient_information, with no supporting source citations.

## Revision Handling

The supplied document set contains two revisions of `QC-SOP-014`:

- Revision 03 — effective 15-Mar-2023.
- Revision 04 — effective 01-Jul-2026.

Revision 04 explicitly supersedes Revision 03. The version manager excludes Revision 03 from the active retrieval index.

The current implementation uses explicit supersession metadata. It does not connect to a live document-control or Quality Management System (QMS), and it cannot independently verify whether a newer controlled revision exists outside the supplied PDFs.

## Safety and Limitations

- This is an assignment prototype, not an approved production or safety-critical decision system.
- Answers are limited to the four supplied PDFs.
- The application cannot verify whether the supplied documents are the latest approved copies in a company's live QMS.
- The similarity threshold is a configurable retrieval heuristic and may need calibration against a larger question set.
- PDF table extraction and chunk boundaries can affect retrieval quality.
- Gemini API availability, rate limits and quotas can affect answer generation.
- The application currently does not implement persistent answer caching.
- Users must verify critical operational and safety instructions against the applicable controlled document and follow their organization's escalation procedures.

## Security

- Keep Gemini API keys in `.env`.
- Never commit credentials or secrets.
- The application uses a local FAISS index; Gemini API calls send the question and relevant document content to the configured Google Gemini service.
- Do not submit confidential production information unless the organization's data-handling requirements permit it.

