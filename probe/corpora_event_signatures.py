"""Полный разбор сигнатур событий в модулях объектов по каноническим выгрузкам корпусов.

Вопрос замера: какие формы обработчиков событий модуля объекта реально используются в конфигурациях,
которые в этой же платформе загружаются и работают. Это доказательство того, что наша форма
разрешена (или запрещена) платформой, независимо от того, что о ней говорит p1c.

Отдельно: p1c проверяет сигнатуры событий только по страницам событий УПРАВЛЯЕМОЙ ФОРМЫ
(`p1c/src/p1c/data/platform_arities.py`, `EVENT_SIGNATURES`: `ПередЗаписью: (2, 2)`,
`ПослеЗаписи: (1, 1)`), то есть сигнатура обработчика в модуле объекта метаданных для него —
слепая зона: ни `IDS_RTE_NEVENTPARAMS_NOTMATCH`, ни какая-либо иная находка там не появится.

Платформу замер не запускает.
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

# Имена событий модулей объектов/менеджеров, формы которых мы используем или должны проверить.
EVENT_NAMES = (
    "ПередЗаписью", "ПослеЗаписи", "ПриНовомОбъекте", "ОбработкаПроведения",
    "ОбработкаПередЗаполнением", "ПриСозданииОбъекта", "ПриЧтении", "ПередЧтением",
    "ПослеПроведения", "ПриУстановкеНовогоНомера", "ПередУстановкойНомера",
)

DECLARATION = re.compile(r"^\s*(Процедура|Функция)\s+(\w+)\s*\(([^)]*)\)", re.M)

WANTED_FILES = ("ObjectModule.bsl", "ManagerModule.bsl")
SCAN_LIMIT = 2000


def main(argv: list | None = None) -> int:
    signatures = collections.defaultdict(collections.Counter)
    samples: dict = {}
    files = 0
    for root in ROOTS:
        for path in corpora.wanted_files(root, WANTED_FILES, SCAN_LIMIT):
            files += 1
            try:
                text = path.read_bytes().decode("utf-8-sig", "replace")
            except OSError:
                continue
            relative = corpora.relative(path, ROOTS)
            for match in DECLARATION.finditer(text):
                event = match.group(2)
                if event not in EVENT_NAMES:
                    continue
                parameters = re.sub(r"\s+", " ", match.group(3)).strip()
                signatures[event][parameters] += 1
                key = event + "|" + parameters
                if len(samples.setdefault(key, [])) < 2:
                    samples[key].append(relative)
    print("модулей объекта/менеджера просмотрено:", files)
    for event in EVENT_NAMES:
        counter = signatures.get(event)
        print("\n===", event, "| всего объявлений:", sum(counter.values()) if counter else 0)
        if not counter:
            continue
        for parameters, count in counter.most_common():
            print("   ", count, "x (", parameters, ")")
            for place in samples[event + "|" + parameters][:1]:
                print("        ", place)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
