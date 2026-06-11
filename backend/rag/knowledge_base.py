from pathlib import Path

from backend.rag.documents import RagDocument

RAG_DIR = Path(__file__).resolve().parent


def _load_documents() -> list[RagDocument]:
    documents: list[RagDocument] = []
    category_dirs = [
        "security",
        "performance",
        "maintainability",
        "architecture",
        "limitations",
    ]

    for category in category_dirs:
        category_path = RAG_DIR / category
        if not category_path.is_dir():
            continue
        for md_file in sorted(category_path.glob("*.md")):
            doc_type = md_file.stem
            content = md_file.read_text(encoding="utf-8").strip()
            doc_id = f"talend-{category}-{doc_type}"
            documents.append(
                RagDocument(
                    id=doc_id,
                    source=f"talend-{category}",
                    content=content,
                    metadata={
                        "category": category,
                        "type": doc_type,
                    },
                )
            )

    return documents


TALEND_KNOWLEDGE_BASE = _load_documents()
