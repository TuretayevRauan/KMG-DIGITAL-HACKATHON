"""
Drop-in модуль: визуальный граф знаний + авто-теги документа + диагностика.
НЕ меняет твои файлы. Подключение в app/main.py (2 строки СРАЗУ после app = FastAPI(...)):

    from graph_api import router as graph_router
    app.include_router(graph_router)

Использует уже существующий singleton geo_graph из graph.py (Neo4j),
схема: (Document)-[:MENTIONS]->(Well|Formation), (Well)-[:PENETRATES]->(Formation).
Только чтение — ничего не пишет.

ЕСЛИ граф показывает "недоступен" — открой в браузере:
    http://localhost:8000/graph_debug
там будет точная причина (import / driver / пустой граф).
"""
from fastapi import APIRouter


# Надёжный импорт: работает и при flat-запуске (python app/main.py),
# и при запуске как пакет (uvicorn app.main:app).
geo_graph = None
_import_err = None
for _path in ("graph", "app.graph"):
    try:
        _mod = __import__(_path, fromlist=["geo_graph"])
        geo_graph = getattr(_mod, "geo_graph")
        break
    except Exception as _e:  # noqa
        _import_err = f"{_path}: {_e}"
if geo_graph is None:
    print(f"graph_api: не удалось импортировать geo_graph ({_import_err})")

router = APIRouter()


def _driver():
    return getattr(geo_graph, "driver", None) if geo_graph else None


@router.get("/graph_debug")
def graph_debug():
    """Диагностика: почему граф (не)доступен."""
    info = {
        "import_ok": geo_graph is not None,
        "import_error": _import_err if geo_graph is None else None,
        "driver_ok": _driver() is not None,
        "counts": {},
        "hint": "",
    }
    drv = _driver()
    if not info["import_ok"]:
        info["hint"] = "graph.py / geo_graph не импортируется. Проверь, что graph_api.py лежит в app/ рядом с graph.py."
        return info
    if not drv:
        info["hint"] = "geo_graph есть, но driver=None → Neo4j не запущен. Подними Neo4j (docker) и перезапусти backend."
        return info
    try:
        with drv.session() as s:
            for label, key in (("Document", "docs"), ("Well", "wells"), ("Formation", "formations")):
                info["counts"][key] = s.run(f"MATCH (n:{label}) RETURN count(n) AS c").single()["c"]
            info["counts"]["PENETRATES"] = s.run(
                "MATCH (:Well)-[r:PENETRATES]->(:Formation) RETURN count(r) AS c").single()["c"]
        if info["counts"].get("wells", 0) == 0 and info["counts"].get("formations", 0) == 0:
            info["hint"] = "Neo4j подключён, но граф ПУСТОЙ. Загрузи документ — твой ner/indexer заполнит Well/Formation. Если рёбер PENETRATES=0, проверь, что пайплайн вызывает geo_graph.link_well_to_formation(...)."
        else:
            info["hint"] = "Всё ок — граф должен отображаться в разделе Аналитика."
    except Exception as e:
        info["hint"] = f"Ошибка запроса к Neo4j: {e}"
    return info


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