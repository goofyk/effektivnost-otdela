"""Гейт одной итерации сборки: метаданные, цикл платформы, сверка источника и выгрузки.

Гейт отвечает на один вопрос: приняла ли платформа то, что написано, и в том ли составе.
Три проверки идут по порядку, от дешёвой к дорогой:

1. `check_metadata` — независимый счётчик по раскладке файлов и декларация `ChildObjects`
   (`scripts/layout.py`) против ожидаемых чисел, заданных спецификацией до сборки.
2. Цикл платформы: `/LoadConfigFromFiles` → `/CheckModules` (пять ключей режима) →
   `/DumpConfigToFiles`.
3. Сверка источника с тем, что вернула платформа: те же независимые числа по выгрузке,
   пофайловое сравнение, признак пустой конфигурации.

Почему числа считаются сами, а не берутся из модели `p1c.load`: наблюдение репозитория
инструментов показывает, что читатель не читает папки `Roles`, `Subsystems`, `Languages`,
`SessionParameters`, `CommonPictures`, `SettingsStorages` и содержимое `Templates`
(`COLLECTIONS_MAP`, `p1c/src/p1c/load/reader.py:64-125`). Гейт на числах только этой модели
не заметил бы, что платформа выбросила все роли и подсистемы. Числа инструмента при этом
пишутся в отчёт отдельной строкой (`tool_counts_*`) и служат замером покрытия инструментов,
но не доказательством сборки.

Гейт никогда не называет итерацию успешной, если выгрузка вернула пустую конфигурацию:
наблюдение показало, что при XDTO-отказе загрузка отменяется целиком, `/CheckModules` после
этого даёт код 0 на пустой базе, а `/DumpConfigToFiles` не затирает прежний дамп (наблюдение
B2: из 239 файлов свежими оказались 3, `Configuration.xml` с `Name=Конфигурация`).

Коды выхода: 0 — расхождений и диагностических находок нет; 1 — находки платформы, расхождение
чисел или нарушенная парность файлов; 2 — проверить нельзя (нет каталога конфигурации, нет файла
ожидаемых чисел, нет файла платформы или базы).

Два правила цикла, выведенные из наблюдения gate-03 (загрузка не завершилась за 600 с, вывод 0
байт): каждый шаг пишет в свой файл вывода (`loop_out_path`), потому что при общем файле пустой
вывод загрузки перезаписывается следующим шагом; и цикл прерывается на шаге, убитом по ожиданию
(`cycle_continues`), потому что показания следующих шагов на недописанной базе читаются как
доказательство, которого нет. Строки успешного вывода платформы («… успешно завершено»,
«Синтаксических ошибок не обнаружено!») находками не считаются (`diagnostic_findings`): иначе
зелёной итерации не бывает никогда.
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import counts                                                    # noqa: E402
import ib_loop                                                   # noqa: E402
import layout                                                    # noqa: E402
import paths                                                     # noqa: E402
import rights                                                    # noqa: E402

EMPTY_CONFIGURATION_NAME = "Конфигурация"
DEFAULT_EXPECTED = ROOT / "docs" / "expected-metadata.json"

# Файлы, которые платформа добавляет в выгрузку сама. Замер: `ConfigDumpInfo.xml` есть в каждом из
# шести канонических корпусов (`corpora_*`) и появляется в нашей выгрузке (`gate-04`:
# `only_dump: ["ConfigDumpInfo.xml"]`). В исходнике его быть не может, поэтому он не должен
# считаться ни лишним файлом, ни лишней метаданной.
PLATFORM_ADDED_FILES = ("ConfigDumpInfo.xml",)


def check_metadata(cfg_dir, expected_path) -> tuple:
    """Сверка метаданных с ожиданием, заданным спецификацией до сборки.

    (код, отчёт): 0 — чисел расхождений и нарушений парности файлов нет; 1 — есть расхождение
    с ожиданием или нарушенная парность файлов; 2 — каталога конфигурации или файла ожидания
    нет, сверка невозможна.
    """
    cfg = pathlib.Path(cfg_dir)
    report = {"cfg_name": cfg.name, "layout": {}, "declared": {}, "expected_mismatch": {},
              "layout_mismatch": {}, "problems": [], "reason": ""}
    if not cfg.is_dir():
        report["reason"] = "каталога конфигурации нет: метаданные не прочитать"
        return 2, report
    expected_file = pathlib.Path(expected_path)
    if not expected_file.is_file():
        report["reason"] = ('файла ожидаемых чисел нет: нужен --expected с JSON вида {"expected": '
                            '{"вид": число}}; числа задаёт спецификация, а не инструмент')
        return 2, report

    expected = json.loads(expected_file.read_text(encoding="utf-8")).get("expected", {})
    counts = layout.layout_counts(cfg)
    report["layout"] = counts
    report["declared"] = layout.declared_children(cfg)
    report["expected_mismatch"] = layout.compare_expected(counts, expected)
    report["layout_mismatch"] = {kind: (declared, counts.get(kind, 0))
                                 for kind, declared in report["declared"].items()
                                 if counts.get(kind, 0) != declared}
    report["problems"] = layout.shape_problems(cfg, counts)
    # Жёсткие проблемы — те, что роняют загрузку платформы гарантированно: нарушенная парность
    # файлов и декларация `ChildObjects` без файла объекта. Расхождение с эталоном чисел —
    # мягкая проблема: на промежуточной итерации сборки объект ещё не дописан, и цикл платформы
    # обязан выполниться, чтобы итерация получила коды платформы.
    report["hard_problems"] = list(report["problems"]) + [
        "ChildObjects объявляет " + kind + ": " + str(declared) + ", файлов объекта: "
        + str(counts.get(kind, 0)) for kind, declared in report["layout_mismatch"].items()]
    if report["hard_problems"]:
        report["reason"] = "парность файлов метаданных нарушена: " + "; ".join(report["hard_problems"])
        return 1, report
    if report["expected_mismatch"]:
        report["reason"] = ("ожидаемые числа метаданных ещё не собраны: "
                            + json.dumps(report["expected_mismatch"], ensure_ascii=False))
    return 0, report


def empty_dump_detected(source: dict, dumped: dict, dump_name: str = "",
                        source_name: str = "") -> bool:
    """Источник с объектами, а выгрузка — пустая конфигурация платформы или не её дамп.

    Наблюдение B2: `/DumpConfigToFiles` после отменённой загрузки пишет 3 свежих файла пустой
    конфигурации (`ConfigDumpInfo.xml`, `Configuration.xml` с `Name=Конфигурация`,
    `Languages/Русский.xml`) и не трогает 236 прежних файлов дампа: каталог с 239 файлами
    выглядит полным.

    Наблюдение D: сравнивать имя с константой «Конфигурация» нельзя — реальная конфигурация
    корпуса «ИИ Чат 1С/Project» сама называется «Конфигурация», и проверка по константе
    превращает зелёную сборку в провал. Сравнивать надо имя выгрузки с именем исходника.
    """
    if not sum(source.values()):
        return False
    if not sum(dumped.values()):
        return True
    return bool(dump_name) and bool(source_name) and dump_name != source_name


def file_diff(cfg_dir, dump_dir, added: tuple = PLATFORM_ADDED_FILES) -> dict:
    """Пофайловое сравнение источника и выгрузки после нормализации BOM и переводов строк.

    Делается здесь, а не `p1c-diff`: наблюдение репозитория показывает, что `p1c-diff`
    сравнивает модели метаданных, а не файлы, и папок `Roles`/`Subsystems`/`Languages`/
    `Templates` в этих моделях нет.

    Два наблюдения real-прогона gate-04 (`probe/dump_vs_source.py`), которые определяют контракт:

    - 8 из 19 «отличающихся» файлов отличались только завершающим переводом строки (мы его пишем,
      платформа нет); поэтому завершающие переводы строки в конце файла нормализуются;
    - `ConfigDumpInfo.xml` в выгрузке есть, а в исходнике его быть не может: это файл платформы
      (он есть во всех канонических выгрузках корпусов), и он называется отдельно — иначе
      «выгрузка длиннее исходника» стало бы вечным отказом.
    """
    def listing(root: pathlib.Path) -> dict:
        return {p.relative_to(root).as_posix(): p for p in root.rglob("*") if p.is_file()}

    def normalized(path: pathlib.Path) -> bytes:
        data = path.read_bytes()
        if data[:3] == b"\xef\xbb\xbf":
            data = data[3:]
        return data.replace(b"\r\n", b"\n").rstrip(b"\r\n")

    a, b = listing(pathlib.Path(cfg_dir)), listing(pathlib.Path(dump_dir))
    same, differ, only_source, only_dump, platform_added = [], [], [], [], []
    for rel in sorted(set(a) | set(b)):
        if rel in a and rel in b:
            (same if normalized(a[rel]) == normalized(b[rel]) else differ).append(rel)
        elif rel in a:
            only_source.append(rel)
        elif rel in added:
            platform_added.append(rel)
        else:
            only_dump.append(rel)
    return {"same": same, "differ": differ, "only_source": only_source, "only_dump": only_dump,
            "platform_added": platform_added}


def loop_steps(ib_ready: bool) -> tuple:
    """Порядок шагов цикла платформы.

    Базу создаёт контур, если её нет: без базы загрузка сообщает «Информационная база не
    обнаружена!» с кодом 1 — неотличимо от битой конфигурации. Повторно создавать существующую
    базу нельзя: CREATEINFOBASE на готовой базе даёт ненулевой код.
    """
    return ("load", "check", "dump") if ib_ready else ("create", "load", "check", "dump")


def loop_out_path(base_out: str, step: str) -> str:
    """Файл вывода каждого шага — отдельный.

    Наблюдение gate-03: на общий файл вывода шагов загрузка (0 байт) была перезаписана
    следующим шагом, и в отчёте остались только строки /CheckModules: «Синтаксических ошибок не
    обнаружено!» при том, что конфигурация не была загружена.
    """
    path = pathlib.Path(base_out)
    return str(path.parent / (path.stem + "-" + step + path.suffix))


def record_diagnostics(report: dict, step: str, lines: list) -> None:
    """Диагностику хранят по шагам: плоский список неудобен, когда шаг молчит или его вывод пуст."""
    report.setdefault("diagnostics_by_step", {})[step] = list(lines)
    report["diagnostics"] = report.setdefault("diagnostics", []) + list(lines)
    report["diagnostic_findings"] = report.setdefault("diagnostic_findings", []) \
        + diagnostic_findings(lines)


# Строки успешного вывода платформы (наблюдены в actual-выводах create и check). Они не находки.
# Важно: «Синтаксических ошибок не обнаружено!» печатается и на базе, куда конфигурация не
# загрузилась, поэтому доказательством оно не является — доказательством служит сверка состава
# выгрузки с исходником.
OBSERVED_OK_LINES = ("успешно завершено", "Синтаксических ошибок не обнаружено")


def diagnostic_findings(lines: list) -> list:
    """Находки диагностики: непустые строки вывода, которые нельзя прочитать как успех."""
    findings = []
    for line in lines:
        text = line.strip()
        if not text or any(marker in text for marker in OBSERVED_OK_LINES):
            continue
        findings.append(text)
    return findings


def step_problem(step: str, result: dict) -> str:
    """Отказ шага, названный по шагу. Таймаут — отдельный случай: ненулевой код у него от убийства
    процесса, а не от платформы, и вывод при таймауте пустой."""
    if result.get("timed_out"):
        return ("шаг '" + step + "' не завершился в пределах ожидания "
                + str(result.get("seconds", 0)) + " с: платформа убита контуром, вывод "
                + str(result.get("bytes", 0)) + " байт")
    if result.get("code") != 0:
        return "шаг '" + step + "' вернул код " + str(result.get("code"))
    return ""


def cycle_continues(step: str, result: dict) -> bool:
    """Продолжать ли цикл платформы после отказа шага.

    Таймаут загрузки — прекращаем: контур убил платформу посреди записи в файловую базу, и
    показания следующих шагов читаются как доказательство, которого нет. В gate-03 именно так и
    вышло: убитая загрузка (600 с, 0 байт), а /CheckModules на той же базе вернул код 0 и
    «Синтаксических ошибок не обнаружено!».

    Ненулевой код загрузки без таймаута — продолжаем: платформа договорала до конца и выгрузка
    нужна, чтобы видеть, что именно осталось в базе (в gate-02 она показала пустую конфигурацию).
    """
    if result.get("timed_out"):
        return False
    if step == "create" and result.get("code") != 0:
        return False
    return True


def run(cfg_dir: str, out_json: str, opts: dict | None = None) -> tuple:
    """Одна итерация гейта. Возвращает (код, отчёт)."""
    opts = dict(opts or {})
    local = paths.load_local(opts.get("local") or str(ROOT / "local.paths.json"))
    cfg = pathlib.Path(opts.get("cfg") or cfg_dir)
    p1c_src = opts.get("p1c") or local.get("p1c", "")
    expected_path = opts.get("expected") or str(DEFAULT_EXPECTED)
    report = {"cfg_name": cfg.name, "expected_file": pathlib.Path(expected_path).name,
              "load_code": None, "check_code": None, "create_code": None, "dump_files": 0,
              "ib_ready_before": None,
              "metadata": {}, "layout_source": {}, "layout_dump": {}, "layout_compare": {},
              "tool_counts_source": {}, "tool_counts_dump": {}, "tool_counts_error": "",
              "diff_files": {}, "diagnostics": [], "diagnostics_by_step": {},
              "diagnostic_findings": [], "step_problems": [], "steps": [], "rights": {},
              "reason": ""}

    def finish(code: int) -> tuple:
        _write(out_json, report)
        return code, report

    # 1. Метаданные источника: дёшево и независимо от платформы. Жёсткие проблемы (парность
    #    файлов, декларация без файла) ловятся до запуска платформы — цикл стоит 10 с и не
    #    объяснит пропущенный файл. Расхождение с эталоном чисел оставляется на итог: на
    #    промежуточной итерации сборки объект ещё не дописан, и коды платформы нужны.
    metadata_code, metadata = check_metadata(cfg, expected_path)
    report["metadata"] = {k: v for k, v in metadata.items() if k != "cfg_name"}
    report["layout_source"] = metadata.get("layout", {})
    if metadata_code == 2:
        report["reason"] = metadata["reason"]
        return finish(2)
    if metadata_code == 1:
        report["reason"] = metadata["reason"]
        return finish(1)

    # 1b. Права ролей: самый дешёвый статический шаг после метаданных и самый дорогой по цене
    #     пропуск — платформа об отказе этого класса молчит (загрузка зависает без кода и вывода),
    #     а p1c права не читает вовсе. Наблюдение gate-03 и `docs/evidence/load-bisect.md`.
    rights_result = rights.check(cfg, rights.load_canon(opts.get("canon")))
    report["rights"] = {"code": rights_result["code"], "counts": rights_result["counts"],
                        "problems": rights_result["problems"], "objects": rights_result["objects"]}
    if rights_result["code"] == 1:
        report["reason"] = ("содержимое прав роли неканонично: "
                            + "; ".join(rights_result["problems"])
                            + " — платформу об этом не спросить: права она принимает молча и "
                              "затем не завершает загрузку")
        return finish(1)
    if rights_result["code"] == 2:
        report["reason"] = "права ролей не проверены: " + "; ".join(rights_result["problems"])
        return finish(2)

    loop_opts = {"bin": opts.get("bin") or local.get("bin", ""),
                 "ib": opts.get("ib") or local.get("ib", ""),
                 "cfg": str(cfg),
                 "dump": opts.get("dump") or local.get("dump", ""),
                 "out": opts.get("loop_out") or str(ROOT / "reports" / "gate-loop-out.txt"),
                 "timeout": opts.get("timeout", 300)}
    refusal = paths.refuse_missing_bin(loop_opts["bin"]) or (
        "" if loop_opts["ib"] else "информационной базы не названо: нужен --ib")
    if refusal or not loop_opts["dump"]:
        report["reason"] = refusal or "каталога выгрузки не названо: нужен --dump"
        return finish(2)

    # 2. Цикл платформы. Каждый шаг пишет в свой файл вывода: наблюдение gate-03 показало, что при
    #    общем файле вывод загрузки (пустой) перезаписывался следующим шагом, и в отчёте оставались
    #    только строки /CheckModules.
    ib_ready = ib_loop.ib_exists(loop_opts["ib"])
    report["ib_ready_before"] = ib_ready
    for step in loop_steps(ib_ready):
        step_opts = dict(loop_opts, out=loop_out_path(loop_opts["out"], step))
        result = ib_loop.run_step(step, step_opts)
        report["steps"].append({k: v for k, v in result.items() if k != "lines"})
        record_diagnostics(report, step, result["lines"][:20])
        if step == "create":
            report["create_code"] = result["code"]
        elif step == "load":
            report["load_code"] = result["code"]
        elif step == "check":
            report["check_code"] = result["code"]
        problem = step_problem(step, result)
        if problem:
            report["step_problems"].append(problem)
            if not cycle_continues(step, result):
                report["reason"] = "цикл платформы прерван на шаге '" + step + "': " + problem
                return finish(1)

    # 3. Что вернула платформа. Свежесть файлов выгрузки — отдельное доказательство: наблюдение
    #    B2 показало, что каталог выгрузки может выглядеть полным файлами прежней выгрузки.
    dump_dir = pathlib.Path(loop_opts["dump"])
    dump_started = min((step.get("started", 0.0) for step in report["steps"]
                        if step["step"] == "dump"), default=0.0)
    report["dump_files"] = (sum(1 for p in dump_dir.rglob("*") if p.is_file())
                            if dump_dir.is_dir() else 0)
    report["dump_fresh_files"] = (sum(1 for p in dump_dir.rglob("*")
                                      if p.is_file() and p.stat().st_mtime >= dump_started - 2.0)
                                  if dump_dir.is_dir() else 0)
    report["source_configuration_name"] = counts.configuration_name(cfg)
    report["dump_configuration_name"] = counts.configuration_name(dump_dir)
    report["layout_dump"] = layout.layout_counts(dump_dir, ignore=PLATFORM_ADDED_FILES)
    report["layout_compare"] = layout.compare_expected(report["layout_source"], report["layout_dump"])
    report["diff_files"] = file_diff(cfg, dump_dir)

    # Числа инструмента — замер покрытия инструментов, не доказательство сборки: читатель не
    # видит часть папок, поэтому недоступный читатель не должен ломать гейт.
    try:
        report["tool_counts_source"] = counts.object_counts(cfg, p1c_src)
        report["tool_counts_dump"] = counts.object_counts(dump_dir, p1c_src)
    except RuntimeError as error:
        report["tool_counts_error"] = str(error)
    report["tool_blind_kinds"] = sorted(
        set(report["layout_source"]) - set(report["tool_counts_source"]))

    if empty_dump_detected(report["layout_source"], report["layout_dump"],
                           dump_name=report["dump_configuration_name"],
                           source_name=report["source_configuration_name"]):
        report["reason"] = (f"состав выгрузки не совпадает с исходником: имя корневого объекта "
                            f"выгрузки {report['dump_configuration_name']!r} против "
                            f"{report['source_configuration_name']!r} в исходнике "
                            f"(свежих файлов выгрузки {report['dump_fresh_files']} из "
                            f"{report['dump_files']}): загрузка не выполнена, несмотря на коды "
                            f"платформы {report['load_code']}/{report['check_code']}")
        if report["diagnostic_findings"]:
            report["reason"] += " | диагностика: " + " || ".join(
                report["diagnostic_findings"][:6])
        return finish(1)

    failed = [step for step in report["steps"] if step["code"] != 0]
    if failed:
        report["reason"] = ("шаг платформы вернул ненулевой код: "
                            + json.dumps([{"step": s["step"], "code": s["code"]} for s in failed],
                                         ensure_ascii=False)
                            + (" | диагностика: " + " || ".join(report["diagnostic_findings"][:6])
                               if report["diagnostic_findings"] else ""))
        return finish(1)
    if report["layout_compare"]:
        report["reason"] = ("числа метаданных источника и выгрузки расходятся: "
                            + json.dumps(report["layout_compare"], ensure_ascii=False))
        return finish(1)
    if report["diff_files"]["only_source"] or report["diff_files"]["only_dump"]:
        report["reason"] = ("файловый состав выгрузки не совпадает с источником: "
                            + json.dumps({"only_source": report["diff_files"]["only_source"],
                                          "only_dump": report["diff_files"]["only_dump"]},
                                         ensure_ascii=False))
        return finish(1)
    if report["diagnostic_findings"]:
        report["reason"] = ("платформа сообщила о проблеме, не вернув ненулевого кода: "
                            + " || ".join(report["diagnostic_findings"][:6]))
        return finish(1)
    # Итог по эталону: числа задаёт спецификация до сборки, поэтому расхождение с ними —
    # провал итерации (недособрано или лишние объекты), даже если платформа молчит.
    expected_mismatch = report["metadata"].get("expected_mismatch", {})
    if expected_mismatch:
        report["reason"] = ("числа метаданных не совпадают с эталоном итерации "
                            + json.dumps(expected_mismatch, ensure_ascii=False)
                            + " (получили, ожидали)")
        return finish(1)
    return finish(0)


def _write(out_json: str, report: dict) -> None:
    if not out_json:
        return
    path = pathlib.Path(out_json)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv: list) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Гейт итерации сборки конфигурации")
    parser.add_argument("--cfg", default="", help="каталог файловой конфигурации")
    parser.add_argument("--out", default="", help="файл JSON-отчёта гейта")
    parser.add_argument("--expected", default=str(DEFAULT_EXPECTED),
                        help="JSON ожидаемых чисел метаданных (задаёт спецификация)")
    parser.add_argument("--bin", default="", help="файл платформы (аргумент или локальный файл путей)")
    parser.add_argument("--ib", default="", help="информационная база")
    parser.add_argument("--dump", default="", help="каталог выгрузки (пересоздаётся)")
    parser.add_argument("--p1c", default="", help="каталог src инструментов p1c")
    parser.add_argument("--local", default=str(ROOT / "local.paths.json"))
    parser.add_argument("--canon", default="",
                        help="JSON измеренного канона прав (docs/canonical-rights.json)")
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--no-platform", action="store_true",
                        help="только сверка метаданных с ожиданием (без цикла платформы)")
    args = parser.parse_args(argv)

    cfg = args.cfg or paths.load_local(args.local).get("cfg", "")
    opts = {"bin": args.bin, "ib": args.ib, "dump": args.dump, "p1c": args.p1c,
            "local": args.local, "timeout": args.timeout, "expected": args.expected,
            "canon": args.canon}
    if args.no_platform:
        code, metadata = check_metadata(cfg, args.expected)
        rights_result = rights.check(cfg, rights.load_canon(args.canon))
        print("гейт метаданных: код " + str(code) + " | " + json.dumps(
            {"layout": metadata.get("layout"), "declared": metadata.get("declared"),
             "hard_problems": metadata.get("hard_problems"),
             "expected_mismatch": metadata.get("expected_mismatch"),
             "rights_code": rights_result["code"], "rights_counts": rights_result["counts"]},
            ensure_ascii=False))
        for problem in rights_result["problems"]:
            print("права:", problem)
        if metadata.get("reason"):
            print("причина: " + metadata["reason"])
        return code if code != 0 else rights_result["code"]

    code, report = run(cfg, args.out, opts)
    print("гейт: код " + str(code) + " | " + json.dumps(
        {"load_code": report.get("load_code"), "check_code": report.get("check_code"),
         "dump_files": report.get("dump_files"), "dump_fresh_files": report.get("dump_fresh_files"),
         "layout_source": report.get("layout_source"),
         "layout_dump": report.get("layout_dump"),
         "expected_mismatch": (report.get("metadata") or {}).get("expected_mismatch"),
         "rights_code": (report.get("rights") or {}).get("code"),
         "rights_counts": (report.get("rights") or {}).get("counts"),
         "tool_counts_source": report.get("tool_counts_source"),
         "tool_blind_kinds": report.get("tool_blind_kinds")}, ensure_ascii=False))
    for problem in (report.get("rights") or {}).get("problems", [])[:8]:
        print("права:", problem)
    if report.get("reason"):
        print("причина: " + report["reason"])
    for problem in report.get("step_problems", []):
        print("отказ шага: " + problem)
    for line in report.get("diagnostic_findings", [])[:12]:
        print("диагностика: " + line)
    return code


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
