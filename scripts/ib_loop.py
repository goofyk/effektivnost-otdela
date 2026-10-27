"""Цикл платформы: создание базы, загрузка конфигурации из файлов, проверка модулей, выгрузка.

Имена режимов и флагов подтверждены наблюдением на платформе 8.3.27.1606:

  CREATEINFOBASE File=<база> /Out <файл> /DisableStartupDialogs                      -> код 0
  DESIGNER /F <база> /Out <файл> /DisableStartupDialogs /LoadConfigFromFiles <каталог> -> код 0
  DESIGNER ... /CheckModules -Server -ThinClient -WebClient -ExternalConnection
             -ThickClientOrdinaryApplication                                          -> код 0 без
                                                                                       диагностик,
                                                                                       101 с ними
  DESIGNER ... /DumpConfigToFiles <каталог>                                           -> код 0

Имя режима запуска обязано идти первым параметром (иначе платформа сообщает
«Неопределен режим запуска», код 1 — наблюдено).

Выгрузка всегда пишется в заново созданный каталог: наблюдение B2 показало, что после
неудачной загрузки выгрузка возвращает пустую конфигурацию платформы, и поверх старого
дампа это выглядело бы как «дамп есть».

Запуск:
    python scripts/ib_loop.py --all [--bin ФАЙЛ] [--ib БАЗА] [--cfg КАТАЛОГ] [--dump КАТАЛОГ]
                              --out ФАЙЛ_JSON [--timeout СЕКУНД]
Коды выхода: 0 — все шаги отработали без отказа формата, 1 — шаг платформы вернул ненулевой
код, 2 — цикл невозможен (нет файла платформы, нет конфигурации, нет базы).
"""
from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import paths                                                    # noqa: E402

STEPS = ("create", "load", "check", "dump")
CHECK_KEYS = ("-Server", "-ThinClient", "-WebClient", "-ExternalConnection",
              "-ThickClientOrdinaryApplication")
DEFAULT_TIMEOUT = 300


IB_MARKERS = (".8cd", ".8dh", ".1cd", ".1cl")


def ib_exists(ib: str) -> bool:
    """Файловая база создана: в каталоге есть маркеры файловой базы.

    Наблюдение 8.3.27.1606: `CREATEINFOBASE File=…` даёт каталог с `1Cv8.1CD` (и `1Cv8.1CL.cfl`),
    а не с «классическими» `1Cv8.8cd`. Отличие важно: без базы загрузка сообщает
    «Информационная база не обнаружена!» с кодом 1 — неотличимо от битой конфигурации.
    """
    if not ib:
        return False
    base = pathlib.Path(ib)
    if not base.is_dir():
        return False
    for entry in base.iterdir():
        name = entry.name.lower()
        if name.startswith("1cv8") and entry.suffix.lower() in IB_MARKERS and entry.is_file():
            return True
    return False


def refusal(step: str, opts: dict) -> str:
    """Причина, по которой шаг не выполняется. Пустая строка — запуск разрешён."""
    if step not in STEPS:
        return "шага платформы с таким именем нет: " + str(step) + " (есть " + ", ".join(STEPS) + ")"
    reason = paths.refuse_missing_bin(opts.get("bin", ""))
    if reason:
        return reason
    if step == "create" and not opts.get("ib"):
        return "информационной базы не названо: нужен --ib"
    if step in ("load", "check", "dump") and not opts.get("ib"):
        return "информационной базы не названо: нужен --ib (база должна быть создана шагом create)"
    if step == "load" and not opts.get("cfg"):
        return "каталога конфигурации не названо: нужен --cfg"
    if step == "dump" and not opts.get("dump"):
        return "каталога выгрузки не названо: нужен --dump"
    if step == "load" and not pathlib.Path(opts["cfg"]).is_dir():
        return "каталога конфигурации нет: --cfg называет каталог, которого не существует"
    if not opts.get("out"):
        return "файла результата не названо: нужен --out (в него пишет платформа)"
    return ""


def build_command(step: str, opts: dict) -> list:
    """Команда платформы для шага: имя режима первым, затем база, затем флаги шага."""
    bin_path, ib, out = opts["bin"], opts["ib"], opts["out"]
    if step == "create":
        return [bin_path, "CREATEINFOBASE", "File=" + ib, "/Out", out, "/DisableStartupDialogs"]
    if step == "load":
        return [bin_path, "DESIGNER", "/F", ib, "/Out", out, "/DisableStartupDialogs",
                "/LoadConfigFromFiles", opts["cfg"]]
    if step == "check":
        return [bin_path, "DESIGNER", "/F", ib, "/Out", out, "/DisableStartupDialogs",
                "/CheckModules"] + list(CHECK_KEYS)
    if step == "dump":
        return [bin_path, "DESIGNER", "/F", ib, "/Out", out, "/DisableStartupDialogs",
                "/DumpConfigToFiles", opts["dump"]]
    return []


