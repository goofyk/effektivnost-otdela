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

Коды выхода: 0 — расхождений и диагностик нет; 1 — diagnostics платформы, расхождение чисел
или нарушенная парность файлов; 2 — проверить нельзя (нет каталога конфигурации, нет файла
ожидаемых чисел, нет файла платформы или базы).
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

EMPTY_CONFIGURATION_NAME = "Конфигурация"
DEFAULT_EXPECTED = ROOT / "docs" / "expected-metadata.json"


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


def file_diff(cfg_dir, dump_dir) -> dict:
    """Пофайловое сравнение источника и выгрузки после нормализации BOM и переводов строк.

    Делается здесь, а не `p1c-diff`: наблюдение репозитория показывает, что `p1c-diff`
    сравнивает модели метаданных, а не файлы, и папок `Roles`/`Subsystems`/`Languages`/
    `Templates` в этих моделях нет.
    """
    def listing(root: pathlib.Path) -> dict:
        return {p.relative_to(root).as_posix(): p for p in root.rglob("*") if p.is_file()}

    def normalized(path: pathlib.Path) -> bytes:
        data = path.read_bytes()
        if data[:3] == b"\xef\xbb\xbf":
            data = data[3:]
        return data.replace(b"\r\n", b"\n")

    a, b = listing(pathlib.Path(cfg_dir)), listing(pathlib.Path(dump_dir))
    same, differ, only_source, only_dump = [], [], [], []
    for rel in sorted(set(a) | set(b)):
        if rel in a and rel in b:
            (same if normalized(a[rel]) == normalized(b[rel]) else differ).append(rel)
        elif rel in a:
            only_source.append(rel)
        else:
            only_dump.append(rel)
    return {"same": len(same), "differ": differ, "only_source": only_source, "only_dump": only_dump}


def run(cfg_dir: str, out_json: str, opts: dict | None = None) -> tuple:
    """Одна итерация гейта. Возвращает (код, отчёт)."""
    opts = dict(opts or {})
    local = paths.load_local(opts.get("local") or str(ROOT / "local.paths.json"))
    cfg = pathlib.Path(opts.get("cfg") or cfg_dir)
    p1c_src = opts.get("p1c") or local.get("p1c", "")
    expected_path = opts.get("expected") or str(DEFAULT_EXPECTED)
    report = {"cfg_name": cfg.name, "expected_file": pathlib.Path(expected_path).name,
              "load_code": None, "check_code": None, "dump_files": 0,
              "metadata": {}, "layout_source": {}, "layout_dump": {}, "layout_compare": {},
              "tool_counts_source": {}, "tool_counts_dump": {}, "tool_counts_error": "",
              "diff_files": {}, "diagnostics": [], "steps": [], "reason": ""}

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

    # 2. Цикл платформы.
    for step in ("load", "check", "dump"):
        result = ib_loop.run_step(step, loop_opts)
        report["steps"].append({k: v for k, v in result.items() if k != "lines"})
        if step == "load":
            report["load_code"] = result["code"]
            if result["code"] != 0:
                report["reason"] = "загрузка не выполнена: код платформы " + str(result["code"])
                report["diagnostics"] = result["lines"][:20]
        elif step == "check":
            report["check_code"] = result["code"]
            report["diagnostics"] = report["diagnostics"] + result["lines"][:20]

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
    report["layout_dump"] = layout.layout_counts(dump_dir)
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
        return finish(1)

    failed = [step for step in report["steps"] if step["code"] != 0]
    if failed:
        report["reason"] = ("шаг платформы вернул ненулевой код: "
                            + json.dumps([{ "step": s["step"], "code": s["code"]} for s in failed],
                                         ensure_ascii=False))
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
    if report["diagnostics"]:
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
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--no-platform", action="store_true",
                        help="только сверка метаданных с ожиданием (без цикла платформы)")
    args = parser.parse_args(argv)

    cfg = args.cfg or paths.load_local(args.local).get("cfg", "")
    opts = {"bin": args.bin, "ib": args.ib, "dump": args.dump, "p1c": args.p1c,
            "local": args.local, "timeout": args.timeout, "expected": args.expected}
    if args.no_platform:
        code, metadata = check_metadata(cfg, args.expected)
        print("гейт метаданных: код " + str(code) + " | " + json.dumps(
            {"layout": metadata.get("layout"), "declared": metadata.get("declared"),
             "hard_problems": metadata.get("hard_problems"),
             "expected_mismatch": metadata.get("expected_mismatch")}, ensure_ascii=False))
        if metadata.get("reason"):
            print("причина: " + metadata["reason"])
        return code

    code, report = run(cfg, args.out, opts)
    print("гейт: код " + str(code) + " | " + json.dumps(
        {"load_code": report.get("load_code"), "check_code": report.get("check_code"),
         "dump_files": report.get("dump_files"), "dump_fresh_files": report.get("dump_fresh_files"),
         "layout_source": report.get("layout_source"),
         "layout_dump": report.get("layout_dump"),
         "expected_mismatch": (report.get("metadata") or {}).get("expected_mismatch"),
         "tool_counts_source": report.get("tool_counts_source"),
         "tool_blind_kinds": report.get("tool_blind_kinds")}, ensure_ascii=False))
    if report.get("reason"):
        print("причина: " + report["reason"])
    for line in report.get("diagnostics", [])[:12]:
        print("диагностика: " + line)
    return code


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
