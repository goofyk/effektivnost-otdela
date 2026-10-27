"""Замыкаем пару команд выгрузки и загрузки внешней обработки через файлы (Task 15).

Имена команд взяты из замера имён платформы `p1c/src/p1c/data/test_cli_flags.json` (426 имён),
а их форма — из наблюдений `scripts/exec_probe.py` (замеры `reports/exec-13-test.json`,
`reports/exec-14-extproc-twoargs.json`, `reports/exec-14-dumpproc-args.json`). Платформа печатает
разобранные аргументы с подписями по позициям, поэтому порядок аргументов читаётся из замера, а не
из догадки.

Что подтверждено этим замером (форма наблюдения — лестница, каждый шаг меняет ровно одну часть
команды: имя команды, первый аргумент или второй аргумент):

1. `/DumpExternalDataProcessorOrReportToFiles <каталог или корневой файл выгрузки>
   <входной бинарный файл .epf>` — код 0, «Выгрузка завершена», выгрузка иерархическая: каталог с
   корневым `<Имя>.xml` и файлами `<Имя>/Forms/...`.
2. Первый аргумент выгрузки — не бинарный файл: вместо каталога подставляем `.epf` (шаг
   `dump-epf-epf`), отказ относится именно к первому аргументу.
3. Второй аргумент выгрузки — файл, не каталог: `dump-epf-dir` даёт «... является путем к
   директории, в то время как ожидается путь к файлу». Значит платформа не подставляет аргументы по
   типу, она читает позиции.
4. Тот же набор аргументов, но другая команда (`load-epf-dir`) — не отказ: платформа приняла
   бинарный `.epf` как «корневой файл выгрузки» и выдала другой бинарный `.epf` (310 мс против
   3100 мс у загрузки выгруженного XML). Значит проверка «является файлом обработки или отчёта»
   у первого аргумента смотрит на содержимое: так было с текстовым файлом программы
   (`reports/exec-13-test.json`, вариант `extproc-file` — «Файл 'file://...txt' не является файлом
   обработки или отчета»).
5. Загрузка выгруженного корневого XML: `load-root-dir` и `load-root-target` — код 0 и бинарный
   `.epf` на выходе (цикл `.epf` -> файлы -> `.epf` замкнут). Целевой аргумент может быть каталогом
   (платформа сама подбирает имя файла) или файлом (замер `reports/exec-14-extproc-twoargs.json`).

Пути (`bin`, `ib`, `work`, `epf`) берутся из `local.paths.json` или из аргументов запуска; путей
пользователя в файле репозитория нет. Прогоны 1С идут строго по одному; исходный `.epf`
только читается (копируется в рабочий каталог).
"""
from __future__ import annotations

import argparse
import json
import pathlib
import shutil
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import paths                                                         # noqa: E402

DUMP = "/DumpExternalDataProcessorOrReportToFiles"
LOAD = "/LoadExternalDataProcessorOrReportFromFiles"

# План наблюдения: (шаг, имя команды, (метка arg1, метка arg2)). Метки — позиции, их пути
# подставляет `resolve_labels`: `outdir` — каталог выгрузки, `epf` — входной бинарный файл
# обработки, `root` — корневой XML, найденный в выгрузке шага 1, `targetdir` — целевой каталог.
# Соседние шаги различаются ровно одной частью: именем команды или одной позицией аргументов.
STEP_PLAN = (
    # Шаг 1: подтверждённая форма выгрузки — каталог, затем бинарный файл.
    ("dump-dir-epf", DUMP, ("outdir", "epf")),
    # Шаг 2: меняем только arg1 — бинарный файл вместо каталога выгрузки.
    ("dump-epf-epf", DUMP, ("epf", "epf")),
    # Шаг 3: меняем только arg2 — каталог вместо бинарного файла.
    ("dump-epf-dir", DUMP, ("epf", "outdir")),
    # Шаг 4: меняем только имя команды, аргументы те же: у загрузки первый аргумент должен быть
    # файлом обработки или отчёта, а не каталогом.
    ("load-epf-dir", LOAD, ("epf", "outdir")),
    # Шаг 5: меняем только arg1 — корневой XML выгрузки вместо бинарного файла.
    ("load-root-dir", LOAD, ("root", "outdir")),
    # Шаг 6: меняем только arg2 — отдельный целевой каталог (ожидается бинарный .epf на выходе).
    ("load-root-target", LOAD, ("root", "targetdir")),
)

