"""
GraphRAG local search wrapper — loaded once at MCP server startup, queried per request.
"""
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
    """Holds config + parquet data. Instantiated once at first query."""

    def __init__(self):
        from graphrag.config.load_config import load_config

        # graphrag resolves relative paths (input/, output/, lancedb) from root_dir
        # load_config internally sets CWD — we restore it afterwards
        orig_cwd = os.getcwd()
        try:
            self.config = load_config(root_dir=GRAPHRAG_ROOT)
        finally:
            os.chdir(orig_cwd)

        # Make lancedb path absolute so it works regardless of CWD at query time
        self.config.vector_store.db_uri = str(OUTPUT_DIR / "lancedb")

        self.entities = _load_parquet("entities")
        self.communities = _load_parquet("communities")
        self.community_reports = _load_parquet("community_reports")
        self.text_units = _load_parquet("text_units")
        self.relationships = _load_parquet("relationships")
        covariates_path = OUTPUT_DIR / "covariates.parquet"
        self.covariates = pd.read_parquet(covariates_path) if covariates_path.exists() else None

        log.info("[graphrag] Index loaded — %d entities, %d text units",
                 len(self.entities), len(self.text_units))


_index: _GraphRAGIndex | None = None


def _get_index() -> _GraphRAGIndex:
    global _index
    if _index is None:
        log.info("[graphrag] Initialising GraphRAG index...")
        _index = _GraphRAGIndex()
    return _index


async def search_documents(query: str) -> dict[str, Any]:
    """
    Search the GraphRAG knowledge graph.
    Returns the answer text and the source document references.
    """
    from graphrag.api.query import local_search

    idx = _get_index()

    response, context = await local_search(
        config=idx.config,
        entities=idx.entities,
        communities=idx.communities,
        community_reports=idx.community_reports,
        text_units=idx.text_units,
        relationships=idx.relationships,
        covariates=idx.covariates,
        community_level=2,
        response_type="Multiple Paragraphs",
        query=query,
    )

    # Extract source file names from context data if available
    sources: list[str] = []
    if isinstance(context, dict):
        for df in context.values():
            if isinstance(df, pd.DataFrame) and "title" in df.columns:
                sources.extend(df["title"].dropna().unique().tolist())

    return {"answer": str(response), "sources": list(set(sources))}
