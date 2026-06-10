# -*- coding: utf-8 -*-
# app/ner.py — извлечение геологических сущностей + нормализация (ТЗ 6.3).
# Вызывается из indexer.py после индексации чанков.
import re
from graph import geo_graph
from normalize import normalize_formation, normalize_well

# Паттерны для геологических сущностей
WELL_PATTERNS = [
    r"скважин[аеыу]?\s*(?:№|N|No\.?)?\s*(\d+[\w\-]*)",
    r"скв\.?\s*(?:№|N|No\.?)?\s*(\d+[\w\-]*)",
]
FORMATION_PATTERNS = [
    r"пласт[аеуов]*\s+([A-Za-zА-Яа-яЁё]{1,3}[\d\-₀-₉⁰-⁹]+)",
    r"горизонт[аеуов]*\s+([A-Za-zА-Яа-яЁё]{1,3}[\d\-₀-₉⁰-⁹]+)",
    r"свит[аеыу]\s+([A-Za-zА-Яа-яЁё]+)",
]


def extract_and_store(chunks: list[dict], doc_id: str):
    """Извлекает скважины и пласты из чанков, НОРМАЛИЗУЕТ и сохраняет в Neo4j.

    Нормализация (ТЗ 6.3): «Ю₁³» ≡ «Ю1-3» ≡ «Ju1-3» приводятся к одному
    каноническому ключу → в графе один узел, без дублей-синонимов.
    """
    geo_graph.add_document(doc_id)
    total_wells, total_formations = set(), set()

    for chunk in chunks:
        text = chunk["text"]
        wells, formations = set(), set()

        for pat in WELL_PATTERNS:
            for m in re.finditer(pat, text, re.IGNORECASE):
                key = normalize_well(m.group(1))
                if key:
                    wells.add(key)
        for pat in FORMATION_PATTERNS:
            for m in re.finditer(pat, text, re.IGNORECASE):
                key = normalize_formation(m.group(1))
                if key and any(c.isdigit() for c in key) or key.isalpha():
                    formations.add(key)

        for w in wells:
            geo_graph.add_well(w, doc_id)
        for f in formations:
            geo_graph.add_formation(f, doc_id)
        # Связь скважина → пласт, если оба упомянуты в одном чанке
        for w in wells:
            for f in formations:
                geo_graph.link_well_to_formation(w, f)

        total_wells |= wells
        total_formations |= formations

    print(f"NER: найдено {len(total_wells)} скважин, {len(total_formations)} пластов "
          f"(нормализовано) в '{doc_id}'")