
import json
from pathlib import Path

import faiss
import numpy as np

from app.services.embeddings import generate_embeddings


BASE_DIR = Path(__file__).resolve().parents[2]
VECTOR_STORE_DIR = BASE_DIR / "vector_store"

INDEX_PATH = VECTOR_STORE_DIR / "sop_index.faiss"
CHUNKS_PATH = VECTOR_STORE_DIR / "indexed_chunks.json"

# Minimum cosine similarity for accepting a retrieved chunk.
# We will calibrate this after testing.
SIMILARITY_THRESHOLD = 0.60


def load_vector_store():
    """Load the FAISS index and its corresponding chunk metadata."""

    if not INDEX_PATH.exists():
        raise FileNotFoundError(
            f"FAISS index not found: {INDEX_PATH}. "
            "Run embeddings.py first."
        )

    if not CHUNKS_PATH.exists():
        raise FileNotFoundError(
            f"Indexed chunks not found: {CHUNKS_PATH}"
        )

    index = faiss.read_index(str(INDEX_PATH))

    with open(CHUNKS_PATH, "r", encoding="utf-8") as file:
        chunks = json.load(file)

    if index.ntotal != len(chunks):
        raise ValueError(
            "FAISS index and chunk metadata have different sizes."
        )

    return index, chunks


def retrieve_relevant_chunks(
    question: str,
    top_k: int = 5,
    threshold: float = SIMILARITY_THRESHOLD
):
    """
    Retrieve the most relevant SOP chunks for a question.

    Returns matching chunks with their similarity scores
    and source metadata.
    """

    if not question or not question.strip():
        raise ValueError("Question cannot be empty.")

    if top_k < 1:
        raise ValueError("top_k must be at least 1.")

    index, chunks = load_vector_store()

    # Convert the user's question into an embedding.
    query_vector = generate_embeddings(
        [question.strip()],
        task_type="RETRIEVAL_QUERY"
    )

    # Search FAISS using cosine similarity.
    # The index uses normalized vectors and inner product.
    search_k = min(top_k, index.ntotal)

    scores, indices = index.search(query_vector, search_k)

    results = []

    for score, chunk_index in zip(scores[0], indices[0]):

        if chunk_index < 0:
            continue

        score = float(score)

        if score < threshold:
            continue

        chunk = chunks[int(chunk_index)]

        results.append({
            "text": chunk["text"],
            "score": round(score, 4),
            "document_number": chunk["document_number"],
            "revision": chunk["revision"],
            "effective_date": chunk["effective_date"],
            "source_file": chunk["source_file"],
            "page_number": chunk["page_number"],
            "chunk_id": chunk["chunk_id"]
        })

    return results


if __name__ == "__main__":

    test_questions = [
        "What is the required coolant concentration for the CNC machine?",
        "What does alarm AL-104 indicate?",
        "What is the inspection tolerance for the BH-220 outer diameter?",
        "What is the company leave policy?"
    ]

    for question in test_questions:

        print("\n" + "=" * 70)
        print(f"QUESTION: {question}")
        print("=" * 70)

        retrieved = retrieve_relevant_chunks(question)

        if not retrieved:
            print("No sufficiently relevant SOP information found.")
            continue

        for result in retrieved:
            print(
                f"\nDocument: {result['document_number']} "
                f"| Revision: {result['revision']}"
            )
            print(
                f"Page: {result['page_number']} "
                f"| Similarity: {result['score']}"
            )
            print(f"Source: {result['source_file']}")
            print(f"Text: {result['text']}")
