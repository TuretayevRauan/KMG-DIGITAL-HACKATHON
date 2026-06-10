# -*- coding: utf-8 -*-
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import os
import tempfile
from dotenv import load_dotenv

from parser import parse_document
from indexer import index_document
from retriever import search_chunks
from answerer import generate_answer
from graph import geo_graph
import bm25_index

load_dotenv()

app = FastAPI(title="ГеоAI API", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health ─────────────────────────────────────────────────────────────────
@app.get("/")
def root():
    return {"status": "работает", "version": "2.0"}


# ── Documents list ─────────────────────────────────────────────────────────
@app.get("/docs_list")
def docs_list():
    return {"docs": bm25_index.list_docs()}


# ── Graph stats ────────────────────────────────────────────────────────────
@app.get("/graph_stats")
def graph_stats():
    if not geo_graph.is_available():
        return {"available": False}
    stats = geo_graph.get_stats()
    stats["available"] = True
    return stats


# ── Upload & index ─────────────────────────────────────────────────────────
@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    suffix = os.path.splitext(file.filename)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        chunks = parse_document(tmp_path, doc_id=file.filename)
        if not chunks:
            return {
                "status": "ошибка",
                "doc_id": file.filename,
                "chunks_count": 0,
                "error": "Не удалось извлечь текст. Возможно, скан без текстового слоя.",
            }
        index_document(chunks, doc_id=file.filename)
        return {"status": "успешно", "doc_id": file.filename, "chunks_count": len(chunks)}
    except Exception as e:
        import traceback; traceback.print_exc()
        return {"status": "ошибка", "doc_id": file.filename, "chunks_count": 0, "error": f"{type(e).__name__}: {e}"}
    finally:
        os.unlink(tmp_path)


# ── Ask ─────────────────────────────────────────────────────────────────
@app.post("/ask")
async def ask_question(body: dict):
    question = body.get("question", "")
    doc_id   = body.get("doc_id") or None
    if not question:
        return {"error": "Вопрос не может быть пустым"}

    chunks = search_chunks(question, top_k=5, doc_id=doc_id)
    answer = generate_answer(question, chunks)
    return {
        "question":  question,
        "answer":    answer["text"],
        "citations": answer["citations"],
        "grounded":  answer.get("grounded", True),
    }


# ── NEW: Search (возвращает только фрагменты без LLM) ──────────────────
class SearchRequest(BaseModel):
    query: str
    doc_id: str | None = None
    top_k: int = 8

@app.post("/search")
def search_raw(req: SearchRequest):
    """Гибридный поиск без генерации ответа — только фрагменты с оценкой."""
    chunks = search_chunks(req.query, top_k=req.top_k, doc_id=req.doc_id)
    return {
        "query":   req.query,
        "results": [
            {
                "rank":     i + 1,
                "doc_id":   c["doc_id"],
                "page":     c["page"],
                "score":    round(c.get("score", 0), 4),
                "preview":  c["text"][:300],
            }
            for i, c in enumerate(chunks)
        ],
    }


# ── NEW: Summary — краткое резюме документа ───────────────────────────
@app.get("/summary/{doc_id:path}")
def doc_summary(doc_id: str):
    """Генерирует краткое саммари документа на основе первых чанков."""
    chunks = search_chunks(
        "Кратко опиши содержание документа: основные объекты, скважины, пласты, выводы",
        top_k=8,
        doc_id=doc_id,
    )
    if not chunks:
        return {"summary": "Документ не найден или пуст."}
    answer = generate_answer(
        "Дай краткое структурированное резюме документа: что за документ, "
        "какие скважины и пласты упоминаются, какие ключевые числа и выводы.",
        chunks,
    )
    return {"doc_id": doc_id, "summary": answer["text"]}


# ── NEW: Delete doc — удалить документ из индекса ─────────────────────
@app.delete("/doc/{doc_id:path}")
def delete_doc(doc_id: str):
    """Удаляет документ из BM25 индекса."""
    try:
        removed = bm25_index.remove_doc(doc_id)
        return {"status": "удалён" if removed else "не найден", "doc_id": doc_id}
    except AttributeError:
        return {"status": "ошибка", "detail": "remove_doc не реализован в bm25_index.py"}


# ── Eval ───────────────────────────────────────────────────────────────────
@app.get("/eval")
def run_evaluation():
    from metrics import run_eval
    return {"results": run_eval()}

from graph_api import router as graph_router
app.include_router(graph_router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)