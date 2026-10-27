"""Правила вырезания объекта метаданных — нужны для биновидного замера загрузки.

Замер «что в конфигурации дорожает» имеет смысл только если вырезание не оставляет висячих
ссылок: иначе отказ платформы объясняется битой конфигурацией, а не дороговизной объекта.
Поэтому вырезается всё, что снимается правилами: файл объекта и его поддерево, декларация у
родителя, пункты Content подсистем и записей регистров документа, блоки прав, и свойства-ссылки
(`DefaultObjectForm`, `MainDataCompositionSchema`). Ссылки на типы (`cfg:CatalogRef.…`) и на
стандартные атрибуты (`Catalog.…StandardAttribute.…`) снять нечем — такое вырезание отказывается,
пока не вырезан зависимый объект. Вызовы в BSL остаются: они не ломают загрузку метаданных,
но замер обязан их показать.
"""
from __future__ import annotations

import pathlib
import re
import shutil

KIND_DIRECTORY = {
    "Language": "Languages",
    "Subsystem": "Subsystems",
    "CommonModule": "CommonModules",
    "Enum": "Enums",
    "Constant": "Constants",
    "Catalog": "Catalogs",
    "Document": "Documents",
    "InformationRegister": "InformationRegisters",
    "AccumulationRegister": "AccumulationRegisters",
    "Report": "Reports",
    "Role": "Roles",
    "DataProcessor": "DataProcessors",
}

SUBKIND_DIRECTORY = {"Form": "Forms", "Template": "Templates"}

# Свойства, значения которых — ссылка на объект метаданных. Только их и позволяем себе
# обнулять: `<name>` в блоке прав — не свойство-ссылка, его снимает правило блока прав.
REFERENCE_PROPERTY = re.compile(r"^(Default|Auxiliary)?.*(Form|Storage|Schema)$")


def copy_source(src: str, dst: str) -> pathlib.Path:
    """Копия конфигурации в каталог варианта (исходник не трогается)."""
    target = pathlib.Path(dst)
    if target.exists():
        shutil.rmtree(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, target)
    return target


def _read(path: pathlib.Path) -> str:
    return path.read_bytes().decode("utf-8-sig", "replace")


def _write(path: pathlib.Path, text: str) -> None:
    path.write_bytes(b"\xef\xbb\xbf" + text.replace("\r\n", "\n").replace("\n", "\r\n").encode("utf-8"))


def _metadata_files(cfg: pathlib.Path) -> list:
    return [p for p in cfg.rglob("*") if p.is_file() and p.suffix == ".xml"]


def _owner_file(cfg: pathlib.Path, kind: str, name: str) -> pathlib.Path:
    return cfg / KIND_DIRECTORY[kind] / (name + ".xml")


def _object_paths(cfg: pathlib.Path, kind: str, owner: str, subkind: str, name: str) -> tuple:
    """(файл объекта, поддерево объекта, файл-родитель с декларацией, декларация)."""
    if subkind is None:
        return (cfg / KIND_DIRECTORY[kind] / (name + ".xml"),
                cfg / KIND_DIRECTORY[kind] / name,
                cfg / "Configuration.xml",
                "<" + kind + ">" + name + "</" + kind + ">")
    directory = cfg / KIND_DIRECTORY[kind] / owner / SUBKIND_DIRECTORY[subkind]
    return (directory / (name + ".xml"), directory / name,
            _owner_file(cfg, kind, owner), "<" + subkind + ">" + name + "</" + subkind + ">")


def _inside(candidate: pathlib.Path, tree: pathlib.Path) -> bool:
    try:
        candidate.relative_to(tree)
        return True
    except ValueError:
        return False


