"""Канон прав роли по выгрузкам корпусов: какие виды объектов и какие имена прав бывает в правах.

Зачем (наблюдение, `docs/evidence/load-bisect.md`): `/LoadConfigFromFiles` не завершается
(30–45 с, 0 байт вывода, кода нет), если в правах роли остаётся блок `<object>` с именем
`Enum.ГрейдыСпециалистов`, даже с единственным правом `Read`. Все остальные блоки прав — на
справочник, документ, оба регистра, отчёт, константу и саму конфигурацию — загружаются за 2 с.

Статическая сверка с корпусами: в канонических файлах прав блоков `Enum.` нет ни разу, хотя блоки
прав на справочники, документы, регистры, константы, отчёты и сами конфигурации встречаются
массово. То есть права на перечисление — не канон 1C, и ловить их должен контур до запуска
платформы: платформа об отказе этого класса не сообщает ничего.

Ни один инструмент p1c прав роли не читает (слепая зона): в `p1c/src/p1c/data/` словаря прав нет,
а `p1c-load model` о ролях и подсистемах молчит.

Замер без платформы, исходник не изменяет. Результат: обычный вывод и (флаг `--json`) файл
канти, который проверяет `scripts/rights.py`.

Использование:
    python probe/corpora_rights_probe.py
    python probe/corpora_rights_probe.py --json docs/canonical-rights.json
    python probe/corpora_rights_probe.py Enum          # подробно только про права перечислений
"""
from __future__ import annotations

import collections
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
CFG = ROOT / "cfg" / "ЭффективностьОтдела"
sys.path.insert(0, str(ROOT / "scripts"))

import corpora                                                   # noqa: E402

CORPORA = corpora.dumps()

# Граница выборки: корпуса содержат сотни ролей с файлами прав; без границы замер не повторяем
# по времени. Порядок выборки — по относительному пути файла прав.
LIMIT_PER_CORPUS = 700

BLOCK = re.compile(r"<object>\s*<name>([^<]+)</name>(.*?)</object>", re.S)
RIGHT = re.compile(r"<right>\s*<name>([^<]+)</name>\s*(.*?)</right>", re.S)
TOP_FLAGS = re.compile(r"<(setForNewObjects|setForAttributesByDefault|independentRightsOfChildObjects)>"
                       r"([^<]*)<", re.S)


def measure() -> dict:
    kinds = collections.Counter()
    names = collections.Counter()
    names_by_kind: dict = collections.defaultdict(collections.Counter)
    values = collections.Counter()
    top_flags = collections.Counter()
    samples: dict = {}
    files = 0
    for root in CORPORA:
        roles = root / "Roles"
        if not roles.is_dir():
            continue
        for path in corpora.files_named([roles], "Rights.xml", LIMIT_PER_CORPUS):
            files += 1
            text = path.read_bytes().decode("utf-8-sig", "replace")
            for match in TOP_FLAGS.finditer(text):
                top_flags[match.group(1) + "=" + match.group(2)] += 1
            for block in BLOCK.finditer(text):
                object_name, body = block.group(1), block.group(2)
                kind = object_name.split(".")[0]
                kinds[kind] += 1
                for right in RIGHT.finditer(body):
                    names[right.group(1)] += 1
                    names_by_kind[kind][right.group(1)] += 1
                    values[re.sub(r"\s+", " ", right.group(2))[:40]] += 1
                if len(samples.setdefault(kind, [])) < 2:
                    samples[kind].append({"where": corpora.relative(path, CORPORA),
                                          "block": re.sub(r"\s+", " ", block.group(0))[:400]})
    return {"rights_files": files, "limit_per_corpus": LIMIT_PER_CORPUS,
            "object_blocks": sum(kinds.values()),
            "object_kinds": dict(kinds.most_common()),
            "right_names": dict(names.most_common()),
            "right_names_by_kind": {kind: dict(counter.most_common(20))
                                    for kind, counter in names_by_kind.items()},
            "top_flags": dict(top_flags.most_common()),
            "samples": samples}


def main(argv: list | None = None) -> int:
    argv = list(argv or [])
    json_out = ""
    if "--json" in argv:
        index = argv.index("--json")
        if index + 1 >= len(argv):
            print("--json без имени файла")
            return 2
        json_out = argv[index + 1]
        argv = argv[:index] + argv[index + 2:]
    only_kind = argv[0] if argv else ""

    report = corpora.report()
    print("корпусов принято к замеру:", len(CORPORA), "|", corpora_keys(CORPORA))
    if report["missing"]:
        print("  пропущено: каталога нет ->", ", ".join(report["missing"]))
    if report["not_a_dump"]:
        print("  пропущено: не выгрузка конфигуратора ->", ", ".join(report["not_a_dump"]))
    data = measure()
    print("файлов прав просмотрено:", data["rights_files"],
          "| выборка не более", data["limit_per_corpus"], "на корпус",
          "| блоков <object>:", data["object_blocks"])

    print("\n== виды объектов в правах (первое слово имени объекта) ==")
    for kind, count in sorted(data["object_kinds"].items(), key=lambda item: -item[1]):
        print("   ", count, "x", kind)

    print("\n== имена прав в каноне (топ-30) ==")
    for name, count in list(data["right_names"].items())[:30]:
        print("   ", count, "x", name)

    print("\n== наши имена прав и объекты против канона ==")
    ours = ours_rights()
    for name, count in sorted(ours["names"].items(), key=lambda item: -item[1]):
        mark = "есть в каноне" if data["right_names"].get(name) else "НЕТ В КАНОНЕ"
        print("   ", count, "x", name, "->", mark)
    for kind, count in sorted(ours["kinds"].items(), key=lambda item: -item[1]):
        mark = data["object_kinds"].get(kind)
        print("   ", count, "x", kind, "->", (str(mark) + " канонических блоков") if mark
              else "НЕТ НИ ОДНОГО КАНОНИЧЕСКОГО БЛОКА")

    print("\n== образцы канонических блоков (по виду объекта) ==")
    for kind in sorted(data["samples"]):
        if only_kind and kind != only_kind:
            continue
        for sample in data["samples"][kind]:
            print("   ", kind, "|", sample["where"])
            print("      ", sample["block"])

    if json_out:
        payload = {"measured_by": "probe/corpora_rights_probe.py",
                   "corpora_accepted": report["accepted"], "corpora_skipped_missing": report["missing"],
                   "corpora_skipped_not_a_dump": report["not_a_dump"],
                   "limit_per_corpus": data["limit_per_corpus"],
                   "rights_files": data["rights_files"], "object_blocks": data["object_blocks"],
                   "object_kinds": data["object_kinds"], "right_names": data["right_names"],
                   "right_names_by_kind": data["right_names_by_kind"], "top_flags": data["top_flags"]}
        target = pathlib.Path(json_out)
        if not target.is_absolute():
            target = pathlib.Path.cwd() / target
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("\nканон записан:", target)
    return 0


def corpora_keys(roots: list) -> str:
    return ", ".join(path.name for path in roots)


def ours_rights() -> dict:
    kinds, names = collections.Counter(), collections.Counter()
    for path in sorted(CFG.rglob("Rights.xml")):
        text = path.read_bytes().decode("utf-8-sig", "replace")
        for block in BLOCK.finditer(text):
            object_name, body = block.group(1), block.group(2)
            kinds[object_name.split(".")[0]] += 1
            for right in RIGHT.finditer(body):
                names[right.group(1)] += 1
    return {"kinds": kinds, "names": names}


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
