from __future__ import annotations

import os
from pathlib import Path

from backend.rag.documents import RagDocument
from backend.rag.embeddings import EmbeddingProviderFactory

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PERSIST_DIR = PROJECT_ROOT / "reports" / "vector_store"


class VectorStoreFactory:
    def __init__(self, embedding_factory: EmbeddingProviderFactory | None = None) -> None:
        self.embedding_factory = embedding_factory or EmbeddingProviderFactory()

    def create(self, documents: list[RagDocument]):
        backend = os.getenv("RAG_VECTOR_DB", "memory").lower()
        langchain_documents = self._to_langchain_documents(documents)

        if backend == "faiss":
            try:
                from langchain_community.vectorstores import FAISS
            except ImportError as exc:
                raise RuntimeError("langchain-community and faiss-cpu are required for FAISS.") from exc
            return FAISS.from_documents(langchain_documents, self.embedding_factory.create())

        if backend == "chroma":
            try:
                from langchain_chroma import Chroma
            except ImportError as exc:
                raise RuntimeError("langchain-chroma and chromadb are required for ChromaDB.") from exc
            persist_dir = os.getenv("RAG_PERSIST_DIR", str(DEFAULT_PERSIST_DIR / "chroma"))
            return Chroma.from_documents(
                documents=langchain_documents,
                embedding=self.embedding_factory.create(),
                persist_directory=persist_dir,
            )

        raise ValueError(f"Unsupported vector database: {backend}")

    def _to_langchain_documents(self, documents: list[RagDocument]) -> list["Document"]:
        try:
            from langchain_core.documents import Document
        except ImportError as exc:
            raise RuntimeError("langchain-core is required for vector store documents.") from exc

        return [
            Document(
                page_content=document.content,
                metadata={
                    "id": document.id,
                    "source": document.source,
                    **document.metadata,
                },
            )
            for document in documents
        ]
