"""Чем канонические роли заполняют блок `Configuration.<имя>` — и почему платформа добавила туда `DataAdministration`.

Зачем. Замер гейта gate-06 (единственное расхождение неподвижности прав зелёной итерации):
в исходнике блок `Configuration.ЭффективностьОтдела` содержит девять прав
(`Administration, Automation, ConfigurationExtensionsAdministration, ExternalConnection,
InteractiveOpenExtDataProcessors, InteractiveOpenExtReports, TechnicalSpecialistMode, ThickClient,
UpdateDataBaseConfiguration`), в выгрузке их десять — платформа дописала `DataAdministration`.
Вопрос: каноническое ли это право в этом блоке (тогда его надо писать самим, и состав исходника
совпадёт с выгрузкой) или платформенная добавка, которую в исходнике писать нельзя.

Замер по блокам `Configuration.` канонических выгрузок корпусов считает:
- какие имена прав встречаются в блоке и с каким значением;
- как часто `Administration` и `DataAdministration` стоят вместе;
- как часто `DataAdministration` встречается без `Administration`.

Платформу не запускает, исходник не изменяет. Вывод — числа и относительные пути свидетельств.
"""
from __future__ import annotations

import collections
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import corpora                                                   # noqa: E402

ROOTS = corpora.dumps()

BLOCK = re.compile(r"<object>\s*<name>(Configuration\.[^<]+)</name>(.*?)</object>", re.S)
RIGHT = re.compile(r"<right>\s*<name>([^<]+)</name>\s*<value>(.*?)</value>", re.S)

LIMIT_PER_CORPUS = 700


def main(argv: list | None = None) -> int:
    argv = list(argv or [])
    out_json = pathlib.Path(argv[argv.index("--json") + 1]) if "--json" in argv else None

    names = collections.Counter()
    values = collections.Counter()
    pairs = collections.Counter()
    samples: dict = {}
    files_seen = blocks_seen = 0
    for root in ROOTS:
        roles = root / "Roles"
        if not roles.is_dir():
            continue
        for path in corpora.files_named([roles], "Rights.xml", LIMIT_PER_CORPUS):
            files_seen += 1
            text = path.read_bytes().decode("utf-8-sig", "replace")
            for block in BLOCK.finditer(text):
                blocks_seen += 1
                granted = {right.group(1): right.group(2).strip()
                           for right in RIGHT.finditer(block.group(2))}
                for name, value in granted.items():
                    names[name] += 1
                    values[(name, value)] += 1
                    if len(samples.setdefault((name, value), [])) < 2:
                        samples[(name, value)].append(
                            corpora.relative(path, ROOTS) + " -> " + block.group(1).strip())
                admin = granted.get("Administration") == "true"
                data = granted.get("DataAdministration") == "true"
                pairs["Administration без DataAdministration" if admin and not data else
                      "DataAdministration без Administration" if data and not admin else
                      "оба права" if admin and data else "ни одного из двух"] += 1

    print("файлов прав просмотрено:", files_seen, "| блоков Configuration.:", blocks_seen,
          "| выборка не более", LIMIT_PER_CORPUS, "файлов на корпус")
    print("\n== имена прав блока Configuration. (блоков, из них true)")
    for name, count in names.most_common():
        print("   ", name.ljust(40), str(count).rjust(6),
              "| true:", values[(name, "true")], "| false:", values[(name, "false")])
    print("\n== сочетание Administration и DataAdministration")
    for key, count in pairs.most_common():
        print("   ", key.ljust(38), count)
    print("\n== свидетельства")
    for key in ("Administration", "DataAdministration"):
        for (name, value), found in samples.items():
            if name == key:
                print("   ", name, value, "->", found[0])
    if out_json:
        out_json.parent.mkdir(parents=True, exist_ok=True)
        out_json.write_text(json.dumps(
            {"rights_files": files_seen, "configuration_blocks": blocks_seen,
             "right_names": dict(names.most_common()),
             "right_values": {name + "|" + value: count for (name, value), count in values.items()},
             "administration_pairs": dict(pairs),
             "samples": {"|".join(key): found for key, found in samples.items()
                         if key[0] in ("Administration", "DataAdministration")}},
            ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("\nзамер записан:", out_json.as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