def blocking_references(cfg: pathlib.Path, full_name: str, own_file: pathlib.Path,
                        own_tree: pathlib.Path) -> list:
    """Ссылки на объект, которые нечем снять: типы и стандартные атрибуты.

    Именно они определяют, какое вырезание допустимо для замера. Короткое имя объекта важно:
    на справочник ссылаются как `cfg:CatalogRef.Сотрудники`, а не `Catalog.Сотрудники`.
    """
    short = full_name.split(".")[-1]
    type_ref = re.compile(r"cfg:[A-Za-z]+(?:Ref|Object|Manager|List|Selection|Record[A-Za-z]*)?\."
                          + re.escape(short) + r"\b")
    attribute_ref = re.compile(re.escape(full_name) + r"\.[A-Za-z]")
    hits = []
    for path in _metadata_files(cfg):
        if path == own_file or _inside(path, own_tree):
            continue
        for line_no, line in enumerate(_read(path).splitlines(), 1):
            if type_ref.search(line) or attribute_ref.search(line):
                hits.append(path.relative_to(cfg).as_posix() + ":" + str(line_no) + " "
                            + line.strip())
    return hits


def _remove_content_items(cfg: pathlib.Path, name: str, skip: tuple) -> int:
    """Пункты `<xr:Item xsi:type="xr:MDObjectRef">…</xr:Item>`: содержимое подсистем и записи
    регистров документа. Пустой родитель становится пустым свойством (`<Content/>`)."""
    item = re.compile(r'[ \t]*<xr:Item\s+xsi:type="xr:MDObjectRef">\s*' + re.escape(name)
                      + r'\s*</xr:Item>\r\n')
    removed = 0
    for path in _metadata_files(cfg):
        if path in skip:
            continue
        body = _read(path)
        found = item.findall(body)
        if not found:
            continue
        new = item.sub("", body)
        new = re.sub(r"<(Content|RegisterRecords|DefaultRoles)>\r\n[ \t]*</\1>", r"<\1/>", new)
        removed += len(found)
        _write(path, new)
    return removed


def _remove_empty_directory(path: pathlib.Path) -> None:
    """Пустой каталог вида (`Forms`, `Templates`) после вырезания — мусор: в выгрузке платформы
    пустых каталогов вида нет, и тест проверяет, чтоvariant не оставляет их."""
    if path.is_dir() and not any(path.iterdir()):
        path.rmdir()


def _remove_rights_objects(cfg: pathlib.Path, name: str) -> int:
    """Блок прав `<object><name>Имя</name> … </object>` из файлов прав ролей."""
    block = re.compile(r"\t<object>\s*<name>\s*" + re.escape(name) + r"\s*</name>.*?</object>\r\n",
                       re.S)
    removed = 0
    for path in cfg.rglob("Ext/Rights.xml"):
        body = _read(path)
        found = block.findall(body)
        if not found:
            continue
        _write(path, block.sub("", body))
        removed += len(found)
    return removed


def _empty_reference_properties(cfg: pathlib.Path, name: str, skip: tuple) -> int:
    """`<DefaultObjectForm>Каталог.Х.Form.Форма</DefaultObjectForm>` -> `<DefaultObjectForm/>`."""
    changed = 0
    for path in _metadata_files(cfg):
        if path in skip:
            continue
        body = _read(path)
        new = re.sub(r"<([A-Za-z]+)>\s*" + re.escape(name) + r"\s*</\1>",
                     lambda m: ("<" + m.group(1) + "/>") if REFERENCE_PROPERTY.match(m.group(1))
                     else m.group(0), body)
        if new != body:
            changed += 1
            _write(path, new)
    return changed


def _module_references(cfg: pathlib.Path, full_name: str, skip: tuple) -> list:
    """Кто вызывает вырезанный объект из BSL: загрузку метаданных это не ломает, но скрывать
    такую цену замера нельзя."""
    short = full_name.split(".")[-1]
    hits = []
    for path in cfg.rglob("*.bsl"):
        if path in skip or short not in _read(path):
            continue
        hits.append(path.relative_to(cfg).as_posix())
    return hits


