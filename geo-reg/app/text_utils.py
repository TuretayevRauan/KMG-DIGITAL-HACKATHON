"""
Токенизация для BM25 с учётом русской морфологии.

Раньше было `text.lower().split()` — пунктуация прилипала к словам
("пласт." != "пласт"), а словоформы "пласт"/"пласта"/"пластов" считались
разными токенами. Здесь: regex-токенизация + русский стеммер Портера
(без внешних зависимостей) → BM25 матчит словоформы.
"""
import re

_TOKEN_RE = re.compile(r"[a-zA-Zа-яёА-ЯЁ0-9]+", re.UNICODE)

# Короткие стоп-слова, которые только шумят в BM25
_STOPWORDS = {
    "и", "в", "во", "не", "что", "он", "на", "я", "с", "со", "как", "а",
    "то", "все", "она", "так", "его", "но", "да", "ты", "к", "у", "же",
    "вы", "за", "бы", "по", "только", "ее", "мне", "было", "вот", "от",
    "the", "a", "an", "of", "to", "in", "is", "on", "for", "and", "or",
}


# --- Русский стеммер Портера (компактная реализация, без зависимостей) ---
_VOWEL = "аеиоуыэюя"
_PERFECTIVE_GERUND = re.compile(
    r"(ив|ивши|ившись|ыв|ывши|ывшись)$|((?<=[ая])(в|вши|вшись))$")
_ADJECTIVE = re.compile(
    r"(ее|ие|ые|ое|ими|ыми|ей|ий|ый|ой|ем|им|ым|ом|его|ого|ему|ому|их|ых"
    r"|ую|юю|ая|яя|ою|ею)$")
_PARTICIPLE = re.compile(
    r"(ивш|ывш|ующ)$|((?<=[ая])(ем|нн|вш|ющ|щ))$")
_REFLEXIVE = re.compile(r"(ся|сь)$")
_VERB = re.compile(
    r"(ила|ыла|ена|ейте|уйте|ите|или|ыли|ей|уй|ил|ыл|им|ым|ен|ило|ыло|ено"
    r"|ят|ует|уют|ит|ыт|ены|ить|ыть|ишь|ую|ю)$|"
    r"((?<=[ая])(ла|на|ете|йте|ли|й|л|ем|н|ло|но|ет|ют|ны|ть|ешь|нно))$")
_NOUN = re.compile(
    r"(а|ев|ов|ие|ье|е|иями|ями|ами|еи|ии|и|ией|ей|ой|ий|й|иям|ям|ием|ем"
    r"|ам|ом|о|у|ах|иях|ях|ы|ь|ию|ью|ю|ия|ья|я)$")
_DERIVATIONAL = re.compile(r"(ост|ость)$")
_SUPERLATIVE = re.compile(r"(ейш|ейше)$")
_I = re.compile(r"и$")
_NN = re.compile(r"нн$")
_SOFT = re.compile(r"ь$")


def _rv(word: str) -> int:
    """Позиция RV — после первой гласной."""
    m = re.search(r"[аеиоуыэюя]", word)
    return m.start() + 1 if m else len(word)


def stem_ru(word: str) -> str:
    word = word.replace("ё", "е")
    rv_start = _rv(word)
    pre, rv = word[:rv_start], word[rv_start:]

    # Шаг 1
    new_rv = _PERFECTIVE_GERUND.sub("", rv)
    if new_rv != rv:
        rv = new_rv
    else:
        rv = _REFLEXIVE.sub("", rv)
        for pat in (_ADJECTIVE, _PARTICIPLE, _VERB, _NOUN):
            new_rv = pat.sub("", rv)
            if new_rv != rv:
                rv = new_rv
                break

    # Шаг 2: убрать "и"
    rv = _I.sub("", rv)
    # Шаг 3: деривация
    rv = _DERIVATIONAL.sub("", rv)
    # Шаг 4
    if _NN.search(rv):
        rv = rv[:-1]
    else:
        rv = _SUPERLATIVE.sub("", rv)
        rv = _NN.sub("н", rv) if _NN.search(rv) else rv
    rv = _SOFT.sub("", rv)

    return pre + rv


def tokenize(text: str, do_stem: bool = True) -> list[str]:
    tokens = [t.lower() for t in _TOKEN_RE.findall(text)]
    out = []
    for t in tokens:
        if t in _STOPWORDS or len(t) < 2:
            continue
        out.append(stem_ru(t) if do_stem and re.search(r"[а-яё]", t) else t)
    return out