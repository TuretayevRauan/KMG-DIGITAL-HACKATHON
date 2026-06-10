"""
BM25-индекс с кэшем в памяти и дедупликацией по doc_id.

Что чинит:
- Раньше каждый /ask грузил весь pickle с диска и распаковывал корпус.
  Теперь индекс держится в памяти процесса (грузится 1 раз), а так как
  indexer и retriever импортируют ЭТОТ ЖЕ модуль в одном процессе FastAPI —
  после загрузки документа поиск сразу видит свежие чанки без перечтения диска.
- Раньше повторная загрузка файла дублировала чанки (`all_chunks.extend`).
  Теперь upsert_doc() сначала удаляет старые чанки этого doc_id → дублей нет.
"""
import os
import pickle
from rank_bm25 import BM25Okapi

from text_utils import tokenize

BM25_INDEX_PATH = os.getenv("BM25_INDEX_PATH", "bm25_index.pkl")

_chunks: list[dict] | None = None
_bm25: BM25Okapi | None = None


def _load() -> None:
    """Однократная загрузка с диска + построение индекса."""
    global _chunks, _bm25
    if _chunks is not None:
        return
    if os.path.exists(BM25_INDEX_PATH):
        with open(BM25_INDEX_PATH, "rb") as f:
            data = pickle.load(f)
        _chunks = data.get("chunks", [])
    else:
        _chunks = []
    _rebuild()


def _rebuild() -> None:
    global _bm25
    if _chunks:
        _bm25 = BM25Okapi([tokenize(c["text"]) for c in _chunks])
    else:
        _bm25 = None


def _save() -> None:
    # Храним только чанки — BM25 пересобирается при загрузке (всегда свежий).
    with open(BM25_INDEX_PATH, "wb") as f:
        pickle.dump({"chunks": _chunks}, f)


def upsert_doc(doc_id: str, new_chunks: list[dict]) -> int:
    """Заменяет все чанки документа doc_id новыми (идемпотентно, без дублей)."""
    global _chunks
    _load()
    _chunks = [c for c in _chunks if c["doc_id"] != doc_id]
    _chunks.extend(new_chunks)
    _rebuild()
    _save()
    print(f"BM25 индекс обновлён: {len(_chunks)} чанков (дубли удалены)")
    return len(_chunks)


def total_chunks() -> int:
    """Сколько всего чанков в индексе (для KPI во фронте)."""
    _load()
    return len(_chunks or [])


def list_docs() -> list[str]:
    """Список уникальных doc_id в индексе (для выбора во фронте)."""
    _load()
    seen, out = set(), []
    for c in _chunks or []:
        if c["doc_id"] not in seen:
            seen.add(c["doc_id"])
            out.append(c["doc_id"])
    return out


def search(question: str, top_k: int, doc_id: str | None = None) -> list[dict]:
    _load()
    if not _bm25 or not _chunks:
        return []
    scores = _bm25.get_scores(tokenize(question))
    order = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
    out = []
    for i in order:
        if scores[i] <= 0:
            continue
        c = _chunks[i]
        if doc_id and c["doc_id"] != doc_id:
            continue
        out.append({
            "chunk_id": c["chunk_id"],
            "doc_id": c["doc_id"],
            "page": c["page"],
            "text": c["text"],
            "score": float(scores[i]),
            "method": "bm25",
        })
        if len(out) >= top_k:
            break
    return out