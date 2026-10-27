"""Канонический способ задать значения по умолчанию новому объекту: форма, метаданные или модуль.

Найденные дефекты нашей конфигурации (`probe/our_event_handlers.py` + `/CheckModules` гейта gate-04):

- в модулях объекта справочника и документа объявлены `Процедура ПриНовомОбъекте()`. У классов
  `CatalogObject` и `DocumentObject` такого события в официальных данных нет, и в 15 055 канонических
  `.bsl` корпусов имя `ПриНовомОбъекте` не встречается ни разу (`probe/corpora_default_values.py`).
  Значит обработчик не вызывается: значения по умолчанию не появляются, а `ГрейдыСпециалистов.Специалист`
  внутри него платформа отметила как «Переменная не определена» (код 101).
- в модуле объекта справочника `ПередЗаписью(Отказ, Замечание, Параметр)` — против официальной
  `CatalogObject.BeforeWrite` (1 параметр `<Отказ>`) и против канона корпусов `(Отказ)` 867 встреч.

Замер unanswered-вопроса: где канонические конфигурации всё-таки задают значения новым объектам.

1. `Объект.Новый` в модулях управляемых форм (`Ext/Form/Module.bsl`) — тот же канон, что и
   `ПриСозданииНаСервере` (12 478 встреч).
2. Как называется узел значений по умолчанию в XML метаданных (искать не точное имя, а любое имя
   узла, содержащее `DefaultValue`).
3. Как канонически обращаться к предопределённому значению перечисления из модуля (`Перечисления.`).

Платформу замер не запускает, исходник не изменяет.
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

SCAN_LIMIT = 3000

BSL_CHECKS = {
    "Объект.Новый (модули управляемых форм)": re.compile(r"\bОбъект\.Новый\b"),
    "Если Объект.Новый Тогда": re.compile(r"Если\s+Объект\.Новый\s+Тогда"),
    "Перечисления.<Имя> (обращение к перечислению)": re.compile(r"\bПеречисления\.[А-Яа-я\w]+"),
    "ЗначениеПоУмолчанию(": re.compile(r"\bЗначениеПоУмолчанию\s*\("),
}

XML_ELEMENT = re.compile(r"<(/?[A-Za-z][A-Za-z0-9_]*(?:DefaultValue|DefaultValues|PredefinedData)[A-Za-z0-9_]*)")

SAMPLE_LIMIT = 3


def main(argv: list | None = None) -> int:
    counts = collections.Counter()
    samples: dict = {}
    xml_names = collections.Counter()
    xml_samples: dict = {}
    form_modules = 0
    xml_files = 0

    for root in ROOTS:
        for path in corpora.wanted_files(root, ("Module.bsl",), SCAN_LIMIT):
            if "Forms" not in path.parts:
                continue
            form_modules += 1
            text = path.read_bytes().decode("utf-8-sig", "replace")
            for name, pattern in BSL_CHECKS.items():
                matches = list(pattern.finditer(text))
                if not matches:
                    continue
                counts[name] += len(matches)
                if len(samples.setdefault(name, [])) < SAMPLE_LIMIT:
                    match = matches[0]
                    line_start = text.rfind("\n", 0, match.start()) + 1
                    line_end = text.find("\n", match.end())
                    samples[name].append({"where": corpora.relative(path, ROOTS),
                                          "line": re.sub(r"\s+", " ", text[line_start:max(line_end, line_start)][:180])})
        for path in corpora.wanted_files(root, ("*.xml",), SCAN_LIMIT):
            xml_files += 1
            text = path.read_bytes().decode("utf-8-sig", "replace")
            for match in XML_ELEMENT.finditer(text):
                tag = match.group(1).lstrip("/")
                xml_names[tag] += 1
                if len(xml_samples.setdefault(tag, [])) < SAMPLE_LIMIT:
                    line_start = text.rfind("\n", 0, match.start()) + 1
                    line_end = text.find("\n", match.end())
                    xml_samples[tag].append({"where": corpora.relative(path, ROOTS),
                                             "line": re.sub(r"\s+", " ", text[line_start:max(line_end, line_start)][:180])})

    print("модулей управляемых форм просмотрено:", form_modules,
          "| xml-файлов просмотрено:", xml_files,
          "| выборка не более", SCAN_LIMIT, "файлов на корпус на имя")
    for name in BSL_CHECKS:
        print("\n==", name, "| встреч:", counts.get(name, 0))
        for sample in samples.get(name, []):
            print("   ", sample["where"])
            print("      ", sample["line"])

    print("\n== узлы метаданных со словами DefaultValue / PredefinedData ==")
    for tag, count in xml_names.most_common(20):
        print("   ", count, "x", tag)
        for sample in xml_samples.get(tag, [])[:2]:
            print("      ", sample["where"], "|", sample["line"])
    if not xml_names:
        print("    ни одного такого узла в выбранной выборке")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
