
import re
import json
from pathlib import Path
from datetime import datetime

import pymupdf


# Project paths
BASE_DIR = Path(__file__).resolve().parents[2]
DOCUMENTS_DIR = BASE_DIR / "documents"

# Chunking configuration
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150


def clean_text(text: str) -> str:
    """Clean extracted PDF text without removing meaningful content."""

    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def extract_metadata(text: str, filename: str) -> dict:
    """Extract document metadata from PDF text and filename."""

    combined = text + "\n" + filename

    doc_match = re.search(
        r"\b((?:QC-SOP|SAF-SOP|MNT-MAN)-[A-Z0-9-]+)\b",
        combined,
        re.IGNORECASE
    )

    revision_match = re.search(
        r"\bRevision\s*0*(\d+)\b",
        text,
        re.IGNORECASE
    )

    if not revision_match:
        revision_match = re.search(
            r"_Rev0*(\d+)",
            filename,
            re.IGNORECASE
        )

    date_match = re.search(
        r"Effective Date\s+(\d{1,2}-[A-Za-z]{3}-\d{4})",
        text,
        re.IGNORECASE
    )

    effective_date = None

    if date_match:
        try:
            effective_date = datetime.strptime(
                date_match.group(1),
                "%d-%b-%Y"
            ).date().isoformat()
        except ValueError:
            pass

    return {
        "document_number": (
            doc_match.group(1).upper() if doc_match else "UNKNOWN"
        ),
        "revision": (
            int(revision_match.group(1))
            if revision_match else None
        ),
        "effective_date": effective_date,
        "source_file": filename
    }


def split_into_chunks(text: str) -> list[str]:
    """Split text into overlapping chunks."""

    paragraphs = [
        p.strip()
        for p in text.split("\n")
        if p.strip()
    ]

    chunks = []
    current_chunk = ""

    for paragraph in paragraphs:

        if len(paragraph) > CHUNK_SIZE:
            if current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = ""

            start = 0

            while start < len(paragraph):
                end = start + CHUNK_SIZE
                chunks.append(paragraph[start:end].strip())
                start += CHUNK_SIZE - CHUNK_OVERLAP

            continue

        if len(current_chunk) + len(paragraph) + 1 <= CHUNK_SIZE:
            current_chunk += "\n" + paragraph
        else:
            if current_chunk.strip():
                chunks.append(current_chunk.strip())

            overlap = current_chunk[-CHUNK_OVERLAP:]

            current_chunk = overlap + "\n" + paragraph

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks


def process_pdf(pdf_path: Path) -> tuple[dict, list[dict]]:
    """Extract page-level text and create metadata-rich chunks."""

    document = pymupdf.open(pdf_path)

    all_text = "\n".join(
        page.get_text("text")
        for page in document
    )

    metadata = extract_metadata(all_text, pdf_path.name)

    metadata["total_pages"] = len(document)

    chunks = []

    for page_index, page in enumerate(document):

        page_number = page_index + 1
        page_text = clean_text(page.get_text("text"))

        if not page_text:
            continue

        page_chunks = split_into_chunks(page_text)

        for chunk_index, chunk_text in enumerate(page_chunks):

            chunks.append({
                "chunk_id": (
                    f"{metadata['document_number']}_"
                    f"REV{metadata['revision']}_"
                    f"P{page_number}_C{chunk_index + 1}"
                ),
                "text": chunk_text,
                "document_number": metadata["document_number"],
                "revision": metadata["revision"],
                "effective_date": metadata["effective_date"],
                "source_file": metadata["source_file"],
                "page_number": page_number
            })

    document.close()

    return metadata, chunks


def process_all_pdfs() -> tuple[list[dict], list[dict]]:
    """Process all manufacturing PDFs in the documents directory."""

    if not DOCUMENTS_DIR.exists():
        raise FileNotFoundError(
            f"Documents directory not found: {DOCUMENTS_DIR}"
        )

    pdf_files = sorted(DOCUMENTS_DIR.glob("*.pdf"))

    if not pdf_files:
        raise FileNotFoundError(
            "No PDF documents found in the documents directory."
        )

    all_metadata = []
    all_chunks = []

    for pdf_path in pdf_files:

        print(f"\nProcessing: {pdf_path.name}")

        metadata, chunks = process_pdf(pdf_path)

        all_metadata.append(metadata)
        all_chunks.extend(chunks)

        print(f"Document number: {metadata['document_number']}")
        print(f"Revision: {metadata['revision']}")
        print(f"Effective date: {metadata['effective_date']}")
        print(f"Pages: {metadata['total_pages']}")
        print(f"Chunks: {len(chunks)}")

    return all_metadata, all_chunks


def save_extraction(metadata: list[dict], chunks: list[dict]):

    output_dir = BASE_DIR / "vector_store"
    output_dir.mkdir(exist_ok=True)

    with open(
        output_dir / "document_metadata.json",
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(metadata, file, indent=4)

    with open(
        output_dir / "document_chunks.json",
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(chunks, file, indent=4, ensure_ascii=False)

    print("\nExtraction files saved successfully.")


if __name__ == "__main__":

    metadata, chunks = process_all_pdfs()

    save_extraction(metadata, chunks)

    print("\n========== EXTRACTION SUMMARY ==========")
    print(f"Total documents: {len(metadata)}")
    print(f"Total chunks: {len(chunks)}")
    print("========================================")
