"""Статическая проверка прав ролей по канону, измеренному на корпусах.

Существует по трём наблюдениям проверочного контура (доказательства:
`docs/evidence/load-bisect.md`, `docs/evidence/dump-canonicalization.md`):

1. p1c права роли не читает вовсе: `p1c-load model` о ролях и подсистемах молчит, словаря прав
   доступа к объектам в `p1c/src/p1c/data/` нет (`docs/evidence/tool-probe-negative-cases.md`,
   раздел 3). Связку «роль ↔ права ↔ объекты метаданных» контур обязан считать сам.
2. Отказ класса «неканоническое содержимое прав» платформа не объясняет никак: `/LoadConfigFromFiles`
   зависает без вывода и без кода. Виновником оказался блок `<object><name>Enum.ГрейдыСпециалистов</name>`:
   по 1672 каноническим файлам прав (103 686 блоков `<object>`) блоков вида `Enum.` нет ни одного
   (`probe/corpora_rights_probe.py`, `docs/canonical-rights.json`).
3. Платформа молча переписывает состав прав (замер `scripts/rights.py` на исходнике и на выгрузке,
   гейт gate-05): снимает права, совпадающие со значением по умолчанию роли (`setForNewObjects=false`
   и `false`-право; `setForNewObjects=true` и выданное право), снимает имена прав, которых нет у вида
   объекта (`Read` у `Report`, `Set` у `InformationRegister`), и дописывает права, без которых
   интерактивные права не работают (`Edit`, `Posting` для документа).

Итог: эта проверка — дешёвая замена отсутствующему инструменту. Она находит и поломку до запуска
платформы (вместо 30–600 с зависания с пустым выводом), и то, что платформа сделает с нашими правами.

Три проверки:
- `problems_of` — канон вида объекта, существование ссылки, имя права (в том числе внутри вида),
  избыточное значение права, отсутствие верхних флагов;
- `composition` — состав прав одной конфигурации (объект → право → значение);
- `immobile` — неподвижность: состав исходника обязан совпасть с составом выгрузки загруженной базы.
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


def default_value(flags: dict) -> str:
    """Значение права по умолчанию роли: `setForNewObjects=true` — право выдано, иначе — не выдано.

    Измерено корпусами (`docs/canonical-rights.json`, `top_flags`): `setForNewObjects=false` в 1648
    файлах из 1672, `true` в 5. Наблюдение платформы (gate-05): при `false` из выгрузки исчезают
    все `false`-права, при `true` — все выданные права.
    """
    return "true" if flags.get("setForNewObjects") == "true" else "false"


def problems_of(files: dict, known: dict, canon: dict) -> list:
    """Находки по правам: неканонический вид объекта, ссылка на отсутствующий объект, имя права
    (вообще или внутри вида объекта), избыточное значение права, отсутствие верхних флагов.

    Пустой канон — отказ проверки, а не «находок нет»: без измеренных чисел нельзя утверждать,
    что чего-то в каноне нет.
    """
    kinds = canon.get("object_kinds") or {}
    if not kinds:
        return ["канон прав не измерен: нужен probe/corpora_rights_probe.py --json "
                "docs/canonical-rights.json (без измеренных чисел нельзя утверждать, "
                "что чего-то в каноне нет)"]
    right_names = canon.get("right_names") or {}
    names_by_kind = canon.get("right_names_by_kind") or {}
    canonical_files = canon.get("rights_files", 0)
    found = []
    for relative, parsed in sorted(files.items()):
        flags = parsed["flags"]
        if "setForNewObjects" not in flags:
            found.append(relative + ": в файле прав нет флага setForNewObjects: по "
                         + str(canonical_files) + " каноническим файлам он есть всегда, и без него "
                               "нельзя сказать, какое значение права платформа сочтёт избыточным")
        redundant_by_object = {}
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
            allowed = names_by_kind.get(kind) or right_names
            blocks_of_kind = kinds.get(kind, 0)
            for right_name in sorted(obj["rights"]):
                if allowed and right_name not in allowed:
                    found.append(relative + ": имя права " + right_name + " в объекте " + name
                                 + " не встречается ни в одном из " + str(blocks_of_kind)
                                 + " канонических блоков вида " + kind
                                 + " — платформа его снимает (наблюдение gate-05: `Read` у отчёта, "
                                   "`Set` у регистра сведений)")
            default = default_value(flags)
            same_default = sorted(right_name for right_name, value in obj["rights"].items()
                                  if value == default)
            if same_default:
                redundant_by_object[name] = same_default
        if redundant_by_object:
            default = default_value(flags)
            found.append(relative + ": права со значением " + default + " ("
                         + "; ".join(name + ": " + ", ".join(names)
                                     for name, names in sorted(redundant_by_object.items()))
                         + ") совпадают со значением по умолчанию роли (setForNewObjects="
                         + flags.get("setForNewObjects", "(нет)") + ") — платформа выбрасывает их при "
                           "загрузке, и состав выгрузки не совпадёт с исходником; канонический стиль "
                           "роли: описывать только выдаваемые права")
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


def composition(cfg_dir) -> dict:
    """Состав прав конфигурации: относительный файл прав -> имя объекта -> {право: значение}.

    Именно в этом виде сравнение исходника и выгрузки не зависит от порядка прав и от перевода строк.
    """
    return {relative: {obj["name"]: obj["rights"] for obj in parsed["objects"]}
            for relative, parsed in rights_files(cfg_dir).items()}


def immobile(source_dir, dump_dir, canon: dict | None = None) -> dict:
    """Неподвижность прав: что написано в исходнике, то и осталось в выгрузке загруженной базы.

    Наблюдение gate-05: исходник 8 блоков / 43 права, выгрузка 6 блоков / 19 прав. Пока составы не
    совпадают, намерение роли нельзя считать зафиксированным, и формулировка «права роли настроены»
    не допускается (это же закреплено в `docs/evidence/dump-canonicalization.md`).
    """
    if not pathlib.Path(source_dir).is_dir():
        return {"code": 2, "problems": ["исходника конфигурации нет: " + str(source_dir)],
                "dropped": [], "added": []}
    if not pathlib.Path(dump_dir).is_dir():
        return {"code": 2, "problems": ["выгрузки загруженной базы нет: " + str(dump_dir)
                                        + " (нужен шаг платформы dump)"], "dropped": [], "added": []}
    source, dump = composition(source_dir), composition(dump_dir)
    dropped, added = [], []
    for relative in sorted(set(source) | set(dump)):
        left, right = source.get(relative, {}), dump.get(relative, {})
        for object_name in sorted(set(left) | set(right)):
            left_rights, right_rights = left.get(object_name), right.get(object_name)
            if left_rights is None:
                added.append(relative + ": платформа добавила блок " + object_name
                             + " (права: " + ", ".join(sorted(right_rights)) + "), которого в "
                               "исходнике нет")
                continue
            if right_rights is None:
                dropped.append(relative + ": блок " + object_name + " исчез из выгрузки целиком ("
                               + str(len(left_rights)) + " прав)")
                continue
            for right_name in sorted(set(left_rights) - set(right_rights)):
                dropped.append(relative + ": право " + right_name + " объекта " + object_name
                               + " (значение " + left_rights[right_name] + ") платформа не сохранила")
            for right_name in sorted(set(right_rights) - set(left_rights)):
                added.append(relative + ": платформа добавила право " + right_name + " объекта "
                             + object_name + " (значение " + right_rights[right_name]
                             + "), которого в исходнике нет")
            for right_name in sorted(set(left_rights) & set(right_rights)):
                if left_rights[right_name] != right_rights[right_name]:
                    dropped.append(relative + ": право " + right_name + " объекта " + object_name
                                   + " сменило значение " + left_rights[right_name] + " -> "
                                   + right_rights[right_name])
    counts = {"source_blocks": sum(len(item) for item in source.values()),
              "dump_blocks": sum(len(item) for item in dump.values()),
              "source_rights": sum(len(rights) for item in source.values() for rights in item.values()),
              "dump_rights": sum(len(rights) for item in dump.values() for rights in item.values())}
    problems = dropped + added
    return {"code": 1 if problems else 0, "problems": problems, "dropped": dropped, "added": added,
            "counts": counts}


if __name__ == "__main__":
    import sys

    argument = sys.argv[1] if len(sys.argv) > 1 else str(ROOT / "cfg" / "ЭффективностьОтдела")
    result = check(argument)
    print("права роли:", json.dumps({"code": result["code"], "counts": result["counts"]},
                                    ensure_ascii=False))
    for problem in result["problems"]:
        print("  находка:", problem)
    raise SystemExit(result["code"])