def decode_output(data: bytes) -> str:
    """Текст вывода платформы: кодирование определяется по признакам байтов (наблюдение)."""
    if not data:
        return ""
    if data[:2] == b"\xff\xfe":
        return data[2:].decode("utf-16-le", "replace")
    if data[:3] == b"\xef\xbb\xbf":
        return data[3:].decode("utf-8", "replace")
    if b"\x00" in data[:200]:
        return data.decode("utf-16-le", "replace")
    for encoding in ("utf-8", "cp1251"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("latin-1", "replace")


def run_step(step: str, opts: dict) -> dict:
    """Один шаг цикла: {'step','code','seconds','bytes','lines','timed_out','reason'}."""
    reason = refusal(step, opts)
    if reason:
        return {"step": step, "code": 2, "seconds": 0.0, "bytes": 0, "lines": [],
                "timed_out": False, "reason": reason}

    out_file = pathlib.Path(opts["out"])
    out_file.parent.mkdir(parents=True, exist_ok=True)
    if out_file.exists():
        out_file.unlink()
    if step == "dump":
        dump_dir = pathlib.Path(opts["dump"])
        if dump_dir.exists():
            import shutil
            shutil.rmtree(dump_dir)
        dump_dir.mkdir(parents=True, exist_ok=True)

    timeout = int(opts.get("timeout") or DEFAULT_TIMEOUT)
    # Момент запуска по настенным часам: по нему гейт отличает файлы, которые записала
    # платформа в этом шаге, от файлов прежней выгрузки (наблюдение B2).
    started_wall = time.time()
    started = time.monotonic()
    proc = subprocess.Popen(build_command(step, opts))
    timed_out = False
    while time.monotonic() - started < timeout:
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
    text = decode_output(data)
    return {"step": step, "code": proc.returncode, "started": round(started_wall, 3),
            "seconds": round(time.monotonic() - started, 1), "bytes": len(data),
            "lines": [line.strip() for line in text.splitlines() if line.strip()],
            "timed_out": timed_out, "reason": ""}


def main(argv: list) -> int:
    parser = argparse.ArgumentParser(description="Цикл платформы для сборки конфигурации")
    parser.add_argument("--bin", default="", help="файл платформы (только аргумент или локальный файл путей)")
    parser.add_argument("--ib", default="", help="информационная база (временная, вне репозитория)")
    parser.add_argument("--cfg", default="", help="каталог конфигурации в файловом формате")
    parser.add_argument("--dump", default="", help="каталог выгрузки (пересоздаётся)")
    parser.add_argument("--out", default="", help="файл JSON-результата (вне репозитория)")
    parser.add_argument("--steps", default="all", help="список шагов через запятую или all")
    parser.add_argument("--all", action="store_true", help="все шаги по порядку")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    parser.add_argument("--local", default=str(ROOT / "local.paths.json"),
                        help="локальный файл путей (не в git)")
    args = parser.parse_args(argv)

    local = paths.load_local(args.local)
    opts = {"bin": args.bin or local.get("bin", ""), "ib": args.ib or local.get("ib", ""),
            "cfg": args.cfg or local.get("cfg", ""), "dump": args.dump or local.get("dump", ""),
            "out": args.out, "timeout": args.timeout}

    steps = list(STEPS) if (args.all or args.steps == "all") else [
        s.strip() for s in args.steps.split(",") if s.strip()]
    results = [run_step(step, opts) for step in steps]

    report = {"steps": results,
              "refusals": [r["reason"] for r in results if r["code"] == 2],
              "platform_errors": [r["code"] for r in results if r["code"] not in (0, 2)]}
    if args.out:
        pathlib.Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        pathlib.Path(args.out).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                                          encoding="utf-8")
    for r in results:
        print("[" + r["step"] + "] code=" + str(r["code"]) + " seconds=" + str(r["seconds"]) +
              " bytes=" + str(r["bytes"]) + (" timed_out" if r["timed_out"] else ""))
        if r["reason"]:
            print("  отказ: " + r["reason"])
        for line in r["lines"][:20]:
            print("  " + line)
    if report["refusals"]:
        return 2
    return 1 if report["platform_errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
