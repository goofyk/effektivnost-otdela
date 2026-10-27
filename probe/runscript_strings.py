"""Где имя `RunScript` встречается в каталоге платформы: все файлы, обе кодировки, соседи.

Зачем. Окно таблицы имён (`probe/platform_name_table.py`) показывает, что в `1cv8.exe` имя
`RunScript` стоит рядом с `/CheckCanApplyConfigurationExtensions`,
`LoadExternalDataProcessorOrReportFromFiles`, `DumpConfigToFiles`, `LoadConfigFromFiles` — то есть
в группе режимов конфигуратора. Это сужение гипотез, но не подтверждение: имя в таблице имён не
описывает ни порядка аргументов, ни режима, который его принимает.

Скрипт ищет имя во всех файлах каталога `bin` в ASCII и UTF-16LE и печатает соседние имена.
Отдельно он печатает полный список имён замера `p1c/src/p1c/data/test_cli_flags.json` — чтобы
выбирать следующую форму запуска из измеренных имён, а не из памяти.

    python probe/runscript_strings.py --needle RunScript
    python probe/runscript_strings.py --needle RunScript --dump-names reports/flags-12-names.json
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from scripts import paths  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
FLAGS_SET = ROOT.parent / "p1c" / "src" / "p1c" / "data" / "test_cli_flags.json"
NAME = re.compile(rb"[A-Za-z][A-Za-z0-9_/]{3,}")


def hits(path: pathlib.Path, needle: str) -> list:
    """Вхождения имени в файле: ASCII и UTF-16LE, с окном текста и соседними именами."""
    data = path.read_bytes()
    found = []
    for label, text in (("ascii", data.decode("latin-1", errors="ignore")),
                        ("utf16", data.decode("utf-16-le", errors="ignore"))):
        start = 0
        while True:
            at = text.find(needle, start)
            if at == -1:
                break
            window = text[max(0, at - 400):at + len(needle) + 400]
            found.append({"encoding": label, "offset": at, "window": window,
                          "neighbours": re.findall(r"[A-Za-z][A-Za-z0-9_/]{3,}", window)[:60]})
            start = at + 1
    return found


def main(argv: list[str]) -> int:
    needle = "RunScript"
    if "--needle" in argv:
        needle = argv[argv.index("--needle") + 1]
    local = paths.load_local(str(ROOT / "local.paths.json"))
    # `local["bin"]` — путь к файлу платформы, а не к каталогу: каталог берём родительский.
    bin_dir = pathlib.Path(local["bin"]).parent
    out = {"needle": needle, "files": {}}
    for file in sorted(bin_dir.iterdir()):
        # Ограничение по размеру нужно, чтобы замер не читал сотни мегабайт ресурсов без нужды:
        # имя параметра встречается в таблицах имён exe/res, а не в больших DLL данных.
        if not file.is_file() or file.stat().st_size > 60 * 1024 * 1024:
            continue
        found = hits(file, needle)
        if found:
            out["files"][file.name] = found
    for name, found in out["files"].items():
        print("==", name)
        for hit in found:
            print("  ", hit["encoding"], "@", hit["offset"])
            print("   соседи:", " ".join(hit["neighbours"]))
    if "--dump-names" in argv:
        target = pathlib.Path(argv[argv.index("--dump-names") + 1])
        data = json.loads(FLAGS_SET.read_text(encoding="utf-8"))
        names = sorted({n for entry in data["files"] for n in entry["names"]})
        target.write_text(json.dumps({"total": len(names), "names": names}, ensure_ascii=False,
                                     indent=2), encoding="utf-8")
        print("имён замера:", len(names), "->", target.as_posix())
    target = ROOT / "reports" / "flags-12-runscript-strings.json"
    target.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print("замер записан:", target.as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
