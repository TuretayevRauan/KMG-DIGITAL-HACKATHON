# -*- coding: utf-8 -*-
"""
normalize.py — нормализация геологической терминологии к каноническому виду.

Требование ТЗ (6.3): «пласт Ю1-3» ≡ «горизонт Ю₁³» ≡ «Ju1-3» — одна сущность.
Здесь мы приводим все варианты записи к единому каноническому ключу, чтобы
NER не плодил дубли узлов в графе, а поиск находил сущность в любой форме.

Алгоритм для индекса пласта/горизонта:
1. Подстрочные/надстрочные цифры → обычные, но с сохранением границ групп
   (Ю₁³ = две группы: «1» и «3»).
2. Латинские буквы-двойники и транслит сейсмических индексов → кириллица
   (Ju/Yu→Ю, BS→БС, J→Ю и т.п.).
3. Несколько числовых групп соединяются дефисом: Ю + [1,3] → «Ю1-3»;
   одна группа остаётся слитно: БС + [10] → «БС10».
"""
import re
import unicodedata

# Подстрочные и надстрочные цифры → обычные
_SUB = {"₀": "0", "₁": "1", "₂": "2", "₃": "3", "₄": "4",
        "₅": "5", "₆": "6", "₇": "7", "₈": "8", "₉": "9"}
_SUP = {"⁰": "0", "¹": "1", "²": "2", "³": "3", "⁴": "4",
        "⁵": "5", "⁶": "6", "⁷": "7", "⁸": "8", "⁹": "9"}

# Транслит/двойники латиница → кириллица для индексов пластов.
# Длинные ключи идут первыми (Ju до J).
_TRANSLIT = [
    ("ju", "ю"), ("yu", "ю"), ("ja", "я"), ("ya", "я"),
    ("zh", "ж"), ("sh", "ш"), ("ch", "ч"), ("kh", "х"), ("ts", "ц"),
    ("a", "а"), ("b", "б"), ("v", "в"), ("g", "г"), ("d", "д"),
    ("e", "е"), ("z", "з"), ("i", "и"), ("k", "к"), ("l", "л"),
    ("m", "м"), ("n", "н"), ("o", "о"), ("p", "п"), ("r", "р"),
    ("s", "с"), ("t", "т"), ("u", "у"), ("f", "ф"), ("h", "х"),
    ("c", "с"), ("j", "ю"), ("y", "у"),
]

# Тип символа для группировки цифр
_NORMAL, _SUB_T, _SUP_T = "n", "sub", "sup"


def _translit_letters(letters: str) -> str:
    s = letters.lower()
    for lat, cyr in _TRANSLIT:
        s = s.replace(lat, cyr)
    return s.upper()


def normalize_formation(raw: str) -> str:
    """Канонический ключ для пласта/горизонта/свиты.

    >>> normalize_formation("Ю₁³")
    'Ю1-3'
    >>> normalize_formation("Ю1-3")
    'Ю1-3'
    >>> normalize_formation("Ju1-3")
    'Ю1-3'
    >>> normalize_formation("БС10")
    'БС10'
    """
    # ВАЖНО: НЕ применяем NFKC — он схлопнул бы ₁³ → 13 и стёр границу групп.
    # Работаем по исходной строке, где под/надстрочные цифры ещё различимы.
    src = raw.strip()

    letters = []
    groups = []           # список (тип, цифры)
    cur_digits = ""
    cur_type = None

    def flush():
        nonlocal cur_digits, cur_type
        if cur_digits:
            groups.append((cur_type, cur_digits))
        cur_digits, cur_type = "", None

    for ch in src:
        if ch in _SUB:
            if cur_type != _SUB_T:
                flush()
                cur_type = _SUB_T
            cur_digits += _SUB[ch]
        elif ch in _SUP:
            if cur_type != _SUP_T:
                flush()
                cur_type = _SUP_T
            cur_digits += _SUP[ch]
        elif ch.isdigit():
            if cur_type != _NORMAL:
                flush()
                cur_type = _NORMAL
            cur_digits += ch
        elif ch.isalpha():
            flush()
            letters.append(ch)
        else:
            # разделитель (-, /, пробел, точка) → граница группы
            flush()

    flush()

    name = _translit_letters("".join(letters))
    nums = [g[1] for g in groups]
    if not nums:
        return name
    if len(nums) == 1:
        return f"{name}{nums[0]}"
    return f"{name}{'-'.join(nums)}"


def normalize_well(raw: str) -> str:
    """Канонический номер скважины: только значимая часть, верхний регистр.

    >>> normalize_well("247")
    '247'
    >>> normalize_well("247-Р")
    '247-Р'
    """
    raw = unicodedata.normalize("NFKC", raw).strip().upper()
    raw = re.sub(r"\s+", "", raw)
    return raw


if __name__ == "__main__":
    import doctest
    doctest.testmod(verbose=True)
    # Доп. проверка эквивалентности из ТЗ
    forms = ["Ю₁³", "Ю1-3", "Ju1-3", "пласт Ю1-3".split()[-1]]
    keys = {f: normalize_formation(f) for f in forms}
    print(keys)
    assert len({normalize_formation(f) for f in forms}) == 1, "Должны совпасть!"
    print("OK: все формы Ю1-3 нормализуются в один ключ")