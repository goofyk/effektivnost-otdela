"""Имена параметров командной строки платформы: таблица имён в 1cv8.exe, окно вокруг имени.

Зачем. Наблюдение `reports/exec-12-runscript.json`: `DESIGNER /F <иб> /Out <файл>
/DisableStartupDialogs /RunScript <файл>` даёт код 1 за 2.0 с и 3 байта вывода (пусто). Имя
`/RunScript` существует — оно есть в замере `p1c/src/p1c/data/test_cli_flags.json` (426 имён) и в
таблице имён `1cv8.exe` (`probe/platform_flag_strings.py`). Но замер даёт только имена: ни порядка
аргументов, ни того, какой режим запуска их принимает.

Таблица имён в `1cv8.exe`/`1cv8c.exe` лежит в кодировании UTF-16LE подряд, поэтому рядом с именем
видны его соседи — обычно это те же группы параметров (например `CmdLine/...` или `/CheckConfig`,
`/DeleteCfg`, `/RollbackCfg`, `/CheckModules`). Окно вокруг имени показывает группу и позволяет
выбрать следующую проверяемую форму запуска, а не угадывать её.

Скрипт читает только байты файлов каталога `bin` платформы; платформу не запускает.

    python probe/platform_name_table.py --needle RunScript --window 1200
    python probe/platform_name_table.py --needle TESTMANAGER --needle LoadCfg --window 900
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

PLATFORM_FILES = ("1cv8.exe", "1cv8c.exe")
TOKEN = re.compile(r"[A-Za-z][A-Za-z0-9_./]{2,}")


def utf16_text(path: pathlib.Path) -> str:
    """Весь файл как UTF-16LE: таблица имён платформы лежит в этом кодировании (наблюдение:
    `probe/platform_flag_strings.py` нашёл имена только в виде `R u n S c r i p t`)."""
    return path.read_bytes().decode("utf-16-le", "replace")


def names_in(text: str) -> list:
    """Имена таблицы имён внутри окна: голые идентификаторы и имена со слешем/дефисом."""
    return TOKEN.findall(text)


def window_around(text: str, needle: str, window: int) -> list:
    """Окна текста вокруг каждого вхождения имени (в символах таблицы имён)."""
    found, start = [], 0
    while True:
        at = text.find(needle, start)
        if at == -1:
            return found
        left, right = max(0, at - window), at + len(needle) + window
        chunk = text[left:right]
        found.append({"offset": at,
                      "text": chunk,
                      "neighbours": names_in(chunk)[:120]})
        start = at + 1


def main(argv: list | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--local", default=str(ROOT / "local.paths.json"))
    parser.add_argument("--bin", default="", help="путь к 1cv8.exe (или каталог bin)")
    parser.add_argument("--needle", action="append", default=[],
                        help="имя параметра без слеша, например RunScript (повторяется)")
    parser.add_argument("--window", type=int, default=900)
    parser.add_argument("--json", default="")
    args = parser.parse_args(argv)

    bin_path = pathlib.Path(args.bin) if args.bin else pathlib.Path(
        paths_script.load_local(args.local).get("bin", ""))
    root = bin_path.parent if bin_path.is_file() else bin_path
    if not str(root) or not root.is_dir():
        print("platform_name_table: нужен --bin (или local.paths.json с ключом bin)", file=sys.stderr)
        return 2

    needles = tuple(args.needle) or ("RunScript", "EXECUTE", "TESTMANAGER")
    results = []
    for name in PLATFORM_FILES:
        path = root / name
        if not path.is_file():
            continue
        text = utf16_text(path)
        for needle in needles:
            windows = window_around(text, needle, args.window)
            print("==", name, "|", needle, "|", len(windows), "вхождений")
            for hit in windows[:3]:
                print("   @", hit["offset"])
                print("   соседние имена:", " ".join(hit["neighbours"])[:900])
            results.append({"file": name, "needle": needle, "windows": windows[:3]})
    if args.json:
        out = pathlib.Path(args.json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({"root": root.as_posix(), "needles": list(needles),
                                   "results": results}, ensure_ascii=False, indent=2) + "\n",
                       encoding="utf-8")
        print("замер записан:", out.as_posix())
    return 0 if any(r["windows"] for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
