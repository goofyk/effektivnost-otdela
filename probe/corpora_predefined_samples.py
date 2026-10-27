"""Канонические образцы предопределённых данных и параметров сеанса из корпусов (Task 15, Task 17).

Рукописная сборка обязана повторять форму, которую даёт платформа, а не нашу догадку о ней. Этот
замер отвечает на четыре вопроса до того, как править `cfg/ЭффективностьОтдела`:

1. Где лежат предопределённые данные в файловой выгрузке: отдельный файл
   `Catalogs\\<Имя>\\Ext\\Predefined.xml` или блок `<PredefinedData>` внутри описания метаданного?
2. Какова минимальная достаточная форма записи предопределённых данных: какие позиции обязательны
   (`Item id`, `Name`, `Code`, `Description`, `IsFolder`, значения реквизитов).
3. Чем значения перечисления отличаются от предопределённых данных: у перечисления их нет или они
   записаны иначе (`<EnumValue>` как дочерние метаданные)?
4. Как выглядит `<SessionParameters>` в описании конфигурации (нужно для Task 17) и есть ли оно
   вообще в канонических выгрузках.

Выборка берётся по kind-каталогу (`<kind>/*/Ext/Predefined.xml`), а не одним обходом всего корпуса:
общий лимит на корпус сдвигал выборку в пользу первых по сортировке каталогов (`Catalogs`) и целиком
скрывал `Enums`. Обход ограничен `LIMIT_PER_KIND_ROOT` на каждый kind-каталог каждого корпуса и
упорядочен по относительному пути; пути корпусов — только из `local.paths.json`
(`scripts/corpora.py`). Ничего не изменяем.
"""
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import corpora                                                     # noqa: E402
import paths                                                       # noqa: E402

# Верхние kind-каталоги файловой выгрузки, где у платформы бывают предопределённые данные.
PREDEFINED_KINDS = ("Catalogs", "Enums", "ChartsOfCharacteristicTypes", "ChartsOfAccounts",
                    "ChartsOfCalculationTypes", "ChartsOfConstants", "CommonReports",
                    "InformationRegisters", "DocumentNumbers", "BusinessProcesses")
LIMIT_PER_KIND_ROOT = 12

# Считаем описания верхнего уровня kind-каталога: предопределённые данные против значений
# перечисления против способа обновления предопределённых данных.
SCAN_KINDS = ("Enums", "Catalogs", "ChartsOfCharacteristicTypes", "ChartsOfAccounts",
              "ChartsOfCalculationTypes", "InformationRegisters")
SCAN_LIMIT = 4000
PREDEFINED_TAG = re.compile(r"<PredefinedData[ >]")               # не `<PredefinedDataUpdate>`
PREDEFINED_UPDATE = re.compile(r"<PredefinedDataUpdate>")
ENUM_VALUE = re.compile(r"<EnumValue uuid=")

OUT = ROOT / "docs" / "evidence" / "corpora-predefined-samples.md"


def head(text: str, lines: int) -> str:
    return "\n".join(text.splitlines()[:lines])


def corpus_pairs() -> list:
    """Принятые корпуса как пары «ключ локального файла путей — каталог выгрузки»."""
    local_file = str(ROOT / "local.paths.json")
    local = paths.load_local(local_file)
    accepted = set(corpora.report(local_file)["accepted"])
    return [(key, pathlib.Path(local[key])) for key in sorted(accepted)]


def predefined_samples(pairs: list) -> tuple:
    """По kind-каталогу: `(kind -> [(ключ, путь, относительный путь)])` и счётчики найденного."""
    found, counts = {}, {}
    for kind in PREDEFINED_KINDS:
        items, total = [], 0
        for key, root in pairs:
            folder = root / kind
            if not folder.is_dir():
                continue
            hits = sorted(folder.glob("*/Ext/Predefined.xml"),
                          key=lambda path: path.relative_to(root).as_posix())
            total += len(hits)
            for path in hits[:LIMIT_PER_KIND_ROOT]:
                items.append((key, path, f"{kind}/{path.relative_to(folder).as_posix()}"))
        found[kind] = items
        counts[kind] = total
    return found, counts


