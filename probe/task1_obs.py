"""Наблюдения Task 1: честность молчания платформы, поведение выгрузки, слепота читателя p1c.

C  — полный цикл на реальной конфигурации (копия вне git).
B1 — /LoadConfigFromFiles с каталогом, которого нет: что сообщает платформа.
B2 — /DumpConfigToFiles поверх каталога с уже хорошим дампом после неудачной загрузки:
     затирается ли предыдущая выгрузка пустой конфигурацией.
D  — гейт на реальной конфигурации: независимые числа метаданных против чисел читателя
     `p1c.load` (какие виды инструментов не увидели) и пофайловая круговая сверка.

Сырые выводы платформы — в reports/ (в git не попадают); compactные числа — в
docs/evidence/task1-observations.md (в git). Пути читаются из локального файла путей:
ни один файл репозитория путей не содержит.
"""
from __future__ import annotations

import json
import pathlib
import shutil
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import counts                                                    # noqa: E402
import gate                                                      # noqa: E402
import ib_loop                                                   # noqa: E402
import layout                                                    # noqa: E402
import paths                                                     # noqa: E402

LOCAL = paths.load_local(ROOT / "local.paths.json")
WORK = pathlib.Path(LOCAL["work"])
SPIKES = pathlib.Path(LOCAL["spikes"])
REPORTS = ROOT / "reports"
EVIDENCE = ROOT / "docs" / "evidence"


def write_json(name: str, data: dict) -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                                encoding="utf-8")


def fresh_ib(name: str) -> str:
    ib = WORK / name
    if ib.exists():
        shutil.rmtree(ib)
    return str(ib)


def bare(result: dict) -> dict:
    return {k: v for k, v in result.items() if k != "lines"}


def run_raw(step: str, opts: dict) -> dict:
    """Запуск платформы напрямую, без защит контура: нужно поведение самой платформы."""
    out_file = pathlib.Path(opts["out"])
    if out_file.exists():
        out_file.unlink()
    started = time.monotonic()
    proc = subprocess.Popen(ib_loop.build_command(step, opts))
    timed_out = False
    while time.monotonic() - started < int(opts.get("timeout", 300)):
        if proc.poll() is not None:
            break
        time.sleep(1)
    else:
        timed_out = True
        proc.terminate()
        try:
            proc.wait(timeout=30)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=30)
    data = out_file.read_bytes() if out_file.is_file() else b""
    text = ib_loop.decode_output(data)
    return {"step": step, "code": proc.returncode, "seconds": round(time.monotonic() - started, 1),
            "bytes": len(data), "timed_out": timed_out,
            "lines": [line.strip() for line in text.splitlines() if line.strip()]}


def observation_c() -> dict:
    real_copy = SPIKES / "cfg_full"
    ib = fresh_ib("ib_real")
    opts = {"bin": LOCAL["bin"], "ib": ib, "cfg": str(real_copy),
            "dump": str(WORK / "dump_real"), "out": str(WORK / "out_real.txt"), "timeout": 600}
    steps = [ib_loop.run_step(step, opts) for step in ("create", "load", "check", "dump")]
    data = {"cfg_files": sum(1 for p in real_copy.rglob("*") if p.is_file()),
            "steps": [bare(step) for step in steps],
            "check_lines": steps[2]["lines"][:8]}
    write_json("contour-real.json", data)
    return data


def observation_b1() -> dict:
    ib = fresh_ib("ib_b1")
    create = ib_loop.run_step("create", {"bin": LOCAL["bin"], "ib": ib,
                                         "out": str(WORK / "out_b1.txt")})
    missing = str(WORK / "каталога-нет")
    refusal = ib_loop.run_step("load", {"bin": LOCAL["bin"], "ib": ib, "cfg": missing,
                                        "dump": str(WORK / "dump_b1"),
                                        "out": str(WORK / "out_b1.txt")})
    raw = run_raw("load", {"bin": LOCAL["bin"], "ib": ib, "cfg": missing,
                           "out": str(WORK / "out_b1.txt"), "timeout": 120})
    data = {"create": bare(create), "contour_refusal": bare(refusal),
            "contour_refusal_reason": refusal["reason"],
            "platform_raw": bare(raw), "platform_raw_lines": raw["lines"][:8]}
    write_json("obs-B1.json", data)
    return data


