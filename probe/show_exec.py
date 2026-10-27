"""Чтение JSON-отчёта `scripts/exec_probe.py`: полная сводка шагов лестницы.

Зачем. Отчёт `reports/exec-12-*.json` содержит argv, вывод и след программы, но печать в
консоли обрывается на середине (PowerShell обрезает длинный вывод). Скрипт печатает только
существенные поля по каждому шагу, поэтому весь прогон видно за один вызов.

    python probe/show_exec.py reports/exec-12-sweep.json
"""
from __future__ import annotations

import json
import pathlib
import sys


def main(argv: list[str]) -> int:
    report = json.loads(pathlib.Path(argv[0]).read_text(encoding="utf-8"))
    print("итог:", report.get("verdict"))
    for step in report.get("results", []):
        print("==", step.get("variant"), "|", step.get("script_encoding"),
              "| код", step.get("code"), "|", step.get("seconds"), "с",
              "| таймаут", step.get("timed_out"),
              "| /Out байт", step.get("bytes"), "| строк", step.get("out_lines"),
              "| stdout", step.get("stdout_bytes"), "| stderr", step.get("stderr_bytes"),
              "| файл программы", step.get("script_encoding_bytes"),
              "| след:", step.get("marker_exists"), str(step.get("marker_text"))[:80])
        print("   argv:", " ".join(step.get("argv", [])))
        for key in ("lines", "console_lines"):
            for line in (step.get(key) or [])[:8]:
                print("   ", key, ":", line[:200])
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
