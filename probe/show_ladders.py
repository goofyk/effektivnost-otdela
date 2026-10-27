"""Сводка лестниц Task 12: одна строка на шаг, компактно."""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]


def show(path: pathlib.Path) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    print("==", path.name)
    for r in data["results"]:
        line = (f"{r.get('variant',''):<22} {r.get('program_kind','-'):<8} "
                f"{r.get('script_encoding','?'):<8} "
                f"code={r['code']} secs={r['seconds']} out_bytes={r['bytes']} "
                f"script_bytes={r.get('script_bytes', 0)} marker={r['marker_exists']} "
                f"lines={len(r['lines'])} console={len(r['console_lines'])}")
        print(line)
        for text in (r["lines"] + r["console_lines"])[:2]:
            print("      вывод:", text[:160])
        print("      argv:", " ".join(r["argv"][-4:]))
    for key in ("controls_classes", "controls_distinct", "negative_classes",
                "negative_matches_runscript", "negative_clean"):
        if key in data:
            print(key, "=", data[key])


for name in sys.argv[1:]:
    show(ROOT / "reports" / name)
