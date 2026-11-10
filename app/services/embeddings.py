
import os
import json
from pathlib import Path

import faiss
import numpy as np

from dotenv import load_dotenv
from google import genai
from google.genai import types

from app.services.version_manager import (
    get_current_documents,
    filter_current_chunks
)


# Load environment variables
BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")

API_KEY = os.getenv("GEMINI_API_KEY")
MODEL = os.getenv(
    "GEMINI_EMBEDDING_MODEL",
    "gemini-embedding-001"
)

DIMENSION = int(
    os.getenv("EMBEDDING_DIMENSION", "768")
)

BATCH_SIZE = 10

if not API_KEY:
    raise ValueError("GEMINI_API_KEY is missing from .env")

client = genai.Client(api_key=API_KEY)


def generate_embeddings(
    texts: list[str],
    task_type: str
) -> np.ndarray:
    """Generate Gemini embeddings in batches."""

    all_vectors = []

    for start in range(0, len(texts), BATCH_SIZE):

        batch = texts[start:start + BATCH_SIZE]

        response = client.models.embed_content(
            model=MODEL,
            contents=batch,
            config=types.EmbedContentConfig(
                task_type=task_type,
                output_dimensionality=DIMENSION
            )
        )

        if not response.embeddings:
            raise RuntimeError("Gemini returned no embeddings")

        for embedding in response.embeddings:

            if not embedding.values:
                raise RuntimeError("Empty embedding returned")

            all_vectors.append(embedding.values)

        print(
            f"Embedded {min(start + len(batch), len(texts))}"
            f"/{len(texts)} texts"
        )

    vectors = np.asarray(all_vectors, dtype="float32")

    if vectors.shape != (len(texts), DIMENSION):
        raise ValueError(
            f"Unexpected embedding shape: {vectors.shape}"
        )

    # Normalize vectors for cosine similarity using FAISS.
    faiss.normalize_L2(vectors)

    return vectors


def build_vector_store():

    metadata_path = BASE_DIR / "vector_store" / "document_metadata.json"
    chunks_path = BASE_DIR / "vector_store" / "document_chunks.json"

    with open(metadata_path, encoding="utf-8") as file:
        metadata = json.load(file)

    with open(chunks_path, encoding="utf-8") as file:
        all_chunks = json.load(file)

    current_documents = get_current_documents(metadata)

    current_chunks = filter_current_chunks(
        all_chunks,
        current_documents
    )

    if not current_chunks:
        raise ValueError("No active document chunks found")

    print("\nGenerating document embeddings...")

    texts = [
        chunk["text"]
        for chunk in current_chunks
    ]

    vectors = generate_embeddings(
        texts,
        task_type="RETRIEVAL_DOCUMENT"
    )

    # Inner product on normalized vectors = cosine similarity.
    index = faiss.IndexFlatIP(DIMENSION)

    index.add(vectors)

    output_dir = BASE_DIR / "vector_store"
    output_dir.mkdir(exist_ok=True)

    faiss.write_index(
        index,
        str(output_dir / "sop_index.faiss")
    )

    with open(
        output_dir / "indexed_chunks.json",
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            current_chunks,
            file,
            indent=4,
            ensure_ascii=False
        )

    print("\n========== VECTOR STORE SUMMARY ==========")
    print("Documents:", len(current_documents))
    print("Indexed chunks:", index.ntotal)
    print("Embedding dimensions:", DIMENSION)
    print("Index saved successfully")
    print("==========================================")


if __name__ == "__main__":
    build_vector_store()
