"""Как имя режима выглядит в файлах платформы: контекст строки вокруг измеренного имени.

Зачем. Наблюдение Task 1 (`reports/exec-12-runscript.json`): `DESIGNER ... /RunScript <файл>`
возвращает код 1 за 2 с и 3 байта вывода (то есть пустой `/Out`), маркер не записан. Код 1 без
сообщения означает, что платформа либо не поняла сочетание, либо потребовала другой аргумент.
Имена флагов мы знаем только из замера `p1c/src/p1c/data/test_cli_flags.json` (426 имён из
строк двух файлов платформы) — имена есть, а их синтаксис нет.

Скрипт читает байты файлов каталога `bin` платформы и печатает контекст вокруг каждого
вхождения имени (и в однобайтовом кодировании, и в UTF-16LE). Соседние строки рядом с именем
режима обычно и есть то, что принимает платформа: имя параметра, текст ошибки, список допустимых
значений.

Читается только то, что лежит на диске: платформа не запускается, файлы не изменяются.

    python probe/platform_flag_strings.py --needle RunScript
    python probe/platform_flag_strings.py --needle RunScript --needle EXECUTE --needle authoff
    python probe/platform_flag_strings.py --root "<каталог bin>" --needle CommandParam
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import paths as paths_script                                       # noqa: E402

CHUNK = 4 << 20
OVERLAP = 4096
CONTEXT = 160


def needle_bytes(needle: str) -> tuple:
    """Имя в двух кодированиях, которые бывают в файлах платформы."""
    return (needle.encode("utf-8"), needle.encode("utf-16-le"))


def printable(data: bytes, start: int, stop: int) -> str:
    text = data[start:stop].decode("utf-8", "replace")
    return re.sub(r"[^\x20-\x7EА-Яа-яЁё\x04-\x0c]+", " ", text).strip()


def scan(path: pathlib.Path, needles: tuple, limit_per_needle: int) -> list:
    """Все вхождения каждого имени в одном файле: (имя, смещение, контекст)."""
    found = []
    size = path.stat().st_size
    with path.open("rb") as handle:
        position = 0
        carried = b""
        while position < size:
            chunk = handle.read(CHUNK)
            if not chunk:
                break
            data = carried + chunk
            for needle in needles:
                for raw in needle_bytes(needle):
                    start = data.find(raw)
                    hits = 0
                    while start != -1 and hits < limit_per_needle:
                        begin = max(0, start - CONTEXT)
                        found.append({"needle": needle, "file": path.name, "offset": position + start,
                                      "context": printable(data, begin, start + len(raw) + CONTEXT)})
                        hits += 1
                        start = data.find(raw, start + 1)
            carried = data[-OVERLAP:] if len(data) > OVERLAP else b""
            position += len(chunk)
    return found


def main(argv: list | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--local", default=str(ROOT / "local.paths.json"))
    parser.add_argument("--root", default="", help="каталог bin платформы (только аргумент или локальный файл путей)")
    parser.add_argument("--needle", action="append", default=[], help="имя режима или ключа (повторяется)")
    parser.add_argument("--limit", type=int, default=6, help="максимум вхождений имени в один файл")
    parser.add_argument("--json", default="")
    args = parser.parse_args(argv)

    # Каталог берётся из аргумента `--root` или из `local.paths.json`: ключ `bin` — путь к
    # 1cv8.exe, а строки режимов лежат в его каталоге. (Прежняя форма `Path("")` давала `.` и
    # тихо сканировала рабочий каталог: 0 вхождений при неверном пути.)
    root = pathlib.Path(args.root) if args.root else pathlib.Path("")
    if not args.root:
        local = paths_script.load_local(args.local)
        bin_path = pathlib.Path(local.get("bin", ""))
        root = bin_path.parent if bin_path.is_file() else bin_path
    if not str(root) or not root.is_dir():
        print("platform_flag_strings: нужен --root (или local.paths.json с bin)", file=sys.stderr)
        return 2
    needles = tuple(args.needle) or ("RunScript", "EXECUTE", "authoff")

    results = []
    for path in sorted(root.iterdir()):
        if not path.is_file() or path.suffix.lower() not in (".exe", ".dll", ".res", ".ini", ".cfg"):
            continue
        hits = scan(path, needles, args.limit)
        if hits:
            print("==", path.name, "|", path.stat().st_size, "байт |", len(hits), "вхождений")
            for hit in hits:
                print("   ", hit["needle"], "@", hit["offset"], "|", hit["context"][:220])
        results.extend(hits)
    print("всего вхождений:", len(results), "| имён:", list(needles), "| каталог:", root.as_posix())
    if args.json:
        out = pathlib.Path(args.json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({"root": root.as_posix(), "needles": list(needles),
                                   "hits": results}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("замер записан:", out.as_posix())
    return 0 if results else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
