"""Сверка имён прав в наших ролях с именами прав в канонических выгрузках корпусов.

Найдено биновидным замером загрузки: конфигурация без ролей загружается за 2 с кодом 0, а с ролями
`/LoadConfigFromFiles` не завершается вовсе (45 с, 0 байт вывода). Значит поломка — в файлах ролей.
Форма `Roles/<Имя>.xml` при этом побайтово совпадает по составу элементов с канонической выгрузкой
UH, поэтому проверять надо содержимое `Ext/Rights.xml`: имена объектов и имена прав.

Находкой считается имя прав, которого нет ни в одной канонической выгрузке (объединение, чтобы
не путать редкое, но законное право с придуманным).
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

# Выборка ограничена и упорядочена по относительному пути: числа наблюдения обязаны
# воспроизводиться на машине с другими каталогами корпусов.
LIMIT_PER_CORPUS = 400

RIGHT_BLOCK = re.compile(r"<right>\s*<name>([^<]+)</name>\s*<value>(.*?)</value>", re.S)
OBJECT_NAME = re.compile(r"<object>\s*<name>([^<]+)</name>", re.S)


def canonical_rights() -> tuple:
    names = collections.Counter()
    files = 0
    for root in CORPORA:
        roles = pathlib.Path(root) / "Roles"
        if not roles.is_dir():
            continue
        taken = sorted(roles.rglob("Ext/Rights.xml"), key=lambda p: p.stat().st_size)[:LIMIT_PER_CORPUS]
        for path in taken:
            files += 1
            text = path.read_bytes().decode("utf-8-sig", "replace")
            for match in RIGHT_BLOCK.finditer(text):
                names[match.group(1)] += 1
    return names, files


def main(argv: list | None = None) -> int:
    canonical, used = canonical_rights()
    print("канонических файлов прав просмотрено:", used, "| уникальных имён прав:", len(canonical))

    ours = collections.Counter()
    objects = collections.Counter()
    our_files = {}
    for path in sorted(CFG.rglob("Ext/Rights.xml")):
        text = path.read_bytes().decode("utf-8-sig", "replace")
        our_files[path.relative_to(CFG).as_posix()] = text
        for match in RIGHT_BLOCK.finditer(text):
            ours[match.group(1)] += 1
        for match in OBJECT_NAME.finditer(text):
            objects[match.group(1)] += 1

    print("\n== наши имена прав ==")
    for name, count in ours.most_common():
        mark = "есть в каноне" if canonical.get(name) else "НЕТ В КАНОНЕ"
        print("  ", count, "x", name, "->", mark)

    print("\n== наши имена объектов в правах ==")
    for name, count in objects.most_common():
        print("  ", count, "x", name)

    print("\n== значения <value>, которые мы пишем ==")
    values = collections.Counter()
    for text in our_files.values():
        for match in RIGHT_BLOCK.finditer(text):
            values[re.sub(r"\s+", " ", match.group(2))[:60]] += 1
    for value, count in values.most_common(10):
        print("  ", count, "x", value)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
