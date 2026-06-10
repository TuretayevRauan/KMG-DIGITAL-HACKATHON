# app/metrics.py — модуль оценки качества RAG-системы (раздел 6.7)
import time
from retriever import search_chunks
from answerer import generate_answer

TEST_QUESTIONS = [
    "Какова пористость пласта БС10?",
    "Какие скважины вскрыли баженовскую свиту?",
    "Какова нефтенасыщенность пласта?",
    "Какова глубина залегания продуктивного горизонта?",
    "Какой дебит нефти у скважин на данном месторождении?",
]


def run_eval(questions: list[str] = TEST_QUESTIONS) -> list[dict]:
    results = []
    for q in questions:
        t0 = time.time()
        try:
            chunks = search_chunks(q, top_k=5)
            answer = generate_answer(q, chunks)
            elapsed = round(time.time() - t0, 2)
            has_citations = len(answer.get("citations", [])) > 0
            results.append({
                "question":     q,
                "answer_len":   len(answer.get("text", "")),
                "citations":    len(answer.get("citations", [])),
                "has_sources":  has_citations,
                "time_sec":     elapsed,
                "status":       "ok",
            })
            print(f"Q: {q[:50]}... | цитат: {len(answer.get('citations', []))} | {elapsed}с")
        except Exception as e:
            elapsed = round(time.time() - t0, 2)
            results.append({
                "question":  q,
                "answer_len": 0,
                "citations":  0,
                "has_sources": False,
                "time_sec":   elapsed,
                "status":     f"error: {e}",
            })
            print(f"Q: {q[:50]}... | ОШИБКА: {e}")
    return results