# -*- coding: utf-8 -*-
"""
vision.py — описание графики из документов (ТЗ 6.2, тип чанка figure_caption).

Из PDF извлекаются встроенные растровые изображения (карты, разрезы,
каротажные планшеты, фото керна). Open-weight VLM формирует текстовое
описание, пригодное для индексации: что изображено, какие объекты подписаны
(скважины, пласты, изолинии), какие числовые значения видны (отметки, масштабы).

Описания сохраняются как отдельные чанки type="figure_caption" и индексируются
наравне с текстом — поиск находит ответ «по картинке».

Включается флагом ENABLE_VISION=1 (по умолчанию выключено, чтобы не жечь
вызовы VLM на каждом документе). Модели берутся из OCR_MODELS (open-weight).
"""
import os
import base64
import fitz
import httpx
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
ENABLE_VISION      = os.getenv("ENABLE_VISION", "0") == "1"
MIN_IMG_BYTES      = int(os.getenv("VISION_MIN_IMG_BYTES", "8000"))   # пропускаем мелкие иконки/логотипы
MAX_IMAGES         = int(os.getenv("VISION_MAX_IMAGES", "40"))        # потолок вызовов на документ

VISION_MODELS = (
    [m.strip() for m in os.getenv("OCR_MODELS", "").split(",") if m.strip()]
    or [
        "qwen/qwen3-vl-8b-instruct",
        "qwen/qwen3-vl-30b-a3b-instruct",
        "nvidia/nemotron-nano-12b-v2-vl:free",
        "google/gemma-4-31b-it:free",
    ]
)

VISION_PROMPT = """Ты — геолог. Опиши это изображение из геологического отчёта для поиска.
Ответь кратко и по делу на русском:
1. Тип графики (карта/геологический разрез/каротажный планшет/фото керна/схема/график).
2. Подписанные объекты: скважины, пласты, горизонты, изолинии, разломы.
3. Числовые значения: отметки глубин, масштаб, координаты, значения свойств.
Если текст/подписи нечитаемы — так и напиши. Ничего не выдумывай."""


def _img_to_b64(image_bytes: bytes) -> str:
    return base64.b64encode(image_bytes).decode("utf-8")


def _describe(image_b64: str) -> str:
    if not OPENROUTER_API_KEY:
        return ""
    content = [
        {"type": "text", "text": VISION_PROMPT},
        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}},
    ]
    for model in VISION_MODELS:
        try:
            r = httpx.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}",
                         "Content-Type": "application/json",
                         "HTTP-Referer": "http://localhost:8000"},
                json={"model": model, "max_tokens": 600,
                      "messages": [{"role": "user", "content": content}]},
                timeout=90.0,
            )
            if r.status_code in (404, 402, 403, 429, 503):
                continue
            r.raise_for_status()
            txt = r.json()["choices"][0]["message"]["content"].strip()
            if txt:
                return txt
        except Exception as e:
            print(f"  vision {model}: {e}")
            continue
    return ""


def extract_figure_captions(file_path: str, doc_id: str) -> list[dict]:
    """Возвращает список чанков figure_caption для всех картинок в PDF."""
    if not ENABLE_VISION:
        return []
    chunks: list[dict] = []
    try:
        doc = fitz.open(file_path)
    except Exception as e:
        print(f"  vision: не открыть {file_path}: {e}")
        return []

    count = 0
    for page_num in range(len(doc)):
        if count >= MAX_IMAGES:
            break
        for img_index, img in enumerate(doc[page_num].get_images(full=True)):
            if count >= MAX_IMAGES:
                break
            xref = img[0]
            try:
                pix = fitz.Pixmap(doc, xref)
                if pix.n - pix.alpha >= 4:          # CMYK → RGB
                    pix = fitz.Pixmap(fitz.csRGB, pix)
                png = pix.tobytes("png")
            except Exception:
                continue
            if len(png) < MIN_IMG_BYTES:
                continue
            desc = _describe(_img_to_b64(png))
            count += 1
            if not desc:
                continue
            chunks.append({
                "chunk_id": f"{doc_id}_p{page_num+1}_fig{img_index}",
                "doc_id":   doc_id,
                "page":     page_num + 1,
                "text":     f"[Изображение, стр. {page_num+1}] {desc}",
                "type":     "figure_caption",
            })
    doc.close()
    print(f"Vision: {len(chunks)} описаний изображений в '{doc_id}'")
    return chunks