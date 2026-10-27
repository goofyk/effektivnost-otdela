"""Конвенции модулей объекта по каноническим выгрузкам: как пишут то, что мы написали неявно.

Замер нужен, чтобы решить, что из диагностики p1c `IDS_STX_VAR_NOTDECLARED` — находка, а что ложная
находка, и как правильно переписать наши модули объекта:

- `Движения.` неявно против `ЭтотОбъект.Движения`;
- неявное присваивание стандартного реквизита (`Дата = …`) против `ЭтотОбъект.Дата = …`;
- как обращаются к описанию справочника (`Description`) в модуле объекта;
- тернарная ФУНКЦИЯ `?(условие, еслиДа, еслиНет)` против инфиксного `условие ? да : нет`.
"""
from __future__ import annotations

import collections
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import corpora                                                   # noqa: E402

ROOTS = corpora.dumps()

WANTED_FILE_NAMES = ("ObjectModule.bsl", "ManagerModule.bsl")
SCAN_LIMIT = 2000

CHECKS = {
    "Движения. неявно": re.compile(r"(?<![\w.])Движения\."),
    "ЭтотОбъект.Движения": re.compile(r"ЭтотОбъект\.Движения"),
    "ЭтотОбъект.Дата =": re.compile(r"ЭтотОбъект\.Дата\s*="),
    "неявное Дата = / Время = / Ссылка =": re.compile(r"^\s*(Дата|Время|Ссылка)\s*=[^=]"),
    "ЭтотОбъект. Описание (Description)": re.compile(r"ЭтотОбъект\.Description"),
    "неявное обращение к Description": re.compile(r"(?<![\w.])Description\b"),
    "тернарная функция ?(": re.compile(r"(?<![\w])\?\s*\("),
    "инфиксный тернарный оператор ` ? ` ... ` : `": re.compile(r"[\w\)\]]\s+\?\s+[^()\n]{2,60}:"),
    "ЭтотОбъект. в модуле объекта (всего)": re.compile(r"ЭтотОбъект\."),
}


def main() -> int:
    counts = collections.Counter()
    samples: dict = {}
    files = 0
    for root in ROOTS:
        base = pathlib.Path(root)
        for path in base.rglob("*"):
            if not path.is_file() or path.name not in ("ObjectModule.bsl", "ManagerModule.bsl"):
                continue
            files += 1
            try:
                text = path.read_bytes().decode("utf-8-sig", "replace")
            except OSError:
                continue
            relative = path.relative_to(base).as_posix()
            for name, pattern in CHECKS.items():
                for line_no, line in enumerate(text.splitlines(), 1):
                    if not pattern.search(line):
                        continue
                    counts[name] += 1
                    if len(samples.setdefault(name, [])) < 3:
                        samples[name].append(relative + ":" + str(line_no) + " "
                                             + line.strip()[:130])
    print("файлов модулей объектов/менеджеров просмотрено:", files)
    for name in CHECKS:
        print("\n###", name, "—", counts[name])
        for line in samples.get(name, []):
            print("   ", line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
