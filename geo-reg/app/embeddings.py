# -*- coding: utf-8 -*-
"""
embeddings.py — загрузка и использование модели эмбеддингов.

Улучшения v2:
- По умолчанию multilingual-e5-small (быстрее на CPU).
- Для максимального качества: EMBED_MODEL=intfloat/multilingual-e5-large в .env
- Коллекция Qdrant пересоздаётся автоматически при смене модели.
"""

import os
from sentence_transformers import SentenceTransformer

EMBED_MODEL_NAME = os.getenv("EMBED_MODEL", "intfloat/multilingual-e5-small")
EMBED_BATCH_SIZE = int(os.getenv("EMBED_BATCH_SIZE", "64"))

# Все ядра CPU
try:
    import torch
    torch.set_num_threads(os.cpu_count() or 4)
except Exception:
    pass

_embedder: SentenceTransformer | None = None


def get_embedder() -> SentenceTransformer:
    global _embedder
    if _embedder is None:
        print(f"Загружаем модель эмбеддингов: {EMBED_MODEL_NAME} ...")
        _embedder = SentenceTransformer(EMBED_MODEL_NAME)
        print("Готово!")
    return _embedder


def get_embed_dim() -> int:
    return get_embedder().get_sentence_embedding_dimension()


def embed_passages(texts: list[str], batch_size: int | None = None):
    """Эмбеддинги для индексации (префикс 'passage:' по стандарту e5)."""
    return get_embedder().encode(
        ["passage: " + t for t in texts],
        batch_size=batch_size or EMBED_BATCH_SIZE,
        show_progress_bar=True,
        normalize_embeddings=True,
        convert_to_numpy=True,
    )


def embed_query(text: str):
    """Эмбеддинг поискового запроса (префикс 'query:')."""
    return get_embedder().encode(
        "query: " + text,
        normalize_embeddings=True,
        convert_to_numpy=True,
    )


# Обратная совместимость: старый импорт EMBED_DIM как константы модуля
def __getattr__(name):
    if name == "EMBED_DIM":
        return get_embed_dim()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")