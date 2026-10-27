"""Статическая сверка рукописной конфигурации с каноническими выгрузками корпусов.

Зачем: загрузка нашей конфигурации `/LoadConfigFromFiles` не завершается (120 с, 0 байт вывода,
постоянный расход CPU), тогда как выгруженная из платформы конфигурация (239 файлов) в том же
режиме загружается за 4 с с кодом 0. Значит дело в содержимом наших файлов. XDTO-ошибки платформа
сообщает быстро; зависание — это то, что XDTO пропустила, но что невозможно разобрать семантически.

Замер без платформы: (1) поиск повторяющихся UUID внутри конфигурации; (2) сравнение имён элементов
наших файлов метаданных с именами элементов канонических выгрузок того же вида.
"""
from __future__ import annotations

import collections
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
CFG = ROOT / "cfg" / "ЭффективностьОтдела"
sys.path.insert(0, str(ROOT / "scripts"))

import corpora                                                   # noqa: E402

CORPORA = corpora.dumps()

UUID = re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b")
ELEMENT = re.compile(r"<(/?[A-Za-z][A-Za-z0-9:_.-]*)\b")


def uuid_occurrences(cfg: pathlib.Path) -> dict:
    where = collections.defaultdict(list)
    for path in sorted(cfg.rglob("*")):
        if not path.is_file():
            continue
        text = path.read_bytes().decode("utf-8-sig", "replace")
        for line_no, line in enumerate(text.splitlines(), 1):
            for value in UUID.findall(line):
                where[value.lower()].append(path.relative_to(cfg).as_posix() + ":" + str(line_no))
    return where


def element_names(path: pathlib.Path) -> set:
    text = path.read_bytes().decode("utf-8-sig", "replace")
    names = set()
    for match in ELEMENT.finditer(text):
        name = match.group(1)
        if name.startswith("xml") or name in ("xs", "xsi"):
            continue
        names.add(name.lstrip("/"))
    return names


def corpus_element_union(kind_dir: str, limit: int = 150) -> tuple:
    """Объединение имён элементов по каноническим выгрузкам одного вида метаданных.

    Объединение (а не один файл) нужно, чтобы необязательные, но законные свойства не считались
    «придуманными нами»: находкой считается только имя, которого нет ни в одной канонической
    выгрузке этого вида.
    """
    names = set()
    used = 0
    for root in CORPORA:
        if kind_dir == "":
            files = [pathlib.Path(root) / "Configuration.xml"]
            directory = None
        else:
            directory = pathlib.Path(root) / kind_dir
        if directory is not None and not directory.is_dir():
            continue
        if directory is None:
            candidates = files
        else:
            candidates = [p for p in directory.rglob("*.xml")]
        candidates = [(p.stat().st_size, p) for p in candidates if p.is_file()]
        for _, path in sorted(candidates, key=lambda x: x[0])[:limit]:
            names |= element_names(path)
            used += 1
    return names, used


KIND_OF_FILE = {
    "Configuration.xml": "",
    "Enums": "Enums",
    "Constants": "Constants",
    "Catalogs": "Catalogs",
    "Documents": "Documents",
    "InformationRegisters": "InformationRegisters",
    "AccumulationRegisters": "AccumulationRegisters",
    "Reports": "Reports",
    "CommonModules": "CommonModules",
    "Subsystems": "Subsystems",
    "Roles": "Roles",
    "Languages": "Languages",
}


def main(argv: list | None = None) -> int:
    if not CFG.is_dir():
        print("нет конфигурации:", CFG)
        return 2

    print("== 1. Повторяющиеся UUID внутри конфигурации ==")
    duplicates = {v: f for v, f in uuid_occurrences(CFG).items() if len(f) > 1}
    if not duplicates:
        print("  повторений нет")
    for value, places in sorted(duplicates.items()):
        print("  ", value, "->", "; ".join(places[:6]))

    print("\n== 2. Имена элементов, которых нет ни в одной канонической выгрузке этого вида ==")
    cache: dict = {}
    for path in sorted(CFG.rglob("*.xml")):
        relative = path.relative_to(CFG).as_posix()
        parts = relative.split("/")
        kind_dir = KIND_OF_FILE.get("Configuration.xml" if path.name == "Configuration.xml"
                                    else parts[0])
        if kind_dir is None:
            print("  ?", relative, "— неизвестный вид, пропущен")
            continue
        if kind_dir not in cache:
            cache[kind_dir] = corpus_element_union(kind_dir)
        allowed, used = cache[kind_dir]
        if not allowed:
            print("  ?", relative, "— канонических образцов вида не найдено:", kind_dir)
            continue
        invented = sorted(element_names(path) - allowed)
        print("  ", relative, "(сверено с", used, "каноническими файлами вида",
              kind_dir or "Configuration", ")")
        if invented:
            print("      придумано нами:", ", ".join(invented))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