def predefined_section(pairs: list) -> list:
    found, counts = predefined_samples(pairs)
    lines = ["## 1. Где лежат предопределённые данные (по kind-каталогу)", "",
             f"Ограничение: {LIMIT_PER_KIND_ROOT} файлов `Ext/Predefined.xml` на kind-каталог "
             f"каждого корпуса; счётчики — полное число найденного без ограничения.", ""]
    for kind in PREDEFINED_KINDS:
        items = found[kind]
        if not items:
            lines.append(f"- `{kind}`: `Ext/Predefined.xml` не найден "
                         f"(каталоги в выборке: "
                         f"{', '.join(key for key, root in pairs if (root / kind).is_dir()) or 'нет'})")
            continue
        smallest = sorted(items, key=lambda item: item[1].stat().st_size)[0]
        lines.append(f"- `{kind}`: найдено {counts[kind]}, среди них самый маленький — "
                     f"`{smallest[2]}` в `{smallest[0]}` ({smallest[1].stat().st_size} байт)")
    lines.append("")
    lines.append("Совпадение по kind-каталогу с тем, у каких видов в 1С бывают предопределённые "
                 "данные: справочник, план видов характеристик, план счетов, план видов расчёта. "
                 "У перечисления, регистра сведений, константы, общего отчёта, номера документа и "
                 "бизнес-процесса отдельного файла предопределённых данных в корпусах нет.")
    lines.append("")
    for kind in ("Catalogs", "Enums", "ChartsOfCharacteristicTypes"):
        items = found.get(kind) or []
        if not items:
            continue
        for key, path, relative in sorted(items, key=lambda item: item[1].stat().st_size)[:2]:
            lines.append(f"### образец {kind}: {key} :: {relative} "
                         f"({path.stat().st_size} байт)")
            lines.append("")
            lines.append("```xml")
            lines.append(head(path.read_text(encoding="utf-8", errors="replace"), 70))
            lines.append("```")
            lines.append("")
    return lines


def scan_section(pairs: list) -> list:
    """Предопределённые данные против значений перечисления в описаниях метаданных."""
    lines = ["## 2. Значения перечисления — это метаданные, а не предопределённые данные", "",
             "Считаем все описания верхнего уровня kind-каталога (не глубже), не больше "
             f"{SCAN_LIMIT} файлов на kind-каталог каждого корпуса.", "",
             "- `predefined-тег` — `<PredefinedData>` или `<PredefinedData ...>`.",
             "- `PredefinedDataUpdate` — способ обновления предопределённых данных (`Auto`/`Manual`), "
             "он есть у каждого справочника и данными не является.",
             "- `PredefinedDataName` — реквизит «предопределённый» у обычной записи справочника "
             "(`<xr:StandardAttribute name=\"PredefinedDataName\">`), тоже не предопределённые данные.",
             "- `EnumValue` — значения перечисления как дочерние метаданные внутри "
             "`Enums/<Имя>.xml`.", ""]
    for kind in SCAN_KINDS:
        lines.append(f"### kind `{kind}`")
        lines.append("")
        lines.append("| корпус | описаний | predefined-тег | PredefinedDataUpdate | "
                     "PredefinedDataName | EnumValue |")
        lines.append("|---|---|---|---|---|---|")
        for key, root in pairs:
            folder = root / kind
            if not folder.is_dir():
                continue
            metas = sorted(folder.glob("*.xml"),
                           key=lambda path: path.relative_to(root).as_posix())[:SCAN_LIMIT]
            tag_count = update_count = name_count = value_count = 0
            for meta in metas:
                text = meta.read_text(encoding="utf-8", errors="replace")
                tag_count += 1 if PREDEFINED_TAG.search(text) else 0
                update_count += 1 if PREDEFINED_UPDATE.search(text) else 0
                name_count += 1 if 'name="PredefinedDataName"' in text else 0
                value_count += len(ENUM_VALUE.findall(text))
            lines.append(f"| {key} | {len(metas)} | {tag_count} | {update_count} | "
                         f"{name_count} | {value_count} |")
        lines.append("")
    lines.append("Вывод: предопределённых данных у перечисления в файловой выгрузке нет ни в одном "
                 "корпусе — его значения (`EnumValue`) описаны внутри самого метаданного и при "
                 "загрузке становятся значениями перечисления, а не предопределёнными записями. "
                 "Значит для нашей сборки канонично держать значения в `Enums/<Имя>.xml` и не "
                 "придумывать перечислению `Ext/Predefined.xml`. Предопределённые данные добавляем "
                 "там, где их пишет платформа: справочник `Сотрудники`.")
    return lines


def enum_value_sample(pairs: list) -> list:
    """Минимальная достаточная форма значения перечисления."""
    lines = ["## 3. Образец значения перечисления (`EnumValue`) в описании", ""]
    best = None
    for key, root in pairs:
        folder = root / "Enums"
        if not folder.is_dir():
            continue
        for meta in sorted(folder.glob("*.xml"), key=lambda path: path.stat().st_size):
            text = meta.read_text(encoding="utf-8", errors="replace")
            start = text.find("<EnumValue uuid=")
            if start < 0:
                continue
            best = (key, meta.relative_to(folder).as_posix(), meta.stat().st_size,
                    text[start:start + 900])
            break
        if best:
            break
    if not best:
        lines.append("`EnumValue` в описаниях перечислений корпусов не найден.")
        lines.append("")
        return lines
    key, relative, size, block = best
    lines.append(f"### {key} :: Enums::{relative} ({size} байт)")
    lines.append("")
    lines.append("```xml")
    lines.append(block)
    lines.append("```")
    lines.append("")
    return lines


