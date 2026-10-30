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
    """Вид метаданных -> число файлов, которые читатель `p1c.load` открыл.

    Считаются пары `path`/`kind` манифеста `read_files`: класс присваивает парсер, открывший
    файл. Ключи модели — намерение читателя, и счётчик по ним называет классы, которых
    читатель не открывал: молчание читателя стало бы неотличимым от пустой конфигурации.
    Вид должен называться так же, как в независимом счётчике по раскладке файлов
    (`scripts/layout.py`), иначе сравнение двух счётчиков нельзя прочитать без догадок.
    Нечитаемые модули — записи диагноза (`skipped_files`), манифестной пары у них нет.
    """
    model = model or {}
    manifest = model.get("read_files") or []
    result: dict[str, int] = {}
    for entry in manifest:
        kind = entry.get("kind", "")
        if kind:
            result[kind] = result.get(kind, 0) + 1
        if str(entry.get("path", "")).endswith(".bsl"):
            result["bsl_module"] = result.get("bsl_module", 0) + 1
    if manifest:
        result["files"] = len(manifest)
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
