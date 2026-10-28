r"""Regenerate the markdown tables of docs/evidence/modifier-effects.md from the run reports.

Why a script and not hand-typed tables: every number in that evidence file must be traceable to a key
of reports/effect-16-*.json, and retyping 42 rows across 7 runs is exactly where numbers get distorted.
The evidence file was built by replacing `<!--TABLE name-->` / `<!--OUT name-->` markers with these
fragments (see `--inject`), and `--check` is what proves afterwards that the numbers in the document
still equal the numbers in the reports.

Usage:
    python probe/render_effect_tables.py                      # write fragments, print a summary
    python probe/render_effect_tables.py --out <file>         # fragments elsewhere
    python probe/render_effect_tables.py --check              # every fragment line present in the doc?
    python probe/render_effect_tables.py --inject <doc>       # replace the markers in a document
"""
import argparse
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
EVIDENCE = ROOT / "docs" / "evidence" / "modifier-effects.md"
RUNS = ["predefined", "extensions", "loadopts", "update", "modes", "repeat", "loadopts-shared"]

# Fragments the evidence document actually contains.  `OUT loadopts-shared` is generated (that run has
# steps with output) but the document quotes its output in bytes only, because that report predates
# `out_line_stats` and carries no line counters.  Listing the used names keeps --check honest instead of
# silently checking fragments the document never promised to show.
IN_DOCUMENT = [
    ("TABLE", "volume"),
    ("TABLE", "predefined"),
    ("TABLE", "extensions"),
    ("OUT", "extensions"),
    ("TABLE", "loadopts"),
    ("OUT", "loadopts"),
    ("TABLE", "loadopts-shared"),
    ("TABLE", "partial"),
    ("TABLE", "update"),
    ("OUT", "update"),
    ("TABLE", "modes"),
    ("TABLE", "repeat"),
    ("TABLE", "expectations"),
    ("TABLE", "dumptwice"),
    ("TABLE", "restore"),
    ("TABLE", "differ8list"),
    ("TABLE", "reorderedlist"),
]
MARKER = re.compile(r"^<!--(TABLE|OUT) ([a-z0-9-]+)-->$")


def report(name):
    key = name if name.endswith("-shared") else name + "-full"
    path = ROOT / "reports" / ("effect-16-%s.json" % key)
    return json.loads(path.read_text(encoding="utf-8"))


def short(argv_tail):
    r"""argv[4:] -> the command and its modifiers, with the long paths collapsed.

    The tails are the ones the runner took from `scripts/exec_probe.py: VARIANT_TAIL`, so collapsing here
    shortens paths only; flag names are shown exactly as they were passed.  `/Out` and
    `/DisableStartupDialogs` are dropped because every step of a ladder carries them identically.
    """
    tail = list(argv_tail)
    if tail[:3] == ["/Out", tail[1] if len(tail) > 1 else "", "/DisableStartupDialogs"]:
        tail = tail[3:]
    out = []
    for tok in tail:
        if "cfg" in tok:
            out.append("<каталог конфигурации>")
        elif tok.endswith("exec_loadlist.txt"):
            out.append("<файл-список>")
        elif "no-such-directory" in tok:
            out.append("<нет такого каталога>")
        else:
            out.append("`%s`" % tok)
    return " ".join(out) or "(хвоста нет)"


def size(fp):
    return "%sф/%sБ" % (fp["files"], fp["bytes"])


def ladder_table(rep, source_uuid):
    rows = ["| # | вариант | хвост команды | код | сек | `/Out` | было → стало | uuid = исходник? | что изменилось |",
            "|---|---|---|---|---|---|---|---|---|"]
    for s in rep["steps"] + [dict(rep["restore"], variant="**восстановление**")]:
        b, a = s["before_fingerprint"], s["fingerprint"]
        chg = s.get("changed_by_step") or {}
        cv = chg.get("config_versions")
        chg_txt = ", ".join(sorted(k for k in chg if k != "config_versions"))
        if isinstance(cv, dict):
            chg_txt = (chg_txt + ", " if chg_txt else "") + "config_versions (%d)" % len(cv)
        rows.append("| %s | %s | %s | %s | %.1f | %s Б / %s стр. | %s → %s | %s | %s |" % (
            s["index"], s["variant"], short(s["argv_tail"]), s["code"], s["seconds"],
            s["out_bytes"], s.get("out_lines_total", "—"), size(b), size(a),
            "да" if a["config_uuid"] == source_uuid else "нет",
            chg_txt or "—"))
    return rows


