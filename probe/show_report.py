"""Покаж выбранные поля отчёта гейта целиком.

Один-единственный способ прочитать JSON-отчёт в этой оболочке: `python -c` с here-string
съедает кавычки (наблюдение журнала), поэтому разбор отчётов делают файлом.

    python probe/show_report.py reports/gate-07.json
"""
from __future__ import annotations

import json
import sys

FIELDS = ("code", "reason", "cycle_continues", "dump_dir", "load_code", "check_code",
          "dump_files", "dump_fresh_files", "expected_mismatch", "rights",
          "rights_immobility", "diagnostics", "diagnostics_by_step", "diagnostic_findings",
          "step_problems", "steps", "loop_steps", "tool_counts_source", "tool_blind_kinds")


def main(argv: list) -> int:
    report = json.load(open(argv[0], encoding="utf-8"))
    for key in FIELDS:
        if key in report:
            print("==", key)
            print(json.dumps(report[key], ensure_ascii=False, indent=2)[:2500])
    diff = report.get("diff_files", {})
    for key in ("only_source", "only_dump", "platform_added"):
        print("==", key, json.dumps(diff.get(key, []), ensure_ascii=False))
    print("== same", len(diff.get("same", [])), "| reordered", len(diff.get("reordered", [])),
          diff.get("reordered", []), "| differ", len(diff.get("differ", [])))
    for item in diff.get("differ", []):
        print("   ", item if isinstance(item, str) else json.dumps(item, ensure_ascii=False)[:400])
    for key, value in report.items():
        if key not in FIELDS and key not in diff and key not in ("diff_files",):
            print("== (вне списка)", key, json.dumps(value, ensure_ascii=False)[:600])
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
