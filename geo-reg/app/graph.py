"""
Drop-in модуль: визуальный граф знаний + авто-теги документа.
НЕ меняет твои файлы. Подключение в app/main.py (2 строки):

    from graph_api import router as graph_router
    app.include_router(graph_router)

Использует уже существующий geo_graph из graph.py (Neo4j),
схема: (Document)-[:MENTIONS]->(Well|Formation), (Well)-[:PENETRATES]->(Formation).
Только чтение — ничего не пишет.
"""
from fastapi import APIRouter

try:
    from graph import geo_graph
except Exception as _e:  # noqa
    print(f"graph_api: graph недоступен: {_e}")
    geo_graph = None

router = APIRouter()


def _driver():
    return getattr(geo_graph, "driver", None) if geo_graph else None


@router.get("/graph_data")
def graph_data(limit: int = 60):
    """Узлы (скважины/пласты) и связи для визуализации."""
    empty = {"available": False, "wells": [], "formations": [], "edges": []}
    drv = _driver()
    if not drv:
        return empty
    try:
        with drv.session() as s:
            wells = [r["n"] for r in s.run(
                "MATCH (w:Well) RETURN w.name AS n LIMIT $l", l=limit)]
            forms = [r["n"] for r in s.run(
                "MATCH (f:Formation) RETURN f.name AS n LIMIT $l", l=limit)]
            edges = [{"well": r["w"], "formation": r["f"], "porosity": r["p"]}
                     for r in s.run(
                         "MATCH (w:Well)-[r:PENETRATES]->(f:Formation) "
                         "RETURN w.name AS w, f.name AS f, r.porosity AS p LIMIT $l",
                         l=limit)]
        return {"available": True, "wells": wells, "formations": forms, "edges": edges}
    except Exception as e:
        print(f"graph_data error: {e}")
        return empty


@router.get("/doc_tags")
def doc_tags(doc_id: str):
    """Авто-теги: какие скважины и пласты упомянуты в документе."""
    out = {"available": False, "wells": [], "formations": []}
    drv = _driver()
    if not drv:
        return out
    try:
        with drv.session() as s:
            rows = s.run(
                "MATCH (d:Document {doc_id:$d})-[:MENTIONS]->(n) "
                "RETURN labels(n)[0] AS t, n.name AS name", d=doc_id)
            for r in rows:
                if r["t"] == "Well":
                    out["wells"].append(r["name"])
                elif r["t"] == "Formation":
                    out["formations"].append(r["name"])
        out["available"] = True
        return out
    except Exception as e:
        print(f"doc_tags error: {e}")
        return out
