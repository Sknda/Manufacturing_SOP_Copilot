
import json

from app.services.version_manager import (
    get_current_documents,
    filter_current_chunks,
    print_revision_summary
)


with open(
    "vector_store/document_metadata.json",
    encoding="utf-8"
) as file:
    metadata = json.load(file)

with open(
    "vector_store/document_chunks.json",
    encoding="utf-8"
) as file:
    chunks = json.load(file)


current_documents = get_current_documents(metadata)

current_chunks = filter_current_chunks(
    chunks,
    current_documents
)

print_revision_summary(metadata, current_documents)

print("\nOriginal chunks:", len(chunks))
print("Current chunks:", len(current_chunks))

print("\nCurrent QC-SOP-014 revision:")

for document in current_documents:
    if document["document_number"] == "QC-SOP-014":
        print("Revision:", document["revision"])
        print("Effective date:", document["effective_date"])
