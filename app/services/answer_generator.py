
import time
from google.genai import errors

import json
import os

from dotenv import load_dotenv
from google import genai
from google.genai import types


load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

if not API_KEY:
    raise RuntimeError("GEMINI_API_KEY is missing from .env")

client = genai.Client(api_key=API_KEY)


def generate_with_retry(prompt, max_attempts=3):
    """
    Call Gemini with bounded retries for temporary API failures.

    Retries:
      - 429: Rate limit or quota-related response
      - 500: Internal server error
      - 502: Bad gateway
      - 503: Service unavailable
      - 504: Gateway timeout

    Permanent errors such as 400, 401, 403 and 404 are not retried.
    """

    retryable_status_codes = {429, 500, 502, 503, 504}

    for attempt in range(1, max_attempts + 1):
        try:
            return client.models.generate_content(
                model=MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    temperature=0.1,
                    response_mime_type="application/json"
                )
            )

        except errors.APIError as error:
            status_code = getattr(error, "code", None)

            if status_code not in retryable_status_codes:
                raise

            if attempt == max_attempts:
                raise RuntimeError(
                    "Gemini is temporarily unavailable or rate-limited. "
                    "Please try again later."
                ) from error

            wait_seconds = 2 ** attempt

            print(
                f"Gemini API error {status_code}. "
                f"Retrying in {wait_seconds} seconds "
                f"(attempt {attempt}/{max_attempts})..."
            )

            time.sleep(wait_seconds)



SYSTEM_INSTRUCTION = """
You are a Manufacturing SOP Copilot for factory supervisors.

Answer operational questions using ONLY the supplied SOP evidence.

STRICT RULES:
1. Never invent procedures, measurements, tolerances, alarm meanings,
   safety instructions, or approval requirements.
2. Do not use general knowledge to fill gaps in the supplied evidence.
3. If the evidence does not answer the question, abstain.
4. If the evidence is ambiguous or conflicting, disclose this.
5. Preserve all relevant safety warnings and authorization requirements.
6. Paraphrase the answer. Do not copy entire paragraphs.
7. Identify only the evidence IDs that directly support your answer.
8. Provide a short supporting excerpt copied exactly from one of
   those evidence items.
9. Never invent or modify evidence IDs.
10. Do not include document references in the answer text.
    Python will construct the source references.

OUTPUT:
Return valid JSON only, using this structure:

{
  "status": "answered",
  "answer": "A concise paraphrased answer.",
  "evidence_ids": ["E1"],
  "supporting_excerpt": "An exact short excerpt from the evidence."
}

If the evidence is insufficient, return:

{
  "status": "insufficient_information",
  "answer": "The available SOP documents do not contain sufficient
  information to answer this question.",
  "evidence_ids": [],
  "supporting_excerpt": ""
}

Do not include Markdown fences or additional text.
"""


def format_context(retrieved_chunks):
    """Assign evidence IDs to retrieved chunks."""

    context_parts = []
    evidence_map = {}

    for index, chunk in enumerate(retrieved_chunks, start=1):

        evidence_id = f"E{index}"
        evidence_map[evidence_id] = chunk

        context_parts.append(
            f"""
Evidence ID: {evidence_id}
Document: {chunk['document_number']}
Revision: {chunk['revision']}
Page: {chunk['page_number']}
Source file: {chunk['source_file']}

Content:
{chunk['text']}
"""
        )

    return "\n".join(context_parts), evidence_map


def normalize_text(value):
    """Normalize whitespace for excerpt verification."""

    return " ".join(value.split())


def build_source_reference(chunk):
    """Build source metadata from trusted Python data."""

    return {
        "document_number": chunk["document_number"],
        "revision": chunk["revision"],
        "page_number": chunk["page_number"],
        "source_file": chunk["source_file"]
    }


