"""Один и тот же UUID у роли с системным именем в канонических выгрузках — и что стоит в описании роли.

Зачем. В нашей конфигурации роль `АдминистраторСистемы` описана с выдуманным UUID
(`6b1e3a24-…`). Системное имя роли платформа связывает с системной ролью, и в канонических
выгрузках такая роль есть: замер отвечает на два вопроса — совпадает ли UUID у неё во всех
корпусах (тогда выдуманный UUID — расхождение с каноном, которое надо исправить) и чем заполнено
само описание роли (`Synonym`, переводы, `Comment`).

Замер также считает раскладку описаний всех ролей выборок корпусов: бывает ли у роли `Synonym`
перевод на язык, которого нет в `Languages/` конфигурации, и встречается ли узел `Comment` пустым.
Платформу не запускает, исходник не изменяет.
"""
from __future__ import annotations

import collections
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import corpora                                                   # noqa: E402

ROOTS = corpora.dumps()
SYSTEM_ROLES = ("АдминистраторСистемы", "ПолныеПрава", "АдминистраторПолногоДоступа")

ROLE_TAG = re.compile(r"<Role uuid=\"([^\"]+)\"")
LANGS = re.compile(r"<v8:lang>([^<]+)</v8:lang>")

LIMIT_PER_CORPUS = 700


def main(argv: list | None = None) -> int:
    found = collections.defaultdict(list)
    shapes = collections.Counter()
    role_files = 0
    for root in ROOTS:
        directory = root / "Roles"
        if not directory.is_dir():
            continue
        # Языки конфигурации: `Languages/Русский.xml` содержит `<LanguageCode>ru</LanguageCode>`,
        # а описания объектов пишут `<v8:lang>ru</v8:lang>`. Сравнивать надо коды, а не имена файлов:
        # по именам «перевод вне Languages/» получилось бы у всех 1099 ролей.
        languages = set()
        if (root / "Languages").is_dir():
            for path in (root / "Languages").glob("*.xml"):
                match = re.search(r"<LanguageCode>([^<]+)</LanguageCode>",
                                  path.read_bytes().decode("utf-8-sig", "replace"))
                if match:
                    languages.add(match.group(1).strip())
        for path in corpora.files_named([directory], "*.xml", LIMIT_PER_CORPUS):
            if path.parent.name == "Ext":
                continue
            role_files += 1
            text = path.read_bytes().decode("utf-8-sig", "replace")
            match = ROLE_TAG.search(text)
            uuid = match.group(1) if match else "(нет uuid)"
            langs = sorted(set(LANGS.findall(text)))
            shapes["описание роли без uuid"] += 0 if match else 1
            shapes["uuid есть"] += 1 if match else 0
            shapes["synonym есть"] += 1 if "<Synonym>" in text else 0
            shapes["comment непустой"] += 1 if re.search(r"<Comment>[^<]", text) else 0
            extra = [lang for lang in langs if languages and lang not in languages]
            shapes["перевод описания вне Languages/"] += 1 if extra else 0
            if path.stem in SYSTEM_ROLES:
                found[path.stem].append((uuid, langs, corpora.relative(path, ROOTS),
                                         sorted(languages)))

    print("описаний ролей просмотрено:", role_files,
          "| выборка не более", LIMIT_PER_CORPUS, "файлов на корпус")
    print("\n== раскладка описаний ролей")
    for key, value in shapes.most_common():
        print("   ", key.ljust(34), value)
    print("\n== UUID ролей с системным именем")
    for name, items in found.items():
        print("   роль", name)
        for uuid, langs, relative, languages in items:
            print("      ", uuid, "| переводы описания:", langs, "| Languages корпуса:", languages,
                  "|", relative)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
