"""Пути окружения проверочного контура.

Путь файла платформы, информационной базы и корпусов существует только как аргумент
командной строки или как значение локального непубличного файла `local.paths.json`
(он в `.gitignore`). Ни один файл этого репозитория путей не содержит.
"""
from __future__ import annotations

import json
import pathlib
import sys

LOCAL_KEYS = ("bin", "ib", "cfg", "dump", "work", "p1c", "spikes")
KNOWN_PREFIXES = ("corpora_",)


def load_local(path_json) -> dict:
    """Значения локального файла путей; отсутствующий файл — пустой словарь.

    Имена ключей проверяются: опечатка в имени пути превращается в отказ запуска платформы
    с непонятной причиной, поэтому неизвестный ключ сообщается в stderr, а не проглатывается.
    Кроме точных имён `LOCAL_KEYS` допускаются группы `corpora_*` (корпуса выгрузок нужны
    замерам покрытия и их заведомо больше одного).
    """
    path = pathlib.Path(path_json)
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    result = {}
    for key, value in data.items():
        if key in LOCAL_KEYS or key.startswith(KNOWN_PREFIXES):
            result[key] = str(value)
        elif not key.startswith("_"):
            print("local.paths.json: неизвестный ключ " + key + " (опечатка в имени пути?)",
                  file=sys.stderr)
    return {key: value for key, value in sorted(result.items())}


def refuse_missing_bin(bin_path: str) -> str:
    """Причина отказа, если файла платформы нет. Пустая строка — запуск разрешён."""
    if not bin_path:
        return "файла платформы нет: нужен --bin (или значение bin в локальном файле путей)"
    if not pathlib.Path(bin_path).is_file():
        return "файла платформы по аргументу --bin нет: проверьте значение bin в локальном файле путей"
    return ""
