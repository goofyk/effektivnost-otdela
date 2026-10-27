"""Как канонические конфигурации задают значения по умолчанию у новых объектов.

Найденный дефект нашей конфигурации: в модулях объекта справочника и документа объявлены
`Процедура ПриНовомОбъекте()`. Такого события у класса `CatalogObject`/`DocumentObject` в официальных
данных нет (`probe/p1c_event_pages.py`: страница `CatalogObject.<Имя>` — BeforeDelete, BeforeWrite,
FillCheckProcessing, Filling, OnCopy, OnSetNewCode, OnWrite), и в 5601 каноническом
`Ext/ObjectModule.bsl` корпусов оно не встречается ни разу (`probe/corpora_object_module_events.py`).
Значит обработчик не вызывается никогда: значения по умолчанию, которые в нём написаны, не
появляются.

Замер отвечает на вопрос, где канонические конфигурации задают значения по умолчанию, чтобы мы
переписали своё тем же способом:
1. встречается ли `ПриНовомОбъекте` вообще хотя бы где-нибудь в корпусах;
2. как устроены значения по умолчанию в метаданных атрибутов (`DefaultValues` в XML объекта);
3. задают ли значения по умолчанию в модулях управляемых форм (`Объект.Новый` + `ПриСозданииНаСервере`);
4. ставят ли дату документа явно (`Дата = ТекущаяДата()`) в модуле объекта.

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

CHECKS = {
    "ПриНовомОбъекте (везде)": re.compile(r"\bПриНовомОбъекте\b"),
    "DefaultValues в XML метаданных": re.compile(r"<DefaultValues>"),
    "DefaultValue (строка выражения)": re.compile(r"<DefaultValue>(?!</DefaultValue>)"),
    "Объект.Новый в модулях": re.compile(r"Объект\.Новый\b"),
    "ПриСозданииНаСервере в модулях": re.compile(r"\bПриСозданииНаСервере\b"),
    "Дата = ТекущаяДата()": re.compile(r"\bДата\s*=\s*ТекущаяДата\s*\("),
    "ЗначениеПоУмолчанию в справочнике (выражение)": re.compile(r"ЗначениеПоУмолчанию"),
}

WANTED = ("*.bsl", "*.xml")
SCAN_LIMIT = 4000


def main(argv: list | None = None) -> int:
    counts = collections.Counter()
    files_seen = collections.Counter()
    samples: dict = {}
    total = 0
    for root in ROOTS:
        for path in corpora.wanted_files(root, WANTED, SCAN_LIMIT):
            total += 1
            files_seen[path.suffix] += 1
            try:
                text = path.read_bytes().decode("utf-8-sig", "replace")
            except OSError:
                continue
            for name, pattern in CHECKS.items():
                matches = list(pattern.finditer(text))
                if not matches:
                    continue
                counts[name] += len(matches)
                if len(samples.setdefault(name, [])) < 3:
                    match = matches[0]
                    line_start = text.rfind("\n", 0, match.start()) + 1
                    line_end = text.find("\n", match.end())
                    samples[name].append({
                        "where": corpora.relative(path, ROOTS),
                        "line": re.sub(r"\s+", " ", text[line_start:max(line_end, line_start)][:220]),
                    })
    print("файлов просмотрено:", total, "|", dict(files_seen),
          "| выборка не более", SCAN_LIMIT, "файлов на корпус на имя")
    for name in CHECKS:
        print("\n==", name, "| встреч:", counts.get(name, 0))
        for sample in samples.get(name, []):
            print("   ", sample["where"])
            print("      ", sample["line"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
