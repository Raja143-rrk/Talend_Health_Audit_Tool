import os


class EmbeddingProviderFactory:
    def create(self):
        provider = os.getenv("RAG_EMBEDDING_PROVIDER", "fake").lower()

        if provider == "openai":
            try:
                from langchain_openai import OpenAIEmbeddings
            except ImportError as exc:
                raise RuntimeError("langchain-openai is required for OpenAI embeddings.") from exc
            return OpenAIEmbeddings(
                model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
            )

        if provider == "fake":
            try:
                from langchain_core.embeddings import FakeEmbeddings
            except ImportError as exc:
                raise RuntimeError("langchain-core is required for fake embeddings.") from exc
            return FakeEmbeddings(size=int(os.getenv("RAG_FAKE_EMBEDDING_SIZE", "1536")))

        raise ValueError(f"Unsupported embedding provider: {provider}")