def observation_b2() -> dict:
    broken_copy = SPIKES / "cfg_min"              # заведомо битый (свойство Content подсистемы)
    good_dump = SPIKES / "dump_full"              # дамп реальной конфигурации
    dump_dir = WORK / "dump_b2"
    if dump_dir.exists():
        shutil.rmtree(dump_dir)
    shutil.copytree(good_dump, dump_dir)
    before = sum(1 for p in dump_dir.rglob("*") if p.is_file())
    ib = fresh_ib("ib_b2")
    out = str(WORK / "out_b2.txt")
    create = ib_loop.run_step("create", {"bin": LOCAL["bin"], "ib": ib, "out": out})
    load = ib_loop.run_step("load", {"bin": LOCAL["bin"], "ib": ib, "cfg": str(broken_copy),
                                     "out": out})
    dump_raw = run_raw("dump", {"bin": LOCAL["bin"], "ib": ib, "dump": str(dump_dir),
                                "out": out, "timeout": 180})
    after = sum(1 for p in dump_dir.rglob("*") if p.is_file())
    fresh = [p.relative_to(dump_dir).as_posix() for p in dump_dir.rglob("*")
             if p.is_file() and time.time() - p.stat().st_mtime < 600]
    data = {"files_before": before, "files_after": after, "fresh_files": fresh,
            "dump_configuration_name": counts.configuration_name(dump_dir),
            "dump_layout_counts": layout.layout_counts(dump_dir),
            "create": bare(create), "load": bare(load), "load_lines": load["lines"][:6],
            "dump_raw": bare(dump_raw),
            "note": ("платформа вызвана напрямую поверх непустого каталога выгрузки; контур так "
                     "не делает: ib_loop пересоздаёт каталог выгрузки перед каждым шагом dump")}
    write_json("obs-B2.json", data)
    return data


def observation_b2_repeats(broken_copy: pathlib.Path) -> dict:
    """Три повтора загрузки одного и того же битого каталога: стабилен ли текст первой ошибки.

    Нужно, потому что вывод записывают целиком и признак провала — коды и состав выгрузки:
    наблюдение показало, что между прогонами меняется даже имя файла в тексте ошибки.
    """
    variants = []
    for attempt in range(3):
        ib = fresh_ib("ib_rep" + str(attempt))
        out = str(WORK / "out_rep.txt")
        ib_loop.run_step("create", {"bin": LOCAL["bin"], "ib": ib, "out": out})
        step = ib_loop.run_step("load", {"bin": LOCAL["bin"], "ib": ib, "cfg": str(broken_copy),
                                         "out": out})
        variants.append({"attempt": attempt, "code": step["code"], "seconds": step["seconds"],
                         "bytes": step["bytes"], "lines": step["lines"][:4]})
        shutil.rmtree(ib, ignore_errors=True)
    data = {"attempts": variants,
            "distinct_first_lines": sorted({(v["lines"] or [""])[0] for v in variants})}
    write_json("obs-B2-repeats.json", data)
    return data


def observation_d() -> dict:
    """Гейт на реальной конфигурации: чем независимый счётчик отличается от чисел читателя p1c.

    Ожидаемые числа для этого наблюдения берутся из раскладки самого корпуса (цель — не гейт
    чужой конфигурации, а замер того, какие виды объектов читатель `p1c.load` не видит).
    """
    real_copy = SPIKES / "cfg_full"
    expected_file = WORK / "expected-real-corpus.json"
    expected_file.write_text(json.dumps({"expected": layout.layout_counts(real_copy)},
                                        ensure_ascii=False, indent=2), encoding="utf-8")
    ib = fresh_ib("ib_real2")
    create = ib_loop.run_step("create", {"bin": LOCAL["bin"], "ib": ib,
                                         "out": str(WORK / "out_gate_real.txt")})
    code, report = gate.run(str(real_copy), str(REPORTS / "gate-real.json"),
                            {"bin": LOCAL["bin"], "ib": ib,
                             "dump": str(WORK / "dump_real2"),
                             "p1c": LOCAL["p1c"], "expected": str(expected_file),
                             "loop_out": str(WORK / "out_gate_real.txt"), "timeout": 600})
    data = {"create": bare(create), "gate_code": code, "gate_reason": report["reason"],
            "load_code": report["load_code"], "check_code": report["check_code"],
            "diagnostics": report["diagnostics"][:4],
            "source_configuration_name": report["source_configuration_name"],
            "dump_configuration_name": report["dump_configuration_name"],
            "dump_fresh_files": report["dump_fresh_files"],
            "layout_source": report["layout_source"], "layout_dump": report["layout_dump"],
            "layout_compare": report["layout_compare"],
            "tool_counts_source": report["tool_counts_source"],
            "tool_counts_dump": report["tool_counts_dump"],
            "tool_blind_kinds": report["tool_blind_kinds"],
            "tool_counts_error": report["tool_counts_error"],
            "diff_same": report["diff_files"]["same"],
            "diff_differ": report["diff_files"]["differ"],
            "diff_only_source": report["diff_files"]["only_source"],
            "diff_only_dump": report["diff_files"]["only_dump"],
            "dump_files": report["dump_files"]}
    write_json("obs-D-gate-real.json", data)
    return data


