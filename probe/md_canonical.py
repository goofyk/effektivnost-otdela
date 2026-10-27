"""Канонические виды генерируемых типов (`InternalInfo`) и значения перечислений по дампу платформы.

Второй прогон итерации 1 дал точные диагнозы платформы 8.3.27.1606:

    узел - Catalog: Отсутствует внутренняя информация (узел InternalInfo) для объекта Catalog.
    Неверное значение перечисления - Turnover
    Неверное значение перечисления - Daily
    Неверное свойство объекта метаданных. Свойство ExtendedPresentation не входит
        в состав объекта метаданных Form.

Значит: `InternalInfo` обязателен там, где платформа его ждёт, а набор генерируемых типов и
значения перечислений нельзя подбирать на слух — их нужно читать из канонической выгрузки.
Скрипт выводит только имена/категории генерируемых типов и наблюдаемые значения свойств;
содержимое чужих конфигураций в репозиторий не переносится.
"""
from __future__ import annotations

import collections
import pathlib
import re
import sys
import xml.etree.ElementTree as ET

XR = "{http://v8.1c.ru/8.3/xcf/readable}"


def generated_types(path):
    root = ET.fromstring(pathlib.Path(path).read_bytes().decode("utf-8-sig", "replace"))
    obj = root[0]
    kind = obj.tag.split("}")[-1]
    info = obj.find("{http://v8.1c.ru/8.3/MDClasses}InternalInfo")
    pairs = []
    if info is None:
        return kind, None, []
    for child in info:
        tag = child.tag.split("}")[-1]
        if tag == "GeneratedType":
            pairs.append(child.get("name", "").split(".")[0] + " / " + str(child.get("category")))
        else:
            class_id = child.find(XR + "ClassId")
            pairs.append("ContainedObject:" + (class_id.text if class_id is not None else "?"))
    return kind, len(pairs), pairs


def property_names(path):
    root = ET.fromstring(pathlib.Path(path).read_bytes().decode("utf-8-sig", "replace"))
    props = root[0].find("{http://v8.1c.ru/8.3/MDClasses}Properties")
    return [child.tag.split("}")[-1] for child in props] if props is not None else []


def smallest(directory: pathlib.Path, exclude=()):
    files = [f for f in directory.glob("*.xml") if f.name not in exclude]
    return min(files, key=lambda f: f.stat().st_size) if files else None


def main(argv):
    """Употребление: python probe/md_canonical.py КОРПУС [КОРПУС…] (argv уже без имени скрипта)."""
    corpora = [pathlib.Path(a) for a in argv]
    kinds = ("Catalogs", "Documents", "Enums", "Constants", "InformationRegisters",
             "AccumulationRegisters", "Reports", "Roles", "CommonModules", "Languages",
             "Subsystems")
    for root in corpora:
        print("=== корпус", root.name)
        for kind in kinds:
            directory = root / kind
            if not directory.is_dir():
                continue
            sample = smallest(directory)
            if sample is None:
                continue
            kind_name, count, pairs = generated_types(sample)
            print("  " + kind_name + " (" + sample.name + "): " + str(count) + " InternalInfo")
            for pair in pairs:
                print("      " + pair)
        templates = list(root.rglob("Templates/*.xml"))
        if templates:
            kind_name, count, pairs = generated_types(min(templates, key=lambda f: f.stat().st_size))
            print("  " + kind_name + " (шаблон): " + str(count) + " InternalInfo " + str(pairs))
        forms = [f for f in root.rglob("Forms/*.xml") if "Ext" not in f.parts]
        if forms:
            sample = min(forms, key=lambda f: f.stat().st_size)
            print("  Form Properties (" + sample.name + "): " + ", ".join(property_names(sample)))
    return 0


def values(corpus_and_props):
    """Наблюдаемые значения перечислений по всем файлам корпуса (для токенов вида RegisterType).

    Употребление: python probe/md_canonical.py --values КОРПУС Свойство1 Свойство2 …
    """
    corpus = pathlib.Path(corpus_and_props[0])
    props = corpus_and_props[1:]
    counts = collections.defaultdict(collections.Counter)
    for kind_dir in (corpus / "AccumulationRegisters", corpus / "InformationRegisters",
                     corpus / "Documents", corpus / "Catalogs"):
        if not kind_dir.is_dir():
            continue
        for f in kind_dir.glob("*.xml"):
            text = f.read_bytes().decode("utf-8-sig", "replace")
            for prop in props:
                for match in re.finditer("<" + prop + ">([^<]+)</" + prop + ">", text):
                    counts[prop][match.group(1)] += 1
    for prop in props:
        print(prop + ":", ", ".join(sorted(counts[prop])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]) if sys.argv[1] and sys.argv[1] != "--values"
                     else values(sys.argv[2:]))
