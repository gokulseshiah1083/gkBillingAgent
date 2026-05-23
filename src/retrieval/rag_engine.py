"""RAG Engine

ChromaDB-backed retrieval over example billing records in `src.data`.

This implementation:
- Indexes `src.data.get_records()` into a local Chroma PersistentClient
- Uses SentenceTransformer embeddings via Chroma's embedding functions
- Supports semantic retrieval for "cases" queries

The LLM generation remains a placeholder.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class _ChromaConfig:
    path: str
    collection_name: str
    embedding_model: str


class RAGEngine:
    def __init__(self, model_config: Dict[str, Any], vector_db_config: Dict[str, Any]):
        self.model_config = model_config
        self.vector_db_config = vector_db_config
        self.logger = logging.getLogger(__name__)

        self._collection = None
        self._indexed = False

    def _get_chroma_config(self) -> _ChromaConfig:
        chroma_cfg = (self.vector_db_config or {}).get("chroma", {})
        path = chroma_cfg.get("path", ".chroma")
        collection_name = chroma_cfg.get("collection_name", "billing-records")
        embedding_model = chroma_cfg.get("embedding_model", "all-MiniLM-L6-v2")
        return _ChromaConfig(path=path, collection_name=collection_name, embedding_model=embedding_model)

    def _ensure_collection(self) -> Any:
        if self._collection is not None:
            return self._collection

        provider = (self.vector_db_config or {}).get("provider", "chroma")
        if provider != "chroma":
            raise ValueError(f"RAGEngine is configured for Chroma but vector_db.provider={provider!r}")

        cfg = self._get_chroma_config()

        import chromadb
        from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

        client = chromadb.PersistentClient(path=cfg.path)

        ef = SentenceTransformerEmbeddingFunction(
            model_name=cfg.embedding_model,
            device="cpu",
            normalize_embeddings=True,
        )

        self._collection = client.get_or_create_collection(
            name=cfg.collection_name,
            embedding_function=ef,
            metadata={"hnsw:space": "cosine"},
        )
        return self._collection

    def _record_to_document(self, record: Dict[str, Any]) -> str:
        # A compact, searchable text representation.
        parts = [
            f"record_id={record.get('record_id')}",
            f"investigation_type={record.get('investigation_type')}",
            f"transaction_id={record.get('transaction_id')}",
            f"pan={record.get('pan')}",
            f"issuer={record.get('issuer')}",
            f"region={record.get('region')}",
            f"country={record.get('country')}",
            f"currency={record.get('currency')}",
            f"amount={record.get('amount')}",
            f"merchant={record.get('merchant')}",
            f"mcc={record.get('mcc')}",
            f"fee_type={record.get('fee_type')}",
            f"fee_amount={record.get('fee_amount')}",
            f"status={record.get('status')}",
            f"anomaly={record.get('anomaly')}",
            f"reason_code={record.get('reason_code')}",
            f"created_at={record.get('created_at')}",
        ]
        return " | ".join(parts)

    async def ensure_indexed(self) -> None:
        if self._indexed:
            return

        collection = self._ensure_collection()

        from src.data import get_records

        records = get_records()

        ids = [r["record_id"] for r in records]
        documents = [self._record_to_document(r) for r in records]
        metadatas = [
            {
                "record_id": r.get("record_id"),
                "investigation_type": r.get("investigation_type"),
                "transaction_id": r.get("transaction_id"),
                "issuer": r.get("issuer"),
                "region": r.get("region"),
                "country": r.get("country"),
                "currency": r.get("currency"),
                "fee_type": r.get("fee_type"),
                "status": r.get("status"),
                "anomaly": bool(r.get("anomaly")),
            }
            for r in records
        ]

        # Clear-and-rebuild on startup to keep demo consistent.
        try:
            collection.delete(ids=ids)
        except Exception:
            pass

        collection.add(ids=ids, documents=documents, metadatas=metadatas)
        self._indexed = True

    async def retrieve(
        self,
        query_type: str,
        query_text: str,
        entities: Any,
        context: Any,
    ) -> Dict[str, Any]:
        await self.ensure_indexed()

        if query_type == "rules":
            # Placeholder: rules retrieval not implemented yet.
            return {"rules": []}

        if query_type == "cases":
            collection = self._ensure_collection()

            n_results = 5
            try:
                n_results = int(getattr(context, "constraints", {}).get("rag_max_results", 5))
            except Exception:
                pass

            res = collection.query(
                query_texts=[query_text],
                n_results=n_results,
                include=["metadatas", "documents", "distances"],
            )

            metadatas = (res.get("metadatas") or [[]])[0]
            documents = (res.get("documents") or [[]])[0]
            distances = (res.get("distances") or [[]])[0]

            cases: List[Dict[str, Any]] = []
            for md, doc, dist in zip(metadatas, documents, distances):
                cases.append(
                    {
                        "summary": doc,
                        "outcome": "N/A",
                        "metadata": md,
                        "distance": dist,
                    }
                )

            return {"cases": cases}

        return {"results": []}

    async def llm_generate(self, prompt: str) -> str:
        return "This is a placeholder response. Connect an approved LLM provider in RAGEngine.llm_generate()."
