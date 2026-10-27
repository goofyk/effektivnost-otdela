"""Как в канонических выгрузках выглядит язык конфигурации: `Languages/<Имя>.xml` и `LanguageCode`.

Зачем. В нашей конфигурации один язык (`Languages/Русский.xml`) с `<LanguageCode>RU</LanguageCode>`,
а тексты объектов пишут `<v8:lang>ru</v8:lang>` — строчными. Замер `probe/corpora_role_uuids.py`
показал, что языки корпусов в `Languages/` задаются кодами `ru` и `en`. Если канон — строчный код,
то `RU` у нас неканонический, и надо понять, к чему это приводит: платформа приняла конфигурацию
молча (замер гейта), но связывает ли она `ru` в текстах с нашим языком `RU` — отдельный вопрос.

Замер по всем выбранным corpus: имя языка, `LanguageCode`, есть ли язык `Английский`, и какие коды
появляются в `<v8:lang>` описаний объектов. Платформу не запускает, исходник не изменяет.

    python probe/corpora_language_codes.py [--json docs/canonical-languages.json]
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

ROOTS = corpora.dumps()

CODE = re.compile(r"<LanguageCode>([^<]*)</LanguageCode>")
NAME = re.compile(r"<Name>([^<]*)</Name>")

LIMIT_PER_CORPUS = 700


def main(argv: list | None = None) -> int:
    argv = list(argv or [])
    out_json = pathlib.Path(argv[argv.index("--json") + 1]) if "--json" in argv else None

    codes = collections.Counter()
    names = collections.Counter()
    languages: list = []
    for root in ROOTS:
        directory = root / "Languages"
        if not directory.is_dir():
            continue
        for path in corpora.files_named([directory], "*.xml", LIMIT_PER_CORPUS):
            text = path.read_bytes().decode("utf-8-sig", "replace")
            name = (NAME.search(text).group(1).strip() if NAME.search(text) else "")
            code = (CODE.search(text).group(1).strip() if CODE.search(text) else "(нет LanguageCode)")
            codes[code] += 1
            names[name] += 1
            languages.append({"corpus": path.parent.parent.name, "file": path.name,
                              "name": name, "code": code})
        # коды языков, которые реально встречаются в текстах описаний объектов
        used = collections.Counter()
        for path in corpora.files_named([root], "*.xml", LIMIT_PER_CORPUS):
            text = path.read_bytes().decode("utf-8-sig", "replace")
            for lang in re.findall(r"<v8:lang>([^<]+)</v8:lang>", text):
                used[lang] += 1
        languages.append({"corpus": "коды <v8:lang> в " + root.name, "used": dict(used.most_common(8))})

    print("файлов языков просмотрено:", sum(1 for item in languages if "code" in item))
    print("\n== LanguageCode в канонических выгрузках")
    for code, count in codes.most_common():
        print("   ", repr(code).ljust(12), count)
    print("\n== имена языков")
    for name, count in names.most_common():
        print("   ", name.ljust(20), count)
    print("\n== коды <v8:lang> в описаниях объектов (по корпусу)")
    for item in languages:
        if "used" in item:
            print("   ", item["corpus"], json.dumps(item["used"], ensure_ascii=False))
    if out_json:
        out_json.parent.mkdir(parents=True, exist_ok=True)
        out_json.write_text(json.dumps({"language_files": sum(1 for i in languages if "code" in i),
                                        "language_codes": dict(codes.most_common()),
                                        "language_names": dict(names.most_common()),
                                        "languages": languages,
                                        "v8_lang_by_corpus": {item["corpus"]: item["used"]
                                                              for item in languages if "used" in item}},
                                       ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("\nзамер записан:", out_json.as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
