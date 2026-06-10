# -*- coding: utf-8 -*-
"""
retriever.py — гибридный поиск: вектор (Qdrant) + BM25 + RRF fusion.

Улучшения v2:
- Cross-encoder reranking: после RRF-слияния прогоняем топ-20 через
  cross-encoder (ms-marco-MiniLM-L-6-v2, CPU, ~50ms на 20 чанков) —
  точность ответов заметно растёт на геологических запросах.
- RETRIEVAL_CANDIDATES вынесен в env и увеличен до 20 по умолчанию.
- Если cross-encoder недоступен (нет torch) — тихо деградируем к RRF.
- doc_id-фильтр применяется и в BM25 и в Qdrant одинаково.
"""

import os
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

from embeddings import embed_query
import bm25_index

load_dotenv()

qdrant = QdrantClient(
    host=os.getenv("QDRANT_HOST", "localhost"),
    port=int(os.getenv("QDRANT_PORT", 6333)),
)

COLLECTION_NAME = "geo_documents"
CANDIDATES      = int(os.getenv("RETRIEVAL_CANDIDATES", "20"))

# ── Cross-encoder (опционально) ──────────────────────────────────────────
_reranker = None

def _get_reranker():
    global _reranker
    if _reranker is not None:
        return _reranker
    try:
        from sentence_transformers import CrossEncoder
        model_name = os.getenv(
            "RERANKER_MODEL",
            "cross-encoder/ms-marco-MiniLM-L-6-v2"   # маленький, быстрый, CPU
        )
        print(f"Загружаем cross-encoder: {model_name} ...")
        _reranker = CrossEncoder(model_name, max_length=512)
        print("Cross-encoder загружен!")
    except Exception as e:
        print(f"⚠ Cross-encoder недоступен ({e}), используем только RRF")
        _reranker = False   # отмечаем, что пробовали и не вышло
    return _reranker


def search_chunks(question: str, top_k: int = 5, doc_id: str | None = None) -> list[dict]:
    """Гибридный поиск с опциональным reranking."""

    qdrant_filter = None
    if doc_id:
        qdrant_filter = Filter(must=[
            FieldCondition(key="doc_id", match=MatchValue(value=doc_id))
        ])

    # ── Векторный поиск ──────────────────────────────────────────────────
    query_vec = embed_query(question).tolist()
    vector_results = qdrant.search(
        collection_name=COLLECTION_NAME,
        query_vector=query_vec,
        limit=CANDIDATES,
        query_filter=qdrant_filter,
    )
    vector_chunks = [
        {
            "chunk_id": r.payload["chunk_id"],
            "doc_id":   r.payload["doc_id"],
            "page":     r.payload["page"],
            "text":     r.payload["text"],
            "score":    r.score,
            "method":   "vector",
        }
        for r in vector_results
    ]

    # ── BM25 ─────────────────────────────────────────────────────────────
    bm25_chunks = bm25_index.search(question, top_k=CANDIDATES, doc_id=doc_id)

    # ── RRF слияние ──────────────────────────────────────────────────────
    # Берём top_k * 4 кандидатов для reranker, потом режем до top_k
    rerank_pool = min(top_k * 4, CANDIDATES)
    merged = _merge_rrf(vector_chunks, bm25_chunks, top_k=rerank_pool)

    # ── Cross-encoder reranking ──────────────────────────────────────────
    reranker = _get_reranker()
    if reranker and merged:
        pairs = [(question, c["text"]) for c in merged]
        try:
            scores = reranker.predict(pairs)
            for chunk, score in zip(merged, scores):
                chunk["rerank_score"] = float(score)
            merged.sort(key=lambda c: c.get("rerank_score", 0), reverse=True)
            print(f"Rerank: лучший score = {merged[0]['rerank_score']:.3f}")
        except Exception as e:
            print(f"⚠ Reranker ошибка: {e}, оставляем RRF порядок")

    result = merged[:top_k]
    print(f"Найдено {len(result)} чанков (vector={len(vector_chunks)}, bm25={len(bm25_chunks)})")
    return result


def _merge_rrf(vector: list, bm25: list, top_k: int) -> list:
    """Reciprocal Rank Fusion (RRF, K=60)."""
    K = 60
    scores:     dict[str, float] = {}
    chunk_data: dict[str, dict]  = {}

    for rank, chunk in enumerate(vector):
        cid = chunk["chunk_id"]
        scores[cid] = scores.get(cid, 0) + 1 / (K + rank + 1)
        chunk_data[cid] = chunk

    for rank, chunk in enumerate(bm25):
        cid = chunk["chunk_id"]
        scores[cid] = scores.get(cid, 0) + 1 / (K + rank + 1)
        chunk_data.setdefault(cid, chunk)

    sorted_ids = sorted(scores, key=lambda cid: scores[cid], reverse=True)
    result = []
    for cid in sorted_ids[:top_k]:
        chunk = chunk_data[cid].copy()
        chunk["final_score"] = scores[cid]
        result.append(chunk)
    return result