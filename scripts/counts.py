"""Числа объектов конфигурации и их сверка «источник против выгрузки платформы».

Модель метаданных строится читателем `p1c.load` (путь к `src` — аргумент или значение
`p1c` из локального файла путей). Числа нужны потому, что наблюдение показало: после
отменённой загрузки `/CheckModules` на пустой базе даёт код 0 («Синтаксических ошибок не
обнаружено!»), и один только код выхода платформы ничего не доказывает.
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]


def counts_from_model(model: dict) -> dict:
    """Вид метаданных -> число объектов в модели `p1c.load`.

    Вид должен называться так же, как в независимом счётчике по раскладке файлов
    (`scripts/layout.py`), иначе сравнение двух счётчиков нельзя прочитать без догадок.
    Общая часть модели (`collections`) даёт только 18 распознаваемых папок выгрузки; общее,
    формы, пропущенные файлы, права ролей и предопределённые данные лежат в других ключах,
    и без них молчание читателя неотличимо от пустой конфигурации.
    """
    model = model or {}
    result: dict[str, int] = {}
    for collection in model.get("collections", {}).values():
        kind = collection.get("kind", "")
        result[kind] = result.get(kind, 0) + len(collection.get("objects", []))
    for key, kind in (("common_modules", "common_module"), ("common_attributes", "common_attribute"),
                      ("common_forms", "common_form")):
        value = model.get(key)
        count = len(value) if isinstance(value, dict) else len(value or [])
        if count:
            result[kind] = result.get(kind, 0) + count

    # Права ролей и предопределённые данные: имена совпадают со счётчиком по файлам
    # (`scripts/layout.py`), потому что без них прочитанные `Ext/Rights.xml` и
    # `Ext/Predefined.xml` остались бы в `tool_blind_kinds`. Имя `role` (дескриптор
    # `Roles/Имя.xml`) не выдаётся: читатель читает файл прав, а не дескриптор роли.
    if model.get("roles"):
        result["role_rights"] = result.get("role_rights", 0) + len(model["roles"])
    if model.get("predefined_data"):
        result["predefined_data"] = result.get("predefined_data", 0) + len(model["predefined_data"])

    forms = sum(len(obj.get("forms", [])) for obj in model.get("objects", {}).values())
    forms += len(model.get("common_forms") or [])
    if forms:
        result["form_data"] = forms
    commands = sum(len(obj.get("commands", [])) for obj in model.get("objects", {}).values())
    if commands:
        result["command_module"] = commands
    if model.get("skipped_files"):
        result["skipped_module_files"] = len(model["skipped_files"])
    return {kind: count for kind, count in sorted(result.items()) if count}


def compare_counts(source: dict, dumped: dict) -> dict:
    """Раскладки чисел: {'mismatch': {вид: (источник, выгрузка)}, 'only_source', 'only_dump'}."""
    mismatch, only_source, only_dump = {}, {}, {}
    for kind in sorted(set(source) | set(dumped)):
        a, b = source.get(kind, 0), dumped.get(kind, 0)
        if a and not b:
            only_source[kind] = a
        elif b and not a:
            only_dump[kind] = b
        elif a != b:
            mismatch[kind] = (a, b)
    return {"mismatch": mismatch, "only_source": only_source, "only_dump": only_dump}


def object_counts(cfg_dir, p1c_src: str) -> dict:
    """Числа объектов файловой конфигурации через читателя p1c.

    Причина отказа сообщается текстом: пустой словарь от молчаливого «читателя не нашли»
    неотличим от конфигурации без объектов.
    """
    if not p1c_src:
        raise RuntimeError("каталога src p1c не названо: нужен --p1c или значение p1c в локальном файле путей")
    src = pathlib.Path(p1c_src)
    if not src.is_dir():
        raise RuntimeError("каталога src p1c нет: " + src.name)
    sys.path.insert(0, str(src))
    try:
        from p1c.load import reader                                               # noqa: E402
        model = reader.load_configuration_model(str(cfg_dir), parallel=False)
    except Exception as error:
        # Отказ читателя сообщается текстом: гейт обязан отличить «инструмент не смог
        # прочитать» от «в конфигурации нет объектов». Наблюдение: пустой каталог выгрузки
        # даёт у читателя ValueError («Не удалось определить раскладку»), и это не пустая
        # конфигурация, а нечитаемый каталог.
        raise RuntimeError("читатель p1c.load не смог прочитать каталог "
                           "(" + type(error).__name__ + "): " + str(error)) from error
    return counts_from_model(model)


def configuration_name(cfg_dir) -> str:
    """Имя корневого объекта конфигурации (пустая база называется «Конфигурация»)."""
    root = pathlib.Path(cfg_dir) / "Configuration.xml"
    if not root.is_file():
        return ""
    text = root.read_bytes().decode("utf-8-sig", "replace")
    start = text.find("<Name>")
    if start < 0:
        return ""
    return text[start + len("<Name>"):text.find("</Name>", start)].strip()
