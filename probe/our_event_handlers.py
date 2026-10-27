"""Аудит обработчиков событий в модулях нашей конфигурации против официальных сигнатур p1c.

Два свидетельства, полученные до этого замера:

1. Официальные сигнатуры событий объектов метаданных в p1c есть, но лежат только в данных
   (`p1c/src/p1c/data/platform_arities.py`, `EVENT_SIGNATURES`: страница `CatalogObject.<Имя>` с
   `BeforeWrite: <Отказ>`, 1/1; `DocumentObject.<Имя>`: `BeforeWrite: <Отказ>, <РежимЗаписи>,
   <РежимПроведения>`, 3/3; `InformationRegisterRecordSet.<Имя>`: `BeforeWrite: <Отказ>, <Замещение>`,
   2/2). Проверяют их только формы (`p1c/src/p1c/check/forms/checks.py`): для модулей объекта
   находки не появляется ни одной.
2. Канон по корпусам (5601 файл `Ext/ObjectModule.bsl`, `probe/corpora_object_module_events.py`):
   `ПередЗаписью` -> `(Отказ)` 867, `(Отказ, РежимЗаписи, РежимПроведения)` 988,
   `(Отказ, Замещение)` 1; `ПриЗаписи(Отказ)` 1054; `ПослеЗаписи` — 0; `ПриНовомОбъекте` — 0.

То есть имена и арности объектных событий различимы: данные p1c и канон корпусов согласуются
(`CatalogObject.BeforeWrite` 1 параметр <-> `(Отказ)` 867 встреч; документ 3/3 <-> 988 встреч;
запись регистра 2/2 <-> `(Отказ, Замещение)`).

Замер показывает все объявления процедур и функций в `Ext/*.bsl` нашей конфигурации и сопоставляет
их с официальной страницей событий соответствующего вида объекта. Платформу не запускает.
"""
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
CFG = ROOT / "cfg" / "ЭффективностьОтдела"
sys.path.insert(0, str(ROOT / "scripts"))

import paths                                                     # noqa: E402

sys.path.insert(0, paths.load_local(str(ROOT / "local.paths.json")).get("p1c", ""))

from p1c.data.platform_arities import EVENT_SIGNATURES           # noqa: E402

DECLARATION = re.compile(r"^\s*(Процедура|Функция)\s+(\w+)\s*\(([^)]*)\)", re.M)

# Модуль -> страница официальных событий объекта (английские канонические имена p1c).
# Модуль формы (`Ext/Forms/…/Module.bsl`) в замер не берётся: его проверяет
# `python -m p1c.check.forms.cli`, и дублировать его проверку контура смысла нет.
WANTED_MODULES = ("ObjectModule.bsl", "ManagerModule.bsl")

# Русские имена объектных событий -> английские канонические имена данных p1c.
# Соответствия взяты из `p1c/src/p1c/data/test_events.json` (пары ru/en для объектов метаданных) и
# подтверждены каноническими корпусами (`ПриЗаписи` 1054 встреч против `OnWrite`).
RU_TO_EN = {
    "ПередЗаписью": "BeforeWrite",
    "ПриЗаписи": "OnWrite",
    "ПослеЗаписи": "AfterWrite",
    "ПередУдалением": "BeforeDelete",
    "ПриКопировании": "OnCopy",
    "ОбработкаЗаполнения": "Filling",
    "ОбработкаПроверкиЗаполнения": "FillCheckProcessing",
    "ОбработкаПроведения": "Posting",
    "ОбработкаУдаленияПроведения": "UndoPosting",
    "ПриУстановкеНовогоНомера": "OnSetNewNumber",
    "ПриУстановкеНовогоКода": "OnSetNewCode",
    "ПриКомпоновкеРезультата": "OnComposeResult",
    "ПриСозданииОбъекта": "OnObjectCreate",
    "ПриНовомОбъекте": "OnNewObject",
    "ПриЧтении": "OnRead",
    "ПередЧтением": "BeforeRead",
}


