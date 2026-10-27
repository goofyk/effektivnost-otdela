"""Как канонические выгрузки описывают qualifiers числового типа (и что делает платформа с нашими).

Найденный дефект (гейт gate-04, `probe/dump_vs_source.py`): мы написали

    <v8:Type><xs:decimal/><v8:DecimalQualifiers><v8:Precision>2</v8:Precision></v8:DecimalQualifiers>

а в выгрузке из базы, куда эта конфигурация загрузилась (код 0), лежит

    <v8:NumberQualifiers><v8:Digits>0</v8:Digits><v8:FractionDigits>0</v8:FractionDigits><v8:AllowedSign>Any</v8:AllowedSign>

То есть платформе наш узел понятен не был: загрузка прошла молча, дробная разрядность `Часы`
стала нулевой. Ни один инструмент p1c этого не видит: `p1c-load model` qualifier'ы реквизитов не
сравнивает, а `p1c-diff` сравнивает модели метаданных, а не файлы.

Замер по корпусам: какие узлы qualifiers встречаются в канонических выгрузках и с какими числами.

Платформу замер не запускает, исходник не изменяет.
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

CHECKS = {
    "v8:NumberQualifiers": re.compile(r"<v8:NumberQualifiers>"),
    "v8:DecimalQualifiers": re.compile(r"<v8:DecimalQualifiers>"),
    "v8:Digits": re.compile(r"<v8:Digits>(\d*)</v8:Digits>"),
    "v8:FractionDigits": re.compile(r"<v8:FractionDigits>(\d*)</v8:FractionDigits>"),
    "v8:Precision": re.compile(r"<v8:Precision>(\d*)</v8:Precision>"),
    "v8:AllowedSign": re.compile(r"<v8:AllowedSign>([^<]*)</v8:AllowedSign>"),
    "xs:decimal как тип": re.compile(r"<v8:Type[^>]*>xs:decimal</v8:Type>|<xs:decimal/>"),
}

SCAN_LIMIT = 3000
WANTED = ("*.xml",)


def main(argv: list | None = None) -> int:
    counts = collections.Counter()
    digits = collections.Counter()
    fraction = collections.Counter()
    precision = collections.Counter()
    signs = collections.Counter()
    samples: dict = {}
    files = 0
    for root in ROOTS:
        for path in corpora.wanted_files(root, WANTED, SCAN_LIMIT):
            files += 1
            text = path.read_bytes().decode("utf-8-sig", "replace")
            for name, pattern in CHECKS.items():
                matches = list(pattern.finditer(text))
                if not matches:
                    continue
                counts[name] += len(matches)
                if name == "v8:Digits":
                    digits[matches[0].group(1)] += 1
                if name == "v8:FractionDigits":
                    fraction[matches[0].group(1)] += 1
                if name == "v8:Precision":
                    precision[matches[0].group(1)] += 1
                if name == "v8:AllowedSign":
                    signs[matches[0].group(1)] += 1
                if len(samples.setdefault(name, [])) < 2:
                    match = matches[0]
                    line_start = text.rfind("\n", 0, match.start()) + 1
                    line_end = text.find("\n", match.end())
                    samples[name].append((corpora.relative(path, ROOTS),
                                          re.sub(r"\s+", " ", text[line_start:max(line_end, line_start)][:120])))
    print("xml-файлов просмотрено:", files, "| выборка не более", SCAN_LIMIT, "на корпус")
    for name in CHECKS:
        print("\n==", name, "| встреч:", counts.get(name, 0))
        for place, line in samples.get(name, []):
            print("   ", place)
            print("      ", line)
    print("\n== первые значения Digits в файле ==")
    for value, count in digits.most_common(8):
        print("   ", count, "x", value)
    print("\n== первые значения FractionDigits в файле ==")
    for value, count in fraction.most_common(8):
        print("   ", count, "x", value)
    print("\n== первые значения Precision в файле ==")
    for value, count in precision.most_common(8):
        print("   ", count, "x", value)
    print("\n== AllowedSign ==")
    for value, count in signs.most_common(5):
        print("   ", count, "x", value)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
