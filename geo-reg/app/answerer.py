import httpx
import os
import time
import random
from dotenv import load_dotenv
from graph import geo_graph

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Актуальные рабочие модели OpenRouter (проверено через /api/v1/models).
# Бесплатные идут первыми, в конце — дешёвый платный fallback на случай 429
# по всем free-моделям (стоит копейки, но гарантирует ответ на демо/хакатоне).
FREE_MODELS = [
    "qwen/qwen3-next-80b-a3b-instruct:free",   # быстрая, хороша для RU + RAG
    "openai/gpt-oss-120b:free",
    "z-ai/glm-4.5-air:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "openai/gpt-oss-20b:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
    # --- платный fallback (можно убрать, если не нужен) ---
    "google/gemini-2.5-flash",
]


def call_model(model: str, system_prompt: str, user_prompt: str) -> str:
    response = httpx.post(
        OPENROUTER_URL,
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:8000",
        },
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "max_tokens": 1500,
            "temperature": 0.1,
        },
        timeout=40.0,
    )
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"]


def generate_answer(question: str, chunks: list[dict]) -> dict:
    if not chunks:
        return {
            "text": "Не удалось найти релевантную информацию в документах.",
            "citations": [],
            "model": None,
        }

    if not OPENROUTER_API_KEY:
        return {
            "text": "Ошибка: OPENROUTER_API_KEY не задан в .env файле.",
            "citations": [],
            "model": None,
        }

    context_parts = []
    for i, chunk in enumerate(chunks):
        context_parts.append(
            f"[Фрагмент {i+1}] Документ: {chunk['doc_id']}, Страница: {chunk['page']}\n"
            f"{chunk['text']}"
        )

    graph_context = geo_graph.get_graph_context(question)
    context = "\n\n---\n\n".join(context_parts) + graph_context

    system_prompt = """Ты — интеллектуальный ассистент геолога нефтяной компании.

ПРАВИЛА:
1. Отвечай ТОЛЬКО на основе предоставленных фрагментов документов.
2. Для каждого факта в ответе указывай источник в формате [doc_id:страница].
3. Если информации недостаточно — честно скажи об этом, НЕ выдумывай данные.
4. Отвечай на русском языке.
5. Будь точным и конкретным — геологи работают с числами."""

    user_prompt = f"""Вопрос геолога: {question}

Доступные фрагменты документов:
{context}

Дай ответ на вопрос, указывая источники для каждого факта."""

    # Цитаты готовим заранее — отдадим их даже если все модели упадут,
    # чтобы пользователь хотя бы видел найденные фрагменты.
    citations = [
        {
            "doc_id": chunk["doc_id"],
            "page": chunk["page"],
            "text_preview": chunk["text"][:150] + "...",
        }
        for chunk in chunks
    ]

    answer_text = "Все модели временно недоступны (rate limit). Попробуйте через минуту."

    for model in FREE_MODELS:
        # Один короткий ретрай при 429, затем сразу к следующей модели.
        # Никаких длинных sleep(20/40/60) — иначе фронтенд ловит timeout.
        for attempt in range(2):
            try:
                answer_text = call_model(model, system_prompt, user_prompt)
                print(f"Ответ получен от модели: {model}")
                return {"text": answer_text, "citations": citations, "model": model}
            except httpx.HTTPStatusError as e:
                code = e.response.status_code
                if code == 429:
                    if attempt == 0:
                        wait = 2 + random.random()
                        print(f"Модель {model} перегружена (429), короткий ретрай через {wait:.1f}с...")
                        time.sleep(wait)
                        continue
                    print(f"Модель {model} всё ещё перегружена, пробую следующую...")
                    break
                if code == 404:
                    print(f"Модель {model} недоступна (404), пробую следующую...")
                    break
                print(f"Ошибка HTTP {code} у {model}: {e.response.text[:200]}")
                break
            except httpx.TimeoutException:
                print(f"Таймаут у {model}, пробую следующую...")
                break
            except Exception as e:
                print(f"Ошибка при вызове {model}: {e}")
                break

    return {"text": answer_text, "citations": citations, "model": None}