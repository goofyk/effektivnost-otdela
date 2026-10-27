"""Как канонические роли пользуются тремя верхними флагами файла прав и что это даёт их составу.

Зачем. Наблюдение гейта gate-05 (`docs/evidence/dump-canonicalization.md`, класс 5) теперь объяснён
измерением, а не догадкой:

1. Платформа выбрасывает из выгрузки права со значением `false` (`Catalog.Сотрудники` мы писали
   `Insert/Update/Delete/InteractiveInsert/InteractiveDelete = false`, в выгрузке их нет) и выбрасывает
   блоки, где таких прав только много (`Configuration.ЭффективностьОтдела` у роли `СотрудникОтдела`:
   все пять прав `false` — блок исчез целиком).
2. Роль `АдминистраторСистемы` с `setForNewObjects=true` в нашей выгрузке осталась **без блоков
   вообще** (8 написанных прав → 0).

Вопрос, на который отвечает этот замер: бывает ли в каноне роль с `setForNewObjects=true` и при этом
с описанными блоками прав, и как выглядит каноническая системная роль `АдминистраторСистемы`
(её флаги и размер состава). От ответа зависит, что писать в наших двух ролях: явные права или
положиться на флаг.

Замер по каноническим выгрузкам, без платформы:
- по всем файлам прав: три верхних флага и число блоков с хотя бы одним правом `true`;
- отдельно роль `АдминистраторСистемы` (её канонический uuid тоже измеряется — у нас выдуманный);
- отдельно все файлы с `setForNewObjects=true`.

Исходник не изменяется, абсолютные пути корпусов в вывод не пишутся (только относительные пути
внутри корпуса и имена ключей корпусов).
"""
from __future__ import annotations

import collections
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import corpora                                                   # noqa: E402
import rights                                                    # noqa: E402

ROOTS = corpora.dumps()

FLAG = re.compile(r"<(setForNewObjects|setForAttributesByDefault|independentRightsOfChildObjects)>"
                  r"([^<]*)<", re.S)
UUID = re.compile(r"<uuid>([^<]+)</uuid>", re.S)

LIMIT_PER_CORPUS = 700


def main(argv: list | None = None) -> int:
    flag_sets = collections.Counter()
    by_flag = collections.defaultdict(collections.Counter)
    admin_rows = []
    admin_uuids = collections.Counter()
    admin_flag_sets = collections.Counter()
    admin_blocks_with_true = collections.Counter()
    files_seen = 0
    for root in ROOTS:
        roles = root / "Roles"
        if not roles.is_dir():
            continue
        for path in corpora.files_named([roles], "Rights.xml", LIMIT_PER_CORPUS):
            files_seen += 1
            text = path.read_bytes().decode("utf-8-sig", "replace")
            flags = {match.group(1): match.group(2).strip() for match in FLAG.finditer(text)}
            parsed = rights.parse_rights(text)
            granted_blocks = sum(1 for obj in parsed["objects"]
                                 if any(value == "true" for value in obj["rights"].values()))
            denied_only = sum(1 for obj in parsed["objects"]
                              if obj["rights"] and not any(v == "true" for v in obj["rights"].values()))
            key = " ".join(name + "=" + flags.get(name, "(нет)") for name in
                           ("setForNewObjects", "setForAttributesByDefault",
                            "independentRightsOfChildObjects"))
            flag_sets[key] += 1
            by_flag["setForNewObjects=" + flags.get("setForNewObjects", "(нет)")][
                "блоков с правом true: " + str(granted_blocks)] += 1
            by_flag["setForNewObjects=" + flags.get("setForNewObjects", "(нет)")][
                "блоков только со false-правами: " + str(denied_only)] += 1

            relative = path.relative_to(roles).as_posix()
            if relative.startswith("АдминистраторСистемы/"):
                role_dir = roles / "АдминистраторСистемы"
                role_xml = role_dir / "Ext" / "Role.xml"
                if not role_xml.is_file():
                    role_xml = roles.parent / "Roles" / "АдминистраторСистемы.xml"
                if role_xml.is_file():
                    match = UUID.search(role_xml.read_bytes().decode("utf-8-sig", "replace"))
                    if match:
                        admin_uuids[match.group(1).strip()] += 1
                admin_flag_sets[key] += 1
                admin_blocks_with_true[granted_blocks] += 1
                if len(admin_rows) < 6:
                    admin_rows.append((corpora.relative(root, ROOTS), relative, key,
                                       len(parsed["objects"]), granted_blocks, denied_only))

    print("файлов прав просмотрено:", files_seen, "| выборка не более", LIMIT_PER_CORPUS,
          "файлов на корпус")
    print("\n== сочетания трёх верхних флагов ==")
    for key, count in flag_sets.most_common(10):
        print("   ", count, "x", key)
    print("\n== размер состава при setForNewObjects ==")
    for flag, rows in sorted(by_flag.items()):
        print("   ", flag)
        for label, count in sorted(rows.items(), key=lambda item: -item[1])[:6]:
            print("      ", count, "x", label)
    print("\n== каноническая роль АдминистраторСистемы ==")
    for key, count in admin_flag_sets.most_common(6):
        print("   ", count, "x", key)
    print("    блоков с правом true:")
    for count_blocks, files in sorted(admin_blocks_with_true.items())[:12]:
        print("      ", files, "x", count_blocks, "блоков")
    print("    uuid роли (из Roles/АдминистраторСистемы.xml или Ext/Role.xml):")
    for uuid, count in admin_uuids.most_common(5):
        print("      ", count, "x", uuid)
    for row in admin_rows:
        print("     ", row[0], "|", row[1], "|", row[2], "| блоков:", row[3],
              "с true:", row[4], "только false:", row[5])
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
