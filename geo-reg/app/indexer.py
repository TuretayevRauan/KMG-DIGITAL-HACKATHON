import os
import uuid
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct,
    Filter, FieldCondition, MatchValue,
)

from embeddings import embed_passages, get_embed_dim
import bm25_index

load_dotenv()

qdrant = QdrantClient(
    host=os.getenv("QDRANT_HOST", "localhost"),
    port=int(os.getenv("QDRANT_PORT", 6333)),
)

COLLECTION_NAME = "geo_documents"


def stable_id(chunk_id: str) -> str:
    """Детерминированный UUID из chunk_id.

    Раньше использовался abs(hash(...)) — встроенный hash() для строк
    рандомизируется при каждом запуске процесса (PYTHONHASHSEED), поэтому
    после рестарта те же чанки получали новые ID и дублировались в Qdrant.
    uuid5 стабилен между запусками → повторная индексация перезаписывает.
    """
    return str(uuid.uuid5(uuid.NAMESPACE_URL, chunk_id))


def _create_collection(dim: int):
    qdrant.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
    )
    # Индекс по doc_id — чтобы быстро удалять старую версию документа
    try:
        qdrant.create_payload_index(
            collection_name=COLLECTION_NAME,
            field_name="doc_id",
            field_schema="keyword",
        )
    except Exception:
        pass
    print(f"Коллекция '{COLLECTION_NAME}' создана (dim={dim})")


def ensure_collection_exists():
    """Создаёт коллекцию. Если размер вектора модели изменился
    (например, сменили EMBED_MODEL) — пересоздаёт коллекцию автоматически,
    чтобы не было ошибки несовпадения размерностей."""
    dim = get_embed_dim()
    collections = [c.name for c in qdrant.get_collections().collections]
    if COLLECTION_NAME in collections:
        try:
            info = qdrant.get_collection(COLLECTION_NAME)
            existing_dim = info.config.params.vectors.size
        except Exception:
            existing_dim = None
        if existing_dim is not None and existing_dim != dim:
            print(f"Размер вектора изменился ({existing_dim}->{dim}), пересоздаём коллекцию...")
            qdrant.delete_collection(COLLECTION_NAME)
            _create_collection(dim)
        return
    _create_collection(dim)


def delete_existing_doc(doc_id: str):
    """Удаляет все точки документа перед переиндексацией (защита от дублей)."""
    try:
        qdrant.delete(
            collection_name=COLLECTION_NAME,
            points_selector=Filter(must=[
                FieldCondition(key="doc_id", match=MatchValue(value=doc_id))
            ]),
        )
    except Exception as e:
        print(f"  (предупреждение) не удалось очистить старый doc: {e}")


def index_document(chunks: list[dict], doc_id: str):
    ensure_collection_exists()
    if not chunks:
        print("Нет чанков для индексации")
        return

    # Чистим прошлую версию этого документа (и в Qdrant, и в BM25)
    delete_existing_doc(doc_id)

    # --- ВЕКТОРНЫЙ ИНДЕКС (Qdrant) ---
    texts = [c["text"] for c in chunks]
    print(f"Создаём эмбеддинги для {len(texts)} чанков...")
    embeddings = embed_passages(texts)

    points = [
        PointStruct(
            id=stable_id(chunk["chunk_id"]),
            vector=emb.tolist(),
            payload={
                "chunk_id": chunk["chunk_id"],
                "doc_id": chunk["doc_id"],
                "page": chunk["page"],
                "text": chunk["text"],
                "type": chunk["type"],
            },
        )
        for chunk, emb in zip(chunks, embeddings)
    ]
    # Грузим батчами, чтобы не отправлять один гигантский запрос
    UPSERT_BATCH = 128
    for i in range(0, len(points), UPSERT_BATCH):
        qdrant.upsert(collection_name=COLLECTION_NAME, points=points[i:i + UPSERT_BATCH])
    print(f"Сохранено {len(points)} векторов в Qdrant")

    # --- BM25 (in-memory + дедуп по doc_id) ---
    bm25_index.upsert_doc(doc_id, chunks)

    # --- NER → Neo4j граф (скважины, пласты, связи) ---
    try:
        from ner import extract_and_store
        extract_and_store(chunks, doc_id)
    except Exception as e:
        print(f"  (предупреждение) NER/граф не сработал: {e}")

    print("Индексация завершена!")