"""Пробел манифеста прочитанных файлов против раскладки выгрузки.

Счётчик `scripts/layout.py` видит файл по имени пути, манифест `read_files` — только
тот файл, который парсер действительно открыл. Разность двух счётчиков и есть список
классов, которые читатель не открывает: по одному корпусу видно, что это не случайность
отдельной конфигурации, а отсутствие ветки читателя (командные модули, дескрипторы
общих коллекций, содержимое общих макетов и картинок).

Запуск (из каталога `effektivnost-otdela`):
    python scripts/manifest_gaps.py                # cfg + фикстуры + корпус пульсара
    python scripts/manifest_gaps.py --src <src>    # путь к src p1c вместо local.paths.json
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import counts as counts_mod                                    # noqa: E402
import layout as layout_mod                                    # noqa: E402

# Класс раскладки -> шаблон пути в выгрузке. Имена классов совпадают с классами
# манифеста читателя (дескрипторы — имена layout.py, содержимое — конвенция читателя),
# чтобы разность счётчиков читалась без догадок.
GAP_KINDS = (
    ("command_descriptor", "Commands", "xml", False),
    ("command_module", "Commands", "bsl", True),
    ("common_command", "CommonCommands", "xml", False),
    ("common_command_module", "CommonCommands", "bsl", True),
    ("command_group", "CommandGroups", "xml", False),
    ("common_attribute", "CommonAttributes", "xml", False),
    ("common_picture", "CommonPictures", "xml", False),
    ("common_picture_content", "CommonPictures", "any", True),
    ("common_template", "CommonTemplates", "xml", False),
    ("common_template_data", "CommonTemplates", "any", True),
    ("common_form", "CommonForms", "xml", False),
    ("form_data", "CommonForms", "any", True),
    ("report_template", "Templates", "xml", False),
    ("report_template_data", "Templates", "any", True),
    ("form_descriptor", "Forms", "xml", False),
    ("form_data", "Forms", "any", True),
)


def _walk(base: pathlib.Path, folder: str, ext: str, in_ext: bool) -> list[pathlib.Path]:
    """Файлы класса раскладки: <папка> на любом уровне, с Ext/ или без него."""
    out: list[pathlib.Path] = []
    for xml in base.rglob("*"):
        if not xml.is_file():
            continue
        rel = xml.relative_to(base)
        parts = [p for p in rel.parts]
        if folder not in parts:
            continue
        i = parts.index(folder)
        has_ext = "Ext" in parts[i + 1:]
        if has_ext != in_ext:
            continue
        if ext != "any" and xml.suffix.lower() != "." + ext:
            continue
        out.append(xml)
    return out


def gaps(base: pathlib.Path, model: dict) -> dict:
    """По классу раскладки: файлов на диске, файлов в манифесте, первые примеры незакрытых."""
    manifest = model.get("read_files") or []
    opened = {str(entry.get("path", "")).replace("\\", "/") for entry in manifest}
    out: dict[str, dict] = {}
    for kind, folder, ext, in_ext in GAP_KINDS:
        disk = _walk(base, folder, ext, in_ext)
        if not disk:
            continue
        missing = [str(p.relative_to(base)).replace("\\", "/") for p in disk
                   if str(p.relative_to(base)).replace("\\", "/") not in opened]
        if missing:
            out[kind] = {"disk": len(disk), "missing": len(missing),
                         "examples": sorted(missing)[:5]}
    return out


def main(argv: list[str]) -> int:
    src = ""
    only: set[str] = set()
    for i, arg in enumerate(argv):
        if arg == "--src" and i + 1 < len(argv):
            src = argv[i + 1]
        elif not arg.startswith("--"):
            only.add(arg)
    if not src:
        src = (json.loads((ROOT / "local.paths.json").read_text(encoding="utf-8-sig"))
               .get("p1c", ""))
    from p1c.load import reader                                        # noqa: E402

    p1c_root = pathlib.Path(src)
    cfg = json.loads((ROOT / "local.paths.json").read_text(encoding="utf-8-sig"))
    bases = [("cfg", ROOT / "cfg" / "ЭффективностьОтдела"),
             ("designer_dump", p1c_root.parent / "examples" / "designer_dump"),
             ("edt_project", p1c_root.parent / "examples" / "edt_project"),
             ("managed_app", p1c_root.parent / "examples" / "managed_app"),
             ("pulsar", pathlib.Path(cfg["corpora_pulsar"]))]
    # Тяжёлые корпуса добавляются только по имени: их обход долог, и он не нужен
    # для проверки читателя, если enough пульсара.
    for key in ("corpora_ssl", "corpora_lso"):
        if key in cfg:
            bases.append((key, pathlib.Path(cfg[key])))
    for name, base in bases:
        if only and name not in only:
            continue
        if not base.is_dir():
            print(f"{name}: нет каталога {base}")
            continue
        lay = layout_mod.layout_counts(base)
        model = reader.load_configuration_model(str(base), parallel=False)
        man = counts_mod.counts_from_model(model)
        print(f"=== {name} base={base}")
        print(f"  layout files={lay.get('files')} manifest files={man.get('files')}")
        for kind in sorted(set(lay) | set(man)):
            if kind == "files":
                continue
            a, b = lay.get(kind, 0), man.get(kind, 0)
            if a != b:
                print(f"  kind {kind}: layout {a} manifest {b}")
        for kind, data in sorted(gaps(base, model).items()):
            print(f"  GAP {kind}: disk {data['disk']} вне манифеста {data['missing']}"
                  f" {data['examples']}")
        for key in ("skipped_files", "skipped_module_files"):
            if model.get(key):
                print(f"  diagnosis {key}: {model[key] if key == 'skipped_module_files' else len(model[key])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
