"""Свидетельства из корпусов shipped-конфигураций: какие конструкции BSL платформа принимает.

Нужно чтобы отличать «находку p1c» от «ложной находки p1c»: если конструкция встречается в
конфигурации, которая в этой же платформе загружается и работает, то конструкция валидна, а
диагностику инструмента надо разбирать как ложную.

Замер только читает файлы корпусов (платформу не запускает).
"""
from __future__ import annotations

import collections
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import corpora                                                   # noqa: E402

ROOTS = corpora.dumps()

PATTERNS = {
    "Движения.<регистр>.Заполнять": re.compile(r"Движения\.\S+\.Заполнять\("),
    "implicit attribute (Если Реквизит < …)": re.compile(r"^\s*Если\s+[А-Яа-я][\w]*\s*[<>=]"),
    "Процедура ПередЗаписью(<сигнатура>)": re.compile(r"Процедура\s+ПередЗаписью\s*\(([^)]*)\)"),
    "Процедура ОбработкаПроведения(<сигнатура>)": re.compile(
        r"Процедура\s+ОбработкаПроведения\s*\(([^)]*)\)"),
    "Тернарный оператор ? : вне строковых литералов": re.compile(r"^[^\"|]*[\w\)\]]\s+\?\s+[\w\"]"),
}

# Только модули объектов/менеджеров/форм: именно в них вопрос «разрешено ли обращаться к
# реквизиту без префикса» решает, является диагностика p1c находкой или ложной находкой.
WANTED_FILE_NAMES = ("ObjectModule.bsl", "ManagerModule.bsl", "Module.bsl")
SCAN_LIMIT = 1500


def main(argv: list | None = None) -> None:
    counts = collections.Counter()
    signatures = collections.defaultdict(collections.Counter)
    samples: dict = {}
    files = 0
    for root in ROOTS:
        base = pathlib.Path(root)
        for path in base.rglob("*"):
            if not path.is_file() or path.name not in WANTED_FILE_NAMES:
                continue
            files += 1
            try:
                text = path.read_bytes().decode("utf-8-sig", "replace")
            except OSError:
                continue
            relative = path.relative_to(base).as_posix()
            for name, pattern in PATTERNS.items():
                for line_no, line in enumerate(text.splitlines(), 1):
                    match = pattern.search(line)
                    if not match:
                        continue
                    counts[name] += 1
                    if name.startswith("Процедура"):
                        signatures[name][match.group(1).strip()] += 1
                    if len(samples.setdefault(name, [])) < 3:
                        samples[name].append(relative + ":" + str(line_no) + " "
                                             + line.strip()[:120])
    print("файлов BSL просмотрено:", files)
    for name in PATTERNS:
        print("\n###", name, "—", counts[name])
        for line in samples.get(name, []):
            print("   ", line)
    for name, counter in signatures.items():
        print("\n=== сигнатуры:", name)
        for signature, count in counter.most_common(8):
            print("   ", count, "x", name.split("(")[0].replace("Процедура ", ""), "(", signature, ")")


if __name__ == "__main__":
    main()
