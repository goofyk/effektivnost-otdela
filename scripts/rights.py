"""Статическая проверка прав ролей по канону, измеренному на корпусах.

Существует по двум наблюдениям проверочного контура:

1. p1c права роли не читает вовсе: `p1c-load model` о ролях и подсистемах молчит, словаря прав
   доступа к объектам в `p1c/src/p1c/data/` нет (`docs/evidence/tool-probe-negative-cases.md`,
   раздел 3). Связку «роль ↔ права ↔ объекты метаданных» контур обязан считать сам.
2. Отказ класса «неканоническое содержимое прав» платформа не объясняет никак:
   `/LoadConfigFromFiles` зависает без вывода и без кода, и единственный наблюдаемый сигнал —
   «шаг не завершился в пределах ожидания» (`docs/evidence/load-bisect.md`). Виновником оказался
   блок `<object><name>Enum.ГрейдыСпециалистов</name>`: по 1672 каноническим файлам прав
   (103 686 блоков `<object>`) блоков вида `Enum.` нет ни одного
   (`probe/corpora_rights_probe.py`, `docs/canonical-rights.json`).

Итог: эта проверка — дешёвая замена отсутствующему инструменту. Она находит поломку до запуска
платформы, вместо того чтобы ждать 30–600 с зависания с пустым выводом.
"""
from __future__ import annotations

import json
import pathlib
import re

import layout                                                    # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_CANON = ROOT / "docs" / "canonical-rights.json"

BLOCK = re.compile(r"<object>\s*<name>([^<]+)</name>(.*?)</object>", re.S)
RIGHT = re.compile(r"<right>\s*<name>([^<]+)</name>\s*<value>(.*?)</value>", re.S)
TOP_FLAGS = re.compile(r"<(setForNewObjects|setForAttributesByDefault|independentRightsOfChildObjects)>"
                       r"([^<]*)<", re.S)

# Вид метаданных -> префикс имени объекта, как его пишет платформа в правах (`Catalog`,
# `InformationRegister`, `CommonAttribute`). Взят обратно из декларации `ChildObjects`: там имена
# видов канонические.
PREFIX_BY_KIND = {}
for _tag, _kind in layout.TAG_KINDS.items():
    PREFIX_BY_KIND.setdefault(_kind, _tag)

# Права в каноне описывают и вложенные объекты: `Catalog.Сотрудники.Command.Отчёт`,
# `HTTPService.Сервис.URLTemplate.Путь.Method.GET`, `Task.Задача.AddressingAttribute.Реквизит`.
# Поэтому «существует ли ссылка» проверяется по владельцу — первым виду и имени объекта.
OWNER_SEGMENTS = 2


def parse_rights(text: str) -> dict:
    """Разобрать один файл прав: блоки `<object>` с правами и три верхних флага файла."""
    objects = []
    for block in BLOCK.finditer(text):
        rights = {}
        for right in RIGHT.finditer(block.group(2)):
            rights[right.group(1)] = right.group(2).strip()
        objects.append({"name": block.group(1).strip(), "rights": rights})
    flags = {match.group(1): match.group(2).strip() for match in TOP_FLAGS.finditer(text)}
    return {"objects": objects, "flags": flags}


def rights_files(cfg_dir) -> dict:
    """Файлы прав конфигурации: относительный путь -> разобранное содержимое."""
    base = pathlib.Path(cfg_dir)
    return {path.relative_to(base).as_posix(): parse_rights(path.read_bytes().decode("utf-8-sig", "replace"))
            for path in sorted(base.rglob("Rights.xml"))}


def owner(name: str) -> str:
    """Владелец имени в правах: `Catalog.Сотрудники.Command.Отчёт` -> `Catalog.Сотрудники`."""
    return ".".join(name.split(".")[:OWNER_SEGMENTS])


