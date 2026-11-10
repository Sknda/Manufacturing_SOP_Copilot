
from collections import defaultdict


# Relationships verified from the supplied documents.
SUPERSEDES = {
    ("QC-SOP-014", 4): [3]
}


def get_current_documents(metadata: list[dict]) -> list[dict]:
    """
    Return the latest applicable revisions.

    A revision is considered superseded only when an explicit
    supersedes relationship is available.
    """

    grouped = defaultdict(list)

    for document in metadata:
        grouped[document["document_number"]].append(document)

    current_documents = []

    for document_number, revisions in grouped.items():

        superseded_revisions = set()

        for revision in revisions:
            key = (
                document_number,
                revision["revision"]
            )

            superseded_revisions.update(
                SUPERSEDES.get(key, [])
            )

        active_revisions = [
            revision
            for revision in revisions
            if revision["revision"] not in superseded_revisions
        ]

        if not active_revisions:
            continue

        # Select the highest revision among non-superseded
        # revisions available in the supplied document set.
        selected = max(
            active_revisions,
            key=lambda item: item["revision"]
        )

        selected = selected.copy()
        selected["status"] = "active"

        current_documents.append(selected)

    return current_documents


def filter_current_chunks(
    chunks: list[dict],
    current_documents: list[dict]
) -> list[dict]:
    """Keep chunks belonging to the selected document revisions."""

    allowed = {
        (
            document["document_number"],
            document["revision"]
        )
        for document in current_documents
    }

    return [
        chunk
        for chunk in chunks
        if (
            chunk["document_number"],
            chunk["revision"]
        ) in allowed
    ]


def print_revision_summary(
    metadata: list[dict],
    current_documents: list[dict]
):
    """Display selected and superseded revisions."""

    current = {
        (
            document["document_number"],
            document["revision"]
        )
        for document in current_documents
    }

    print("\n========== REVISION SUMMARY ==========")

    for document in metadata:

        key = (
            document["document_number"],
            document["revision"]
        )

        status = "ACTIVE" if key in current else "SUPERSEDED"

        print(
            f"{document['document_number']} | "
            f"Rev {document['revision']} | "
            f"{status}"
        )

    print("======================================")
