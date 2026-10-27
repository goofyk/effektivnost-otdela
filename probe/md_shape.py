"""Канонический порядок свойств метаданных по дампу платформы (анализ формата, не генератор).

Нужно, чтобы рукописный XML не спорил с XDTO: наблюдение B2b показало, что порядок свойств
строгий («Текущее ChildObjects, ожидаемое CommonModule»), а пропуск свойства безопасен
(омиттируемые свойства платформа берёт по умолчанию). Скрипт выводит только имена тегов по
порядку — содержимое корпусов в репозиторий не переносится.
"""
from __future__ import annotations

import pathlib
import sys
import xml.etree.ElementTree as ET

MD_NS = "{http://v8.1c.ru/8.3/MDClasses}"


def children_names(element, limit=0):
    names = []
    for child in element:
        name = child.tag.replace(MD_NS, "")
        names.append(name)
        if limit and len(names) >= limit:
            break
    return names


def shape(path, interesting=()):
    root = ET.fromstring(pathlib.Path(path).read_bytes().decode("utf-8-sig", "replace"))
    obj = root[0]
    out = [pathlib.Path(path).name, "  корень: " + obj.tag.replace(MD_NS, "")]
    props = obj.find(MD_NS + "Properties")
    if props is not None:
        out.append("  Properties (" + str(len(list(props))) + "): " + ", ".join(children_names(props)))
    for section in obj:
        name = section.tag.replace(MD_NS, "")
        if name == "Properties":
            continue
        kids = children_names(section)
        out.append("  " + name + " (" + str(len(kids)) + "): " + ", ".join(dict.fromkeys(kids)))
        for child in section:
            cname = child.tag.replace(MD_NS, "")
            if interesting and cname not in interesting:
                continue
            for sub in child:
                sname = sub.tag.replace(MD_NS, "")
                names = children_names(sub)
                out.append("    " + cname + "/" + sname + " (" + str(len(names)) + "): "
                           + ", ".join(names))
                if sname in ("Attribute", "Dimension", "Resource", "Column"):
                    out.append("      " + cname + "." + sname + " Properties ("
                               + str(len(names)) + "): " + ", ".join(names))
                if sname == "StandardAttributes":
                    for attr in sub:
                        aname = attr.tag.replace(MD_NS, "")
                        for ssub in attr:
                            out.append("      " + cname + ".StandardAttributes/" + aname + "/"
                                       + ssub.tag.replace(MD_NS, "") + ": "
                                       + ", ".join(children_names(ssub)))
    return "\n".join(out)


def main(argv):
    for arg in argv[1:]:
        print(shape(arg))
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