def out_table(rep):
    rows = ["| # | вариант | строки `/Out` дословно |", "|---|---|---|"]
    for s in rep["steps"]:
        if not s.get("out_lines_total"):
            continue
        text = " <br> ".join(r.replace("|", "\\|") for r in s["out_lines_unique"])
        if len(text) > 900:
            text = text[:900] + " …"
        note = "" if s["out_lines_total"] == len(s["out_lines_unique"]) else \
            " _(всего строк %d, неповторяющихся %d)_" % (
                s["out_lines_total"], len(s["out_lines_unique"]))
        rows.append("| %s | %s | %s%s |" % (s["index"], s["variant"], text, note))
    return rows


def fragments():
    """(kind, name) -> generated lines, in the order the evidence document shows them."""
    reps = {name: report(name) for name in RUNS}
    out = {}

    for name in RUNS:
        out[("TABLE", name)] = ladder_table(reps[name], reps[name]["source_uuid"])
        if name in ("extensions", "loadopts", "update"):
            out[("OUT", name)] = out_table(reps[name])

    lines = ["| прогон | шагов лестницы | загрузок (с восстановлением) | `CREATEINFOBASE` | выгрузок | свежая ИБ на шаг |",
             "|---|---|---|---|---|---|"]
    tot = [0, 0, 0, 0]
    six = [0, 0, 0, 0]
    for name in RUNS:
        rep = reps[name]
        row = [len(rep["ladder_variants"]), len(rep["steps"]) + 1, len(rep["create_codes"]),
               len(rep["dump_codes"])]
        tot = [a + b for a, b in zip(tot, row)]
        if name != "loadopts-shared":
            six = [a + b for a, b in zip(six, row)]
        lines.append("| %s | %d | %d | %d | %d | %s |" % (
            name, row[0], row[1], row[2], row[3], "да" if rep["ib_fresh_each_step"] else "нет"))
    lines.append("| **шесть `-full`** | %d | %d | %d | %d | да (кроме `repeat`) |" % tuple(six))
    lines.append("| **все семь прогонов** | %d | %d | %d | %d | — |" % tuple(tot))
    out[("TABLE", "volume")] = lines

    lines = ["| прогон | шагов | файлы совпали | байты совпали | uuid совпал | uuid разошёлся |",
             "|---|---|---|---|---|---|"]
    for name in RUNS:
        tw = [s["dump_twice"] for s in reps[name]["steps"]]
        lines.append("| %s | %d | %d | %d | %d | %d |" % (
            name, len(tw), sum(1 for x in tw if x["same_files"]),
            sum(1 for x in tw if x["same_bytes"]), sum(1 for x in tw if x["same_uuid"]),
            sum(1 for x in tw if not x["same_uuid"])))
    out[("TABLE", "dumptwice")] = lines

    exp = (reps["loadopts"].get("expectations") or {})[
        "partial-second-identifier-is-ib-uuid-before-step"]
    lines = ["| # | вариант | первый названный | второй названный | uuid ИБ **до** шага | uuid ИБ **после** шага | первый = uuid исходника? | второй = до? | второй = после? |",
             "|---|---|---|---|---|---|---|---|---|"]
    for ev in exp["evidence"]:
        named = ev["named"]
        lines.append("| %s | %s | `%s…` | `%s…` | `%s…` | `%s…` | %s | %s | %s |" % (
            ev["index"], ev["variant"], named[0][:13], named[1][:13],
            ev["before_uuid"][:13], ev["after_uuid"][:13],
            "да" if ev["first_is_source_uuid"] else "нет",
            "да" if ev["second_is_before_uuid"] else "**нет**",
            "да" if named[1] == ev["after_uuid"] else "**нет**"))
    out[("TABLE", "partial")] = lines

    names = sorted((reps["predefined"].get("expectations") or {}).keys())
    lines = ["| ожидание (записано до прогона) | " + " | ".join(RUNS) + " |",
             "|---" * (len(RUNS) + 1) + "|"]
    for n in names:
        cells = []
        for run in RUNS:
            exp = (reps[run].get("expectations") or {}).get(n) or {}
            met = exp.get("met")
            cells.append({True: "сбылось (%d)" % len(exp.get("evidence") or []),
                          False: "**опровергнуто** (%d)" % len(exp.get("evidence") or []),
                          None: "непроверяемо"}[met])
        lines.append("| `%s` | %s |" % (n, " | ".join(cells)))
    out[("TABLE", "expectations")] = lines

    lines = ["| прогон | код | same | reordered | differ | only_source | only_dump | платформа добавила |",
             "|---|---|---|---|---|---|---|---|"]
    for name in RUNS:
        d = reps[name]["restore"]["diff_vs_source"]
        lines.append("| %s | %s | %d | %d | %d | %d | %d | %s |" % (
            name, reps[name]["restore"]["code"], len(d["same"]), len(d["reordered"]),
            len(d["differ"]), len(d["only_source"]), len(d["only_dump"]),
            ", ".join(d["platform_added"])))
    out[("TABLE", "restore")] = lines

    d = reps["predefined"]["restore"]["diff_vs_source"]
    out[("TABLE", "differ8list")] = ["- `%s`" % rel for rel in d["differ"]]
    out[("TABLE", "reorderedlist")] = ["- `%s`" % rel for rel in d["reordered"]]
    out[("OUT", "loadopts-shared")] = out_table(reps["loadopts-shared"])
    return out


