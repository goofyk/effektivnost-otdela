"""Как канонические конфигурации пишут запросы и типовые конструкции BSL: счётчики по корпусам.

Зачем это нужно. План оптимизации инструментов p1c должен говорить, какие проверки имеют опору в
каноне, а какие нет. У `p1c-check-bsl` и `p1c-sdbl` нет ответа на вопрос «как пишет платформа»:
без счётчиков находка выглядит одинаково и в случае канонической записи, и в случае выдуманной.
Этот замер даёт именно числа: сколько раз та или иная запись встречается в выгрузках реальных
конфигураций.

Что считается. Ровно написания из журнала наблюдений (например `СУММА(` и `МАКСИМУМ(`, а не
`СУММ(`), плюс производные меры, где важен контекст строки: `Новый Массив` с последующей скобкой,
`ЕСТЬNULL(` с `Неопределено` в той же строке, `ДФ=dd.MM.yyyy` внутри строки с `Формат(`.

Два порядка счёта, и они подписаны раздельно. `derived` считается по одной строке модуля.
`derived_text` считается по тексту модуля целиком, потому что канонический текст запроса переносит
слова через вертикальную черту: `ВЫБОР` в начале строки и `КОГДА` в следующей строке — одно выражение
запроса, но подстрока `ВЫБОР КОГДА` его не находит. Перекрывающие подстроки тоже разложены своими
же счётчиками: `ВЫБОР` находит и `ВЫБОРКА`, поэтому рядом стоят `ВЫБОРКА`, `ВЫБОР КОГДА` и
`ВЫБОР ПЕРВОЕ`, и число выражений `ВЫБОР` получается разностью, а не общим счётчиком.

Отличие от `probe/corpora_cli_usage.py`. Тот замер ищет вызовы командной строки и потому не
считает строки длиннее 400 символов. Здесь длина строки не ограничивается вовсе: текст запроса в
каноне — одна строка с переводами через вертикальную черту, и обрезка таких строк занизила бы
счётчик агрегатных функций. Считаются вхождения подстроки, а не числа файлов и не числа строк;
это подписано в отчёте ключом `counting`.

Пути берутся только из `local.paths.json` (ключи `corpora_*`) через `scripts/corpora.py`: в этом
файле путей нет. Читаются только модули (`*.bsl`) размером не больше 2 МБ; обход подписан числом
прочитанных модулей и модулей форм на каждый корпус.

    $env:PYTHONIOENCODING="utf-8"
    python probe/corpora_query_canon.py --json reports/corpora-query-canon-16.json
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import corpora                                                   # noqa: E402
import paths                                                     # noqa: E402

# Простые подстроки: считаем ровно это написание, без вариантов. Имена агрегатных функций берутся
# каноническими: `СУММ(` и `МАКС(` здесь перечислены именно как проверка «так не пишут» — у них
# ожидается ноль или близкие к нулю значения.
NEEDLES = (
    "СУММА(",
    "МАКСИМУМ(",
    "МИНИМУМ(",
    "СУММ(",
    "МАКС(",
    "ЕСТЬNULL(",
    "ПОМЕСТИТЬ вт",
    "УНИЧТОЖИТЬ вт",
    "ЛЕВОЕ СОЕДИНЕНИЕ вт",
    ".Обороты(",
    "Новый Массив",
    ".Добавить(",
    "Новый Соответствие",
    ".Получить(",
    ".Существует(",
    "СтрСоединить",
    "СтрСконать",
    "ЧДЦ=",
    "ЧДЦ=2",
    "ЧГ=0",
    "ДФ=dd.MM.yyyy",
    "Формат(",
    "ВЫБОР",
    # `ВЫБОР` само по себе считает и `ВЫБОРКА` (в нём же подстрока), поэтому рядом стоят отдельные
    # счётчики: `ВЫБОРКА` как ключевое слово запроса и две формы выражения `ВЫБОР`.
    "ВЫБОРКА",
    "ВЫБОР КОГДА",
    "ВЫБОР ПЕРВОЕ",
)

# Производные меры: важно не само написание, а то, стоит ли оно в одном контексте с другим.
# Поиск не жадный (`*?`): в одной строке бывает два `ЕСТЬNULL(..., Неопределено)`, и жадный поиск
# посчитал бы такую строку один раз.
DERIVED = {
    "Новый Массив(": re.compile(r"Новый\s+Массив\s*\("),
    "ЕСТЬNULL(...Неопределено)": re.compile(r"ЕСТЬNULL\([^\n]*?Неопределено"),
    "ДФ=dd.MM.yyyy внутри Формат(": re.compile(r"Формат\([^\n]*?ДФ=dd\.MM\.yyyy"),
    "?(": re.compile(r"\?\("),
}

# Текстовые меры: двухсловные написания запроса в каноне стоят на разных строках одной и той же
# строки-запроса (`ВЫБОР` и `КОГДА` разделены переводом строки и вертикальной чертой), поэтому
# посострочный поиск их не видит вовсе. Эти меры считаются по тексту модуля целиком и поэтому
# подписаны отдельно: `ВЫБОР КОГДА` как подстрока считает только однострочную запись.
DERIVED_TEXT = {
    "ВЫБОР ... КОГДА (любой перенос)": re.compile(r"ВЫБОР[\s|]+КОГДА"),
    "ВЫБОР ... ПЕРВОЕ (любой перенос)": re.compile(r"ВЫБОР[\s|]+ПЕРВОЕ"),
}

# Файлы больше 2 МБ в корпусах — выгрузки макетов и форм; модули такого размера встречаются редко,
# и пропуск подписан числом пропущенных файлов.
MAX_FILE_BYTES = 2 * 1024 * 1024

FORM_MODULE_SUFFIX = "/Ext/Form/Module.bsl"


def is_form_module(path: pathlib.Path, root: pathlib.Path) -> bool:
    """Модуль формы, а не модуль объекта/общего модуля/обработки.

    Формы в выгрузке лежат двумя способами: у объекта — `<Объект>/Forms/<Форма>/Ext/Form/Module.bsl`
    (есть каталог `Forms`), у общих форм — `CommonForms/<Форма>/Ext/Form/Module.bsl` (каталога
    `Forms` нет, есть корневой каталог с окончанием `Forms`). Проверка только по `/Forms/`
    занижает число модулей форм: в `corpora_ssl` так теряются 120 модулей общих форм.
    """
    posix = path.relative_to(root).as_posix()
    if not posix.endswith(FORM_MODULE_SUFFIX):
        return False
    directories = posix.split("/")[:-2]
    return "Forms" in directories or bool(directories) and directories[0].endswith("Forms")


def scan(roots: dict, needles: tuple = NEEDLES, derived: dict | None = None,
         derived_text: dict | None = None) -> dict:
    """Счёт вхождений по модулям каждого корпуса.

    `derived` считается по строкам целиком (без ограничения длины строки), потому что текст запроса
    в каноне — одна длинная строка. `derived_text` считается по тексту модуля целиком, потому что
    двухсловные написания запроса в каноне разделены переносом строки-запроса.
    """
    derived = DERIVED if derived is None else derived
    derived_text = DERIVED_TEXT if derived_text is None else derived_text
    counts = {needle: {} for needle in needles}
    derived_counts = {name: {} for name in derived}
    derived_text_counts = {name: {} for name in derived_text}
    modules_scanned, form_modules, skipped_large = {}, {}, {}
    for label, root in sorted(roots.items()):
        root = pathlib.Path(root)
        seen = forms = large = 0
        for path in sorted(root.rglob("*.bsl"), key=lambda item: item.relative_to(root).as_posix()):
            if not path.is_file():
                continue
            try:
                if path.stat().st_size > MAX_FILE_BYTES:
                    large += 1
                    continue
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            seen += 1
            if is_form_module(path, root):
                forms += 1
            lines = text.splitlines()
            for needle in needles:
                hits = text.count(needle)
                if hits:
                    counts[needle][label] = counts[needle].get(label, 0) + hits
            for name, pattern in derived.items():
                hits = sum(len(pattern.findall(line)) for line in lines)
                if hits:
                    derived_counts[name][label] = derived_counts[name].get(label, 0) + hits
            for name, pattern in derived_text.items():
                hits = len(pattern.findall(text))
                if hits:
                    derived_text_counts[name][label] = derived_text_counts[name].get(label, 0) + hits
        modules_scanned[label] = seen
        form_modules[label] = forms
        skipped_large[label] = large
    return {"counts": counts, "derived_counts": derived_counts,
            "derived_text_counts": derived_text_counts,
            "modules_scanned": modules_scanned, "form_modules": form_modules,
            "skipped_large_files": skipped_large}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--local", default=str(ROOT / "local.paths.json"))
    parser.add_argument("--json", default=str(ROOT / "reports" / "corpora-query-canon-16.json"))
    args = parser.parse_args(argv)

    local = paths.load_local(args.local)
    roots = {}
    for key, value in sorted(local.items()):
        if not key.startswith(paths.KNOWN_PREFIXES[0]):
            continue
        directory = pathlib.Path(value)
        if directory.is_dir():
            roots[key.removeprefix(paths.KNOWN_PREFIXES[0])] = directory
    accepted = corpora.report(args.local)
    scan_roots = {label: path for label, path in roots.items()
                  if f"corpora_{label}" in accepted["accepted"]}
    skipped = [key for key in accepted["configured"]
               if key not in {f"corpora_{label}" for label in scan_roots}]

    result = scan(scan_roots)
    result["corpora_accepted"] = accepted["accepted"]
    result["corpora_skipped"] = skipped
    result["needles"] = list(NEEDLES)
    result["derived"] = list(DERIVED)
    result["derived_text"] = list(DERIVED_TEXT)
    result["counting"] = ("число вхождений подстроки во все прочитанные модули (*.bsl); строки не "
                          "обрезаются по длине; производные меры считаются регулярным выражением по "
                          "одной строке; текстовые меры — регулярным выражением по тексту модуля "
                          "целиком")
    result["limits"] = {"max_file_bytes": MAX_FILE_BYTES}
    result["totals"] = {needle: sum(counts.values()) for needle, counts in result["counts"].items()}
    result["derived_totals"] = {name: sum(counts.values())
                                for name, counts in result["derived_counts"].items()}
    result["derived_text_totals"] = {name: sum(counts.values())
                                     for name, counts in result["derived_text_counts"].items()}
    output = pathlib.Path(args.json)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    for needle in NEEDLES:
        print(f"{needle}: {result['totals'][needle]} -> "
              f"{json.dumps(result['counts'][needle], ensure_ascii=False)}")
    for name in DERIVED:
        print(f"{name}: {result['derived_totals'][name]} -> "
              f"{json.dumps(result['derived_counts'][name], ensure_ascii=False)}")
    for name in DERIVED_TEXT:
        print(f"{name}: {result['derived_text_totals'][name]} -> "
              f"{json.dumps(result['derived_text_counts'][name], ensure_ascii=False)}")
    print(f"modules_scanned: {json.dumps(result['modules_scanned'], ensure_ascii=False)}")
    print(f"form_modules: {json.dumps(result['form_modules'], ensure_ascii=False)}")
    print(f"skipped_large_files: {json.dumps(result['skipped_large_files'], ensure_ascii=False)}")
    print(f"accepts: {', '.join(accepted['accepted'])}")
    print(f"skipped: {', '.join(skipped) or 'нет'}")
    print(f"report -> {output.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