def page_for(relative: str) -> str:
    """Имя класса событий по раскладке файла: `Catalogs/Сотрудники/Ext/ObjectModule.bsl` -> `CatalogObject`.

    Имя вида метаданных берётся из папки выгрузки (`Catalogs` -> `CatalogObject`), вид модуля —
    из имени файла (`ObjectModule.bsl` -> объект, `ManagerModule.bsl` -> менеджер).
    """
    parts = pathlib.PurePosixPath(relative).parts
    if len(parts) < 4 or parts[2] != "Ext":
        return ""
    return PAGE_BY_FOLDER.get(parts[0], {}).get(parts[-1], "")


PAGE_BY_FOLDER = {
    "Catalogs": {"ObjectModule.bsl": "CatalogObject", "ManagerModule.bsl": "CatalogManager"},
    "Documents": {"ObjectModule.bsl": "DocumentObject", "ManagerModule.bsl": "DocumentManager"},
    "InformationRegisters": {"ObjectModule.bsl": "InformationRegisterRecordSet",
                             "ManagerModule.bsl": "InformationRegisterManager"},
    "AccumulationRegisters": {"ObjectModule.bsl": "AccumulationRegisterRecordSet",
                              "ManagerModule.bsl": "AccumulationRegisterManager"},
    "Constants": {"ManagerModule.bsl": "ConstantManager"},
    "Reports": {"ObjectModule.bsl": "ReportObject"},
    "DataProcessors": {"ObjectModule.bsl": "DataProcessorObject"},
}


def official(cls: str) -> dict:
    """Официальные события класса: русское имя -> (английское имя, min, max, параметры).

    Страницы в данных p1c названы с хвостом-заполнителем (`CatalogObject.&lt;Catalog name&gt;`),
    поэтому класс сопоставляется по части имени до первой точки.
    """
    result = {}
    for page, events in EVENT_SIGNATURES.items():
        if page.split(".")[0] != cls:
            continue
        for name, signature in events.items():
            for ru, en in RU_TO_EN.items():
                if en == name:
                    result[ru] = (name, signature["min_args"], signature["max_args"],
                                  signature["params"])
    return result


def main(argv: list | None = None) -> int:
    known_classes = {page.split(".")[0] for page in EVENT_SIGNATURES}
    missing_classes = sorted({cls for cls in
                              {page_for(path.relative_to(CFG).as_posix())
                               for path in CFG.rglob("*.bsl")} if cls and cls not in known_classes})
    if missing_classes:
        print("классов событий нет в данных p1c (проверить нельзя):", ", ".join(missing_classes))

    total = 0
    findings = []
    for path in sorted(CFG.rglob("*.bsl")):
        relative = path.relative_to(CFG).as_posix()
        if path.name not in WANTED_MODULES:
            continue
        cls = page_for(relative)
        events = official(cls)
        text = path.read_bytes().decode("utf-8-sig", "replace")
        declarations = DECLARATION.findall(text)
        total += len(declarations)
        print("\n---", relative, "| класс событий:", cls or "(не объектный модуль)",
              "| объявлений:", len(declarations))
        for kind, name, parameters in declarations:
            args = [item.strip() for item in parameters.split(",") if item.strip()]
            event = events.get(name)
            if event:
                en, minimum, maximum, params = event
                mark = "ок" if minimum <= len(args) <= maximum else "НАХОДКА"
                print("   ", mark, kind, name, "(", parameters, ")", "->", cls + "." + en,
                      "| официально", minimum, "/", maximum, ":", ", ".join(params))
                if mark == "НАХОДКА":
                    findings.append(relative + ": " + name + "(" + parameters + ") против "
                                    + cls + "." + en + " " + str(minimum) + "/" + str(maximum))
            else:
                en = RU_TO_EN.get(name, "")
                classes_with = sorted({pg.split(".")[0] for pg in EVENT_SIGNATURES
                                       if en and en in EVENT_SIGNATURES[pg]})
                hint = "" if not classes_with else " (это событие других классов: " \
                    + ", ".join(classes_with[:3]) + ")"
                print("    ?", kind, name, "(", parameters, ")",
                      "-> события с таким именем у класса", cls, "нет", hint)
    print("\nобъявлений в объектных/менеджерных модулях:", total)
    print("находок:", len(findings))
    for finding in findings:
        print("  -", finding)
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
