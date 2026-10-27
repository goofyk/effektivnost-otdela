"""Сверка описаний ролей в источнике и в выгрузке платформы: UUID, переводы, порядок файлов.

Зачем. Роль `АдминистраторСистемы` в нашей конфигурации написана с выдуманным UUID
(`6b1e3a24-…`). В канонических выгрузках корпусов у роли с таким именем UUID один и тот же во
всех пяти корпусах: `76702e9e-fa7a-4b98-befa-f9b37db2dae0` (`probe/corpora_role_uuids.py`).
Вопрос: платформа приняла наш UUID как есть, подставила системный или переписала — и что при
этом произошло с синонимом и переводом. Ответ нужен, чтобы решить, какой UUID должен быть в
исходнике рукописной конфигурации.

Скрипт сравнивает только прочитанное: исходник (`cfg/...`) и выгрузку гейта. Платформу не запускает.

    python probe/role_dump_vs_source.py
    python probe/role_dump_vs_source.py --cfg <каталог> --dump <каталог>
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import paths as paths_script                                     # noqa: E402

UUID = re.compile(r"<Role uuid=\"([^\"]+)\"")
LANG = re.compile(r"<v8:lang>([^<]+)</v8:lang>")


def describe(path: pathlib.Path) -> dict:
    text = path.read_bytes().decode("utf-8-sig", "replace")
    out = {}
    out["uuid"] = UUID.search(text).group(1) if UUID.search(text) else "(нет uuid)"
    out["languages"] = sorted(set(LANG.findall(text)))
    out["has_synonym"] = "<Synonym>" in text
    out["has_comment"] = bool(re.search(r"<Comment>[^<]", text))
    out["bytes"] = path.stat().st_size
    return out


def main(argv: list) -> int:
    argv = list(argv or [])
    opts = {argv[i]: argv[i + 1] for i in range(0, len(argv) - 1, 2)}
    local = paths_script.load_local(ROOT / "local.paths.json")
    cfg = pathlib.Path(opts.get("cfg") or local["cfg"])
    dump = pathlib.Path(opts.get("dump") or local["dump"])

    for name in sorted(set(p.stem for p in (cfg / "Roles").glob("*.xml"))
                       | set(p.stem for p in (dump / "Roles").glob("*.xml"))):
        source, out = cfg / "Roles" / (name + ".xml"), dump / "Roles" / (name + ".xml")
        print("== роль", name)
        for label, path in (("источник", source), ("выгрузка", out)):
            if not path.is_file():
                print("   ", label, ": нет файла")
                continue
            print("   ", label, json.dumps(describe(path), ensure_ascii=False))
        if source.is_file() and out.is_file():
            same = source.read_bytes() == out.read_bytes()
            print("    побайтово:", "совпадает" if same else "различается")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
