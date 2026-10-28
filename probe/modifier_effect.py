"""Замер эффекта модификаторов загрузки: чем лестница Task 16 обернулась для ИБ.

Код возврата 0 у шага лестницы (`scripts/exec_probe.py`) означает только «команду разобрали».
Этот замер отвечает на второй вопрос: что после шага реально лежит в ИБ. Шаг выгружается трижды:
выгрузкой ДО шага (состояние ИБ, на котором шаг стартует), выгрузкой ПОСЛЕ него и ещё раз сразу
после второй выгрузки (между второй и третьей выгрузкой прогона нет); снимки сравниваются по шести
признакам:

1. `PredefinedDataUpdate` в корневых XML объектов (значение ищется по всему дампу);
2. наличие, размер и состав `Catalogs/Сотрудники/Ext/Predefined.xml` (предопределённые данные);
3. `configVersion` каждого метаданного из `ConfigDumpInfo.xml` — отпечатка конфигурации, который
   платформа пишет в выгрузку сама (замер gate-11: `Metadata name=... configVersion=...`). Он
   читается вместе с контролем `--ladder repeat`, потому что сам по себе хешем содержимого не
   является (см. наблюдение ниже);
4. числа раскладки (`scripts/layout.py`) и побайтовое сравнение выгрузки с исходником
   (`scripts/gate.py`, `file_diff`);
5. `config_uuid` — идентификатор конфигурации из тега `<Configuration uuid="...">` в
   `Configuration.xml` выгрузки. Он нужен потому, что о неполной загрузке платформа сообщает
   двумя идентификаторами («идентификатор ... загружаемой конфигурации отличается от
   идентификатора ...»), и второй идентификатор от прогона к прогону меняется (`замеры
   effect-16-loadopts-fresh`, `effect-16-extensions-fresh`, `effect-16-update-fresh`), не совпадая
   ни с uuid конфигурации в исходнике, ни с uuid `Configuration.xml` в выгрузке того же шага.
   Сверка с uuid ИБ ДО шага раньше не измерялась — этот замер её и делает.
6. `dump_twice` — сравнение второй и третьей выгрузок одного шага, между которыми прогона нет (и нет
   `reset_ib` даже в режиме `--fresh-ib`): всё, что в такой паре расходится, делает сама выгрузка.
   Контроль нужен потому, что на ИБ без конфигурации uuid `Configuration.xml` расходится между
   выгрузкой до шага и выгрузкой после него при равных файлах и байтах (замер
   `reports/effect-16-loadopts-fresh2.json`), и без третьей выгрузки нечем отделять «шаг изменил
   идентификатор» от «выгрузка пересоздаёт идентификатор оболочки».

Зачем нужен именно дамп: без него «модификатор принят и применён» и «модификатор принят и
проигнорирован» выглядят одинаково — у шагов `/SetPredefinedDataUpdate <значение>` код 0 бывает
и там, и там. Этот замер переводит наблюдение из «код есть» в «изменение видно».

Два режима прогона (первый режим оставил наблюдение, которое второй и снял):
- общий ИБ (без `--fresh-ib`): шаги идут по одному и тому же состоянию ИБ. Первый замер
  (`reports/effect-16-predefined.json`) показал шесть побайтово одинаковых выгрузок за 1.0 с
  против 2.0 с у эталонного `load-ok` — на уже загруженной ИБ «изменений нет» неотличимо от
  «загрузка не делалась»;
- свежая ИБ на каждый шаг (`--fresh-ib`): каталог ИБ удаляется и создаётся шагом `create` перед
  каждым шагом (`reset_ib`), поэтому шаг сравнивается с тем же шагом на одном старте. Этот режим
  и дал вывод (`reports/effect-16-predefined-fresh.json`): после `/SetPredefinedDataUpdate` в
  хвосте команды `/LoadConfigFromFiles <каталог>` конфигурация в ИБ не загружается вовсе —
  в выгрузке 3 файла вместо 32, при коде 0 и пустом выводе.

Контроль `--ladder repeat` (`REPEAT_CONTROL`, три одинаковых `load-ok` на общей ИБ) измеряет
сам признак `configVersion`: он меняется на каждом шаге (`reports/effect-16-repeat.json`),
то есть `configVersion` из `ConfigDumpInfo.xml` НЕ является хешем содержимого и сам по себе не
доказывает, что модификатор ничего не изменил. На нём стоят вывод `restore_matches_base` и
колонка `config_versions` в отчёте.

Ожидания (`EXPECTATIONS`) пишутся в этом файле ДО прогона и проверяются функцией
`check_expectations` по факту выгрузок: сбылось (`met: true`) или нет (`met: false`), с доказательством
в ключе `evidence`. Ожидание, которое в данном режиме прогона не проверяемо (например сверка
повторных загрузок одной ИБ в режиме `--fresh-ib`), остаётся в отчёте с `met: null`, ненулевым
`note` (почему не проверяемо) и пустым `evidence` — отсутствие проверки не выглядит как сбывшееся
ожидание.

Правила замера:
- прогон только на отдельной временной ИБ: ИБ гейта (ключ `ib` из `local.paths.json`) полигоном
  быть отказывается (код 2), как и прогон без `--allow-mutating`;
- `--fresh-ib` удаляет каталог ИБ: разрешено только для временной ИБ того же каталога, где лежит
  ИБ гейта (и никогда — для самой ИБ гейта);
- 1С-прогоны строго последовательные: выгрузка ИБ до шага, шаг, выгрузка ИБ после шага, вторая
  выгрузка того же состояния, сравнение;
- `cfg/ЭффективностьОтдела` во время замера не изменяется: исходник только читается.

Коды выхода: 0 — все три выгрузки каждого шага (до шага, после него и вторая выгрузка того же
состояния) получились (исходы шагов живут в ключах отчёта, включая `expectations`);
1 — выгрузка шага не получилась или шага нет (замер неполон); 2 — прогон запрещён (ИБ гейта,
нет `--allow-mutating`, ИБ не создана, нет файла платформы).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import exec_probe                                                  # noqa: E402
import gate                                                        # noqa: E402
import ib_loop                                                     # noqa: E402
import layout                                                      # noqa: E402
import paths                                                       # noqa: E402

# Тег пишется без префикса `v8:` (замер gate-11: `<PredefinedDataUpdate>Auto</PredefinedDataUpdate>`);
# префикс в регулярном выражении сделан необязательным, потому что поиск только с `v8:` даёт None
# (наблюдение этой же проверки).
PREDEFINED_TAG = re.compile(r"<(?:v8:)?PredefinedDataUpdate>(.*?)</(?:v8:)?PredefinedDataUpdate>")
METADATA_VERSION = re.compile(r'<Metadata name="([^"]+)"[^>]*?configVersion="([0-9a-fA-F]+)"')
PREDEFINED_ITEM = re.compile(r'<Item id="')
# Идентификатор конфигурации в выгрузке пишется атрибутом корневого тега (`замер gate-11`:
# `<Configuration uuid="6b1e3a24-1c77-4c0a-90d1-0a2f4c6e8001">`).
CONFIG_UUID_TAG = re.compile(r'<Configuration\b[^>]*\buuid="([0-9a-fA-F-]{36})"')
# Так же выглядят идентификаторы, которые платформа называет в тексте ошибки: их читают списком,
# чтобы видеть и «загружаемый», и «тот, от которого отличается».
UUID_TOKEN = re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
                        r"[0-9a-fA-F]{12}\b")
# Списочные признаки выгрузки, которые сравниваются поэлементно (числа файлов и байтов и идентификатор
# `config_uuid` сравниваются отдельно, `config_versions` — своим изменением). Ни один из них не
# выводится из кода шага.
MAP_KEYS = ("counts", "predefined_settings", "predefined_data")

# Названные лестницы `scripts/exec_probe.py`, эффект которых замеряется. Имена и значения
# модификаторов берутся не отсюда, а оттуда: этот замер только смотрит на следствие.
# `repeat` — контроль, которого в `exec_probe.py` нет: три одинаковых шага `/LoadConfigFromFiles`.
# Он нужен из-за находки первого замера (`reports/effect-16-predefined.json`): `configVersion` в
# `ConfigDumpInfo.xml` у двух выгрузок одной и той же конфигурации совпадал для шагов лестницы и
# разошёлся для шага восстановления. Пока не измерено, меняются ли эти версии от самого факта
# загрузки, ни один вывод «изменений нет» на них опираться не должен.
LADDERS = {"predefined": ("PREDEFINED_LADDER", exec_probe.PREDEFINED_LADDER),
           "extensions": ("EXTENSION_LADDER", exec_probe.EXTENSION_LADDER),
           "loadopts": ("LOADOPTS_LADDER", exec_probe.LOADOPTS_LADDER),
           "update": ("UPDATE_LADDER", exec_probe.UPDATE_LADDER),
           "modes": ("MODE_LADDER", exec_probe.MODE_LADDER),
           "repeat": ("REPEAT_CONTROL", (("load-ok", "marker", "cp1251"),) * 3)}


def dump_listing(dump_dir) -> dict:
    """Файлы выгрузки: относительный путь -> файл."""
    base = pathlib.Path(dump_dir)
    return {p.relative_to(base).as_posix(): p for p in sorted(base.rglob("*")) if p.is_file()}


def predefined_settings(dump_dir) -> dict:
    """Значения `PredefinedDataUpdate` по всем XML выгрузки: путь -> значение (или список)."""
    found = {}
    for rel, file in dump_listing(dump_dir).items():
        if file.suffix.lower() != ".xml":
            continue
        values = PREDEFINED_TAG.findall(file.read_text(encoding="utf-8-sig", errors="replace"))
        if values:
            found[rel] = values[0] if len(values) == 1 else values
    return found


def predefined_data(dump_dir) -> dict:
    """Предопределённые данные: файл -> размер, число записей и отпечаток содержимого."""
    found = {}
    for rel, file in dump_listing(dump_dir).items():
        if not rel.endswith("/Ext/Predefined.xml"):
            continue
        data = file.read_bytes()
        text = data.decode("utf-8-sig", "replace")
        found[rel] = {"bytes": len(data), "items": len(PREDEFINED_ITEM.findall(text)),
                      "sha1": hashlib.sha1(data).hexdigest()[:16]}
    return found


def config_versions(dump_dir) -> dict:
    """`configVersion` из `ConfigDumpInfo.xml`: отпечаток той конфигурации, что лежит в ИБ."""
    file = pathlib.Path(dump_dir) / "ConfigDumpInfo.xml"
    if not file.is_file():
        return {}
    return dict(METADATA_VERSION.findall(file.read_text(encoding="utf-8-sig", errors="replace")))


def config_uuid(dump_dir) -> str:
    """Идентификатор конфигурации, который платформа записала в выгрузку (пустая строка, если
    `Configuration.xml` в выгрузке не читается или тега без атрибута `uuid` в нём нет)."""
    file = pathlib.Path(dump_dir) / "Configuration.xml"
    if not file.is_file():
        return ""
    match = CONFIG_UUID_TAG.search(file.read_text(encoding="utf-8-sig", errors="replace"))
    return match.group(1).lower() if match else ""


def source_config_uuid(cfg) -> str:
    """Uuid конфигурации в исходнике: с ним сверяются идентификаторы, названные платформой."""
    return config_uuid(cfg)


def out_line_stats(lines) -> tuple:
    """Все непустые строки вывода шага и их неповторяющаяся часть.

    Нужно потому, что в отчёт попадают только первые 8 строк (`lines`): по ним многострочный отказ
    выглядит коротким. Наблюдение `reports/effect-16-extensions-fresh.json`, шаг
    `load-allextensions-flag`: в отчёте 8 строк, а полный вывод — 24 строки в 12 каталогах.
    """
    rows = [line.strip() for line in lines or [] if line.strip()]
    return rows, sorted(set(rows))


def identifiers_in(lines) -> list:
    """Идентификаторы, названные платформой в выводе шага, в порядке появления (без повторов)."""
    found = []
    for line in lines or []:
        for value in UUID_TOKEN.findall(line):
            if value.lower() not in found:
                found.append(value.lower())
    return found


def fingerprint(dump_dir) -> dict:
    """Снимок выгрузки: независимые признаки состояния конфигурации ИБ."""
    files = dump_listing(dump_dir)
    return {"files": len(files),
            "bytes": sum(file.stat().st_size for file in files.values()),
            "counts": layout.layout_counts(dump_dir, ignore=("ConfigDumpInfo.xml",)),
            "predefined_settings": predefined_settings(dump_dir),
            "predefined_data": predefined_data(dump_dir),
            "config_versions": config_versions(dump_dir),
            "config_uuid": config_uuid(dump_dir)}


def version_changes(previous: dict, current: dict) -> dict:
    """Изменения отпечатка: имя метаданного -> [прежняя версия, новая версия]."""
    names = set(previous) | set(current)
    return {name: [previous.get(name), current.get(name)] for name in sorted(names)
            if previous.get(name) != current.get(name)}


def fingerprint_diff(previous: dict | None, current: dict) -> dict:
    """Что изменилось между выгрузками соседних шагов (пустой словарь = изменений нет).

    `previous` может быть `None`: базовый шаг лестницы (`load-ok`) сравнивать не с чем, его выгрузка
    и есть база для последующих сравнений.
    """
    if previous is None:
        return {}
    changed = {}
    for key in ("files", "bytes", "config_uuid"):
        if previous.get(key) != current.get(key):
            changed[key] = [previous.get(key), current.get(key)]
    for key in MAP_KEYS:
        before, after = previous.get(key, {}), current.get(key, {})
        names = set(before) | set(after)
        items = {name: [before.get(name), after.get(name)] for name in sorted(names)
                 if before.get(name) != after.get(name)}
        if items:
            changed[key] = items
    if versions := version_changes(previous.get("config_versions", {}),
                                   current.get("config_versions", {})):
        changed["config_versions"] = versions
    return changed


# Ожидания, записанные ДО прогона. Их источник — наблюдения прежних замеров (в тексте каждой строки
# назван отчёт); проверяет их `check_expectations` по факту выгрузок. Ни одно ожидание не выводится
# из кода возврата шага: код в этих проверках не читается вовсе.
EXPECTATIONS = {
    "partial-second-identifier-is-ib-uuid-before-step":
        "В сообщении о частичной загрузке второй названный идентификатор равен `config_uuid` ИБ ДО "
        "этого шага. Наблюдение, из которого оно выросло: `reports/effect-16-loadopts-fresh.json`, "
        "`effect-16-extensions-fresh.json`, `effect-16-update-fresh.json` — второй идентификатор "
        "каждый прогон новый и не совпадает ни с uuid исходника, ни с uuid `Configuration.xml` в "
        "выгрузке этого же шага.",
    "full-load-keeps-source-uuid":
        "Выгрузка, где `config_uuid` равен uuid конфигурации в исходнике, содержит всю конфигурацию "
        "(файлов ровно столько, сколько у шага восстановления); выгрузка с чужим uuid содержит "
        "только оболочку ИБ. Проверяет вывод «код 0 при ИБ без конфигурации».",
    "empty-ib-has-its-own-uuid":
        "У ИБ, в которую ничего не загружали (выгрузка до первого шага на свежей ИБ), свой "
        "`config_uuid`; uuid исходника появляется в ИБ только вместе с загрузкой.",
    "ib-uuid-survives-its-own-dump":
        "Выгрузка состояние ИБ не меняет: `config_uuid` выгрузки ДО шага N равен `config_uuid` "
        "выгрузки ПОСЛЕ шага N-1 (общий ИБ, без `--fresh-ib`).",
    "repeat-load-keeps-uuid":
        "Повторная загрузка той же конфигурации в ту же ИБ не меняет `config_uuid`, хотя "
        "`config_versions` при этом расходятся (контроль `--ladder repeat` на общей ИБ).",
    "dump-regenerates-uuid-of-empty-ib":
        "Две выгрузки одного и того же состояния ИБ без конфигурации (между ними нет шага) дают "
        "разные `config_uuid` при равных файлах и байтах: идентификатор оболочки выгрузка "
        "пересоздаёт сама. Наблюдение, из которого оно выросло: `reports/effect-16-loadopts-"
        "fresh2.json` — на шагах с отказом загрузки файлов 3 и байт 11873 ровно столько же, "
        "сколько в выгрузке до шага, но `config_uuid` другой, и он же не равен второму "
        "идентификатору из вывода шага.",
    "dump-keeps-uuid-of-loaded-config":
        "Две выгрузки одного и того же состояния ИБ с загруженной конфигурацией (между ними нет "
        "шага) дают одинаковый `config_uuid`, одинаковые файлы и байты: идентификатор загруженной "
        "конфигурации выгрузка не двигает.",
}
EXPECTATION_NOT_APPLICABLE = "ожидание в этом режиме прогона не проверяемо: нет подходящих пар шагов"


def _uuid_of(step: dict, key: str) -> str:
    """`config_uuid` из снимка шага (`fingerprint` — после шага, `before_fingerprint` — до него)."""
    return (step.get(key) or {}).get("config_uuid", "")


def check_partial_identifier(report: dict) -> dict:
    """Второй идентификатор сообщения о частичной загрузке = идентификатор конфигурации в ИБ до шага."""
    source = report.get("source_uuid", "")
    rows = []
    for step in report["steps"]:
        named = step.get("identifiers") or []
        if len(named) < 2:
            continue
        rows.append({"index": step["index"], "variant": step["variant"], "named": named,
                     "first_is_source_uuid": named[0] == source,
                     "before_uuid": _uuid_of(step, "before_fingerprint"),
                     "after_uuid": _uuid_of(step, "fingerprint"),
                     "second_is_before_uuid": named[1] == _uuid_of(step, "before_fingerprint")})
    if not rows:
        return {"claim": EXPECTATIONS["partial-second-identifier-is-ib-uuid-before-step"],
                "met": None, "note": EXPECTATION_NOT_APPLICABLE, "evidence": rows}
    return {"claim": EXPECTATIONS["partial-second-identifier-is-ib-uuid-before-step"],
            "met": all(row["second_is_before_uuid"] for row in rows), "evidence": rows}


def check_full_load_keeps_source_uuid(report: dict) -> dict:
    """Свой uuid выгрузки <=> полная раскладка конфигурации (сверка с шагом восстановления)."""
    source = report.get("source_uuid", "")
    full = report["restore"]["fingerprint"]["files"]
    rows = []
    for step in list(report["steps"]) + [report["restore"]]:
        uuid = _uuid_of(step, "fingerprint")
        rows.append({"index": step["index"], "variant": step["variant"],
                     "files": step["fingerprint"]["files"], "uuid": uuid,
                     "uuid_is_source": uuid == source,
                     "full_layout": step["fingerprint"]["files"] == full,
                     "agrees": (uuid == source) == (step["fingerprint"]["files"] == full)})
    return {"claim": EXPECTATIONS["full-load-keeps-source-uuid"],
            "met": all(row["agrees"] for row in rows), "evidence": rows}


def check_empty_ib_has_own_uuid(report: dict) -> dict:
    """Свежесозданная ИБ (выгрузка до первого шага) имеет свой идентификатор конфигурации."""
    source = report.get("source_uuid", "")
    full = report["restore"]["fingerprint"]["files"]
    rows = [{"index": step["index"], "variant": step["variant"],
             "files": (step.get("before_fingerprint") or {}).get("files", 0),
             "uuid": _uuid_of(step, "before_fingerprint"), "uuid_is_source":
                 _uuid_of(step, "before_fingerprint") == source}
            for step in report["steps"]
            if (step.get("before_fingerprint") or {}).get("files", 0) < full]
    if not rows:
        return {"claim": EXPECTATIONS["empty-ib-has-its-own-uuid"], "met": None,
                "note": EXPECTATION_NOT_APPLICABLE, "evidence": rows}
    return {"claim": EXPECTATIONS["empty-ib-has-its-own-uuid"],
            "met": all(row["uuid"] and not row["uuid_is_source"] for row in rows),
            "distinct_uuids": sorted({row["uuid"] for row in rows}), "evidence": rows}


def _consecutive_pairs(steps: list) -> list:
    """Пары соседних шагов (N-1 -> N) с идентификаторами: что переносит выгрузка и что меняет шаг."""
    pairs = []
    for previous, current in zip(steps, steps[1:]):
        pairs.append({"from": previous["index"], "to": current["index"],
                      "variants": [previous["variant"], current["variant"]],
                      "after_previous_uuid": _uuid_of(previous, "fingerprint"),
                      "before_current_uuid": _uuid_of(current, "before_fingerprint"),
                      "after_current_uuid": _uuid_of(current, "fingerprint"),
                      # Выгрузка состояния ИБ не меняет: идентификатор до шага N = идентификатор после
                      # шага N-1.
                      "same_uuid": _uuid_of(previous, "fingerprint")
                      == _uuid_of(current, "before_fingerprint"),
                      # Шаг той же команды повторную загрузку не меняет: идентификатор до шага N =
                      # идентификатор после шага N.
                      "load_kept_uuid": _uuid_of(current, "before_fingerprint")
                      == _uuid_of(current, "fingerprint")})
    return pairs


def check_uuid_survives_dump(report: dict) -> dict:
    """Выгрузка ИБ не меняет её идентификатор (сравниваются выгрузки без шага между ними)."""
    if report.get("ib_fresh_each_step"):
        # Между выгрузкой после шага N и выгрузкой до шага N+1 каталог ИБ удаляется и создаётся
        # заново, поэтому сравнение этих двух выгрузок ничего про выгрузку не сообщает.
        return {"claim": EXPECTATIONS["ib-uuid-survives-its-own-dump"], "met": None,
                "note": "в режиме --fresh-ib между выгрузками стоит `reset_ib`; пары выгрузок без "
                        "шага между ними даёт ключ `dump_twice` (ожидания `dump-regenerates-uuid-of-"
                        "empty-ib` и `dump-keeps-uuid-of-loaded-config`)", "evidence": []}
    pairs = _consecutive_pairs(report["steps"])
    return {"claim": EXPECTATIONS["ib-uuid-survives-its-own-dump"],
            "met": all(pair["same_uuid"] for pair in pairs) if pairs else None,
            "note": EXPECTATION_NOT_APPLICABLE if not pairs else "", "evidence": pairs}


def check_repeat_load_keeps_uuid(report: dict) -> dict:
    """Повтор той же команды загрузки на той же ИБ оставляет идентификатор неизменным."""
    if report.get("ib_fresh_each_step"):
        return {"claim": EXPECTATIONS["repeat-load-keeps-uuid"], "met": None,
                "note": "в режиме --fresh-ib каждый повтор идёт на своей ИБ", "evidence": []}
    pairs = [pair for pair in _consecutive_pairs(report["steps"]) if pair["variants"][0]
             == pair["variants"][1]]
    if not pairs:
        return {"claim": EXPECTATIONS["repeat-load-keeps-uuid"], "met": None,
                "note": EXPECTATION_NOT_APPLICABLE, "evidence": pairs}
    # Повтор той же команды не двигает идентификатор: `before` шага = `after` этого же шага, и он же
    # = `after` предыдущего шага (иначе сравнение было бы сравнением двух разных ИБ).
    return {"claim": EXPECTATIONS["repeat-load-keeps-uuid"],
            "met": all(pair["same_uuid"] and pair["load_kept_uuid"] for pair in pairs),
            "evidence": pairs}


def _dump_twice(report: dict) -> list:
    """Пары «выгрузка ПОСЛЕ шага -> вторая выгрузка того же состояния»: шага между ними нет.

    Это единственный контроль замера, где две выгрузки идут подряд без прогона между ними (и без
    `reset_ib` в режиме `--fresh-ib`): всё, что расходится в такой паре, делает сама выгрузка.
    """
    return [{"index": step["index"], "variant": step["variant"], **step["dump_twice"]}
            for step in list(report["steps"]) + [report["restore"]] if step.get("dump_twice")]


def check_dump_regenerates_empty_ib_uuid(report: dict) -> dict:
    """На ИБ без конфигурации повторная выгрузка пересоздаёт её идентификатор конфигурации."""
    full = report["restore"]["fingerprint"]["files"]
    rows = [row for row in _dump_twice(report) if max(row["files"]) < full]
    if not rows:
        return {"claim": EXPECTATIONS["dump-regenerates-uuid-of-empty-ib"], "met": None,
                "note": EXPECTATION_NOT_APPLICABLE, "evidence": rows}
    return {"claim": EXPECTATIONS["dump-regenerates-uuid-of-empty-ib"],
            "met": all(not row["same_uuid"] and row["same_files"] and row["same_bytes"]
                       for row in rows), "evidence": rows}


def check_dump_keeps_loaded_uuid(report: dict) -> dict:
    """На ИБ с загруженной конфигурацией повторная выгрузка идентификатор не меняет."""
    full = report["restore"]["fingerprint"]["files"]
    rows = [row for row in _dump_twice(report)
            if min(row["files"]) == full and max(row["files"]) == full]
    if not rows:
        return {"claim": EXPECTATIONS["dump-keeps-uuid-of-loaded-config"], "met": None,
                "note": EXPECTATION_NOT_APPLICABLE, "evidence": rows}
    return {"claim": EXPECTATIONS["dump-keeps-uuid-of-loaded-config"],
            "met": all(row["same_uuid"] and row["same_files"] and row["same_bytes"]
                       for row in rows), "evidence": rows}


EXPECTATION_CHECKS = {
    "partial-second-identifier-is-ib-uuid-before-step": check_partial_identifier,
    "full-load-keeps-source-uuid": check_full_load_keeps_source_uuid,
    "empty-ib-has-its-own-uuid": check_empty_ib_has_own_uuid,
    "ib-uuid-survives-its-own-dump": check_uuid_survives_dump,
    "repeat-load-keeps-uuid": check_repeat_load_keeps_uuid,
    "dump-regenerates-uuid-of-empty-ib": check_dump_regenerates_empty_ib_uuid,
    "dump-keeps-uuid-of-loaded-config": check_dump_keeps_loaded_uuid,
}


def check_expectations(report: dict) -> dict:
    """Сбылось ли написанное до прогона: имя ожидания -> {claim, met, evidence} (или met null)."""
    return {name: EXPECTATION_CHECKS[name](report) for name in EXPECTATIONS}


def reset_ib(ib: str, bin_path: str, work: pathlib.Path, index: int, timeout: int) -> dict:
    """Уничтожить каталог ИБ и создать его заново шагом `create` (режим `--fresh-ib`).

    Зачем: первый замер (`reports/effect-16-predefined.json`) показал, что шаги лестницы шли по
    быстрой цепи — 1.0 с вместо 2.0 с у эталонного `load-ok`, шесть выгрузок совпали побайтово,
    а `PredefinedDataUpdate` остался `Auto`. На уже загруженной ИБ «никаких изменений» нельзя
    отличить от «загрузка не делалась». Каждый шаг в этом режиме начинается с пустой ИБ.
    """
    path = pathlib.Path(ib)
    removed = False
    if path.exists():
        shutil.rmtree(path)
        removed = True
    result = ib_loop.run_step("create", {"bin": bin_path, "ib": ib,
                                         "out": str(work / f"effect_{index:02d}_create.txt"),
                                         "timeout": timeout})
    return {"removed": removed, "code": result["code"], "seconds": result["seconds"],
            "bytes": result["bytes"], "timed_out": result["timed_out"],
            "lines": result["lines"][:4], "reason": result.get("reason", "")}


def run_and_dump(variant: str, kind: str, encoding: str, bin_path: str, ib: str, cfg: str,
                 work: pathlib.Path, dump_root: pathlib.Path, index: int, timeout: int,
                 loadlist: str) -> dict:
    """Один шаг: выгрузка ИБ ДО шага, прогон варианта лестницы, затем выгрузка ИБ ПОСЛЕ шага.

    Выгрузка до шага нужна для одного вопроса: с каким идентификатором конфигурации шаг встретил ИБ.
    Сообщение о частичной загрузке называет два идентификатора, и раньше сверять было не с чем:
    второй идентификатор сравнивался только с выгрузкой этого же шага (после прогона).

    Третья выгрузка (`dump_twice`) идёт сразу за второй, без прогона между ними: она нужна, чтобы
    отделить «шаг изменил состояние ИБ» от «сама выгрузка пересоздаёт идентификатор». Разница между
    второй и третьей выгрузкой объясняется только выгрузкой: между ними не происходит ничего.
    """
    before_dir = dump_root / f"{index:02d}_{variant}_before"
    before_dump = ib_loop.run_step("dump", {"bin": bin_path, "ib": ib, "cfg": cfg,
                                            "dump": str(before_dir),
                                            "out": str(work / f"effect_{index:02d}_{variant}_before.txt"),
                                            "timeout": timeout})
    result = exec_probe.run(bin_path, ib, exec_probe.PROGRAMS[kind], variant, work, timeout,
                            encoding, program_kind=kind,
                            write_script=kind != "missing" and exec_probe.needs_script(variant),
                            cfg=cfg, loadlist=loadlist)
    dump_dir = dump_root / f"{index:02d}_{variant}"
    dump_result = ib_loop.run_step("dump", {"bin": bin_path, "ib": ib, "cfg": cfg,
                                            "dump": str(dump_dir),
                                            "out": str(work / f"effect_{index:02d}_{variant}_dump.txt"),
                                            "timeout": timeout})
    # Третья выгрузка того же состояния (без шага между второй и третьей): разделительный контроль
    # для наблюдения `effect-16-loadopts-fresh2.json` — на ИБ без конфигурации идентификатор
    # `Configuration.xml` расходится между выгрузкой ДО шага и выгрузкой ПОСЛЕ него, хотя файлов и
    # байтов ровно столько же. Без этой третьей выгрузки непонятно, кто его двигает: шаг или сама
    # выгрузка (между второй и третьей выгрузкой шага нет ничего).
    after2_dir = dump_root / f"{index:02d}_{variant}_after2"
    after2_result = ib_loop.run_step("dump", {"bin": bin_path, "ib": ib, "cfg": cfg,
                                              "dump": str(after2_dir),
                                              "out": str(work / f"effect_{index:02d}_{variant}_after2.txt"),
                                              "timeout": timeout})
    fingerprint_before = fingerprint(before_dir)
    fingerprint_after = fingerprint(dump_dir)
    fingerprint_after2 = fingerprint(after2_dir)
    pair = fingerprint_diff(fingerprint_after, fingerprint_after2)
    dump_twice = {"files": [fingerprint_after["files"], fingerprint_after2["files"]],
                  "bytes": [fingerprint_after["bytes"], fingerprint_after2["bytes"]],
                  "config_uuid": [fingerprint_after["config_uuid"],
                                  fingerprint_after2["config_uuid"]],
                  "same_files": pair.get("files") is None,
                  "same_bytes": pair.get("bytes") is None,
                  "same_uuid": pair.get("config_uuid") is None}
    out_rows, unique_rows = out_line_stats(result["lines"])
    return {"index": index, "variant": variant, "code": result["code"],
            "timed_out": result["timed_out"], "seconds": result["seconds"],
            "out_bytes": result["bytes"], "outcome": exec_probe.outcome_key(result),
            # `lines` — только первые 8 строк, чтобы отчёт не разрастался; полный счётчик и полный
            # набор неповторяющихся строк стоят рядом, иначе многострочный отказ читается по обрезке
            # (шаг `load-allextensions-flag`: в `lines` 8 строк, на самом деле 24 в 12 каталогах).
            "lines": out_rows[:8], "out_lines_total": len(out_rows),
            "out_lines_unique": unique_rows,
            "console_lines": result["console_lines"][:8],
            "argv_tail": result["argv"][4:], "identifiers": identifiers_in(out_rows),
            "before_dump_dir": before_dir.as_posix(), "before_dump_code": before_dump["code"],
            "before_dump_seconds": before_dump["seconds"],
            "before_fingerprint": fingerprint_before,
            "changed_by_step": fingerprint_diff(fingerprint_before, fingerprint_after),
            "dump_dir": dump_dir.as_posix(),
            "dump_code": dump_result["code"], "dump_seconds": dump_result["seconds"],
            "dump_lines": dump_result["lines"][:4], "fingerprint": fingerprint_after,
            "after2_dump_dir": after2_dir.as_posix(), "after2_dump_code": after2_result["code"],
            "after2_dump_seconds": after2_result["seconds"], "fingerprint_after2": fingerprint_after2,
            "dump_twice": dump_twice}


def measure(ladder_name: str, ladder: tuple, bin_path: str, ib: str, cfg: str,
            work: pathlib.Path, dump_root: pathlib.Path, timeout: int,
            fresh: bool = False) -> dict:
    """Замер по лестнице: шаг -> выгрузка -> сравнение с прежней выгрузкой, затем восстановление.

    `fresh` — перед каждым шагом ИБ создаётся заново (см. `reset_ib`): тогда шаг сравнивается с
    таким же шагом на том же старте, а не на состоянии, которое оставил прежний шаг.
    """
    loadlist = ""
    if any(exec_probe.needs_loadlist(variant) for variant, _, _ in ladder):
        list_path, list_names = exec_probe.write_loadlist(pathlib.Path(cfg), work)
        loadlist = str(list_path)
        print(f"файл списка загрузки: {list_path.as_posix()} ({len(list_names)} имён)")
    steps, previous = [], None
    for index, (variant, kind, encoding) in enumerate(ladder):
        create = reset_ib(ib, bin_path, work, index, timeout) if fresh else {}
        step = run_and_dump(variant, kind, encoding, bin_path, ib, cfg, work, dump_root, index,
                            timeout, loadlist)
        step["create"] = create
        step["changed_vs_previous"] = fingerprint_diff(previous, step["fingerprint"])
        previous = step["fingerprint"]
        steps.append(step)
    base = steps[0]["fingerprint"]
    # Восстановление: полный `/LoadConfigFromFiles` (тот же шаг, что у гейта) и его выгрузка.
    # Смысл: замер обязан оставить ИБ в том же состоянии, в котором начал, иначе следующие замеры
    # читаются на повреждённой базе. В режиме `fresh` это тот же шаг на свежей ИБ, и его сравнение
    # с базовым шагом отвечает на вопрос «воспроизводится ли выгрузка вообще».
    restore_index = len(steps)
    restore_create = reset_ib(ib, bin_path, work, restore_index, timeout) if fresh else {}
    restore = run_and_dump("load-ok", "marker", "cp1251", bin_path, ib, cfg, work, dump_root,
                           restore_index, timeout, loadlist)
    restore["create"] = restore_create
    restore["changed_vs_base"] = fingerprint_diff(base, restore["fingerprint"])
    restore["diff_vs_source"] = gate.file_diff(cfg, restore["dump_dir"])
    report = {"ladder_name": ladder_name,
              "ladder_variants": [variant for variant, _, _ in ladder],
              "source_uuid": source_config_uuid(cfg), "ib_fresh_each_step": fresh,
              "steps": steps, "restore": restore,
              "restore_matches_base": not restore["changed_vs_base"],
              "restore_same_to_source": len(restore["diff_vs_source"]["same"]),
              "restore_differ_to_source": len(restore["diff_vs_source"]["differ"]),
              "dump_codes": [code for step in steps + [restore]
                             for code in (step["before_dump_code"], step["dump_code"],
                                          step["after2_dump_code"])],
              "create_codes": [step["create"]["code"] for step in steps + [restore]
                               if step["create"]]}
    # Ожидания пишутся в `EXPECTATIONS` до прогона; здесь сравнивается только записанное с фактом.
    report["expectations"] = check_expectations(report)
    return report


def main(argv: list | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--local", default=str(ROOT / "local.paths.json"))
    parser.add_argument("--bin", default="")
    parser.add_argument("--ib", default="", help="временная ИБ для mutating-прогонов")
    parser.add_argument("--cfg", default="")
    parser.add_argument("--work", default="")
    parser.add_argument("--dump-root", default="", help="каталог выгрузок этого замера")
    parser.add_argument("--ladder", default="predefined", choices=sorted(LADDERS))
    parser.add_argument("--allow-mutating", action="store_true")
    parser.add_argument("--fresh-ib", action="store_true",
                        help="перед каждым шагом удалять каталог ИБ и создавать его заново: шаг "
                             "сравнивается с тем же шагом на одном старте, а не на состоянии "
                             "прежнего шага")
    parser.add_argument("--timeout", type=int, default=90)
    parser.add_argument("--json", default="")
    args = parser.parse_args(argv)

    local = paths.load_local(args.local)
    bin_path = args.bin or local.get("bin", "")
    ib = args.ib or ""
    cfg = args.cfg or local.get("cfg", "")
    work = pathlib.Path(args.work or local.get("work", str(ROOT / "work")))
    ladder_name, ladder = LADDERS[args.ladder]
    if not bin_path or not ib or not cfg:
        print("probe: нужны --bin, --ib (временная ИБ) и --cfg (или local.paths.json)",
              file=sys.stderr)
        return 2
    if gate_ib := local.get("ib", ""):
        if pathlib.Path(gate_ib).resolve() == pathlib.Path(ib).resolve():
            print("probe: лестница меняет состояние ИБ: ИБ гейта (ключ `ib` из local.paths.json) "
                  "полигоном не делается. Нужна отдельная временная ИБ.", file=sys.stderr)
            return 2
    if mutating := [variant for variant, _, _ in ladder
                    if variant in exec_probe.MUTATING_VARIANTS]:
        if not args.allow_mutating:
            print(f"probe: лестница {ladder_name} содержит варианты, способные изменить состояние "
                  f"ИБ ({', '.join(mutating)}). Нужен --allow-mutating.", file=sys.stderr)
            return 2
    if args.fresh_ib:
        # Уничтожение каталога ИБ — самая разрушительная операция замера: она разрешена только для
        # временной ИБ из того же каталога, где лежит ИБ гейта, и никогда — для самой ИБ гейта.
        gate_ib = local.get("ib", "")
        if not gate_ib or (pathlib.Path(gate_ib).resolve().parent
                           != pathlib.Path(ib).resolve().parent):
            print("probe: --fresh-ib удаляет каталог ИБ: разрешено только для временной ИБ того же "
                  "каталога, где лежит ИБ гейта", file=sys.stderr)
            return 2
    elif not ib_loop.ib_exists(ib):
        print("probe: временная ИБ не создана: шаг create (`scripts/ib_loop.py`) не сделан",
              file=sys.stderr)
        return 2

    dump_root = pathlib.Path(args.dump_root or work / "modifier_effect")
    print(f"замер {ladder_name} на ИБ: {ib} | выгрузки: {dump_root} | свежая ИБ на шаг:",
          bool(args.fresh_ib))
    report = measure(ladder_name, ladder, bin_path, ib, str(pathlib.Path(cfg).resolve()), work,
                     dump_root, args.timeout, fresh=args.fresh_ib)
    report.update({"ib": ib, "cfg": cfg, "timeout": args.timeout,
                   "ib_fresh_each_step": bool(args.fresh_ib),
                   "ladder_mutating_variants": [variant for variant, _, _ in ladder
                                                if variant in exec_probe.MUTATING_VARIANTS]})
    for step in report["steps"]:
        print("==", step["index"], step["variant"], "| код", step["code"], "|", step["seconds"],
              "с | байт", step["out_bytes"], step["outcome"], "| выгрузка код", step["dump_code"],
              "| файлов", step["fingerprint"]["files"], "| байт", step["fingerprint"]["bytes"],
              "| предопределённых файлов", len(step["fingerprint"]["predefined_data"]))
        if step["create"]:
            print("   новая ИБ: код", step["create"]["code"], "|", step["create"]["seconds"], "с")
        print("   uuid ИБ: до шага", _uuid_of(step, "before_fingerprint") or "-",
              "| после шага", _uuid_of(step, "fingerprint") or "-",
              "| uuid исходника", report["source_uuid"] or "-")
        if step["identifiers"]:
            print("   идентификаторы в выводе шага:", ", ".join(step["identifiers"]))
        twice = step["dump_twice"]
        print("   две выгрузки одного состояния (шага между ними нет): файлы", twice["files"],
              "байты", twice["bytes"], "uuid", twice["config_uuid"],
              "| равны:", twice["same_files"], twice["same_bytes"], twice["same_uuid"])
        for key, value in step["changed_by_step"].items():
            print("   шаг изменил:", key, json.dumps(value, ensure_ascii=False)[:400])
        for key, value in step["changed_vs_previous"].items():
            print("   изменилось:", key, json.dumps(value, ensure_ascii=False)[:400])
        for line in step["lines"][:4]:
            print("   вывод:", line)
        if step["out_lines_total"] > len(step["lines"]):
            print("   строк в выводе всего:", step["out_lines_total"],
                  "| неповторяющихся:", len(step["out_lines_unique"]))
    restore = report["restore"]
    print("== восстановление (load-ok) | код", restore["code"], "| выгрузка код",
          restore["dump_code"], "| файлов", restore["fingerprint"]["files"],
          "| совпадает с базой:", report["restore_matches_base"],
          "| к исходнику same/differ:", report["restore_same_to_source"],
          report["restore_differ_to_source"])
    for key, value in restore["changed_vs_base"].items():
        print("   после восстановления изменилось:", key,
              json.dumps(value, ensure_ascii=False)[:400])
    print(f"uuid конфигурации в исходнике: {report['source_uuid'] or 'не читается'}")
    for name, check in sorted(report["expectations"].items()):
        print("ожидание", name, "->", "сбылось" if check["met"] else
              ("не проверяемо" if check["met"] is None else "НЕ сбылось"),
              "|", json.dumps(check["evidence"], ensure_ascii=False)[:500])
    if args.json:
        pathlib.Path(args.json).write_text(json.dumps(report, ensure_ascii=False, indent=1),
                                           encoding="utf-8")
        print("замер записан:", args.json)
    return 0 if all(code == 0 for code in report["dump_codes"] + report["create_codes"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
