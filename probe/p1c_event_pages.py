"""Что p1c знает о сигнатурах событий модулей объекта и кто из проверок это использует.

Наблюдение, из-за которого сделан этот замер: в модуле объекта справочника мы написали
`ПередЗаписью(Отказ, Замечание, Параметр)`, и ни один инструмент p1c об этом не сообщил. При этом
в данных p1c (`p1c/src/p1c/data/platform_arities.py`, `EVENT_SIGNATURES`) страницы событий объектов
метаданных есть — например `CatalogObject.<Имя справочника>` с `BeforeWrite: min_args/max_args`
и именами параметров. Значит вопрос не в том, знает ли p1c официальные сигнатуры, а в том,
какие проверки их читают.

Замер отвечает на два вопроса:
1. какие страницы `EVENT_SIGNATURES` относятся к модулям объектов/менеджеров (не к формам);
2. знает ли p1c имя `ПриНовомОбъекте` (у нас обработчик с таким именем) и что оно такое.

Платформу замер не запускает, исходник конфигурации не изменяет.
"""
from __future__ import annotations

import re
import sys

ROOT = __import__("pathlib").Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import paths                                                     # noqa: E402

sys.path.insert(0, paths.load_local(str(ROOT / "local.paths.json")).get("p1c", ""))

from p1c.data.platform_arities import EVENT_SIGNATURES           # noqa: E402

# Страницы событий объектов метаданных: имена вида `CatalogObject.<Имя>`, `CatalogManager.<Имя>`.
# Формные страницы устроены иначе — это фразы с пробелами (`Catalog item form extension`).
OBJECT_PAGE = re.compile(r"^[A-Za-z]+\.")


def main(argv: list | None = None) -> int:
    pages = sorted(EVENT_SIGNATURES)
    object_pages = [page for page in pages if OBJECT_PAGE.match(page)]
    form_pages = [page for page in pages if page not in object_pages]
    print("страниц событий всего:", len(pages),
          "| страниц объектов метаданных:", len(object_pages),
          "| страниц форм:", len(form_pages))

    print("\n== сигнатуры объектных страниц, которые нам нужны ==")
    wanted = ("CatalogObject", "CatalogManager", "DocumentObject", "ConstantManager",
              "InformationRegisterRecordSet", "AccumulationRegisterRecordSet", "ReportObject")
    for wanted_name in wanted:
        for page in object_pages:
            if not page.startswith(wanted_name + "."):
                continue
            print("\n---", page)
            for event, signature in sorted(EVENT_SIGNATURES[page].items()):
                print("   ", event, "| параметры:", ", ".join(signature["params"]),
                      "| min/max:", signature["min_args"], "/", signature["max_args"])

    print("\n== знает ли p1c имена событий модулей объекта, которые есть у нас ==")
    for name in ("ПриНовомОбъекте", "ПередЗаписью", "ПослеЗаписи", "ОбработкаПроведения"):
        hits = []
        for page in pages:
            for event, signature in EVENT_SIGNATURES[page].items():
                if event == name:
                    hits.append((page, signature["min_args"], signature["max_args"],
                                 ", ".join(signature["params"])))
        if not hits:
            print("   ", name, "-> в EVENT_SIGNATURES нет ни одной страницы с таким именем")
        for page, minimum, maximum, params in hits[:8]:
            print("   ", name, "|", page, "|", minimum, "/", maximum, "|", params)
        if len(hits) > 8:
            print("    … всего страниц с этим именем:", len(hits))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
