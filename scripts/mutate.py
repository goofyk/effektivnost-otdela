"""Копия конфигурации с ровно одной преднамеренной поломкой — источник отрицательного прогона.

Зачем это нужно: положительный прогон доказывает только то, что инструмент молчит. Чтобы
измерить, что p1c говорит о конкретной ошибке метаданных или модуля, нужен воспроизводимый
источник этой ошибки. Каждый вид поломки меняется по одному месту, чтобы диагностику нельзя
было объяснить чем-то другим.

Отличия от генератора конфигурации: здесь ничего не создаётся — существующий файл исходника
переписывается с одной заменой, в копии. Исходник (`SOURCE_CFG`) остаётся нетронутым.
"""
from __future__ import annotations

import pathlib
import shutil
import sys

import layout
import normalize_text

ROOT = pathlib.Path(__file__).resolve().parent.parent
SOURCE_CFG = ROOT / "cfg" / "ЭффективностьОтдела"

# Объект, которого в конфигурации нет: подсистема ссылается на него в Content.
MISSING_OBJECT = "Catalog.ТакогоНет"
# Функция общего модуля, которой нет: вызов в модуле объекта документа.
MISSING_FUNCTION = "ПроверитьЧасыДокумента"

MUTATIONS = ("subsystem_bad_content", "form_missing_handler", "unknown_function_call")


def copy_source(src: str, dst: str) -> int:
    """Копия исходной конфигурации. Возвращает количество скопированных файлов."""
    source, target = pathlib.Path(src), pathlib.Path(dst)
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target)
    return len([p for p in target.rglob("*") if p.is_file()])


def refusal(kind: str) -> dict:
    return {"code": 2, "reason": "неизвестный вид поломки '" + kind + "', известны: "
            + ", ".join(MUTATIONS)}


def _write(path: pathlib.Path, text: str) -> None:
    path.write_bytes(b"\xef\xbb\xbf" + text.replace("\r\n", "\n").replace("\n", "\r\n").encode("utf-8"))


def _read(path: pathlib.Path) -> str:
    return path.read_bytes().decode("utf-8-sig", "replace")


def break_subsystem_bad_content(directory: pathlib.Path) -> dict:
    """Ссылка подсистемы на несуществующий объект метаданных (содержимое подсистемы)."""
    path = directory / "Subsystems" / "ЭффективностьОтдела.xml"
    if not path.is_file():
        return {"code": 2, "reason": "нет файла подсистемы: " + path.name}
    body = _read(path)
    needle = '<xr:Item xsi:type="xr:MDObjectRef">Catalog.Сотрудники</xr:Item>'
    if needle not in body:
        return {"code": 2, "reason": "в содержимом подсистемы нет ссылки на Catalog.Сотрудники"}
    _write(path, body.replace(needle, '<xr:Item xsi:type="xr:MDObjectRef">'
                                      + MISSING_OBJECT + "</xr:Item>", 1))
    return {"code": 0, "kind": "subsystem_bad_content", "file": str(path),
            "changed": "ссылка подсистемы Content: Catalog.Сотрудники -> " + MISSING_OBJECT}


def break_form_missing_handler(directory: pathlib.Path) -> dict:
    """Обработчик события формы удалён из модуля формы, но объявлен в описании формы."""
    descriptor = directory / "Catalogs" / "Сотрудники" / "Forms" / "ФормаЭлемента" / "Ext" / "Form.xml"
    module = directory / "Catalogs" / "Сотрудники" / "Forms" / "ФормаЭлемента" / "Ext" / "Form" / "Module.bsl"
    handler = "ПриСозданииНаСервере"
    if not descriptor.is_file() or not module.is_file():
        return {"code": 2, "reason": "нет тройки файлов формы справочника"}
    body = _read(module)
    start = body.find("&НаСервере")
    head = "Процедура " + handler + "("
    if start < 0 or head not in body:
        return {"code": 2, "reason": "в модуле формы нет процедуры " + handler}
    end = body.find("КонецПроцедуры", body.find(head))
    if end < 0:
        return {"code": 2, "reason": "у процедуры " + handler + " нет КонецПроцедуры"}
    _write(module, body[:start] + body[end + len("КонецПроцедуры"):])
    return {"code": 0, "kind": "form_missing_handler", "file": str(module),
            "descriptor": str(descriptor), "handler": handler,
            "changed": "из модуля формы удалена процедура " + handler
                       + ", объявленная в <Event name=\"OnCreateAtServer\">"}


def break_unknown_function_call(directory: pathlib.Path) -> dict:
    """Вызов несуществующей функции общего модуля из модуля объекта документа."""
    path = directory / "Documents" / "ФактРаботы" / "Ext" / "ObjectModule.bsl"
    definition = directory / "CommonModules" / "РасчётПоказателей" / "Ext" / "Module.bsl"
    needle = "Движения.ЗатратыВремени.Заполнять(Истина);"
    if not path.is_file() or needle not in _read(path):
        return {"code": 2, "reason": "в модуле объекта документа нет строки " + needle}
    body = _read(path)
    call = "Часы = РасчётПоказателей." + MISSING_FUNCTION + "(Часы);"
    _write(path, body.replace(needle, call + "\n\t" + needle, 1))
    return {"code": 0, "kind": "unknown_function_call", "file": str(path),
            "definition": str(definition), "call": MISSING_FUNCTION,
            "changed": "в модуль объекта документа добавлен вызов РасчётПоказателей."
                       + MISSING_FUNCTION + "()"}


def apply_mutation(kind: str, directory: str) -> dict:
    """Одна преднамеренная поломка в копии конфигурации (исходник не трогается)."""
    if kind not in MUTATIONS:
        return refusal(kind)
    target = pathlib.Path(directory)
    if not target.is_dir():
        return {"code": 2, "reason": "нет каталога копии: " + str(target)}
    result = globals()["break_" + kind](target)
    if result["code"] == 0:
        normalize_text.normalize(str(target))
    return result


def source_layout_counts() -> dict:
    return layout.layout_counts(str(SOURCE_CFG))


def shape_problems_for_source() -> list:
    return layout.shape_problems(str(SOURCE_CFG), source_layout_counts())


def main(argv: list) -> int:
    if len(argv) < 2:
        print("употребление: python scripts/mutate.py <вид_поломки> <каталог_копии>")
        print("виды:", ", ".join(MUTATIONS))
        return 2
    result = apply_mutation(argv[0], argv[1])
    if result["code"] != 0:
        print("отказ:", result["reason"])
        return result["code"]
    print("поломка '" + result["kind"] + "': " + result["changed"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
