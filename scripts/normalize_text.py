"""Приведение текстовых файлов конфигурации к кодировке и концам строк платформы.

Наблюдение (корпуса и выгрузка 8.3.27): файлы метаданных и модулей — UTF-8 с BOM и CRLF.
Для модулей BSL это не косметика: без BOM платформа читает файл как ANSI (cp1251), и кириллица
в процедурах превращается в мусор, что даёт синтаксические ошибки вместо ошибок логики.

Скрипт меняет только способ записи байтов: кодировку (UTF-8 + BOM) и концы строк (CRLF).
Содержимое — те же символы, что были; имена файлов и структура каталога не меняются.
"""
from __future__ import annotations

import pathlib
import sys

SUFFIXES = (".xml", ".bsl")


def normalize(directory) -> dict:
    """(изменено, уже было как в платформе) — по текстовым файлам конфигурации."""
    changed = 0
    same = 0
    for path in sorted(p for p in pathlib.Path(directory).rglob("*") if p.is_file()):
        if path.suffix not in SUFFIXES:
            continue
        data = path.read_bytes()
        text = data.decode("utf-8-sig", "strict") if data[:3] == b"\xef\xbb\xbf" \
            else data.decode("utf-8", "strict")
        wanted = b"\xef\xbb\xbf" + text.replace("\r\n", "\n").replace("\n", "\r\n").encode("utf-8")
        if wanted != data:
            path.write_bytes(wanted)
            changed += 1
        else:
            same += 1
    return {"changed": changed, "already_canonical": same}


def main(argv: list) -> int:
    if len(argv) < 1:
        print("употребление: python scripts/normalize_text.py <каталог конфигурации>")
        return 2
    result = normalize(argv[0])
    print("кодировка конфигурации: изменено " + str(result["changed"])
          + ", уже как в платформе " + str(result["already_canonical"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