def main() -> int:
    WORK.mkdir(parents=True, exist_ok=True)
    c = observation_c()
    b1 = observation_b1()
    b2 = observation_b2()
    repeats = observation_b2_repeats(SPIKES / "cfg_min")
    d = observation_d()

    lines = ["# Наблюдения Task 1 (платформа 8.3.27.1606)", "",
             "Номера наблюдений соответствуют плану (раздел «Поправки плана», B1/B2) и журналу.",
             ""]
    lines.append("## C. Полный цикл на реальной конфигурации (копия)")
    lines.append(f"- исходных файлов: {c['cfg_files']}")
    for step in c["steps"]:
        lines.append(f"- {step['step']}: код {step['code']}, {step['seconds']} с, "
                     f"байт вывода {step['bytes']}")
    for line in c["check_lines"]:
        lines.append("  диагностика /CheckModules: " + line)

    lines += ["", "## B1. `/LoadConfigFromFiles` с каталогом, которого нет",
              "- контур отказывает до запуска платформы: код "
              f"{b1['contour_refusal']['code']}, причина: {b1['contour_refusal_reason']}",
              f"- платформа напрямую: код {b1['platform_raw']['code']}, байт вывода "
              f"{b1['platform_raw']['bytes']}, "
              + ("ожидания превышены" if b1["platform_raw"]["timed_out"] else "уложилось")]
    for line in b1["platform_raw_lines"]:
        lines.append("  вывод: " + line)
    lines.append("- вывод: молчания нет; и контур, и платформа сообщают об отсутствии каталога")

    lines += ["", "## B2. `/DumpConfigToFiles` после неудачной загрузки поверх хорошего дампа",
              f"- файлов в каталоге выгрузки: до {b2['files_before']}, после {b2['files_after']}",
              f"- свежих файлов после выгрузки: {len(b2['fresh_files'])} — {b2['fresh_files']}",
              f"- имя корневого объекта выгрузки: {b2['dump_configuration_name']!r}",
              f"- числа выгрузки по независимому счётчику: {json.dumps(b2['dump_layout_counts'], ensure_ascii=False)}",
              f"- код загрузки битой конфигурации: {b2['load']['code']}, код выгрузки: "
              f"{b2['dump_raw']['code']}"]
    for line in b2["load_lines"]:
        lines.append("  вывод загрузки: " + line)
    lines.append("- вывод: платформа не затирает прежний дамп; признак провала — расхождение имени "
                 "корневого объекта с именем исходника и свежие файлы, а не число файлов каталога")
    lines += ["", "## B2b. Три повтора загрузки одного и того же битого каталога",
              "- коды прогонов: " + ", ".join(str(v["code"]) for v in repeats["attempts"]),
              "- разные тексты первой ошибки: " + json.dumps(repeats["distinct_first_lines"],
                                                              ensure_ascii=False)]
    for variant in repeats["attempts"]:
        lines.append(f"  попытка {variant['attempt']}: код {variant['code']}, "
                     f"{variant['seconds']} с, байт {variant['bytes']}, строк вывода "
                     f"{len(variant['lines'])}")
    lines.append("- вывод: текст первой ошибки между прогонами не стабилен — вывод пишут целиком, "
                 "признак провала ищут в кодах и составе выгрузки")

    lines += ["", "## D. Гейт на реальной конфигурации: что видит независимый счётчик и что — читатель p1c",
              f"- код гейта: {d['gate_code']} ({d['gate_reason']})",
              f"- коды платформы: load {d['load_code']}, check {d['check_code']}",
              f"- файлов выгрузки: {d['dump_files']}, свежих (записанных этим шагом): {d['dump_fresh_files']}",
              f"- имя корневого объекта: исходник {d['source_configuration_name']!r}, "
              f"выгрузка {d['dump_configuration_name']!r}",
              f"- пофайловая сверка: идентично {d['diff_same']}, различается "
              f"{len(d['diff_differ'])}, только в источнике {len(d['diff_only_source'])}, "
              f"только в выгрузке {len(d['diff_only_dump'])}"]
    lines.append("- расхождение чисел источника и выгрузки: "
                 + json.dumps(d["layout_compare"], ensure_ascii=False))
    lines.append("- числа независимого счётчика (источник): "
                 + json.dumps(d["layout_source"], ensure_ascii=False))
    lines.append("- числа независимого счётчика (выгрузка): "
                 + json.dumps(d["layout_dump"], ensure_ascii=False))
    lines.append("- числа читателя p1c.load (источник): "
                 + json.dumps(d["tool_counts_source"], ensure_ascii=False))
    lines.append("- числа читателя p1c.load (выгрузка): "
                 + json.dumps(d["tool_counts_dump"], ensure_ascii=False))
    lines.append("- читатель p1c.load не сообщает ни о чём из этого: "
                 + json.dumps(d["tool_blind_kinds"], ensure_ascii=False))
    if d["tool_counts_error"]:
        lines.append("- читатель p1c.load недоступен: " + d["tool_counts_error"])
    for rel in d["diff_differ"][:12]:
        lines.append("  различается файл: " + rel)

    EVIDENCE.mkdir(parents=True, exist_ok=True)
    (EVIDENCE / "task1-observations.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
