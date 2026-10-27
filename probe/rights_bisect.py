"""Биновидный замер внутри одного файла прав роли.

Найденное ранее (см. docs/evidence/load-bisect.md): вся конфигурация загружается, если убрать оба
`Ext/Rights.xml` (`no_rights_files`: код 0, 2 с), загружается с ролью `АдминистраторСистемы` и её
правами (`admin_role_only`: код 0, 2 с), но зависает, если оставить роль `СотрудникОтдела` с её
правами (`sotrudnik_role_only`: 45 с, 0 байт вывода, кода нет).

Первая лестница этого замера (журнал `%TEMP%\\opencode\\p1c_effektivnost\\rights_bisect.txt`)
разделила блоки `<object>` по видам метаданных: блоки прав на справочник, документ, оба регистра,
отчёт и саму конфигурацию загружаются по 2 с с кодом 0; зависание дают права на перечисление и
константу (`keep_enum_constant`, `drop_configuration`).

Вторая лестница (варианты `keep_enum_only`, `keep_constant_only`, `enum_without_view`,
`constant_without_update`) разделяет эти два блока и внутри них — отдельные имена прав.

За один запуск — ровно один вызов платформы; исходник `cfg/ЭффективностьОтдела` не изменяется.
"""
from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import ib_loop                                                   # noqa: E402
import paths                                                     # noqa: E402

SOURCE = ROOT / "cfg" / "ЭффективностьОтдела"
RIGHTS_FILE = "Roles/СотрудникОтдела/Ext/Rights.xml"

BLOCK = re.compile(r"[ \t]*<object>\s*<name>([^<]+)</name>.*?</object>\r\n", re.S)
RIGHT = re.compile(r"[ \t]*<right>\s*<name>([^<]+)</name>.*?</right>\r\n", re.S)

# Каждая ступень — вариант: оставить блоки по префиксам имён объектов, и (опционально) снять внутри
# оставшихся блоков отдельные имена прав.
VARIANTS = (
    {"name": "keep_none", "keep": [], "comment": "файл прав на месте, но ни одного блока <object>"},
    {"name": "keep_configuration", "keep": ["Configuration."],
     "comment": "только блок прав на саму конфигурацию"},
    {"name": "keep_catalog", "keep": ["Catalog."], "comment": "только блок прав на справочник"},
    {"name": "keep_document", "keep": ["Document."], "comment": "только блок прав на документ"},
    {"name": "keep_registers", "keep": ["InformationRegister.", "AccumulationRegister."],
     "comment": "только блоки прав на оба регистра"},
    {"name": "keep_report", "keep": ["Report."], "comment": "только блок прав на отчёт"},
    {"name": "keep_enum_constant", "keep": ["Enum.", "Constant."],
     "comment": "только блоки прав на перечисление и константу — наблюдённое зависание"},
    {"name": "keep_enum_only", "keep": ["Enum."],
     "comment": "разделение: только права на перечисление"},
    {"name": "keep_constant_only", "keep": ["Constant."],
     "comment": "разделение: только права на константу"},
    {"name": "enum_without_view", "keep": ["Enum."], "drop_rights": ["View"],
     "comment": "права перечисления без View (остался только Read)"},
    {"name": "constant_without_update", "keep": ["Constant."], "drop_rights": ["Update"],
     "comment": "права константы без Update (остался только Read)"},
    {"name": "drop_configuration",
     "keep": ["Catalog.", "Document.", "InformationRegister.", "AccumulationRegister.", "Enum.",
              "Constant.", "Report."],
     "comment": "все блоки, кроме прав на конфигурацию"},
    {"name": "keep_all",
     "keep": ["Catalog.", "Document.", "InformationRegister.", "AccumulationRegister.", "Enum.",
              "Constant.", "Report.", "Configuration."],
     "comment": "исходный файл прав целиком — подтверждение наблюдения sotrudnik_role_only"},
)