PART_NAMES = ("command", "arg1", "arg2")


def plan_diffs(steps: tuple = STEP_PLAN) -> list:
    """Чем соседние шаги различаются: имя команды или одна позиция аргументов (ровно одно)."""
    diffs = []
    for index in range(1, len(steps)):
        left, right = steps[index - 1], steps[index]
        changed = []
        if left[1] != right[1]:
            changed.append("command")
        for position in (0, 1):
            if left[2][position] != right[2][position]:
                changed.append(PART_NAMES[position + 1])
        diffs.append({"from": left[0], "to": right[0], "changed": changed,
                      "single_command_part": len(changed) == 1})
    return diffs


def decode_out(raw: bytes) -> list:
    """Строки `/Out`-файла платформы: UTF-8 с BOM, иначе cp1251."""
    for encoding in ("utf-8-sig", "cp1251"):
        try:
            text = raw.decode(encoding)
        except UnicodeDecodeError:
            continue
        return text.splitlines()
    return ["(не удалось декодировать /Out)"]


def tree_files(directory: pathlib.Path) -> list:
    if not directory.is_dir():
        return []
    return [{"path": path.relative_to(directory).as_posix(), "bytes": path.stat().st_size}
            for path in sorted(directory.rglob("*")) if path.is_file()]


def root_candidates(directory: pathlib.Path) -> list:
    """Файлы, которые могут быть корневым файлом иерархической выгрузки: XML в корне каталога."""
    if not directory.is_dir():
        return []
    return [item["path"] for item in tree_files(directory)
            if item["path"].lower().endswith(".xml") and "/" not in item["path"]]


def run_step(name: str, command: str, args: list, bin_path: pathlib.Path, ib: str,
             work: pathlib.Path, timeout: int) -> dict:
    """Один прогон платформы: команда с двумя аргументами, вывод в файл `/Out`."""
    out_file = work / f"epf_{name}_out.txt"
    if out_file.exists():
        out_file.unlink()
    argv = [str(bin_path), "DESIGNER", "/F", ib, "/Out", str(out_file),
            "/DisableStartupDialogs", command] + [str(item) for item in args]
    started = time.time()
    timed_out = False
    code = None
    try:
        process = subprocess.Popen(argv)
        try:
            code = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            process.kill()
            process.wait(timeout=10)
    except OSError as error:
        return {"step": name, "argv": argv, "error": str(error)}
    raw = out_file.read_bytes() if out_file.is_file() else b""
    return {"step": name, "argv": argv, "code": code, "timed_out": timed_out,
            "seconds": round(time.time() - started, 1), "out_bytes": len(raw),
            "out_lines": [line for line in decode_out(raw) if line.strip()]}


def report_step(result: dict, produced: list) -> None:
    print("==", result["step"], "| код", result.get("code"), "|", result.get("seconds"), "с",
          "| байт /Out", result.get("out_bytes"), "| файлов", len(produced))
    for line in result.get("out_lines", []):
        print("   вывод:", line)
    for item in produced[:25]:
        print("   файл:", item["path"], item["bytes"])