def render(out_path):
    fr = fragments()
    lines = []
    for key in IN_DOCUMENT:
        lines.append("<!--%s %s-->" % key)
        lines += fr[key]
        lines.append("")
    if ("OUT", "loadopts-shared") in fr:
        lines.append("<!--OUT loadopts-shared-->")
        lines += fr[("OUT", "loadopts-shared")]
        lines.append("")
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return fr


def check(out_path):
    r"""Every generated line must appear verbatim in the evidence document.

    A mismatch means either the document was edited by hand after injection or the reports changed.
    Both are worth knowing about before the numbers get quoted somewhere else.
    """
    fr = render(out_path)
    doc_lines = {line.strip() for line in EVIDENCE.read_text(encoding="utf-8-sig").splitlines()}
    missing = []
    counted = 0
    for key in IN_DOCUMENT:
        for line in fr[key]:
            counted += 1
            if line.strip() not in doc_lines:
                missing.append((key, line))
    unused = sorted(set(fr) - set(IN_DOCUMENT))
    print("fragments:", len(fr), "checked lines:", counted)
    print("unused fragments:", ", ".join("%s %s" % kv for kv in unused) or "none")
    if missing:
        print("MISSING from", EVIDENCE)
        for key, line in missing[:40]:
            print("  %s %s: %s" % (key[0], key[1], line))
        return 1
    print("all checked lines present verbatim in the document")
    return 0


def inject(doc_path, out_path):
    """Replace `<!--TABLE name-->` / `<!--OUT name-->` markers with the generated fragments."""
    raw = doc_path.read_bytes()
    crlf = b"\r\n" in raw
    bom = raw.startswith(b"\xef\xbb\xbf")
    fr = render(out_path)
    used, missing, lines = [], [], []
    for line in raw.decode("utf-8-sig").splitlines():
        m = MARKER.match(line.strip())
        if not m:
            lines.append(line)
            continue
        frag = fr.get((m.group(1), m.group(2)))
        if not frag:
            missing.append((m.group(1), m.group(2)))
            lines.append(line)
            continue
        used.append((m.group(1), m.group(2)))
        lines.extend(frag)
    body = "\r\n" if crlf else "\n"
    doc_path.write_bytes(("\ufeff" if bom else "") .encode("utf-8")
                         + body.join(lines).encode("utf-8") + body.encode("utf-8"))
    print("injected", len(used), "markers, missing fragments:", missing or "none")
    print("crlf", crlf, "bom", bom, "lines", len(lines))
    return 1 if missing else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(pathlib.Path(__file__).resolve().parents[1]
                                         / "reports" / "effect-tables.md"))
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--inject", metavar="DOC", help="markdown document whose markers get replaced")
    args = ap.parse_args()
    out_path = pathlib.Path(args.out)
    if args.inject:
        return inject(pathlib.Path(args.inject), out_path)
    if args.check:
        return check(out_path)
    fr = render(out_path)
    print("wrote", out_path, "fragments", len(fr))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