def generate_answer(question, retrieved_chunks):
    """
    Generate a grounded answer and validate its evidence references.

    Source metadata is always constructed from retrieved chunks,
    never from model-generated document references.
    """

    if not question or not question.strip():
        raise ValueError("Question cannot be empty.")

    if not retrieved_chunks:
        return {
            "status": "insufficient_information",
            "answer": (
                "I couldn't find sufficient supporting information "
                "for this question in the available SOP documents. "
                "Please consult the relevant department or supervisor."
            ),
            "sources": [],
            "supporting_excerpt": ""
        }

    context, evidence_map = format_context(retrieved_chunks)

    prompt = f"""
USER QUESTION:
{question}

RETRIEVED SOP EVIDENCE:
{context}

Answer using only this evidence.

Return the required JSON structure.
Select only evidence IDs that directly support the answer.
The supporting excerpt must be copied exactly from the selected evidence.
"""

    response = generate_with_retry(prompt)

    if not response.text:
        raise RuntimeError("Gemini returned an empty response.")

    try:
        result = json.loads(response.text)
    except json.JSONDecodeError as error:
        raise RuntimeError(
            f"Gemini returned invalid JSON: {response.text}"
        ) from error

    status = result.get("status")
    answer = result.get("answer", "").strip()
    evidence_ids = result.get("evidence_ids", [])
    excerpt = result.get("supporting_excerpt", "").strip()

    if status == "insufficient_information":
        return {
            "status": "insufficient_information",
            "answer": (
                "I couldn't find sufficient supporting information "
                "for this question in the available SOP documents. "
                "Please consult the relevant department or supervisor."
            ),
            "sources": [],
            "supporting_excerpt": ""
        }

    if status != "answered" or not answer:
        raise RuntimeError("Gemini returned an invalid answer structure.")

    if not isinstance(evidence_ids, list) or not evidence_ids:
        raise RuntimeError(
            "Gemini did not identify supporting evidence."
        )

    # Reject evidence IDs that were not supplied to Gemini.
    if any(
        not isinstance(evidence_id, str)
        or evidence_id not in evidence_map
        for evidence_id in evidence_ids
    ):
        raise RuntimeError(
            "Gemini returned an unknown evidence ID."
        )

    # Remove duplicate evidence IDs while preserving order.
    evidence_ids = list(dict.fromkeys(evidence_ids))

    selected_chunks = [
        evidence_map[evidence_id]
        for evidence_id in evidence_ids
    ]

    # Verify that the supporting excerpt exists in selected evidence.
    normalized_excerpt = normalize_text(excerpt)

    excerpt_is_valid = (
        bool(normalized_excerpt)
        and any(
            normalized_excerpt in normalize_text(chunk["text"])
            for chunk in selected_chunks
        )
    )

    if not excerpt_is_valid:
        # Safe fallback: use an actual passage from the first
        # selected source rather than displaying an invented quote.
        source_text = selected_chunks[0]["text"].strip()
        excerpt = source_text[:240].strip()

        if len(source_text) > 240:
            excerpt += "..."

    # Construct references exclusively from selected retrieved chunks.
    sources = []
    seen_sources = set()

    for chunk in selected_chunks:
        source = build_source_reference(chunk)

        source_key = (
            source["document_number"],
            source["revision"],
            source["page_number"],
            source["source_file"]
        )

        if source_key not in seen_sources:
            sources.append(source)
            seen_sources.add(source_key)

    return {
        "status": "answered",
        "answer": answer,
        "sources": sources,
        "supporting_excerpt": excerpt
    }


if __name__ == "__main__":

    from app.services.retriever import retrieve_relevant_chunks

    test_questions = [
        "What is the required coolant concentration for the CNC machine?",
        "What does alarm AL-104 indicate?",
        "What is the company leave policy?"
    ]

    for question in test_questions:

        print("\n" + "=" * 70)
        print("QUESTION:", question)
        print("=" * 70)

        chunks = retrieve_relevant_chunks(question)
        result = generate_answer(question, chunks)

        print("\nSTATUS:", result["status"])
        print("\nANSWER:\n", result["answer"])

        if result["sources"]:
            print("\nVERIFIED SOURCE REFERENCES:")

            for source in result["sources"]:
                print(source)

            print("\nSUPPORTING EXCERPT:")
            print(result["supporting_excerpt"])
