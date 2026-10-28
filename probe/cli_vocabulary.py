"""Enumerate the measured command vocabulary of every p1c CLI (read-only introspection).

For each CLI module found under `p1c/src/p1c/**/cli.py`: take the subcommand list from the
module's own `--help` text, then take the flags of every subcommand from its `--help`. Nothing is
invented and no CLI is run against data: only usage texts are read.

Output: `reports/cli-vocabulary-22.json`, `reports/cli-vocabulary-22.txt`.
"""
from __future__ import annotations

import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import paths  # noqa: E402

CHOICE_RE = re.compile(r"^\s*\{([a-z0-9_,\-]+)\}", re.M)
OPT_RE = re.compile(r"^\s*(--[A-Za-z0-9\-]+)(?:[ =<]|$)", re.M)


def _text(argv: list) -> tuple:
    proc = subprocess.run([sys.executable, "-m"] + argv, capture_output=True,
                          text=True, encoding="utf-8", errors="replace")
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def cli_modules(p1c_src: str) -> list:
    base = pathlib.Path(p1c_src) / "p1c"
    out = []
    for f in sorted(base.rglob("cli.py")):
        rel = f.relative_to(base).with_suffix("")
        out.append("p1c." + ".".join(rel.parts))
    return out


def main() -> int:
    mods = cli_modules(paths.load_local(ROOT / "local.paths.json")["p1c"])
    vocab = {}
    for mod in mods:
        code, text = _text([mod, "--help"])
        subs = []
        m = CHOICE_RE.search(text)
        if m:
            subs = [s for s in m.group(1).split(",") if s]
        entry = {"help_exit": code, "subcommands": subs, "top_options": sorted(set(OPT_RE.findall(text))),
                 "flags_by_subcommand": {}}
        for sub in subs:
            c2, t2 = _text([mod, sub, "--help"])
            entry["flags_by_subcommand"][sub] = {"exit": c2, "options": sorted(set(OPT_RE.findall(t2)))}
        vocab[mod] = entry

    out = ROOT / "reports" / "cli-vocabulary-22.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(vocab, ensure_ascii=False, indent=2) + "\n", "utf-8")

    lines = ["# Измеренный словарь подкоманд и флагов CLI p1c (только тексты `--help`)", ""]
    for mod in mods:
        e = vocab[mod]
        lines.append("## %s  (`--help`: exit %d)" % (mod, e["help_exit"]))
        lines.append("common flags: %s" % ", ".join(e["top_options"]))
        for sub in e["subcommands"]:
            f = e["flags_by_subcommand"][sub]
            lines.append("  %-22s exit %d  flags: %s"
                         % (sub, f["exit"], ", ".join(f["options"]) or "нет"))
        lines.append("")
    txt = "\n".join(lines)
    (ROOT / "reports" / "cli-vocabulary-22.txt").write_text(txt + "\n", "utf-8")
    print(txt)
    print("wrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
