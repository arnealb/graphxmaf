"""
Vector RAG using the graphrag-built LanceDB index.
Flow: embed query → LanceDB top-5 → single LLM call.
Avoids graphrag local_search (multiple LLM calls + retry loops).
"""
import asyncio
import logging
import os
from pathlib import Path
from typing import Any

import pandas as pd

log = logging.getLogger("graph.graphrag")

GRAPHRAG_ROOT = Path(__file__).parent / "graphrag"
OUTPUT_DIR = GRAPHRAG_ROOT / "output"


def _load_parquet(name: str) -> pd.DataFrame:
    path = OUTPUT_DIR / f"{name}.parquet"
    return pd.read_parquet(path) if path.exists() else pd.DataFrame()


class _GraphRAGIndex:
    """Holds parquet data + LanceDB table. Instantiated once at first query."""

    def __init__(self):
        import lancedb
        from dotenv import load_dotenv

        # Local dev: load .env into os.environ if vars not already set.
        # Azure Container Apps: env vars are set at the container level → .env is ignored.
        load_dotenv(GRAPHRAG_ROOT / ".env", override=False)

        self.api_key = os.environ["GRAPHRAG_API_KEY"]
        self.api_base = os.environ["GRAPHRAG_API_BASE"]
        self.chat_deployment = os.environ.get("GRAPHRAG_CHAT_DEPLOYMENT", "gpt-4o-mini")
        self.embedding_deployment = os.environ.get("GRAPHRAG_EMBEDDING_DEPLOYMENT", "text-embedding-3-small")
        self.api_version = "2025-01-01-preview"

        self.text_units = _load_parquet("text_units")
        self.documents = _load_parquet("documents")

        db = lancedb.connect(str(OUTPUT_DIR / "lancedb"))
        self.vector_table = db.open_table("text_unit_text")

        log.info("[graphrag] Index loaded — %d text units, %d documents",
                 len(self.text_units), len(self.documents))


_index: _GraphRAGIndex | None = None


def _get_index() -> _GraphRAGIndex:
    global _index
    if _index is None:
        log.info("[graphrag] Initialising GraphRAG index...")
        _index = _GraphRAGIndex()
    return _index


def _search_sync(query: str) -> dict[str, Any]:
    """Synchronous: embed → LanceDB search → single LLM call."""
    from openai import AzureOpenAI

    idx = _get_index()

    client = AzureOpenAI(
        api_key=idx.api_key,
        azure_endpoint=idx.api_base,
        api_version=idx.api_version,
    )

    # 1. Embed the query
    emb = client.embeddings.create(model=idx.embedding_deployment, input=query)
    query_vector = emb.data[0].embedding

    # 2. Vector search → top-5 most similar text chunks
    results = idx.vector_table.search(query_vector).limit(5).to_pandas()
    chunk_ids = results["id"].tolist()

    # 3. Retrieve text + source document titles
    chunks = idx.text_units[idx.text_units["id"].isin(chunk_ids)]
    doc_id_to_title = idx.documents.set_index("id")["title"].to_dict()

    sources: list[str] = []
    context_parts: list[str] = []
    for _, row in chunks.iterrows():
        title = (
            doc_id_to_title.get(row.get("document_id", ""), "unknown")
            .replace(".docx.txt", "")
            .replace(".txt", "")
        )
        sources.append(title)
        context_parts.append(f"[{title}]\n{row['text']}")

    context = "\n\n---\n\n".join(context_parts)

    # 4. Single LLM call
    resp = client.chat.completions.create(
        model=idx.chat_deployment,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a helpful assistant answering questions about internal company documents. "
                    "Use only the provided context. "
                    "Answer in the same language as the question. "
                    "If the context does not contain the answer, say so clearly."
                ),
            },
            {
                "role": "user",
                "content": f"Context:\n{context}\n\nQuestion: {query}",
            },
        ],
        temperature=0,
    )

    return {"answer": resp.choices[0].message.content, "sources": list(set(sources))}


async def search_documents(query: str) -> dict[str, Any]:
    """Search company documents. Runs in a thread to avoid blocking the MCP event loop."""
    return await asyncio.to_thread(_search_sync, query)
