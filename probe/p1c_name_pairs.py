"""Проверка пар ru/en имён платформы в данных p1c (`platform_name_pairs.py`).

Зачем: `PLATFORM_NAME_PAIRS` объявлен как «Пары имён платформы (EN-канон, RU)», и оба читателя
раскладывают его именно так:

- `p1c/src/p1c/graph/graph.py:50` — `for _en, _ru in PLATFORM_NAME_PAIRS`;
- `p1c/src/p1c/metadata/model.py:396` — `for en_name, ru_name in PLATFORM_NAME_PAIRS`.

При этом, начиная со строки 795, пары выглядят перевёрнутыми и сдвинутыми: `("Заполнить", "UUID")`,
`("УникальныйИдентификатор", "CheckFilling")`, `("ЭтоНовый", "MainWindowModeFullscreenWorkplace")`.
Правильные соответствия в этой же области — `УникальныйИдентификатор` ↔ `UUID`,
`ПроверитьЗаполнение` ↔ `CheckFilling`, `Прочитать` ↔ `Read`, `Записать` ↔ `Write`,
`ЭтоНовый` ↔ `IsNew` — то есть EN-колонка отстаёт от RU-колонки на одну строку.

Замер без платформы: где начинается рассинхрон, сколько пар в нём находится, и какие имена из
наших модулей при таком рассинхроне получат неверный перевод.

Важно: `IsNew`/`ЭтоНовый` — из этой же области. Именно поэтому контур не стал писать в форме
`Если Объект.Новый Тогда`: в 5903 канонических модулях управляемых форм корпусов это обращение
встречается 0 раз (`probe/corpora_default_places.py`).
"""
from __future__ import annotations

import re
import sys

ROOT = __import__("pathlib").Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import paths                                                     # noqa: E402

sys.path.insert(0, paths.load_local(str(ROOT / "local.paths.json")).get("p1c", ""))

CYRILLIC = re.compile(r"[А-Яа-яЁё]")
LATIN = re.compile(r"[A-Za-z]")


def main(argv: list | None = None) -> int:
    from p1c.data.platform_name_pairs import PLATFORM_NAME_PAIRS

    total = len(PLATFORM_NAME_PAIRS)
    flipped = [index for index, (first, second) in enumerate(PLATFORM_NAME_PAIRS)
               if CYRILLIC.search(first) and not CYRILLIC.search(second)]
    correct = total - len(flipped)
    print("пар всего:", total, "| объявлен как (EN, RU)")
    print("пар, где первая часть кириллическая, а вторая латинская (то есть (RU, EN)):",
          len(flipped), "| в обратном порядке:", correct)
    if flipped:
        print("первая такая пара в строке списка", flipped[0], ":",
              PLATFORM_NAME_PAIRS[flipped[0]])
        print("последняя такая пара в строке списка", flipped[-1], ":",
              PLATFORM_NAME_PAIRS[flipped[-1]])
        print("\n== образец рассинхрона (10 пар вокруг первой находки) ==")
        for index in range(max(0, flipped[0] - 2), min(total, flipped[0] + 8)):
            first, second = PLATFORM_NAME_PAIRS[index]
            print("   ", index, "->", (first, second),
                  "| читается как en=" + first + ", ru=" + second)
        print("\n== имена, которые встречаются и как ru, и как en (перевод неоднозначен) ==")
        firsts = {item[0] for item in PLATFORM_NAME_PAIRS}
        seconds = {item[1] for item in PLATFORM_NAME_PAIRS}
        both = sorted(firsts & seconds)
        print("   ", len(both), "имён", both[:12])
    return 1 if flipped else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