def drop_metadata(cfg_dir, full_name: str) -> dict:
    """Вырезает объект (или его форму/шаблон) вместе со всеми снимаемыми ссылками."""
    cfg = pathlib.Path(cfg_dir)
    parts = full_name.split(".")
    if len(parts) == 2:
        kind, owner, subkind, name = parts[0], None, None, parts[1]
    elif len(parts) == 4:
        kind, owner, subkind, name = parts
    else:
        return {"code": 2, "reason": "непонятное имя объекта (нужно 'Вид.Имя' или "
                                     "'Вид.Владелец.Подвид.Имя'): " + full_name}
    if kind not in KIND_DIRECTORY:
        return {"code": 2, "reason": "неизвестный вид метаданных '" + kind + "', известны: "
                                     + ", ".join(sorted(KIND_DIRECTORY))}
    if subkind is not None and subkind not in SUBKIND_DIRECTORY:
        return {"code": 2, "reason": "неизвестный подвид '" + subkind + "', известны: "
                                     + ", ".join(sorted(SUBKIND_DIRECTORY))}

    own_file, own_tree, parent_file, declaration = _object_paths(cfg, kind, owner, subkind, name)
    if not (own_file.is_file() or own_tree.is_dir()):
        return {"code": 2, "reason": "нет файла объекта, который предполагаем вырезать: "
                                     + full_name}
    if not parent_file.is_file():
        return {"code": 2, "reason": "нет файла-родителя для декларации '" + full_name + "'"}

    blocked = blocking_references(cfg, full_name, own_file, own_tree)
    if blocked:
        return {"code": 2, "reason": "нельзя вырезать '" + full_name + "' без вырезания "
                                     "зависимого объекта; остаются ссылки, которые нечем снять: "
                                     + "; ".join(blocked[:8])}

    skip = tuple(p for p in _metadata_files(cfg) if p == own_file or _inside(p, own_tree))
    removed_files = 0
    if own_file.is_file():
        own_file.unlink()
        removed_files += 1
    if own_tree.is_dir():
        shutil.rmtree(own_tree)
        removed_files += 1
    _remove_empty_directory(own_file.parent)

    body = _read(parent_file)
    if declaration not in body:
        return {"code": 2, "reason": "декларация '" + declaration + "' не найдена в "
                                     + parent_file.name + "; копия изменена частично"}
    _write(parent_file, body.replace(declaration, ""))

    return {"code": 0, "changed": True, "dropped": full_name, "removed_files": removed_files,
            "content_items": _remove_content_items(cfg, full_name, skip),
            "rights_objects": _remove_rights_objects(cfg, full_name),
            "reference_properties": _empty_reference_properties(cfg, full_name, skip),
            "module_references_left": _module_references(cfg, full_name, skip)}


def build_variant(src, dst: str, drops: list) -> dict:
    """Копия конфигурации с последовательно вырезанными объектами — вариант биновидного замера.

    Помимо имён метаданных допускаются пункты `file:<относительный путь>`: они снимают ровно один
    файл без правил ссылок. Это нужно, чтобы различить дескриптор объекта и его `Ext`-файл: например
    `file:Roles/СотрудникОтдела/Ext/Rights.xml` оставляет роль, но без прав.
    """
    cfg = copy_source(str(src), dst)
    applied = []
    for full_name in drops:
        if full_name.startswith("file:"):
            target = cfg / full_name[len("file:"):]
            if not target.is_file():
                return {"code": 2, "reason": "нет файла, который предполагаем снять: "
                                             + full_name, "cfg": str(cfg), "dropped": applied}
            target.unlink()
            applied.append(full_name)
            continue
        result = drop_metadata(cfg, full_name)
        if result["code"] != 0:
            return {**result, "cfg": str(cfg), "dropped": applied,
                    "reason": "вариант не собран: " + result["reason"]}
        applied.append(full_name)
    return {"code": 0, "cfg": str(cfg), "dropped": applied,
            "files": sum(1 for p in cfg.rglob("*") if p.is_file())}
