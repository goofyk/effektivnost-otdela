"""Как канонические роли описывают права одного объекта: наборы имён прав и их совместность.

Зачем. Наблюдение гейта gate-05 (`docs/evidence/dump-canonicalization.md`, класс 5): платформа
переписывает написанные нами права. Для `Catalog.Сотрудники` мы написали восемь прав
(`Delete, InputByString, Insert, InteractiveDelete, InteractiveInsert, Read, Update, View`), а в
выгрузке из загруженной базы осталось три (`Read, View, InputByString`). Для
`Document.ФактРаботы` платформа, наоборот, **добавила** `Edit` и `Posting` и сняла `Delete` и
`InteractiveDelete`. Имена при этом канонические: они встречаются в измеренном каноне
(`docs/canonical-rights.json`, `right_names_by_kind`), значит дело не в опечатке имён, а в
**совместности прав внутри одного блока**.

Замер отвечает на вопрос без запуска платформы: какие права в каноне стоят вместе.

1. Для каждого вида объекта: самые частые наборы прав со значением `true` в одном блоке.
2. Для каждого имени права `R` этого вида: в скольких блоках `R=true` встречается вместе с
   `Edit=true` / `Read=true` / `View=true`, а в скольких — без него. Это и есть проверка гипотезы
   «`Update`/`Insert`/`Delete`/интерактивные права держатся только при наличии `Edit`»: если без
   `Edit` таких блоков практически нет, то наша роль потеряла их законно, и каноническое написание
   роли — начинать блок с `Edit`.
3. Сохраняет измеренный канон совместности в JSON (`--json`), чтобы контур мог проверять им
   исходник статически, до 30–600 с зависания платформы.

Платформу замер не запускает, исходник не изменяет.
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

BLOCK = re.compile(r"<object>\s*<name>([^<]+)</name>(.*?)</object>", re.S)
RIGHT = re.compile(r"<right>\s*<name>([^<]+)</name>\s*<value>(.*?)</value>", re.S)

# Виды, по которым замеряем совместность: те, что есть в нашей конфигурации.
KINDS = ("Catalog", "Document", "InformationRegister", "AccumulationRegister", "Constant", "Report",
         "Configuration")

# Права-«условия», по которым проверяем совместность (все три встречаются в каноне у всех видов).
CONDITIONS = ("Edit", "Read", "View")

LIMIT_PER_CORPUS = 700


def blocks_of(text: str, kind: str) -> list:
    """Блоки `<object>` нужного вида: (имя объекта, {имя права: значение})."""
    result = []
    for block in BLOCK.finditer(text):
        name = block.group(1).strip()
        if name.split(".")[0] != kind:
            continue
        rights = {right.group(1): right.group(2).strip() for right in RIGHT.finditer(block.group(2))}
        result.append((name, rights))
    return result


def main(argv: list | None = None) -> int:
    argv = list(argv or [])
    out_json = None
    if "--json" in argv:
        out_json = pathlib.Path(argv[argv.index("--json") + 1])
        argv = [item for index, item in enumerate(argv) if index not in (argv.index("--json"),
                                                                        argv.index("--json") + 1)]
    wanted = tuple(argv) or KINDS

    report = {"measured_by": "probe/corpora_rights_patterns.py",
              "corpora_accepted": corpora.report()["accepted"],
              "limit_per_corpus": LIMIT_PER_CORPUS,
              "kinds": {}}
    files_seen = 0
    for root in ROOTS:
        roles = root / "Roles"
        if not roles.is_dir():
            continue
        for path in corpora.files_named([roles], "Rights.xml", LIMIT_PER_CORPUS):
            files_seen += 1
            text = path.read_bytes().decode("utf-8-sig", "replace")
            for kind in wanted:
                for name, rights in blocks_of(text, kind):
                    granted = sorted(key for key, value in rights.items() if value == "true")
                    entry = report["kinds"].setdefault(
                        kind, {"blocks": 0, "granted_sets": collections.Counter(),
                               "rights": collections.Counter(),
                               "with": {condition: collections.Counter() for condition in CONDITIONS},
                               "without": {condition: collections.Counter() for condition in CONDITIONS},
                               "samples": {}})
                    entry["blocks"] += 1
                    entry["granted_sets"][", ".join(granted)] += 1
                    for right_name in granted:
                        entry["rights"][right_name] += 1
                        for condition in CONDITIONS:
                            if right_name == condition:
                                continue
                            bucket = "with" if rights.get(condition) == "true" else "without"
                            entry[bucket][condition][right_name] += 1
                    key = ", ".join(granted)
                    if key not in entry["samples"]:
                        entry["samples"][key] = corpora.relative(path, ROOTS)

    print("файлов прав просмотрено:", files_seen, "| выборка не более", LIMIT_PER_CORPUS,
          "файлов на корпус на вид")
    for kind in wanted:
        entry = report["kinds"].get(kind) or {}
        print("\n== вид", kind, "| блоков:", entry.get("blocks", 0))
        granted = entry.get("rights") or {}
        if not granted:
            print("    блоков этого вида в выборке нет")
            continue
        print("   самые частые наборы разрешённых прав (true):")
        for pattern, count in entry["granted_sets"].most_common(10):
            print("     ", count, "x [", pattern or "(ни одного права со значением true)", "]")
            print("        ", entry["samples"].get(pattern, ""))
        print("   совместность: право | есть условие | нет условия")
        for right_name, count in granted.most_common(12):
            row = [f"{right_name}: {count}"]
            for condition in CONDITIONS:
                if right_name == condition:
                    continue
                row.append(f"{condition}={entry['with'][condition].get(right_name, 0)}"
                           f"/{entry['without'][condition].get(right_name, 0)}")
            print("     ", " | ".join(row))

    if out_json:
        plain = {"measured_by": report["measured_by"],
                 "corpora_accepted": report["corpora_accepted"],
                 "limit_per_corpus": report["limit_per_corpus"],
                 "rights_files": files_seen,
                 "kinds": {kind: {
                     "blocks": entry["blocks"],
                     "granted_sets": dict(entry["granted_sets"].most_common(40)),
                     "rights": dict(entry["rights"]),
                     "with": {condition: dict(counts) for condition, counts in entry["with"].items()},
                     "without": {condition: dict(counts) for condition, counts in
                                 entry["without"].items()},
                 } for kind, entry in report["kinds"].items()}}
        out_json.write_text(json.dumps(plain, ensure_ascii=False, indent=1), encoding="utf-8")
        print("\nканон совместности прав записан:", out_json.as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