def main(argv: list | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Выгрузка и загрузка внешней обработки через файлы (форма команд платформы)")
    parser.add_argument("--local", default=str(ROOT / "local.paths.json"))
    parser.add_argument("--bin", default="", help="файл платформы (или ключ `bin` локального файла путей)")
    parser.add_argument("--ib", default="", help="каталог информационной базы")
    parser.add_argument("--work", default="", help="рабочий каталог (создаётся подкаталог `epf`)")
    parser.add_argument("--epf", default="", help="бинарный файл внешней обработки (.epf), только читается")
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--json", default="", help="файл JSON-отчёта замера")
    args = parser.parse_args(argv)

    local = paths.load_local(args.local)
    if not all((args.bin, args.ib, args.work)):
        missing = [key for key in ("bin", "ib", "work") if key not in local]
        if missing:
            print("нет путей в local.paths.json:", missing, file=sys.stderr)
            return 2
        args.bin = args.bin or local["bin"]
        args.ib = args.ib or local["ib"]
        args.work = args.work or local["work"]
    epf_source = pathlib.Path(args.epf or local.get("epf", ""))
    if not epf_source.is_file():
        print("нет файла внешней обработки: укажите --epf или ключ `epf` в local.paths.json",
              file=sys.stderr)
        return 2

    bin_path, ib = pathlib.Path(args.bin), args.ib
    work = pathlib.Path(args.work)
    stage = work / "epf"
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True)
    epf = stage / epf_source.name
    shutil.copyfile(epf_source, epf)
    outdir = stage / "dump_outdir"
    targetdir = stage / "load_targetdir"
    outdir.mkdir()
    targetdir.mkdir()

    diffs = plan_diffs()
    report = {"plan": [[name, command, list(labels)] for name, command, labels in STEP_PLAN],
              "plan_diffs": diffs,
              "plan_single_command_part": all(step["single_command_part"] for step in diffs),
              "epf_source_bytes": epf_source.stat().st_size, "steps": []}
    print("план:", [step[0] for step in STEP_PLAN],
          "| одна часть команды на шаг:", report["plan_single_command_part"])
    for step in diffs:
        print("   шаг", step["from"], "->", step["to"], "| изменилось:", step["changed"] or "ничего")

    resolved = {"epf": epf, "outdir": outdir, "targetdir": targetdir, "root": None}
    executed = []
    for name, command, labels in STEP_PLAN:
        step_args = list(labels)
        if "root" in labels:
            # Корневой XML берём из выгрузки шага 1; снимок дерева берём до шагов загрузки,
            # чтобы шаг с целевым каталогом выгрузки не подмешал в него свои файлы.
            if resolved["root"] is None:
                roots = root_candidates(outdir)
                report["dump_root_candidates"] = roots
                if not roots:
                    print("шаг", name, "и остальные шаги загрузки пропущены: выгрузка не дала "
                          "корневого XML в корне каталога")
                    break
                resolved["root"] = outdir / roots[0]
                resolved["dump_tree"] = tree_files(outdir)
                report["dump_tree"] = resolved["dump_tree"]
            step_args = ["root" if label == "root" else label for label in labels]
        result = run_step(name, command, [resolved[label] for label in step_args],
                          bin_path, ib, work, args.timeout)
        result["labels"] = list(labels)
        result["produced"] = (tree_files(outdir) if command == DUMP
                              else tree_files(targetdir) if labels[1] == "targetdir"
                              else [item for item in tree_files(outdir)
                                    if item["path"].lower().endswith(".epf")])
        report["steps"].append(result)
        executed.append((name, command, labels))
        report_step(result, result["produced"])

    dumped = any(step["step"] == "dump-dir-epf" and step.get("code") == 0 and step.get("produced")
                 for step in report["steps"])
    loaded = any(step["step"] == "load-root-target" and step.get("code") == 0
                 and any(item["path"].lower().endswith(".epf") for item in step.get("produced", []))
                 for step in report["steps"])
    report["dump_confirmed"] = dumped
    report["load_confirmed"] = loaded
    report["roundtrip_closed"] = dumped and loaded
    if args.json:
        out = pathlib.Path(args.json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("замер записан:", out.as_posix())
    print("выгрузка подтверждена:", dumped, "| загрузка подтверждена:", loaded,
          "| цикл замкнут:", report["roundtrip_closed"])
    return 0 if (report["roundtrip_closed"] and report["plan_single_command_part"]) else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
