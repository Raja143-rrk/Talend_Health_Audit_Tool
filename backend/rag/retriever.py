import os
from threading import Lock

from backend.rag.documents import RagDocument
from backend.rag.documents import RagSearchResult, RetrievalContext
from backend.rag.knowledge_base import TALEND_KNOWLEDGE_BASE
from backend.rag.vector_store import VectorStoreFactory


class RagRetriever:
    """Contextual retriever with vector DB support and local lexical fallback."""

    def __init__(
        self,
        documents: list[RagDocument] | None = None,
        vector_store_factory: VectorStoreFactory | None = None,
    ) -> None:
        self._documents: list[RagDocument] = documents or list(TALEND_KNOWLEDGE_BASE)
        self._vector_store_factory = vector_store_factory or VectorStoreFactory()
        self._vector_store = None
        self._vector_enabled = os.getenv("RAG_VECTOR_DB", "memory").lower() in {"faiss", "chroma"}
        self._last_backend = "memory"
        self._vector_store_lock = Lock()

    def add_documents(self, documents: list[RagDocument]) -> None:
        self._documents.extend(documents)
        self._vector_store = None

    def search(self, query: str, limit: int = 5) -> list[RagSearchResult]:
        if self._vector_enabled:
            try:
                results = self._semantic_search(query, limit)
                self._last_backend = os.getenv("RAG_VECTOR_DB", "memory").lower()
                return results
            except Exception:
                self._last_backend = "memory"
                return self._lexical_search(query, limit)
        self._last_backend = "memory"
        return self._lexical_search(query, limit)

    def retrieve_context(self, query: str, limit: int = 5) -> RetrievalContext:
        results = self.search(query, limit)
        context_text = "\n\n".join(
            f"[{result.rank}] {result.document.source}: {result.document.content}"
            for result in results
        )
        return RetrievalContext(
            query=query,
            results=results,
            context_text=context_text,
            backend=self._active_backend(),
        )

    def _semantic_search(self, query: str, limit: int) -> list[RagSearchResult]:
        vector_store = self._get_vector_store()
        raw_results = vector_store.similarity_search_with_score(query, k=limit)
        results: list[RagSearchResult] = []

        for rank, (document, score) in enumerate(raw_results, start=1):
            metadata = dict(document.metadata or {})
            rag_document = RagDocument(
                id=str(metadata.pop("id", f"semantic-{rank}")),
                source=str(metadata.pop("source", "vector-store")),
                content=document.page_content,
                metadata={str(key): str(value) for key, value in metadata.items()},
            )
            results.append(RagSearchResult(document=rag_document, score=float(score), rank=rank))

        return results

    def _lexical_search(self, query: str, limit: int) -> list[RagSearchResult]:
        normalized_query = query.lower()
        query_terms = {term for term in normalized_query.split() if len(term) > 2}
        scored: list[tuple[float, RagDocument]] = []

        for document in self._documents:
            searchable_text = f"{document.content} {' '.join(document.metadata.values())}".lower()
            exact_boost = 5 if normalized_query in searchable_text else 0
            term_score = sum(1 for term in query_terms if term in searchable_text)
            score = exact_boost + term_score
            if score > 0:
                scored.append((float(score), document))

        scored.sort(key=lambda item: item[0], reverse=True)
        return [
            RagSearchResult(document=document, score=score, rank=index)
            for index, (score, document) in enumerate(scored[:limit], start=1)
        ]

    def _get_vector_store(self):
        with self._vector_store_lock:
            if self._vector_store is None:
                self._vector_store = self._vector_store_factory.create(self._documents)
        return self._vector_store

    def _active_backend(self) -> str:
        return self._last_backend