def metadata_names(cfg_dir) -> dict:
    """Имена объектов метаданных конфигурации в той форме, в которой их пишут в правах."""
    base = pathlib.Path(cfg_dir)
    names = {}
    configuration = base / "Configuration.xml"
    if configuration.is_file():
        for token in configuration.read_bytes().decode("utf-8-sig", "replace").splitlines():
            match = re.search(r"^\s*<Name>([^<]+)</Name>", token)
            if match:
                names["Configuration." + match.group(1).strip()] = "Configuration.xml"
                break
    for folder, kind in layout.KIND_FOLDERS.items():
        directory = base / folder
        if not directory.is_dir():
            continue
        prefix = PREFIX_BY_KIND.get(kind)
        if not prefix:
            continue
        for path in layout._object_files(base, directory):
            names.setdefault(prefix + "." + path.stem, path.relative_to(base).as_posix())
    return names


def load_canon(path_json=None) -> dict:
    """Канон прав (`docs/canonical-rights.json`); создаёт `probe/corpora_rights_probe.py --json`."""
    path = pathlib.Path(path_json or DEFAULT_CANON)
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def problems_of(files: dict, known: dict, canon: dict) -> list:
    """Находки по правам: неканонический вид объекта, ссылка на отсутствующий объект, выдуманное имя права.

    Пустой канон — отказ проверки, а не «находок нет»: без измеренных чисел нельзя утверждать,
    что чего-то в каноне нет.
    """
    kinds = canon.get("object_kinds") or {}
    if not kinds:
        return ["канон прав не измерен: нужен probe/corpora_rights_probe.py --json "
                "docs/canonical-rights.json (без измеренных чисел нельзя утверждать, "
                "что чего-то в каноне нет)"]
    right_names = canon.get("right_names") or {}
    canonical_files = canon.get("rights_files", 0)
    found = []
    for relative, parsed in sorted(files.items()):
        for obj in parsed["objects"]:
            name = obj["name"]
            kind = name.split(".")[0]
            if kind not in kinds:
                found.append(relative + ": права на метаданные " + kind + " (" + name + "), а по "
                             + str(canonical_files) + " каноническим файлам прав блоков вида "
                             + kind + ". нет ни одного")
            elif known and owner(name) not in known:
                found.append(relative + ": права ссылаются на объект, которого в конфигурации нет: "
                             + name + " (платформа об этом молчит и загружает такую базу дальше)")
            for right_name in sorted(obj["rights"]):
                if right_names and right_name not in right_names:
                    found.append(relative + ": имя права " + right_name + " в объекте " + name
                                 + " не встречается ни в одном каноническом файле прав")
    return found


def check(cfg_dir, canon: dict | None = None) -> dict:
    """Проверка прав одной конфигурации: код 0 — находок нет, 1 — есть, 2 — проверить нельзя."""
    base = pathlib.Path(cfg_dir)
    if not base.is_dir():
        return {"code": 2, "problems": ["каталога конфигурации нет: " + base.as_posix()], "counts": {},
                "objects": {}}
    canon = canon if canon is not None else load_canon()
    files = rights_files(base)
    found = problems_of(files, metadata_names(base), canon)
    counts = {"rights_files": len(files),
              "object_blocks": sum(len(parsed["objects"]) for parsed in files.values()),
              "rights": sum(len(obj["rights"]) for parsed in files.values() for obj in parsed["objects"])}
    objects = {relative: [obj["name"] for obj in parsed["objects"]]
               for relative, parsed in files.items()}
    return {"code": 1 if found else 0, "problems": found, "counts": counts, "objects": objects}


if __name__ == "__main__":
    import sys

    argument = sys.argv[1] if len(sys.argv) > 1 else str(ROOT / "cfg" / "ЭффективностьОтдела")
    result = check(argument)
    print("права роли:", json.dumps({"code": result["code"], "counts": result["counts"]},
                                    ensure_ascii=False))
    for problem in result["problems"]:
        print("  находка:", problem)
    raise SystemExit(result["code"])
