"""Поиск в бинарнике платформы имён файлов выгрузки внешних обработок/отчётов.

Идея: команда `/DumpExternalDataProcessorOrReportToFiles` печатает «Формат: Иерархический»,
значит выгрузка — каталог с корневым файлом. Имя корневого файла — константа платформы; её можно
найти в таблице строк рядом с упоминаниями ExternalDataProcessor.
"""
import pathlib
import re
import sys

BIN_DIR = pathlib.Path(sys.argv[1])
PATTERN = re.compile(r"[\w\-\.]{3,60}\.(?:xml|cf|cfe|bin)", re.ASCII | re.IGNORECASE)

targets = [BIN_DIR / "1cv8.exe", BIN_DIR / "1cv8c.exe", BIN_DIR / "mngui.dll",
           BIN_DIR / "backbas.dll", BIN_DIR / "compiler.dll"]
found = {}
for path in targets:
    if not path.is_file():
        print("нет файла:", path.as_posix())
        continue
    data = path.read_bytes()
    hits = set()
    # UTF-16LE: символы чередуются с нулём.
    wide = data.decode("utf-16-le", errors="ignore")
    for match in PATTERN.finditer(wide):
        name = match.group(0)
        if len(name) > 60:
            continue
        hits.add(name)
    # Обычная ASCII-таблица строк.
    for match in PATTERN.finditer(data.decode("latin-1", errors="ignore")):
        hits.add(match.group(0))
    interesting = sorted(name for name in hits
                         if re.search(r"external|export|settings|processor|report|dump|ext",
                                      name, re.IGNORECASE))
    print(f"== {path.name}: всего имён файлов {len(hits)}, релевантных {len(interesting)}")
    for name in interesting:
        print("   ", name)
        found.setdefault(name.lower(), []).append(path.name)

print()
print("== имена, найденные в нескольких файлах:")
for name, files in sorted(found.items()):
    if len(set(files)) > 1:
        print("   ", name, "->", sorted(set(files)))
