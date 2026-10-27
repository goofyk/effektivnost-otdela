"""Как выглядит системная роль `АдминистраторСистемы` в канонических выгрузках корпусов.

Зачем. В нашей конфигурации есть роль с таким именем, и гейт gate-06 показал единственное
расхождение неподвижности прав: платформа дописала право `DataAdministration` в блок
`Configuration.ЭффективностьОтдела`, которого в исходнике не было. Роль с системным именем —
единственный объект, где «как пишет платформа» можно прочитать напрямую: в корпусах такая роль
есть, и она выгружена той же платформой.

Замер для каждой найденной роли `АдминистраторСистемы`:
- три верхних флага файла прав (`setForNewObjects`, `setForAttributesByDefault`,
  `independentRightsOfChildObjects`);
- блок `Configuration.`: какие права и с каким значением;
- сколько блоков и прав всего, по каким видам метаданных;
- содержимое самого описания роли (`Roles/АдминистраторСистемы.xml`): UUID, `Supplement`,
  `Presentation`, `Comment` — чтобы сравнить с нашей ролью и не выдумывать системный UUID.

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
import rights as rights_script                                   # noqa: E402

ROOTS = corpora.dumps()
ROLE_NAME = "АдминистраторСистемы"


def main(argv: list | None = None) -> int:
    argv = list(argv or [])
    out_json = pathlib.Path(argv[argv.index("--json") + 1]) if "--json" in argv else None

    findings = []
    for root in ROOTS:
        description = root / "Roles" / (ROLE_NAME + ".xml")
        path = root / "Roles" / ROLE_NAME / "Ext" / "Rights.xml"
        if not path.is_file() and not description.is_file():
            continue
        item = {"corpus": corpora.relative(path if path.is_file() else description, ROOTS)}
        if description.is_file():
            text = description.read_bytes().decode("utf-8-sig", "replace")
            item["role_description"] = {
                tag: match.group(1).strip()
                for tag in ("UUID", "Name", "SynonymName", "Presentation", "Comment", "Supplement")
                for match in [re.search(r"<" + tag + r">(.*?)</" + tag + ">", text, re.S)]
                if match
            }
        if not path.is_file():
            item["rights_file"] = "нет"
            findings.append(item)
            continue
        parsed = rights_script.parse_rights(path.read_bytes().decode("utf-8-sig", "replace"))
        item["flags"] = parsed["flags"]
        item["blocks"] = len(parsed["objects"])
        item["rights"] = sum(len(obj["rights"]) for obj in parsed["objects"])
        kinds = collections.Counter(obj["name"].split(".")[0] for obj in parsed["objects"])
        item["blocks_by_kind"] = dict(kinds.most_common())
        item["configuration_block"] = {
            obj["name"]: obj["rights"] for obj in parsed["objects"]
            if obj["name"].split(".")[0] == "Configuration"}
        item["blocks_by_object"] = {
            obj["name"]: sorted(name for name, value in obj["rights"].items() if value == "true")
            for obj in parsed["objects"]}
        findings.append(item)

    print("ролей", ROLE_NAME, "найдено:", len(findings))
    for item in findings:
        print("\n==", item["corpus"])
        print("   описание роли:", json.dumps(item.get("role_description", {}), ensure_ascii=False))
        print("   флаги:", json.dumps(item.get("flags", {}), ensure_ascii=False),
              "| блоков:", item.get("blocks"), "| прав:", item.get("rights"))
        print("   виды блоков:", json.dumps(item.get("blocks_by_kind", {}), ensure_ascii=False))
        print("   блок Configuration.:", json.dumps(item.get("configuration_block", {}),
                                                    ensure_ascii=False))
        for name, granted in sorted((item.get("blocks_by_object") or {}).items()):
            if name.split(".")[0] != "Configuration" and granted:
                print("      ", name, "->", ", ".join(granted))
    if out_json:
        out_json.parent.mkdir(parents=True, exist_ok=True)
        out_json.write_text(json.dumps({"role_name": ROLE_NAME, "roles": findings},
                                       ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("\nзамер записан:", out_json.as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
