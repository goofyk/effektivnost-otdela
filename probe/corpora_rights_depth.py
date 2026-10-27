"""Чьими правами на самом деле являются «права вида» в канонических ролях: верхний объект или ребёнок.

Зачем. Платформа переписывает написанные нами права (`docs/evidence/dump-canonicalization.md`,
класс 5): для `Catalog.Сотрудники` из восьми написанных прав остались `Read, View, InputByString`
(сняты `Update`, `Insert`, `Delete`, `InteractiveInsert`, `InteractiveDelete`), для
`Constant.НормаЧасовВМесяц` из `Read, Update` остался `Read`, для
`InformationRegister.ПланЗагрузки` из `Read, Set, Update, View` остались `Read, View`. При этом в
измеренном каноне все эти имена прав у соответствующих видов есть (`docs/canonical-rights.json`,
`right_names_by_kind`: `Catalog.Update` 3416, `Constant.Update` 2118,
`InformationRegister.Update` 4129). Значит имя права каноническое, но платформа его не приняла.

Гипотеза, которую проверяет этот замер: в канонических ролях `Update`/`Insert`/`Delete` у вида
`Catalog`/`Constant`/`InformationRegister` стоят **не на верхнем объекте**, а на его детях —
табличных частях, реквизитах, командных панелях: имена вида
`Catalog.Сотрудники.TabularSection.История`, `Catalog.Сотрудники.Attribute.Ставка`,
`Catalog.Сотрудники.Command.Отчёт`. Тогда «канонический Update справочника» — это право на табличную
часть, а не на справочник целиком, и писать его в блоке верхнего объекта неканонично.

Замер разделяет блоки `<object>` по глубине имени (2 сегмента — сам объект; 4 и больше — ребёнок) и
считает, у каких прав какое значение встречается в какой глубине. Платформу не запускает, исходник
не изменяет.
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

BLOCK = re.compile(r"<object>\s*<name>([^<]+)</name>(.*?)</object>", re.S)
RIGHT = re.compile(r"<right>\s*<name>([^<]+)</name>\s*<value>(.*?)</value>", re.S)

KINDS = ("Catalog", "Document", "InformationRegister", "AccumulationRegister", "Constant", "Report")

# Имена прав, из-за которых спор: их платформа сняла с наших верхних объектов.
WANTED_RIGHTS = ("Update", "Insert", "Delete", "InteractiveInsert", "InteractiveDelete",
                 "InteractiveSetDeletionMark", "InteractiveClearDeletionMark", "Edit", "Read",
                 "View", "InputByString", "Set", "Posting", "TotalsControl", "Use")

LIMIT_PER_CORPUS = 700


def depth_of(name: str) -> int:
    """Сколько сегментов в имени объекта прав: `Catalog.Сотрудники` -> 2,
    `Catalog.Сотрудники.TabularSection.История` -> 4."""
    return len(name.split("."))


def main(argv: list | None = None) -> int:
    counts = {(kind, right, bucket): 0 for kind in KINDS for right in WANTED_RIGHTS
              for bucket in ("верхний объект", "ребёнок")}
    blocks = collections.Counter()
    samples: dict = {}
    files_seen = 0
    for root in ROOTS:
        roles = root / "Roles"
        if not roles.is_dir():
            continue
        for path in corpora.files_named([roles], "Rights.xml", LIMIT_PER_CORPUS):
            files_seen += 1
            text = path.read_bytes().decode("utf-8-sig", "replace")
            for block in BLOCK.finditer(text):
                name = block.group(1).strip()
                kind = name.split(".")[0]
                if kind not in KINDS:
                    continue
                blocks[kind] += 1
                bucket = "верхний объект" if depth_of(name) == 2 else "ребёнок"
                for right in RIGHT.finditer(block.group(2)):
                    right_name = right.group(1)
                    if right_name not in WANTED_RIGHTS or right.group(2).strip() != "true":
                        continue
                    key = (kind, right_name, bucket)
                    counts[key] += 1
                    if len(samples.setdefault(key, [])) < 2:
                        samples[key].append(corpora.relative(path, ROOTS) + " -> " + name)

    print("файлов прав просмотрено:", files_seen, "| выборка не более", LIMIT_PER_CORPUS,
          "файлов на корпус")
    for kind in KINDS:
        print("\n== вид", kind, "| блоков:", blocks[kind])
        for right in WANTED_RIGHTS:
            top = counts[(kind, right, "верхний объект")]
            child = counts[(kind, right, "ребёнок")]
            if not top and not child:
                continue
            print("   ", right.ljust(28), "на верхнем объекте:", str(top).rjust(6),
                  "| на ребёнке:", child)
            if top and not child:
                print("       (только верхний объект; примеры:", *samples[(kind, right, "верхний объект")][:1], ")")
            if child:
                print("       примеры ребёнка:", *samples[(kind, right, "ребёнок")][:1])
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
