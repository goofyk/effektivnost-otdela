"""Имена событий и их сигнатуры в модулях объекта по каноническим выгрузкам корпусов.

Зачем: платформа при загрузке проверяет только синтаксис модулей (`/CheckModules`), а имя и сигнатура
процедуры-обработчика события в модуле объекта проверяются только в момент, когда событие возникает
(или не возникают вовсе). Значит обработчик с выдуманным именем или лишним параметром загрузится
молча и никогда не выполнится. p1c сигнатуры событий модулей объекта не знает вовсе: в
`p1c/src/p1c/data/platform_arities.py` (`EVENT_SIGNATURES`) есть только сигнатуры событий
управляемой формы (`ПередЗаписью: (2, 2)`, `ПослеЗаписи: (1, 1)`).

Замер без платформы: список всех процедур, объявленных в `Ext/ObjectModule.bsl` канонических
выгрузок, и их сигнатуры. Пути корпусов берутся из `local.paths.json`.
"""
from __future__ import annotations

import collections
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import paths                                                     # noqa: E402

DECLARATION = re.compile(r"^\s*(Процедура|Функция)\s+(\w+)\s*\(([^)]*)\)", re.M)
EXPORTED = re.compile(r"^\s*(Процедура|Функция)\s+(\w+)\s*\(([^)]*)\)\s*Экспорт", re.M)


def main(argv: list | None = None) -> int:
    local = paths.load_local(str(ROOT / "local.paths.json"))
    roots = [value for key, value in local.items() if key.startswith("corpora_")]
    names = collections.Counter()
    signatures = collections.defaultdict(collections.Counter)
    exported = collections.Counter()
    samples: dict = {}
    files = 0
    for root in roots:
        base = pathlib.Path(root)
        if not base.is_dir():
            print("нет каталога корпуса:", root)
            continue
        for path in base.rglob("ObjectModule.bsl"):
            files += 1
            try:
                text = path.read_bytes().decode("utf-8-sig", "replace")
            except OSError:
                continue
            relative = path.relative_to(base).as_posix()
            for match in DECLARATION.finditer(text):
                name = match.group(2)
                parameters = re.sub(r"\s+", " ", match.group(3)).strip()
                names[name] += 1
                signatures[name][parameters] += 1
                if len(samples.setdefault(name, [])) < 1:
                    samples[name].append(relative)
            for match in EXPORTED.finditer(text):
                exported[match.group(2)] += 1
    print("файлов Ext/ObjectModule.bsl просмотрено:", files)
    print("\n== имена процедур модуля объекта (топ-40) ==")
    for name, count in names.most_common(40):
        forms = ", ".join("(" + parameters + ")" for parameters, _ in
                          signatures[name].most_common(4))
        print("   ", count, "x", name, "->", forms, "|", samples[name][0])
    print("\n== интересует конкретно наши имена ==")
    for name in ("ПриНовомОбъекте", "ПередЗаписью", "ПослеЗаписи", "ОбработкаПроведения",
                 "ПриСозданииОбъекта"):
        print("   ", name, "->", dict(signatures.get(name, {})) or "не встречается")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