def rewrite_rights(cfg: Path, keep_prefixes: list, drop_rights: list | None = None) -> dict:
    """Переписать файл прав: оставить нужные блоки `<object>` и снять внутри них именованные права.

    Файл при этом остаётся на месте (снимается не файл, а его содержимое), чтобы замер отвечал на
    вопрос «какое именно содержимое прав не даёт загрузке завершиться».
    """
    path = cfg / RIGHTS_FILE
    text = path.read_bytes().decode("utf-8-sig", "replace")
    blocks = [match for match in BLOCK.finditer(text)]
    if not blocks:
        return {"code": 2, "reason": "в файле прав нет блоков <object>", "blocks": 0}
    kept_blocks = []
    for match in blocks:
        if not any(match.group(1).startswith(prefix) for prefix in keep_prefixes):
            continue
        block = match.group(0)
        if drop_rights:
            block = RIGHT.sub("", block) if drop_rights == ["*"] else block
            for right_name in drop_rights:
                block = re.sub(r"[ \t]*<right>\s*<name>" + re.escape(right_name)
                               + r"</name>.*?</right>\r\n", "", block, flags=re.S)
        kept_blocks.append(block)
    head_end = text.find("<object>")
    tail_start = text.rfind("</object>") + len("</object>")
    new = text[:head_end] + "".join(kept_blocks) + text[tail_start:]
    new = new.replace("\r\n", "\n").replace("\n", "\r\n")
    path.write_bytes(b"\xef\xbb\xbf" + new.encode("utf-8"))
    return {"code": 0, "blocks_total": len(blocks), "blocks_kept": len(kept_blocks),
            "kept_names": [match.group(1) for match in blocks
                           if any(match.group(1).startswith(prefix)
                                  for prefix in keep_prefixes)],
            "rights_dropped": list(drop_rights or [])}


def main(argv: list) -> int:
    local = paths.load_local(str(ROOT / "local.paths.json"))
    # Порядок позиционных аргументов не важен: число — ожидание загрузки, слово — имя варианта
    # (наблюдение: `python probe/load_bisect.py 90` однажды сломался именно из-за порядка).
    only, timeout = "", 30
    for arg in argv:
        if arg.isdigit():
            timeout = int(arg)
        else:
            only = arg
    names = [variant["name"] for variant in VARIANTS]
    if only and only not in names:
        print("варианты:", ", ".join(names))
        return 2
    work = Path(local["work"]) / "rights"
    work.mkdir(exist_ok=True)
    for variant in VARIANTS:
        if only and only != variant["name"]:
            continue
        cfg = work / ("variant-" + variant["name"])
        if cfg.exists():
            shutil.rmtree(cfg)
        shutil.copytree(SOURCE, cfg)
        record = {"variant": variant["name"], "comment": variant["comment"]}
        edits = rewrite_rights(cfg, variant["keep"], variant.get("drop_rights"))
        record["edit"] = edits
        if edits["code"] != 0:
            print(json.dumps(record, ensure_ascii=False))
            continue
        ib = work / ("ib-" + variant["name"])
        if ib.exists():
            shutil.rmtree(ib)
        out_dir = work / ("out-" + variant["name"])
        out_dir.mkdir(exist_ok=True)
        opts = {"bin": local["bin"], "ib": str(ib), "cfg": str(cfg), "out": "", "timeout": timeout}
        for step in ("create", "load"):
            opts["out"] = str(out_dir / (step + ".txt"))
            result = ib_loop.run_step(step, opts)
            record[step + "_code"] = result["code"]
            record[step + "_seconds"] = result.get("seconds")
            record[step + "_bytes"] = result.get("bytes")
            record[step + "_timed_out"] = result.get("timed_out")
            if step == "load":
                record["load_head"] = [line for line in result.get("lines", []) if line.strip()][:8]
        print(json.dumps(record, ensure_ascii=False))
        sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
