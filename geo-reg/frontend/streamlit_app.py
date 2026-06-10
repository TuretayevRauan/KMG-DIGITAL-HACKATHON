import io
import re
import time
from datetime import datetime

import httpx
import streamlit as st

try:
    import pandas as pd
except Exception:
    pd = None

API_URL = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="KMG GeoHub — интеллектуальная документация",
    page_icon="🛢️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ──────────────────────────────────────────────────────────────────────────────
#  СТИЛИ
# ──────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500&display=swap');
:root {
    --accent:#2DD4BF; --accent-2:#38BDF8; --bg:#0B0F14; --card:#11161D;
    --card-2:#161D26; --border:#222B36; --text:#E6EDF3; --muted:#8B98A8;
    --good:#22C55E; --warn:#F59E0B;
}
html, body, [class*="css"], .stApp { font-family:'Inter',sans-serif; }
.stApp { background:
    radial-gradient(900px 500px at 12% -8%, #134e4a22 0%, transparent 60%),
    radial-gradient(800px 500px at 100% 0%, #0ea5e91a 0%, transparent 55%), var(--bg); }
.block-container { padding-top:1.4rem; max-width:1220px; }
#MainMenu, footer, header { visibility:hidden; }

.hero { position:relative; overflow:hidden;
    background:linear-gradient(125deg,#0d2b2a 0%,#10343a 45%,#0d1b2a 100%);
    border:1px solid var(--border); border-radius:22px; padding:24px 30px;
    margin-bottom:16px; box-shadow:0 20px 50px -28px #000; }
.hero::after{ content:""; position:absolute; inset:-2px;
    background:radial-gradient(420px 160px at 85% 0%, #2DD4BF33, transparent 70%);
    animation:glow 7s ease-in-out infinite alternate; pointer-events:none; }
@keyframes glow { from{opacity:.5} to{opacity:1} }
.hero-top { display:flex; align-items:center; gap:14px; }
.logo { width:50px; height:50px; border-radius:14px; flex:0 0 auto; display:grid;
    place-items:center; font-size:1.6rem;
    background:linear-gradient(135deg,var(--accent),var(--accent-2));
    box-shadow:0 8px 24px -6px var(--accent); }
.hero h1 { font-size:1.5rem; margin:0; font-weight:800; letter-spacing:-.4px;
    background:linear-gradient(90deg,#fff,#bdeee7); -webkit-background-clip:text;
    -webkit-text-fill-color:transparent; }
.hero .brandline { color:var(--accent); font-size:.8rem; font-weight:600; margin-top:1px; }
.kpis { display:flex; gap:10px; flex-wrap:wrap; margin-top:14px; position:relative; z-index:2; }
.kpi { background:#0c1117aa; border:1px solid var(--border); border-radius:13px;
    padding:8px 15px; min-width:92px; backdrop-filter:blur(6px); }
.kpi .v { font-size:1.2rem; font-weight:800; font-family:'JetBrains Mono',monospace; }
.kpi .v.ac { color:var(--accent); }
.kpi .l { font-size:.68rem; color:var(--muted); text-transform:uppercase; letter-spacing:.5px; }
.dot { display:inline-block; width:8px; height:8px; border-radius:50%; margin-right:6px; }
.dot.on { background:var(--good); animation:pulse 1.8s infinite; }
.dot.off{ background:#ef4444; }
@keyframes pulse { 0%{box-shadow:0 0 0 0 #22C55E55} 70%{box-shadow:0 0 0 6px #22C55E00} 100%{box-shadow:0 0 0 0 #22C55E00} }

.meta { display:flex; gap:8px; flex-wrap:wrap; margin:6px 0 2px; }
.badge { display:inline-flex; align-items:center; gap:5px; font-size:.74rem; font-weight:600;
    padding:3px 10px; border-radius:999px; border:1px solid var(--border);
    background:var(--card-2); color:var(--muted); }
.badge.ok { color:var(--good); border-color:#22C55E44; background:#22C55E14; }
.badge.warn { color:var(--warn); border-color:#F59E0B44; background:#F59E0B14; }
.badge.model{ color:var(--accent-2); border-color:#38BDF844; background:#38BDF814;
    font-family:'JetBrains Mono',monospace; }
.tag { display:inline-block; font-size:.74rem; font-weight:600; padding:3px 10px; margin:3px 4px 0 0;
    border-radius:999px; border:1px solid var(--border); }
.tag.well { color:#fbbf24; border-color:#fbbf2444; background:#fbbf2414; }
.tag.form { color:#a78bfa; border-color:#a78bfa44; background:#a78bfa14; }
.cite { display:inline-block; font-family:'JetBrains Mono',monospace; font-size:.78rem;
    font-weight:700; color:var(--accent); background:#2DD4BF1f; border:1px solid #2DD4BF55;
    border-radius:7px; padding:0 6px; margin:0 1px; }

.src-card { background:linear-gradient(180deg,var(--card),#0e141b);
    border:1px solid var(--border); border-left:3px solid var(--accent);
    border-radius:13px; padding:12px 16px; margin:9px 0; transition:.18s; }
.src-card:hover { border-left-color:var(--accent-2); transform:translateX(2px); }
.src-head { display:flex; align-items:center; gap:8px; flex-wrap:wrap; }
.chip-doc { font-weight:700; color:var(--accent); font-size:.84rem;
    font-family:'JetBrains Mono',monospace; word-break:break-all; }
.chip-page { font-size:.72rem; font-weight:700; color:#0b0f14;
    background:var(--accent); border-radius:6px; padding:1px 8px; }
.src-prev { color:var(--muted); font-size:.85rem; margin-top:6px; line-height:1.5; }
.relbar { height:5px; border-radius:4px; background:#1b2430; margin-top:9px; overflow:hidden; }
.relbar > i { display:block; height:100%;
    background:linear-gradient(90deg,var(--accent),var(--accent-2)); }
.relrow { display:flex; align-items:center; gap:8px; margin-top:8px; }
.relrow .lbl { font-size:.68rem; color:var(--muted); text-transform:uppercase; white-space:nowrap; }
.gcard { background:var(--card); border:1px solid var(--border); border-radius:11px;
    padding:9px 11px; text-align:center; }
.gcard .gv { font-size:1.15rem; font-weight:800; color:var(--accent);
    font-family:"JetBrains Mono",monospace; }
.gcard .gl { font-size:.66rem; color:var(--muted); text-transform:uppercase; margin-top:1px; }

.stButton>button { border-radius:11px; font-weight:600; border:1px solid var(--border);
    background:var(--card); color:var(--text); transition:.15s; }
.stButton>button:hover { border-color:var(--accent); color:var(--accent); }
.stButton>button[kind="primary"] { border-color:var(--accent);
    background:linear-gradient(135deg,var(--accent),#1fb6a3); color:#062a26; }
[data-testid="stChatMessage"] { background:transparent; border-radius:14px; }
[data-testid="stSidebar"] { background:#0c1117; border-right:1px solid var(--border); }
.welcome { text-align:center; padding:34px 16px 8px; color:var(--muted); }
.welcome .big { font-size:2.3rem; margin-bottom:6px; }
.welcome h3 { color:var(--text); margin:.2rem 0; font-weight:700; }
hr { border-color:var(--border); }
</style>
""", unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────────────
#  API-ХЕЛПЕРЫ (всё с graceful-фолбэком)
# ──────────────────────────────────────────────────────────────────────────────
def backend_stats():
    try:
        r = httpx.get(f"{API_URL}/stats", timeout=5.0)
        if r.status_code == 200:
            d = r.json()
            return True, d.get("docs_count", 0), d.get("chunks_count"), d.get("docs", [])
    except Exception:
        pass
    try:
        docs = httpx.get(f"{API_URL}/docs_list", timeout=5.0).json().get("docs", [])
        return True, len(docs), None, docs
    except Exception:
        return False, 0, None, []


def get_json(path, params=None):
    try:
        r = httpx.get(f"{API_URL}{path}", params=params, timeout=8.0)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


def ask_backend(question, doc_id, top_k=5):
    t0 = time.time()
    r = httpx.post(f"{API_URL}/ask",
                   json={"question": question, "doc_id": doc_id, "top_k": top_k},
                   timeout=120.0)
    data = r.json()
    data["_latency"] = time.time() - t0
    return data


def log_analytics(question, doc_id, result):
    rec = {
        "ts": datetime.now(),
        "question": question,
        "doc": doc_id or "все",
        "latency": result.get("_latency"),
        "grounded": bool(result.get("grounded", result.get("citations"))),
        "cited_docs": [c["doc_id"] for c in (result.get("citations") or [])],
    }
    st.session_state.setdefault("analytics", []).append(rec)


CITE_RE = re.compile(r"\[([^\[\]:]+):\s*(\d+)\]")


def highlight_citations(text):
    """Оборачивает [doc:page] в кликабельно-выглядящий бейдж."""
    return CITE_RE.sub(lambda m: f'<span class="cite">[{m.group(1)}:{m.group(2)}]</span>', text or "")


def stream_text(placeholder, text):
    """Печатает ответ посимвольно (typing-эффект), как в ChatGPT."""
    if not text:
        placeholder.markdown("")
        return
    step = 1 if len(text) < 600 else 4  # длинные ответы — быстрее
    shown = ""
    for i in range(0, len(text), step):
        shown = text[:i + step]
        placeholder.markdown(highlight_citations(shown) + " ▌", unsafe_allow_html=True)
        time.sleep(0.008)
    placeholder.markdown(highlight_citations(text), unsafe_allow_html=True)


def render_citation_buttons(citations, kp):
    """Кнопки по найденным цитатам: клик разворачивает превью фрагмента."""
    if not citations:
        return
    st.caption("🔗 Цитаты (клик — превью):")
    cols = st.columns(min(4, len(citations)))
    for idx, c in enumerate(citations):
        label = f"📎 {c['doc_id']}:{c['page']}"
        if cols[idx % len(cols)].button(label, key=f"{kp}_cite{idx}",
                                        use_container_width=True):
            cur = st.session_state.get(f"{kp}_open")
            st.session_state[f"{kp}_open"] = None if cur == idx else idx
    oi = st.session_state.get(f"{kp}_open")
    if oi is not None and oi < len(citations):
        c = citations[oi]
        prev = (c.get("text_preview") or "").strip()
        st.info(f"**{c['doc_id']} · стр. {c['page']}**\n\n…{prev}")


# ─── рендер ───
def render_sources(citations):
    if not citations:
        return
    with st.expander(f"📎 Источники ({len(citations)})", expanded=False):
        for c in citations:
            prev = (c.get("text_preview") or "").strip()
            sc = c.get("score")
            relbar = ""
            if sc is not None:
                try:
                    pct = max(6, min(100, int(float(sc) * 100)))
                    relbar = (f'<div class="relrow"><span class="lbl">релевантность</span>'
                              f'<div class="relbar" style="flex:1"><i style="width:{pct}%"></i></div></div>')
                except Exception:
                    relbar = ""
            st.markdown(
                f'<div class="src-card">'
                f'<div class="src-head"><span class="chip-doc">{c["doc_id"]}</span>'
                f'<span class="chip-page">стр. {c["page"]}</span></div>'
                f'<div class="src-prev">…{prev}</div>{relbar}'
                f'</div>', unsafe_allow_html=True)


def render_meta(grounded, model, latency, n_src):
    g = ('<span class="badge ok">✓ С опорой на источники</span>' if grounded
         else '<span class="badge warn">⚠ Без цитат — проверьте факты</span>')
    m = f'<span class="badge model">⚙ {model}</span>' if model else ''
    lat = f'<span class="badge">⏱ {latency:.1f}с</span>' if latency else ''
    src = f'<span class="badge">📎 {n_src} фрагм.</span>' if n_src else ''
    st.markdown(f'<div class="meta">{g}{m}{lat}{src}</div>', unsafe_allow_html=True)


def render_tags(doc_id):
    """Авто-теги: скважины/пласты из графа (если есть graph_api)."""
    t = get_json("/doc_tags", {"doc_id": doc_id})
    if not t or not t.get("available"):
        return
    wells, forms = t.get("wells", []), t.get("formations", [])
    if not wells and not forms:
        return
    chips = "".join(f'<span class="tag well">🛢 {w}</span>' for w in wells[:12])
    chips += "".join(f'<span class="tag form">🪨 {f}</span>' for f in forms[:12])
    st.markdown(f"**🏷️ Найдено в документе:**<br>{chips}", unsafe_allow_html=True)


def build_answer_pdf(question, answer, citations):
    """PDF одного ответа со ссылками. Кириллица через системный TTF."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    except Exception:
        return None
    import os
    font = "Helvetica"
    for path in [r"C:\Windows\Fonts\arial.ttf", r"C:\Windows\Fonts\ARIALUNI.TTF",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                 "/Library/Fonts/Arial.ttf"]:
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont("CyrFont", path))
                font = "CyrFont"
                break
            except Exception:
                pass
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=20 * mm, bottomMargin=18 * mm)
    ss = getSampleStyleSheet()
    h = ParagraphStyle("h", parent=ss["Title"], fontName=font, fontSize=16, textColor="#0d9488")
    sub = ParagraphStyle("sub", parent=ss["Normal"], fontName=font, fontSize=9, textColor="#666")
    q = ParagraphStyle("q", parent=ss["Normal"], fontName=font, fontSize=11, textColor="#111",
                       spaceAfter=6, leading=15)
    body = ParagraphStyle("b", parent=ss["Normal"], fontName=font, fontSize=10.5, leading=15)
    cite = ParagraphStyle("c", parent=ss["Normal"], fontName=font, fontSize=9, textColor="#0d9488")

    def esc(t):
        return (t or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    flow = [Paragraph("KMG GeoHub — ответ системы", h),
            Paragraph(datetime.now().strftime("%d.%m.%Y %H:%M"), sub), Spacer(1, 10),
            Paragraph(f"<b>Вопрос:</b> {esc(question)}", q),
            Paragraph(f"<b>Ответ:</b> {esc(answer)}", body), Spacer(1, 10)]
    if citations:
        flow.append(Paragraph("<b>Источники:</b>", body))
        for c in citations:
            flow.append(Paragraph(f"• {esc(c['doc_id'])} · стр. {c['page']}", cite))
    doc.build(flow)
    buf.seek(0)
    return buf.getvalue()


# ──────────────────────────────────────────────────────────────────────────────
#  HERO + KPI
# ──────────────────────────────────────────────────────────────────────────────
online, docs_count, chunks_count, docs = backend_stats()
gstats = get_json("/graph_stats") if online else None
analytics = st.session_state.get("analytics", [])

status = ('<span class="dot on"></span>Онлайн' if online
          else '<span class="dot off"></span>Офлайн')
chunks_html = (f'<div class="kpi"><div class="v ac">{chunks_count}</div>'
               f'<div class="l">Чанков</div></div>') if chunks_count is not None else ''
graph_html = ''
if gstats and gstats.get("available"):
    graph_html = (f'<div class="kpi"><div class="v">{gstats.get("nodes", 0)}</div>'
                  f'<div class="l">🕸 Узлов</div></div>')
q_html = (f'<div class="kpi"><div class="v ac">{len(analytics)}</div>'
          f'<div class="l">Запросов</div></div>') if analytics else ''

hero_html = (
    '<div class="hero">'
    '<div class="hero-top">'
    '<div class="logo">🛢️</div>'
    '<div><h1>KMG GeoHub</h1>'
    '<div class="brandline">интеллектуальная система геологической документации</div></div>'
    '</div>'
    '<div class="kpis">'
    f'<div class="kpi"><div class="v">{docs_count}</div><div class="l">Документов</div></div>'
    f'{chunks_html}{graph_html}{q_html}'
    f'<div class="kpi"><div class="v" style="font-size:.95rem;padding-top:4px">{status}</div>'
    '<div class="l">Статус</div></div>'
    '</div></div>'
)
st.markdown(hero_html, unsafe_allow_html=True)
if not online:
    st.warning("Backend недоступен. Запусти: `python app/main.py` (порт 8000).")


# ──────────────────────────────────────────────────────────────────────────────
#  САЙДБАР: загрузка, область поиска, навигация, настройки
# ──────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 📄 Загрузка документа")
    uploaded_file = st.file_uploader(
        "Выберите файл",
        type=["pdf", "docx", "txt", "md", "csv", "tsv", "xlsx", "xlsm", "xls",
              "pptx", "png", "jpg", "jpeg", "tif", "tiff", "bmp", "webp"],
        help="PDF, Word, Excel, PowerPoint, текст/CSV и картинки (сканы — через OCR)")
    if uploaded_file and st.button("⚙️ Обработать документ", type="primary",
                                   use_container_width=True):
        with st.spinner("Парсим и индексируем…"):
            try:
                r = httpx.post(f"{API_URL}/upload",
                               files={"file": (uploaded_file.name, uploaded_file.getvalue())},
                               timeout=600.0)
                result = r.json()
                if result.get("status") == "успешно":
                    st.success(f"✅ Готово · чанков: {result['chunks_count']}")
                    st.session_state.active_doc = uploaded_file.name
                    st.session_state.last_uploaded = uploaded_file.name
                    st.balloons()
                else:
                    st.error(f"Ошибка: {result.get('error', result)}")
            except Exception as e:
                st.error(f"Ошибка подключения: {e}")

    if st.session_state.get("last_uploaded"):
        render_tags(st.session_state["last_uploaded"])

    if docs:
        st.markdown("---")
        st.markdown("### 🎯 Область поиска")
        ALL = "🌐 Все документы"
        options = [ALL] + docs
        active = st.session_state.get("active_doc")
        idx = options.index(active) if active in options else 0
        choice = st.radio("Поиск только здесь:", options, index=idx,
                          label_visibility="collapsed")
        st.session_state.query_doc = None if choice == ALL else choice

    st.markdown("---")
    st.markdown("### 🧭 Разделы")
    section = st.radio("Раздел", ["💬 Чат", "⚖️ Сравнение", "📊 Аналитика", "📝 История"],
                       label_visibility="collapsed")

    if gstats and gstats.get("available"):
        st.markdown("---")
        st.markdown("### 🕸 Граф знаний")
        g1, g2, g3 = st.columns(3)
        g1.markdown(f'<div class="gcard"><div class="gv">{gstats.get("documents",0)}</div>'
                    f'<div class="gl">📄 Док</div></div>', unsafe_allow_html=True)
        g2.markdown(f'<div class="gcard"><div class="gv">{gstats.get("wells",0)}</div>'
                    f'<div class="gl">🛢 Скв</div></div>', unsafe_allow_html=True)
        g3.markdown(f'<div class="gcard"><div class="gv">{gstats.get("formations",0)}</div>'
                    f'<div class="gl">🪨 Пласт</div></div>', unsafe_allow_html=True)
        st.caption(f"🔗 Связей: **{gstats.get('relationships',0)}**")

    st.markdown("---")
    with st.expander("⚙️ Настройки поиска"):
        st.session_state.top_k = st.slider("Фрагментов (top-k)", 3, 12,
                                            st.session_state.get("top_k", 5))
    st.caption("KMG GeoHub · open-weight RAG")


# ──────────────────────────────────────────────────────────────────────────────
#  РАЗДЕЛ: ЧАТ
# ──────────────────────────────────────────────────────────────────────────────
st.session_state.setdefault("messages", [])
EXAMPLES = ["Какая пористость пласта БС10?", "Признаки органического происхождения нефти?",
            "Перечисли изученные месторождения", "Какие методы поиска залежей описаны?"]


def render_chat():
    if not st.session_state.messages:
        st.markdown(
            '<div class="welcome"><div class="big">🔎</div>'
            '<h3>Задайте вопрос по вашим документам</h3>'
            '<div>Загрузите файл слева и спросите что угодно — ответ придёт с источниками.</div>'
            '</div>', unsafe_allow_html=True)
        cols = st.columns(2)
        for i, ex in enumerate(EXAMPLES):
            if cols[i % 2].button(f"💡 {ex}", key=f"ex_{i}", use_container_width=True):
                st.session_state._pending = ex
                st.rerun()

    for mi, msg in enumerate(st.session_state.messages):
        avatar = "🛢️" if msg["role"] == "assistant" else "🧑‍🔬"
        with st.chat_message(msg["role"], avatar=avatar):
            if msg["role"] == "assistant":
                st.markdown(highlight_citations(msg["content"]), unsafe_allow_html=True)
                render_meta(msg.get("grounded"), msg.get("model"),
                            msg.get("latency"), len(msg.get("citations") or []))
                render_citation_buttons(msg.get("citations"), f"m{mi}")
                render_sources(msg.get("citations"))
                pdf = build_answer_pdf(msg.get("question", ""), msg["content"],
                                       msg.get("citations"))
                if pdf:
                    st.download_button("📄 Скачать ответ (PDF)", pdf,
                                       file_name=f"kmg_answer_{mi+1}.pdf",
                                       mime="application/pdf", key=f"pdf_{mi}")
            else:
                st.markdown(msg["content"])

    question = st.session_state.pop("_pending", None) or \
        st.chat_input("Например: Какая пористость пласта БС10?")
    if question:
        st.session_state.messages.append({"role": "user", "content": question})
        with st.chat_message("user", avatar="🧑‍🔬"):
            st.markdown(question)
        with st.chat_message("assistant", avatar="🛢️"):
            try:
                with st.spinner("Ищу в документах и формирую ответ…"):
                    res = ask_backend(question, st.session_state.get("query_doc"),
                                      st.session_state.get("top_k", 5))
                ans = res.get("answer", "Нет ответа")
                cits = res.get("citations", [])
                stream_text(st.empty(), ans)  # typing-эффект
                render_meta(res.get("grounded", bool(cits)), res.get("model"),
                            res.get("_latency"), len(cits))
                render_sources(cits)
                log_analytics(question, st.session_state.get("query_doc"), res)
                st.session_state.messages.append({
                    "role": "assistant", "content": ans, "citations": cits,
                    "grounded": res.get("grounded", bool(cits)),
                    "model": res.get("model"), "latency": res.get("_latency"),
                    "question": question})
                st.rerun()
            except Exception as e:
                st.error(f"Ошибка: {e}")


# ──────────────────────────────────────────────────────────────────────────────
#  РАЗДЕЛ: СРАВНЕНИЕ (один вопрос — два документа рядом)
# ──────────────────────────────────────────────────────────────────────────────
def render_compare():
    st.markdown("### ⚖️ Сравнение ответов по двум документам")
    if len(docs) < 2:
        st.info("Нужно минимум 2 загруженных документа для сравнения.")
        return
    c1, c2 = st.columns(2)
    doc_a = c1.selectbox("Документ A", docs, index=0)
    doc_b = c2.selectbox("Документ B", docs, index=1)
    q = st.text_input("Вопрос для обоих документов",
                      placeholder="Напр.: Какая пористость основного пласта?")
    if st.button("🔍 Сравнить", type="primary") and q:
        with st.spinner("Спрашиваю оба документа…"):
            ra = ask_backend(q, doc_a, st.session_state.get("top_k", 5))
            rb = ask_backend(q, doc_b, st.session_state.get("top_k", 5))
        col_a, col_b = st.columns(2)
        for col, doc_id, r in [(col_a, doc_a, ra), (col_b, doc_b, rb)]:
            with col:
                st.markdown(f"#### 📄 {doc_id}")
                st.markdown(r.get("answer", "Нет ответа"))
                cits = r.get("citations", [])
                render_meta(r.get("grounded", bool(cits)), r.get("model"),
                            r.get("_latency"), len(cits))
                render_sources(cits)


# ──────────────────────────────────────────────────────────────────────────────
#  РАЗДЕЛ: АНАЛИТИКА (графики + live-метрики + визуальный граф)
# ──────────────────────────────────────────────────────────────────────────────
def render_analytics():
    st.markdown("### 📊 Аналитика сессии")
    a = st.session_state.get("analytics", [])
    if not a:
        st.info("Пока нет запросов. Задайте вопросы в разделе 💬 Чат — здесь появятся метрики.")
    else:
        total = len(a)
        avg_lat = sum((x["latency"] or 0) for x in a) / total
        grounded_pct = 100 * sum(1 for x in a if x["grounded"]) / total
        m1, m2, m3 = st.columns(3)
        m1.metric("⚡ Средн. скорость ответа", f"{avg_lat:.1f} с")
        m2.metric("✓ Ответов с цитатами", f"{grounded_pct:.0f}%")
        m3.metric("💬 Всего запросов", total)

        if pd is not None:
            cited = [d for x in a for d in x["cited_docs"]]
            if cited:
                st.markdown("#### 🏆 Топ документов по цитированию")
                df = pd.Series(cited).value_counts().head(8)
                st.bar_chart(df)
            st.markdown("#### 🕒 Активность по времени")
            times = pd.to_datetime([x["ts"] for x in a])
            ser = pd.Series(1, index=times).resample("1min").sum()
            st.line_chart(ser)

    # Визуальный граф
    st.markdown("---")
    st.markdown("### 🗺️ Граф знаний: скважины и пласты")

    # Демо-данные (используются, если Neo4j ещё не подключён/пуст) —
    # чтобы раздел всегда выглядел наглядно на презентации.
    DEMO_WELLS = ["Скв. Тенгиз-1", "Скв. Кашаган-3", "Скв. Узень-12", "Скв. Жетыбай-7"]
    DEMO_FORMS = ["Горизонт КТ-I", "Горизонт КТ-II", "Пласт Ю-1", "Пласт М-II"]
    DEMO_EDGES = [
        {"well": "Скв. Тенгиз-1",  "formation": "Горизонт КТ-I",  "porosity": 12.4},
        {"well": "Скв. Тенгиз-1",  "formation": "Горизонт КТ-II", "porosity": 9.8},
        {"well": "Скв. Кашаган-3", "formation": "Горизонт КТ-I",  "porosity": 14.1},
        {"well": "Скв. Узень-12",  "formation": "Пласт Ю-1",      "porosity": 21.6},
        {"well": "Скв. Жетыбай-7", "formation": "Пласт Ю-1",      "porosity": 19.3},
        {"well": "Скв. Жетыбай-7", "formation": "Пласт М-II",     "porosity": 17.0},
    ]

    gd = get_json("/graph_data")
    is_demo = False
    if gd and gd.get("available") and (gd.get("wells") or gd.get("formations")):
        wells, forms, edges = gd.get("wells", []), gd.get("formations", []), gd.get("edges", [])
    else:
        wells, forms, edges, is_demo = DEMO_WELLS, DEMO_FORMS, DEMO_EDGES, True

    dot = ['digraph G { rankdir=LR; bgcolor="transparent"; node [style=filled, fontname="Inter", fontcolor="#0b0f14"];']
    for w in wells[:40]:
        dot.append(f'"{w}" [shape=ellipse, fillcolor="#fbbf24"];')
    for f in forms[:40]:
        dot.append(f'"{f}" [shape=box, fillcolor="#a78bfa"];')
    for e in edges[:80]:
        attrs = 'color="#2DD4BF"'
        if e.get("porosity") is not None:
            attrs += f', label="{e["porosity"]}%", fontcolor="#8B98A8"'
        dot.append(f'"{e["well"]}" -> "{e["formation"]}" [{attrs}];')
    dot.append("}")
    st.graphviz_chart("\n".join(dot), use_container_width=True)
    st.caption("🟡 скважины · 🟣 пласты · стрелка = вскрывает (с пористостью)")
    if is_demo:
        st.caption("ℹ️ Демо-вид графа. Реальные связи появятся после подключения Neo4j "
                   "и загрузки документов со скважинами/пластами.")


# ──────────────────────────────────────────────────────────────────────────────
#  РАЗДЕЛ: ИСТОРИЯ
# ──────────────────────────────────────────────────────────────────────────────
def render_history():
    st.markdown("### 📝 История сессии")
    msgs = st.session_state.get("messages", [])
    pairs = [m for m in msgs]
    if not pairs:
        st.info("История пуста — задайте вопросы в разделе 💬 Чат.")
        return
    md_lines = ["# KMG GeoHub — история сессии\n"]
    for m in msgs:
        if m["role"] == "user":
            md_lines.append(f"## 🧑‍🔬 {m['content']}\n")
        else:
            md_lines.append(f"**🛢️ Ответ:** {m['content']}\n")
            for c in (m.get("citations") or []):
                md_lines.append(f"> 📎 {c['doc_id']} · стр. {c['page']}")
            md_lines.append("")
    c1, c2 = st.columns([1, 1])
    c1.download_button("💾 Скачать историю (.md)", "\n".join(md_lines),
                       file_name="kmg_geohub_history.md", mime="text/markdown",
                       use_container_width=True)
    if c2.button("🗑️ Очистить сессию", use_container_width=True):
        st.session_state.messages = []
        st.session_state.analytics = []
        st.rerun()
    st.markdown("---")
    for m in msgs:
        if m["role"] == "user":
            st.markdown(f"**🧑‍🔬 Вопрос:** {m['content']}")
        else:
            with st.expander("🛢️ Ответ", expanded=False):
                st.markdown(m["content"])
                render_sources(m.get("citations"))


# ──────────────────────────────────────────────────────────────────────────────
#  РОУТИНГ
# ──────────────────────────────────────────────────────────────────────────────
if section.startswith("💬"):
    render_chat()
elif section.startswith("⚖️"):
    render_compare()
elif section.startswith("📊"):
    render_analytics()
else:
    render_history()
