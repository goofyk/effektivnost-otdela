"""Замер очереди модулей, которую читатель `p1c.load` выставляет на сканирование (замер, только чтение).

Вопрос замера: сколько слотов модулей читатель собирается просканировать на выгрузке и сколько из них
оказываются файлами на диске. Число нужно как объяснение строки прогресса `модулей к сканированию N`
и как проверка того, что отсутствующий слот не попадает ни в манифест прочитанных файлов, ни в
`skipped_files`.

Как замер измеряет, а не восстанавливает: `p1c.load.scan.scan_one` подменяется обёрткой, которая
записывает каждый полученный путь и вызывает настоящую функцию. Аргументы этой подмены и есть
очередь `module_jobs` читателя (`p1c.load.reader`), а пересечение записанных путей с манифестом
`model["read_files"]` делит очередь на «файл есть» и «слота нет на диске».

Абсолютных путей в этом файле нет: корни берутся из ключей `dump`, `p1c` файла `local.paths.json`.

Выход замера: `reports/reader-module-queue.txt` (очередь построчно, разложение по группам, строки
прогресса читателя).
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"

PATHS = json.loads((ROOT / "local.paths.json").read_text(encoding="utf-8-sig"))
sys.path.insert(0, str(pathlib.Path(PATHS["p1c"]) / "src"))

import p1c.load.scan as scan                                        # noqa: E402

CALLS: list[str] = []
_REAL_SCAN_ONE = scan.scan_one


def _spy(path):
    CALLS.append(str(path))
    return _REAL_SCAN_ONE(path)


scan.scan_one = _spy

from p1c.load.reader import load_configuration_model                # noqa: E402

DUMP = pathlib.Path(PATHS["dump"])

# Имена слотов модулей объектов — по замеру имени файла, а не по догадке.
MODULE_FILES = {
    "ManagerModule.bsl": "менеджер значений",
    "ObjectModule.bsl": "модуль объекта",
    "RecordSetModule.bsl": "модуль набора записей (регистр)",
    "ValueManagerModule.bsl": "менеджер значений (регистр)",
    "Module.bsl": "модуль (общий модуль)",
}


def main() -> int:
    messages: list[str] = []
    model = load_configuration_model(str(DUMP), parallel=False, progress=messages.append)
    manifest = {entry["path"].replace("\\", "/") for entry in model["read_files"]}

    lines = ["=== строки прогресса читателя"]
    for message in messages:
        lines.append("    %s" % message)

    lines.append("=== очередь модулей к сканированию: %d записей" % len(CALLS))
    groups: dict[str, int] = {}
    read = miss = 0
    for raw in sorted(CALLS, key=lambda p: p.replace("\\", "/")):
        rel = pathlib.Path(raw).relative_to(DUMP).as_posix()
        parts = rel.split("/")
        if rel in manifest:
            read += 1
            mark = "ЕСТЬ"
        else:
            miss += 1
            mark = "НЕТ"
        if "Forms" in parts:
            group = "модуль формы"
        elif parts[0] == "CommonModules":
            group = "модуль общего модуля"
        else:
            group = "модуль объекта: " + MODULE_FILES.get(parts[-1], "?")
        groups[group] = groups.get(group, 0) + 1
        lines.append("    %-4s %-52s %s" % (mark, rel, group))

    lines.append("=== разложение очереди по группам")
    for group in sorted(groups):
        lines.append("    %-40s %d" % (group, groups[group]))
    lines.append("    %-40s %d" % ("ИТОГО", len(CALLS)))
    lines.append("файлов на диске %d, отсутствующих слотов %d" % (read, miss))
    lines.append("записей манифеста %d, skipped_files %d"
                 % (len(model["read_files"]), len(model["skipped_files"])))
    lines.append("объектов %d, форм объектов %d, общих модулей %d, общих форм %d"
                 % (len(model["objects"]), sum(len(o.get("forms", [])) for o in model["objects"].values()),
                    len(model.get("common_modules", {})), len(model.get("common_forms", []))))

    REPORTS.mkdir(exist_ok=True)
    (REPORTS / "reader-module-queue.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[-6:]))
    print("report: reports/reader-module-queue.txt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
