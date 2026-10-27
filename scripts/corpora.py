"""Каталоги корпусов канонических выгрузок: только из локального файла путей.

Корпус — каталог выгрузки реальной конфигурации (УХ, ERP, ЗУП и другие), которая в этой же платформе
загружается и работает. Он нужен как свидетельство «так пишет платформа»: по нему проверяют,
каноническая ли конструкция в нашей рукописной конфигурации, и является ли диагностика p1c
находкой либо ложной находкой.

Два правила этого модуля:

1. Пути корпусов существуют только в `local.paths.json` (ключи `corpora_*`) или в аргументах
   командной строки. В файлах репозитория путей нет: иначе наблюдение нельзя воспроизвести на
   другой машине и нельзя отличить от случайного везения.
2. Обход корпуса ограничивается и подписывается в выводе (`files_named(..., limit_per_root=…)`):
   корпус УХ содержит десятки тысяч файлов, и неограниченный замер не повторяем по времени.
   Выборка упорядочена по относительному пути, чтобы она не зависела от порядка обхода файловой
   системы.
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import paths                                                     # noqa: E402

CORPORA_KEY_PREFIX = "corpora_"


def _candidates(local_file: str | None) -> list:
    local = paths.load_local(local_file or str(ROOT / "local.paths.json"))
    return [(key, value) for key, value in sorted(local.items())
            if key.startswith(CORPORA_KEY_PREFIX)]


def _looks_like_dump(directory: pathlib.Path) -> bool:
    """Выгрузка конфигуратора: корневой `Configuration.xml` или папка ролей."""
    return (directory / "Configuration.xml").is_file() or (directory / "Roles").is_dir()


def report(local_file: str | None = None) -> dict:
    """Что контур увидел в корпусах: принятые, отсутствующие, не похожие на выгрузку.

    Нужно, чтобы вывод «в каноне такого нет» нельзя было получить из корпусов, которые контур
    вообще не прочитал (например из каталога с одиночными `.cf`-файлами).
    """
    accepted, missing, not_a_dump = [], [], []
    for key, value in _candidates(local_file):
        directory = pathlib.Path(value)
        if not directory.is_dir():
            missing.append(key)
        elif not _looks_like_dump(directory):
            not_a_dump.append(key)
        else:
            accepted.append(key)
    return {"configured": [key for key, _ in _candidates(local_file)],
            "accepted": accepted, "missing": missing, "not_a_dump": not_a_dump}


def dumps(local_file: str | None = None) -> list:
    """Каталоги принятых корпусов (существующие выгрузки конфигуратора), в порядке имён ключей."""
    accepted = set(report(local_file)["accepted"])
    return [pathlib.Path(value) for key, value in _candidates(local_file) if key in accepted]


def files_named(roots: list, filename: str, limit_per_root: int = 0) -> list:
    """Файлы заданного имени в корпусах; `limit_per_root` — граница выборки на каждый корпус."""
    result = []
    for root in roots:
        found = sorted((path for path in root.rglob(filename) if path.is_file()),
                       key=lambda path: path.relative_to(root).as_posix())
        result.extend(found[:limit_per_root] if limit_per_root else found)
    return result


def wanted_files(root: pathlib.Path, names, limit_per_root: int = 0) -> list:
    """Файлы заданных имён внутри одного корпуса, без обхода всего дерева корпуса.

    `rglob("*")` по корпусу УХ — десятки тысяч файлов; замер, который их все читает, не повторяем
    по времени. Имена файлов — те, ради которых замер и затеян.
    """
    found = []
    for name in names:
        found.extend(files_named([root], name, limit_per_root))
    return sorted(found, key=lambda path: path.relative_to(root).as_posix())


def largest(files: list, limit: int) -> list:
    """Самые большие файлы выборки.

    Для файлов прав роли размер и есть полнота состава: крупная роль содержит права почти на все
    объекты конфигурации, поэтому именно крупные роли отвечают на вопрос «бывает ли такое в каноне».
    """
    return sorted(files, key=lambda path: (-path.stat().st_size, path.as_posix()))[:limit]


def relative(path: pathlib.Path, roots: list) -> str:
    """Путь свидетельства внутри его корпуса (подпись наблюдения); вне корпуса — полный путь."""
    for root in roots:
        try:
            return path.relative_to(root).as_posix()
        except ValueError:
            continue
    return path.as_posix()