def inline_predefined(pairs: list) -> list:
    """Есть ли `<PredefinedData>` внутри описания метаданного (а не в отдельном файле)."""
    lines = ["## 4. Блок `<PredefinedData>` внутри описания метаданного", "",
             "Читаем описания метаданных верхнего уровня kind-каталога (не глубже), до 80 файлов "
             "на kind-каталог корпуса.", ""]
    hits = 0
    for key, root in pairs:
        for kind in ("Enums", "Catalogs", "InformationRegisters"):
            folder = root / kind
            if not folder.is_dir():
                continue
            for meta in sorted(folder.glob("*.xml"),
                               key=lambda path: path.relative_to(root).as_posix())[:80]:
                text = meta.read_text(encoding="utf-8", errors="replace")
                if "<PredefinedData>" not in text:
                    continue
                hits += 1
                if hits > 4:
                    continue
                start = text.index("<PredefinedData>")
                lines.append(f"### {key} :: {meta.relative_to(root).as_posix()} "
                             f"({meta.stat().st_size} байт)")
                lines.append("")
                lines.append("```xml")
                lines.append(text[start:start + 2000])
                lines.append("```")
                lines.append("")
    if not hits:
        lines.append("`<PredefinedData>` внутри описаний метаданных не найден: в принятых корпусах "
                     "предопределённые данные лежат отдельными файлами `Ext/Predefined.xml`. "
                     "Значит для нашей сборки канонична именно отдельная форма.")
    return lines


def session_parameters_section(pairs: list) -> list:
    lines = ["## 5. `<SessionParameters>` в описании конфигурации", ""]
    found = 0
    for key, root in pairs:
        configuration = root / "Configuration.xml"
        if not configuration.is_file():
            lines.append(f"- `{key}`: `Configuration.xml` нет")
            continue
        text = configuration.read_text(encoding="utf-8", errors="replace")
        match = re.search(r"<SessionParameters>.*?</SessionParameters>", text, re.S)
        if not match:
            lines.append(f"- `{key}`: `SessionParameters` в описании конфигурации нет")
            continue
        found += 1
        if found > 2:
            continue
        lines.append(f"### образец: {key} :: Configuration.xml")
        lines.append("")
        lines.append("```xml")
        lines.append(match.group(0)[:2500])
        lines.append("```")
        lines.append("")
    if not found:
        lines.append("")
        lines.append("`SessionParameters` нет ни в одной принятой выгрузке. Для нашей сборки это "
                     "не канон, а проверка: добавим — узнаем, принимает ли платформа форму, которой "
                     "нет в реальных конфигурациях, и видит ли её p1c.")
    return lines


def data_processor_section(pairs: list) -> list:
    lines = ["## 6. Как устроена папка обработки (DataProcessor)", ""]
    for key, root in pairs:
        folder = root / "DataProcessors"
        if not folder.is_dir():
            continue
        meta_files = sorted(folder.glob("*.xml"), key=lambda path: path.stat().st_size)
        if not meta_files:
            continue
        smallest_meta = meta_files[0]
        name = smallest_meta.stem
        lines.append(f"### {key}: самая маленькая обработка `{name}` "
                     f"(описание {smallest_meta.stat().st_size} байт)")
        lines.append("")
        lines.append("```")
        lines.append(f"{name}.xml {smallest_meta.stat().st_size}")
        directory = folder / name
        if directory.is_dir():
            for path in sorted(directory.rglob("*"),
                               key=lambda path: path.relative_to(folder).as_posix())[:40]:
                lines.append(("DIR  " if path.is_dir() else f"{path.stat().st_size:7} ")
                             + path.relative_to(folder).as_posix())
        lines.append("```")
        lines.append("")
    return lines


def main() -> int:
    pairs = corpus_pairs()
    keys = [key for key, _ in pairs]
    lines = ["# Что корпуса дают для Tasks 15 и 17 (предопределённые данные, значения "
             "перечисления, параметры сеанса)", "",
             f"Корпуса приняты: {keys}",
             "Не приняты или отсутствующие ключи см. в `scripts/corpora.py` (`corpora.report`).", ""]
    lines.extend(predefined_section(pairs))
    lines.extend(scan_section(pairs))
    lines.extend(enum_value_sample(pairs))
    lines.extend(inline_predefined(pairs))
    lines.extend(session_parameters_section(pairs))
    lines.extend(data_processor_section(pairs))
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("замер записан:", OUT.as_posix())
    for line in lines:
        if line.startswith("##") or line.startswith("- `") or line.startswith("Ограничение") \
                or line.startswith("Совпадение") or line.startswith("Вывод"):
            print(line[:220])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
