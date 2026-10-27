"""Конвенции BSL и форм по корпусам shipped-конфигураций: чем проверять наши рукописные модули.

Вопросы, на которые отвечает только массовый просмотр реальных конфигураций (платформу не запускаем):

1. разрешено ли в модуле объекта обращаться к реквизитам и стандартным свойствам без префикса
   (`Движения.…`, `Дата = …`, `ЗначениеЗаполнено(Сотрудник)`) — от этого зависит, является
   `IDS_STX_VAR_NOTDECLARED` у p1c находкой или ложной находкой;
2. как в управляемых формах пишут `DataPath` стандартного реквизита «Наименование»:
   `Объект.Наименование` или `Объект.Description`;
3. какие сигнатуры обработчиков событий реально используются (сравнение с нашим модулем).
"""
from __future__ import annotations

import collections
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import corpora                                                   # noqa: E402

ROOTS = corpora.configurator_dumps()

WANTED_FILE_NAMES = ("ObjectModule.bsl", "ManagerModule.bsl", "Module.bsl", "Form.xml")
SCAN_LIMIT = 1200

CHECKS = {
    "модуль объекта: Движения.<регистр>": re.compile(r"\bДвижения\."),
    "модуль объекта: ЗначениеЗаполнено(<ИмяРеквизита>)": re.compile(
        r"ЗначениеЗаполнено\(\s*([А-Яа-яA-Za-z][\w]*)\s*\)"),
    "модуль объекта: ЭтотОбъект.": re.compile(r"\bЭтотОбъект\."),
    "модуль объекта: implicit Дата = / Часы = ": re.compile(r"^\s*(Дата|Часы|Сумма)\s*="),
    "форма: DataPath Объект.Наименование": re.compile(r"<DataPath>Объект\.Наименование<"),
    "форма: DataPath Объект.Description": re.compile(r"<DataPath>Объект\.Description<"),
}


def main() -> int:
    counts = collections.Counter()
    names = collections.Counter()
    samples: dict = {}
    files = 0
    for root in ROOTS:
        base = pathlib.Path(root)
        for path in corpora.wanted_files(base, WANTED_FILE_NAMES, SCAN_LIMIT):
            files += 1
            try:
                text = path.read_bytes().decode("utf-8-sig", "replace")
            except OSError:
                continue
            relative = path.relative_to(base).as_posix()
            for name, pattern in CHECKS.items():
                if not pattern.search(text):
                    continue
                for line_no, line in enumerate(text.splitlines(), 1):
                    match = pattern.search(line)
                    if not match:
                        continue
                    counts[name] += 1
                    if match.groups():
                        names[match.group(1)] += 1
                    if len(samples.setdefault(name, [])) < 3:
                        samples[name].append(relative + ":" + str(line_no) + " "
                                             + line.strip()[:120])
    print("файлов просмотрено:", files, "| выборка ограничена", SCAN_LIMIT,
          "файлов на корпус на имя")
    for name in CHECKS:
        print("\n###", name, "—", counts[name])
        for line in samples.get(name, []):
            print("   ", line)
    print("\n=== имена аргументов ЗначениеЗаполнено(...) в модулях ---")
    for name, count in names.most_common(14):
        print("   ", count, "x", name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
