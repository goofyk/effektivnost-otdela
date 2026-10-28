r"""Regenerate the markdown tables of the query/SKD/SDBL/.epf evidence files from the run reports.

Why a script: the four evidence documents (docs/evidence/canonical-queries.md,
docs/evidence/sdbl-controls.md, docs/evidence/epf-roundtrip.md, docs/evidence/tool-coverage.md)
quote counters that live in reports/*.json.  Retyping them is where numbers drift, so every table
here is produced from a key of a report and injected into the document through a
`<!--TABLE name-->` marker.

Four families of sources:

* corpus measurements  -> reports/corpora-query-canon-16.json, reports/self-canonical-17.json,
  reports/vt3_groupby.json, reports/vt_skd_statements.json, reports/vt_vocab.json,
  reports/itogi_decompose.json;
* static SDBL controls -> every reports/sweep*.json / reports/skd_q_*.json / reports/skd2_*.json,
  with the exit code taken from the matching `*_summary.txt` block (the JSON report of p1c carries no
  exit code);
* the `.epf` roundtrip -> reports/epf-16-roundtrip.json.

Usage:
    python probe/render_query_tables.py                     # write fragments, print a summary
    python probe/render_query_tables.py --out <file>        # fragments elsewhere
    python probe/render_query_tables.py --check             # every fragment line present in the docs?
    python probe/render_query_tables.py --inject <doc>      # replace the markers in one document
"""
import argparse
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
REPORTS = ROOT / "reports"

# The roots of the measured layout live in `local.paths.json` (gitignored).  This script uses the cfg
# root for one thing only: to shorten the absolute paths the run reports store into the relative paths
# the gate counts, and to read the source line a finding points at.  No absolute path is written here.
PATHS = json.loads((ROOT / "local.paths.json").read_text(encoding="utf-8-sig")) \
    if (ROOT / "local.paths.json").is_file() else {}

CANON_DOC = ROOT / "docs" / "evidence" / "canonical-queries.md"
SDBL_DOC = ROOT / "docs" / "evidence" / "sdbl-controls.md"
EPF_DOC = ROOT / "docs" / "evidence" / "epf-roundtrip.md"
COVERAGE_DOC = ROOT / "docs" / "evidence" / "tool-coverage.md"

# The tool coverage matrices belong to probe/tool_coverage.py, which runs the p1c CLIs over our own
# layout; this script only carries those two tables into the document, it does not recompute them.
COVERAGE_MATRIX = REPORTS / "tool-coverage-matrix-18.md"
COVERAGE_RUNS = REPORTS / "toolcov_runs.json"

# Which coverage runs the evidence document walks, and in which of its two blocks.
COVERAGE_LOAD_RUNS = ("load-model-dump", "load-model-cfg", "load-forms-dump", "load-object-catalog",
                      "load-qualifiers-dump", "diff-model-cfg-dump", "graph-build-dump",
                      "graph-roots-dump", "metrics-top-dump")
COVERAGE_CHECK_RUNS = ("load-object-wrong-order", "forms-form-wrong-order", "bsl-check-cfg",
                       "forms-check-dump", "forms-events-dump", "forms-form-element",
                       "sdbl-check-cfg", "sdbl-query-skd")
CF_RUN = "cf-info-cfg-dir"

# The prefix of the line the shared XML-loading context writes to stderr (the only console text any
# successful coverage run produces).
CONTEXT_LINE = "[context] XML"

# `context_effective` repeats the context we passed to the tool and `context_signature` hashes it;
# `schema` names the report schema.  None of the three is content of our own layout, so the content
# blocks below skip them.
SKIP_REPORT_KEYS = ("context_effective", "context_signature", "schema")

# A backslash, spelled so that no file of the contour carries a drive-letter path (the reason
# tests/test_corpora.py::NoEnvironmentPathsInRepositoryTest exists at all).
BACKSLASH = chr(92)

# Which fragments each document promises to show (kept explicit so --check cannot pass silently).
IN_DOCUMENT = {
    CANON_DOC.name: [
        ("TABLE", "canon-needles"),
        ("TABLE", "canon-derived"),
        ("TABLE", "groupby-writings"),
        ("TABLE", "dotted-examples"),
        ("TABLE", "skd-statements"),
        ("TABLE", "skd-shapes"),
        ("TABLE", "vt-suffixes"),
        ("TABLE", "itogi-decompose"),
        ("TABLE", "self-dotted"),
    ],
    SDBL_DOC.name: [
        ("TABLE", "sdbl-runs"),
        ("TABLE", "sdbl-findings"),
        ("TABLE", "sdbl-signature"),
        ("TABLE", "sdbl-fields"),
        ("TABLE", "sdbl-vt-controls"),
        ("TABLE", "skd-old-vs-new"),
        ("OUT", "skd-texts"),
    ],
    EPF_DOC.name: [
        ("TABLE", "epf-steps"),
        ("TABLE", "epf-files"),
        ("TABLE", "epf-positions"),
        ("TABLE", "epf-snapshot-fix"),
    ],
    COVERAGE_DOC.name: [
        ("TABLE", "coverage-runs"),
        ("TABLE", "coverage-kinds"),
        ("TABLE", "coverage-echo"),
        ("TABLE", "coverage-bsl"),
        ("OUT", "coverage-content-load"),
        ("OUT", "coverage-content-checks"),
        ("OUT", "coverage-cf"),
        ("OUT", "coverage-reconcile"),
    ],
}
MARKER = re.compile(r"^<!--(TABLE|OUT) ([a-z0-9-]+)-->$")

# reports/sweep_dp-file.json -> (sweep_summary.txt, "dp-file"): the exit code lives only in the
# summary block, everything else is read from the JSON report itself.
FAMILIES = [("sweep4_", "sweep4_summary.txt"), ("sweep2_", "sweep2_summary.txt"),
            ("sweep3_", "sweep3_summary.txt"), ("sweep_", "sweep_summary.txt"),
            ("skd_q_", "skd_q_summary.txt"), ("skd2_", "skd2_summary.txt")]
EXIT_LINE = re.compile(r"^=== ([a-z0-9-]+): exit (\d+)")
CLI_PREFIX = "python -m p1c.check.sdbl.cli "

# The three SDBL sub-commands p1c exposes, in the order the evidence walks them.
SUBCOMMANDS = ("check", "query", "fields")

VT_HELP_TOKENS = ("границы", "данныеграфика", "движенияссубконто", "задачипоисполнителю",
                  "обороты", "оборотыдткт", "остатки", "остаткииобороты", "срезпервых",
                  "срезпоследних", "субконто", "фактическийпериоддействия")


def load(name):
    return json.loads((REPORTS / name).read_text(encoding="utf-8-sig"))


def family_and_label(json_name):
    for prefix, summary in FAMILIES:
        if json_name.startswith(prefix):
            return summary, json_name[len(prefix):-len(".json")]
    return None, None


def exit_codes(summary_name):
    """label -> exit code, read from the `=== label: exit N` lines of a summary file."""
    return {label: block["exit"] for label, block in summary_blocks(summary_name).items()}


def summary_blocks(summary_name):
    """`label -> {exit: int, key: [values]}` for every indented line of a `=== label: exit N` block.

    The summaries record the command tail under two different spellings (`argv:` in
    reports/sweep_summary.txt and reports/sweep3_summary.txt, `argv tail:` in
    reports/sweep2_summary.txt), and sweep_sdbl4.py records the query under `query source line:`.
    Everything is read per block: the same key appears in several blocks with different values, so a
    file-wide "first match" search would attach the wrong line to a row.
    """
    blocks = {}
    label = None
    for line in (REPORTS / summary_name).read_text(encoding="utf-8-sig").splitlines():
        m = EXIT_LINE.match(line.strip())
        if m:
            label = m.group(1)
            blocks[label] = {"exit": int(m.group(2))}
            continue
        if line.startswith("=== "):
            label = None                       # a title line, not a run block
            continue
        if label is None or not line.strip():
            continue
        key, sep, value = line.strip().partition(":")
        blocks[label].setdefault(key.strip(), []).append(value.strip() if sep else key.strip())
    return blocks


SUB_RE = re.compile(r"python -m p1c\.check\.sdbl\.cli")
TOKEN_RE = re.compile(r"'((?:[^']|'')*)'")


def argv_tokens(summary_name, label):
    """Tokens of a block's recorded command tail, sub-command first; None when not recorded."""
    block = summary_blocks(summary_name).get(label) or {}
    for key in ("argv tail", "argv"):
        if key in block:
            raw = SUB_RE.sub(" ", " ".join(block[key]))
            return [collapse_token(tok) for tok in TOKEN_RE.findall(raw)]
    return None


# Longest first, so `<work>` wins over `<tmp>` inside the same path.  Every recorded path of these
# runs lives under one of these roots; the tables name the root and keep the rest verbatim.  The
# roots are read from `local.paths.json` and from this repository's own directory, so no absolute
# path is typed into a file of the contour (tests/test_corpora.py::NoEnvironmentPathsInRepositoryTest).
_WORK = str(PATHS.get("work") or "")
_TMP = str(pathlib.Path(_WORK).parent) if _WORK else ""
PLACEHOLDERS = sorted([(root, name) for root, name in (
    (_WORK, "<work>"),
    (_TMP, "<tmp>"),
    (str(ROOT), "<repo>"),
    (str(PATHS.get("p1c") or ""), "<p1c>"),
) if root], key=lambda pair: -len(pair[0]))


def collapse_token(token):
    tok = token.strip().strip("'").replace("\\\\", "\\")
    for absolute, placeholder in PLACEHOLDERS:
        tok = re.sub("(?i)" + re.escape(absolute), placeholder, tok, count=1)
    if "\\n" in tok or "\n" in tok:
        head = tok.replace("\\n", " ").split()[0] if tok.replace("\\n", " ").split() else ""
        return "`%s …` (%d симв.)" % (head, len(tok))
    if len(tok) > 46:
        return "%s… (%d симв.)" % (tok[:43], len(tok))
    return tok


def collapse_argv(raw):
    """Tokens of a recorded command tail, in order, with the module prefix removed."""
    raw = SUB_RE.sub(" ", raw)
    return " ".join(collapse_token(tok) for tok in TOKEN_RE.findall(raw))


def stats_cell(stats, keys=None):
    """`stats` dict -> one compact cell; `keys=None` keeps every key the report has."""
    keys = keys or sorted(stats)
    return ", ".join("%s %s" % (k, stats[k]) for k in keys if k in stats) or "—"


def codes_of(report):
    counts = {}
    for r in report.get("results") or []:
        code = r.get("code") or r.get("own_code") or "?"
        counts[code] = counts.get(code, 0) + 1
    return counts


def strip_query_comments(text):
    """Убрать строки комментария запроса (`//`), чтобы `;` считалось только по операторам."""
    kept = []
    for line in text.splitlines():
        if line.strip().startswith("//"):
            continue
        kept.append(line)
    return "\n".join(kept)


def statements_of(text):
    return [part.strip() for part in strip_query_comments(text).split(";") if part.strip()]


def last_statement_head(text):
    parts = statements_of(text)
    return parts[-1].split()[0].upper() if parts else "—"


# ---------------------------------------------------------------- canonical-queries fragments

def canon_tables():
    out = {}
    ours = load("self-canonical-17.json")
    corpora = load("corpora-query-canon-16.json")
    skd = ours["skd_measurements"][0]

    lines = ["| игла канона | шесть корпусов, всего | наш cfg `*.bsl` | наш SKD `<query>` |",
             "|---|---|---|---|"]
    for needle, pair in ours["needles"].items():
        lines.append("| `%s` | %d | %d | %d |" % (
            needle, pair["corpora"], pair["ours_bsl"], skd["needles_in_query"].get(needle, 0)))
    out[("TABLE", "canon-needles")] = lines

    lines = ["| производная мера | шесть корпусов, всего | наш cfg `*.bsl` |", "|---|---|---|"]
    for name, total in corpora["derived_counts"].items():
        lines.append("| `%s` | %d | %d |" % (name, sum(total.values()),
                                             ours["derived_ours"].get(name, 0)))
    for name, total in corpora["derived_text_counts"].items():
        lines.append("| `%s` | %d | %d |" % (name, sum(total.values()),
                                             ours["derived_text_ours"].get(name, 0)))
    out[("TABLE", "canon-derived")] = lines

    vt3 = load("vt3_groupby.json")
    gb = ours["group_by_writings"]
    lines = ["| написание | что считаем | шесть корпусов | наш cfg |", "|---|---|---|---|"]
    lines.append("| клауза `СГРУППИРОВАТЬ ПО` | отдельная строка/часть запроса | %d | %d |" % (
        sum(vt3["clause"].values()), gb["bsl_clause"] + skd["clause_in_query"]))
    dotted_groupby = sum(1 for h in gb["dotted_writings_all"]
                         if h["suffix"] == "сгруппировать")
    lines.append("| dotted `<вид>.<имя>.СГРУППИРОВАТЬ` | суффикс источника данных | %d | %d |" % (
        sum(vt3["dotted"].values()), dotted_groupby))
    lines.append("| склеенное `СГРУППИРОВАТЬПО` | написания без пробела | %d | 0 |" % (
        sum(vt3["glued"].values())))
    out[("TABLE", "groupby-writings")] = lines

    lines = ["| корпус | файл:строка | строка дословно |", "|---|---|---|"]
    for item in vt3["dotted_examples"]:
        corpus, rest = item.split(" | ", 1)
        where, _, text = rest.partition(" | ")
        lines.append("| %s | `%s` | `%s` |" % (corpus, where, text.replace("|", "\\|")))
    out[("TABLE", "dotted-examples")] = lines

    st = load("vt_skd_statements.json")
    lines = ["| мера по текстам `<query>` | шесть корпусов | наш SKD |", "|---|---|---|"]
    for key, label in (("queries_total", "текстов `<query>`"),
                       ("statements_total", "операторов после `;`"),
                       ("texts_one_statement", "текстов с одним оператором"),
                       ("texts_many_statements", "текстов с несколькими операторами"),
                       ("texts_with_group_by_clause", "текстов с клаузой `СГРУППИРОВАТЬ ПО`")):
        lines.append("| %s | %d | %s |" % (label, st[key], skd[key.replace("_total", "")]
                                           if key.replace("_total", "") in skd else "—"))
    out[("TABLE", "skd-statements")] = lines

    lines = ["| форма текста `<query>` | шесть корпусов | наш SKD |", "|---|---|---|"]
    for shape, n in sorted(st["shapes"].items(), key=lambda kv: -kv[1]):
        lines.append("| `%s` | %d | %d |" % (shape, n, skd["shapes"].get(shape, 0)))
    our_last_head = last_statement_head(skd["query_texts"][0] if skd["query_texts"] else "")
    lines.append("| последний оператор текста `<query>` | %s | `%s` |" % (
        ", ".join("%s %d" % (k, v) for k, v in sorted(st["last_statement_head"].items())),
        our_last_head))
    out[("TABLE", "skd-shapes")] = lines

    vocab = load("vt_vocab.json")
    known = sorted(vocab["dot_mode"])
    assert tuple(known) == VT_HELP_TOKENS, "12 токенов DOT_MODE разошлись с замером"
    lines = ["| суффикс после точки в текстах `<query>` | всего в шести корпусах | "
             "суффикс знает лексер p1c (12 токенов `DOT_MODE`)? |", "|---|---|---|"]
    top = sorted(vocab["skd_query"].items(), key=lambda kv: -kv[1])[:18]
    for suffix, n in top:
        lines.append("| `%s` | %d | %s |" % (suffix, n, "да" if suffix in known else "**нет**"))
    out[("TABLE", "vt-suffixes")] = lines

    it = load("itogi_decompose.json")
    lines = ["| написания в шести корпусах | всего вхождений | как отдельное слово | "
             "как начало более длинного имени | как суффикс источника данных | в комментарии |",
             "|---|---|---|---|---|---|"]
    for needle in (".Итоги", ".Движения"):
        comment = (it["comment_split"].get(needle) or {}).get("в комментарии", 0)
        lines.append("| `%s` | %d | %d | %d | %d | %d |" % (
            needle, it["per_needle"][needle],
            it["per_needle"].get(needle + " как слово", 0),
            it["per_needle"].get(needle + " как начало более длинного имени", 0),
            it["per_needle"].get(needle + " как суффикс источника данных", 0), comment))
    lines.append("| с вызовом скобок (`<источник>.<суффикс>(`) | не измерялось для `.Итоги` | 0 для "
                 "`.Движения` (`per_needle`) | — | — | — |")
    vocab = it["suffix_of_source"]
    known = {name: count for name, count in vocab.items() if name in set(VT_HELP_TOKENS)}
    lines.append("| вызов с параметрами (`<источник>.Движения(`) | 0 (`per_needle`) | — | — | — | — |")
    lines.append("| словарь имён, стоящих после точки в тех же строках | %d различных имён, "
                 "%d вхождений; суффиксы из 12 токенов `DOT_MODE`: %s | — | — | — | — |" % (
                     len(vocab), sum(vocab.values()),
                     ", ".join("`%s` %d" % (n, c) for n, c in sorted(known.items(),
                                                                     key=lambda kv: -kv[1]))))
    out[("TABLE", "itogi-decompose")] = lines

    lines = ["| где написание | `<вид>.<имя>.<суффикс>`, как разобрал самомер | строка дословно | "
             "суффикс в 12 токенах `DOT_MODE`? | что это на самом деле |", "|---|---|---|---|---|"]
    for hit in gb["dotted_writings_all"]:
        what = ("дotted-написание виртуальной таблицы" if hit["known_vt_token"] else
                "источник данных, третья часть — не суффикс ВТ" if hit["kind_is_data_source"]
                else "не написание источника данных (шум самомера)")
        lines.append("| `%s` | `%s.%s.%s` | `%s` | %s | %s |" % (
            hit["where"], hit["kind"], hit["name"], hit["suffix_as_written"],
            hit["line"].replace("|", "\\|").strip(),
            "да" if hit["known_vt_token"] else "**нет**", what))
    out[("TABLE", "self-dotted")] = lines
    return out


# ---------------------------------------------------------------- sdbl-controls fragments

def sdbl_report_names():
    """Every sdbl/SKD run report that is a single p1c result (the `_runs`/`_texts` files are indexes)."""
    names = sorted(p.name for p in REPORTS.glob("*.json")
                   if p.name.startswith(("sweep_", "sweep2_", "sweep3_", "sweep4_", "skd_q_",
                                         "skd2_")))
    return [n for n in names if family_and_label(n)[0] and not n.endswith(("_runs.json",
                                                                            "_texts.json"))]


# Families whose driver summary records the exit code and the query text but not the command tail.
# For them the tail is rebuilt from the artifacts (see run_tail_cell) and marked with a dagger.
TEXTS_FILES = {"skd_q_": "skd_q_texts.json", "skd2_": "skd2_texts.json"}


def run_tail_cell(name):
    """Command tail of a run, plus a dagger when the summary did not record it.

    Recorded tails are read from the summary block (`argv:` or `argv tail:`, with the repeated
    `python -m p1c.check.sdbl.cli` prefix of reports/sweep_summary.txt removed).  For the
    `skd_q_*`/`skd2_*`/`sweep4_*` families the pieces are taken from the artifacts themselves: the
    query text from `skd_q_texts.json`/`skd2_texts.json` or from the block's `query source line:`, the
    root from the report's own `context_effective.context.config.root`, the report file from the row's
    own artifact name; the fixed part `--format json --out <файл>` is the shape quoted in prose.
    """
    summary, label = family_and_label(name)
    tokens = argv_tokens(summary, label)
    if tokens:
        return " ".join("`%s`" % tok for tok in tokens)
    rep = load(name)
    root = ((rep.get("context_effective") or {}).get("context") or {}).get("config", {}).get("root")
    text = None
    for prefix, fname in TEXTS_FILES.items():
        if name.startswith(prefix):
            text = (load(fname) or {}).get(label)
            break
    if text is None:
        recorded = summary_blocks(summary).get(label, {}).get("query source line")
        text = recorded[0] if recorded else ""
    cells = ["`query`", "`%s`" % collapse_token(text)]
    if root:
        cells.append("`--root %s`" % collapse_token(root))
    cells.append("`--format json --out <файл этой строки>`†")
    return " ".join(cells)


def sdbl_tables():
    out = {}
    names = sdbl_report_names()
    order = ([n for n in names if n.startswith(("sweep_", "sweep2_", "sweep3_"))]
             + [n for n in names if n.startswith("sweep4_")]
             + [n for n in names if n.startswith("skd_q_")]
             + [n for n in names if n.startswith("skd2_")])

    lines = ["| прогон | хвост команды (пути свёрнуты) | код | находок | `schema_available` | "
             "`context_signature` |", "|---|---|---|---|---|---|"]
    for name in order:
        summary, label = family_and_label(name)
        rep = load(name)
        code = exit_codes(summary).get(label, "?")
        avail = rep.get("schema_available")
        lines.append("| `%s` | %s | %s | %d | %s | `%s…` |" % (
            label, run_tail_cell(name), code,
            len(rep.get("results") or []), "**нет ключа в отчёте**" if avail is None else avail,
            str(rep.get("context_signature"))[:16]))
    out[("TABLE", "sdbl-runs")] = lines

    # Refusals that wrote no report file at all (the code-2 `fields` runs) still have a row here:
    # their exit code lives in the summary, and the absence of a JSON report is itself the finding.
    prefix_of = {summary: prefix for prefix, summary in FAMILIES}
    for summary in ("sweep_summary.txt", "sweep2_summary.txt", "sweep3_summary.txt",
                    "sweep4_summary.txt", "skd_q_summary.txt", "skd2_summary.txt"):
        for label, code in sorted(exit_codes(summary).items()):
            name = "%s%s.json" % (prefix_of[summary], label)
            if (REPORTS / name).is_file():
                continue
            tokens = argv_tokens(summary, label)
            tail = " ".join("`%s`" % tok for tok in tokens) if tokens else "(хвост не записан)"
            lines.append("| `%s` | %s | %s | — | **отчёт JSON не записан** | — |" % (
                label, tail, code))
    out[("TABLE", "sdbl-runs")] = lines

    lines = ["| прогон | код находки | серьёзность | строка | файл | текст находки дословно |",
             "|---|---|---|---|---|---|"]
    for name in order:
        summary, label = family_and_label(name)
        for r in load(name).get("results") or []:
            lines.append("| `%s` | `%s` | %s | %s | `%s` | %s |" % (
                label, r.get("code"), r.get("severity"), r.get("line"),
                str(r.get("file") or r.get("source") or "").replace("\\", "/"),
                str(r.get("text") or "").replace("|", "\\|")))
    out[("TABLE", "sdbl-findings")] = lines

    lines = ["| прогон | `config.root` в отчёте | как передан | `stats` | `context_signature` |",
             "|---|---|---|---|---|"]
    for name in [n for n in names if n.startswith("sweep3_")] + ["sweep_whole-cfg.json",
                                                                  "sweep_root-is-src.json",
                                                                  "sweep_no-model.json",
                                                                  "sweep2_no-root.json"]:
        summary, label = family_and_label(name)
        rep = load(name)
        # sweep_sdbl3.py records the root exactly as p1c stored it; the other families do not, so the
        # value comes from the report's own `context_effective`.
        recorded = summary_blocks(summary).get(label, {}).get("config.root as recorded")
        root = recorded[0] if recorded else (((rep.get("context_effective") or {})
                                              .get("context") or {}).get("config") or {}).get("root")
        how = ("`--root` не передан" if not root else
               "относительный путь" if ":" not in root else "абсолютный путь")
        lines.append("| `%s` | %s | %s | %s | `%s…` |" % (
            label, "`%s`" % collapse_token(root) if root else "(`--root` не передан)", how,
            stats_cell(rep.get("stats") or {}), str(rep.get("context_signature"))[:16]))
    out[("TABLE", "sdbl-signature")] = lines

    # Every `fields` run: the exit code and the argv shape come from the summary block, the report
    # file exists only when p1c actually wrote one (the code-2 refusals write nothing).
    lines = ["| прогон команды `fields` | аргумент после `fields` | код | отчёт JSON |",
             "|---|---|---|---|"]
    for summary in ("sweep_summary.txt", "sweep2_summary.txt"):
        for label, code in sorted(exit_codes(summary).items()):
            if not label.startswith("fields"):
                continue
            name = "%s.json" % (label if summary == "sweep2_summary.txt"
                                else "sweep_" + label)
            rep = load(name) if (REPORTS / name).is_file() else None
            tokens = argv_tokens(summary, label) or []
            arg = tokens[1] if len(tokens) > 1 else "(аргумент не записан)"
            lines.append("| `%s` | %s | %s | %s |" % (
                label, "`%s`" % arg.split("/")[-1].split("\\")[-1], code,
                "есть: %s" % ", ".join(sorted(rep)) if rep else "**не записан**"))
    out[("TABLE", "sdbl-fields")] = lines

    lines = ["| контроль | строка запроса дословно | код | находки | `stats` |", "|---|---|---|---|---|"]
    blocks = summary_blocks("sweep4_summary.txt")
    for name in ("sweep4_skd-groupedby-vt.json", "sweep4_skd-totals-vt.json",
                 "sweep4_movements-vt.json", "sweep4_slice-vt.json"):
        summary, label = family_and_label(name)
        rep = load(name)
        recorded = blocks.get(label, {}).get("query source line") or [""]
        source = recorded[0]
        lines.append("| `%s` | `%s` | %s | %s | %s |" % (
            label, source, exit_codes(summary).get(label, "?"),
            ", ".join("%s %s" % (k, v) for k, v in codes_of(rep).items()) or "0",
            stats_cell(rep.get("stats") or {})))
    out[("TABLE", "sdbl-vt-controls")] = lines

    lines = ["| контроль | семейство прогонов | длина текста запроса | код | находки | "
             "коды находок |", "|---|---|---|---|---|---|"]
    for name in ("skd_q_skd-exact.json", "skd_q_min-groupedby.json", "skd_q_min-totals.json",
                 "skd_q_clause-groupby.json", "skd_q_no-groupby.json", "skd_q_bogus-field.json",
                 "skd_q_bogus-suffix.json", "skd2_new-exact.json", "skd2_new-temp-only.json",
                 "skd2_new-join-temp.json", "skd2_new-bogus-temp-table.json",
                 "skd2_new-bogus-temp-field.json"):
        if not (REPORTS / name).is_file():
            continue
        summary, label = family_and_label(name)
        rep = load(name)
        codes = codes_of(rep)
        family = ("`skd_q_*` (прежний текст SKD и его варианты)" if name.startswith("skd_q_")
                  else "`skd2_*` (переписанный текст SKD и его варианты)")
        texts = load("skd_q_texts.json" if name.startswith("skd_q_") else "skd2_texts.json")
        lines.append("| `%s` | %s | %d | %s | %d | %s |" % (
            label, family, len(texts.get(label) or ""),
            exit_codes(summary).get(label, "?"), len(rep.get("results") or []),
            ", ".join("%s %s" % (k, v) for k, v in codes.items()) or "—"))
    out[("TABLE", "skd-old-vs-new")] = lines

    # The control texts verbatim: the whole point of these runs is the exact spelling handed to
    # `p1c-check-sdbl query`, so the fragments are quoted instead of summarised in prose.
    lines = []
    for fname in ("skd_q_texts.json", "skd2_texts.json"):
        for label, text in load(fname).items():
            lines.append("=== %s: %d симв." % (label, len(text)))
            lines.extend(text.rstrip().splitlines())
            lines.append("")
    out[("OUT", "skd-texts")] = lines
    return out


# ---------------------------------------------------------------- epf-roundtrip fragments

def epf_tables():
    out = {}
    rep = load("epf-16-roundtrip.json")
    lines = ["| шаг | команда | аргументы | код | сек | `/Out`, байт | строка `/Out` о времени операции |",
             "|---|---|---|---|---|---|---|"]
    for s in rep["steps"]:
        argv = s["argv"]
        tail = argv[argv.index("/DumpExternalDataProcessorOrReportToFiles"):] if any(
            "DumpExternalDataProcessorOrReportToFiles" in a for a in argv) else \
            argv[argv.index("/LoadExternalDataProcessorOrReportFromFiles"):]
        cmd, args = tail[0], [collapse_token(a) for a in tail[1:]]
        times = [ln.strip() for ln in s.get("out_lines") or [] if "Суммарное время" in ln]
        lines.append("| `%s` | `%s` | %s | %s | %.1f | %d | %s |" % (
            s["step"], cmd, ", ".join("`%s`" % a for a in args), s["code"], s["seconds"],
            s["out_bytes"], "; ".join("`%s`" % t for t in times) or "нет такой строки"))
    out[("TABLE", "epf-steps")] = lines

    lines = ["| шаг | файл выгрузки | байт | sha1 |", "|---|---|---|---|"]
    for s in rep["steps"]:
        for f in s["produced"]:
            lines.append("| `%s` | `%s` | %d | `%s` |" % (s["step"], f["path"], f["bytes"],
                                                           f["sha1"]))
    lines.append("| исходный `.epf` | `ГПН_КонсольЗаданий.epf` | %d | — |" % rep["epf_source_bytes"])
    out[("TABLE", "epf-files")] = lines

    pos = rep["snapshot_positions"]
    lines = ["| позиция аргумента (0 = первый после `/DisableStartupDialogs`) | что стоит |",
             "|---|---|"]
    for i in range(6):
        what = []
        if i in pos["dump_at"]:
            what.append("каталог выгрузки")
        if i in pos["root_at"]:
            what.append("корневой файл `.xml`")
        lines.append("| %d | %s |" % (i, ", ".join(what) or "—"))
    lines.append("| вывод | `dump_before_first_root` = **%s** |" % pos["dump_before_first_root"])
    out[("TABLE", "epf-positions")] = lines

    lines = ["| что сравниваем | `epf-15-roundtrip.json` | `epf-16-roundtrip.json` |", "|---|---|---|"]
    old = load("epf-15-roundtrip.json")
    old_pos = old.get("snapshot_positions") or {}
    lines.append("| снимок файлов шага взят из | каталога, который шаг **использует** как вход "
                 "(ошибочно) | каталога `produced_dir`, который шаг **произвёл** |")
    lines.append("| `dump_at` | `%s` | `%s` |" % (old_pos.get("dump_at"), pos["dump_at"]))
    lines.append("| `root_at` | `%s` | `%s` |" % (old_pos.get("root_at"), pos["root_at"]))
    lines.append("| `roundtrip_closed` | %s | %s |" % (old.get("roundtrip_closed"),
                                                        rep["roundtrip_closed"]))
    old_steps = {s["step"]: s for s in old["steps"]}
    for step in ("load-root-dir", "load-root-target"):
        o, n = old_steps.get(step, {}), [s for s in rep["steps"] if s["step"] == step][0]
        lines.append("| `%s`: sha1 произведённого `.epf` | `%s` | `%s` |" % (
            step, (o.get("produced") or [{}])[0].get("sha1"), (n["produced"] or [{}])[0].get("sha1")))
    out[("TABLE", "epf-snapshot-fix")] = lines
    return out


def coverage_bsl_table():
    """The findings of `p1c.check.bsl.cli check <cfg> --root <dump>`, one row per finding.

    Codes, texts, lines and groundings are taken from the run report `reports/toolcov_bsl-check-cfg.json`
    (`results` and `summary`); nothing is re-derived here.  The source line is added only so that a
    reader can see what the finding points at: the line is read from the cfg file the report names,
    and the report's `file` key is shortened to the relative path the gate counts.
    """
    name = "toolcov_bsl-check-cfg.json"
    if not (REPORTS / name).is_file():
        return {}
    report = load(name)
    cfg_root = str(PATHS.get("cfg") or "").replace("\\", "/").rstrip("/")
    lines = ["| код | текст находки | строка | файл cfg | строка исходника | grounding |",
             "|---|---|---|---|---|---|"]
    for finding in report.get("results", []):
        raw = str(finding.get("file", "")).replace("\\", "/")
        rel = raw[len(cfg_root) + 1:] if cfg_root and raw.startswith(cfg_root + "/") else raw
        source = ""
        if cfg_root:
            try:
                source = (pathlib.Path(cfg_root) / rel).read_text(encoding="utf-8-sig") \
                    .splitlines()[int(finding.get("line", 0)) - 1].strip()
            except (OSError, IndexError, ValueError):
                source = "<нет такой строки>"
        lines.append("| `%s` | %s | %d | `%s` | `%s` | %s |" % (
            finding.get("code", ""), finding.get("text", ""), int(finding.get("line", 0)),
            rel, source.replace("|", "\\|"), finding.get("grounding", "")))
    return {("TABLE", "coverage-bsl"): lines}


def coverage_echo_table():
    """Where a layout name appears in an instrument report only as a piece of a file path.

    Both columns are read from `reports/toolcov_runs.json`: `matrix_by_kind[].tools_name_echo_only`
    says which tools carry the name as a path fragment, and the `name_hits_path_echo_only` lists of
    the individual runs say which name it was and in which run.  Nothing is re-derived here.
    """
    if not COVERAGE_RUNS.is_file():
        return {}
    data = json.loads(COVERAGE_RUNS.read_text(encoding="utf-8-sig"))
    echo_names = {}
    for run in data.get("runs", []):
        for kind, hits in (run.get("hits") or {}).items():
            for name in hits.get("name_hits_path_echo_only") or []:
                echo_names.setdefault(kind, []).append("%s (`%s`)" % (cell(name), run["label"]))
    lines = ["| класс макета | файлов cfg | инструменты, где имя сущности только часть пути | "
             "эхо-имя (прогон) |", "|---|---|---|---|"]
    for entry in sorted(data.get("matrix_by_kind") or [], key=lambda item: item["kind"]):
        names = echo_names.get(entry["kind"]) or []
        if not entry["tools_name_echo_only"] and not names:
            continue
        lines.append("| `%s` | %d | %s | %s |" % (
            entry["kind"], entry["files"], name_list(entry["tools_name_echo_only"]),
            ", ".join(names) or "(нет таких имён)"))
    return {("TABLE", "coverage-echo"): lines}


def coverage_tables():
    """The tool coverage matrices, taken from the file `probe/tool_coverage.py` wrote.

    No counting happens here: `probe/tool_coverage.py` already ran the p1c CLIs over our own layout,
    and recomputing those numbers in this script would be a second generator for one measurement.
    The tables are carried verbatim, which is also what makes `--check` meaningful for them.
    """
    out = coverage_bsl_table()
    out.update(coverage_echo_table())
    if not COVERAGE_MATRIX.is_file():
        return out
    current = None
    for line in COVERAGE_MATRIX.read_text(encoding="utf-8-sig").splitlines():
        match = MARKER.match(line.strip())
        if match:
            current = (match.group(1), match.group(2))
            out.setdefault(current, [])
            continue
        if current and line.strip():
            out[current].append(line.rstrip())
    return {key: lines for key, lines in out.items() if lines}


# The content blocks quote what a tool actually returned for our own layout: every line below is read
# from a key of reports/toolcov_<label>.json, so the document quotes a report and not a restatement.


def collapse_line(line: str) -> str:
    """Absolute roots recorded inside the run reports -> the placeholders the documents use."""
    for absolute, placeholder in PLACEHOLDERS:
        line = re.sub("(?i)" + r"\\{1,2}".join(re.escape(part) for part in absolute.split("\\")),
                      placeholder, line)
    return line


def coverage_runs() -> dict:
    """`label -> the recorded run`: exit code, command tail, console text, produced report file."""
    if not COVERAGE_RUNS.is_file():
        return {}
    data = json.loads(COVERAGE_RUNS.read_text(encoding="utf-8-sig"))
    return {run["label"]: run for run in data.get("runs", [])}


def coverage_report(label):
    """The JSON report one coverage run wrote; None when the run produced no report at all."""
    path = REPORTS / ("toolcov_%s.json" % label)
    return json.loads(path.read_text(encoding="utf-8-sig")) if path.is_file() else None


def cell(value) -> str:
    """One report value as a cell: names in backticks, change groups as `+N/~N/-N`, collections by size."""
    if isinstance(value, str):
        return "`%s`" % value if value else "(пусто)"
    if isinstance(value, (dict, list)) and not value:
        return "0 (пусто)"
    if isinstance(value, dict) and set(value) <= {"added", "changed", "removed"}:
        return "+%d/~%d/-%d" % (len(value.get("added") or []), len(value.get("changed") or []),
                                len(value.get("removed") or []))
    if isinstance(value, (dict, list)):
        return str(len(value))
    return json.dumps(value, ensure_ascii=False)


def names_of_items(items) -> str:
    """Backticked names of a report list, in the order the report holds them."""
    out = []
    for item in items or []:
        name = item.get("name") if isinstance(item, dict) else item
        out.append("`%s`" % (name if name is not None else "?"))
    return ", ".join(out)


def pair_lines(prefix: str, mapping: dict) -> list:
    """`prefix.key value` lines for a flat report dict; sub-dicts are rendered inline."""
    lines = []
    for key in sorted(mapping):
        value = mapping[key]
        if isinstance(value, dict) and not set(value) <= {"added", "changed", "removed"}:
            lines.append("  %s.%s: %s" % (prefix, key, ", ".join(
                "%s %s" % (k, v) for k, v in sorted(value.items())) or "(пусто)"))
        else:
            lines.append("  %s.%s %s" % (prefix, key, cell(value)))
    return lines


def coverage_report_lines(report) -> list:
    """Counters a run wrote about itself: `stats`, the finding `summary`, the skipped rules."""
    lines = []
    for key in ("stats", "summary"):
        if isinstance(report.get(key), dict):
            lines += pair_lines(key, report[key])
    if report.get("skipped_rules"):
        lines.append("  skipped_rules: " + ", ".join(
            "%s (%s)" % (cell(rule.get("id")), cell(rule.get("skipped_reason")))
            for rule in report["skipped_rules"]))
    if "schema_available" in report:
        lines.append("  schema_available %s" % cell(report["schema_available"]))
    return lines


def coverage_model_lines(report) -> list:
    """`p1c.load model`: every section of the model it built, with the names each section holds."""
    lines = []
    for key in sorted(report.get("model") or {}):
        value = report["model"][key]
        names = (", ".join("`%s`" % name for name in sorted(value)) if isinstance(value, dict)
                 else names_of_items(value))
        lines.append("  model.%s = %d%s" % (key, len(value), ": " + names if names else ""))
    return lines


def coverage_forms_lines(report) -> list:
    """`p1c.load forms`: one line per form the reader found in the layout."""
    lines = ["  forms %s, count %s" % (cell(report.get("forms")), cell(report.get("count")))]
    for form in report.get("forms") or []:
        lines.append("  form %s: kind %s, object %s, attributes %d, items %d, events %d, commands %d" % (
            cell(form.get("name")), cell(form.get("kind")), cell(form.get("object")),
            len(form.get("attributes") or []), len(form.get("items") or []),
            len(form.get("events") or []), len(form.get("commands") or [])))
    return lines


def coverage_object_lines(report) -> list:
    """`p1c.load object <объект>`: the object header plus the names of every collection it lists."""
    obj = report.get("object") or {}
    lines = pair_lines("object", {key: value for key, value in obj.items()})
    for key, value in sorted(obj.items()):
        if isinstance(value, list) and value:
            lines.append("  object.%s (%d): %s" % (key, len(value), names_of_items(value)))
    return lines


def coverage_qualifiers_lines(report) -> list:
    """`p1c.load qualifiers`: the qualifiers the reader resolved, each pinned to its object."""
    quals = report.get("qualifiers") or []
    lines = ["  qualifiers %s, count %s" % (cell(report.get("qualifiers")), cell(report.get("count")))]
    lines += ["  qualifier %s.%s: type %s" % (cell(qual.get("object")), cell(qual.get("name")),
                                              cell(qual.get("type"))) for qual in quals]
    return lines


def coverage_diff_lines(report) -> list:
    """`p1c.diff model`: per-section counts, then the chain of names that actually differ."""
    changes = report.get("changes") or {}
    lines = ["  changes.%s %s" % (key, cell(changes[key])) for key in sorted(changes)
             if isinstance(changes[key], dict) and "changed" in changes[key]]
    return lines + coverage_diff_trail(changes, 1)


def coverage_diff_trail(changes: dict, depth: int) -> list:
    """The `changed` entries below a `changes` group, nested the way the report nests them."""
    lines = []
    for key in sorted(k for k in changes if isinstance(changes[k], dict) and "changed" in changes[k]):
        for entry in changes[key].get("changed") or []:
            inner = entry.get("changes") or {}
            counts = ", ".join("%s %s" % (sub, cell(inner[sub])) for sub in sorted(inner)
                               if isinstance(inner.get(sub), dict) and "changed" in inner[sub])
            lines.append("  " * depth + "- %s.%s%s%s" % (
                key, entry.get("name", ""), " — " if counts else "", counts))
            lines += coverage_diff_trail(inner, depth + 1)
    return lines


def coverage_graph_lines(report) -> list:
    """`p1c.graph build` / `p1c.graph roots`: only what the `stats` counters do not already say."""
    lines = []
    fan = report.get("top_fan_out") or []
    if fan:
        lines.append("  top_fan_out %d: %s … %s" % (
            len(fan), fan_cell(fan[0]), fan_cell(fan[-1])))
    roots = report.get("roots") or []
    if roots:
        lines.append("  roots %d" % len(roots))
        for first in range(0, len(roots), 5):
            lines.append("  roots[%d:%d]: %s" % (first, min(first + 5, len(roots)), ", ".join(
                "`%s`" % root for root in roots[first:first + 5])))
    return lines


def fan_cell(entry) -> str:
    return "%s calls %s" % (cell(entry.get("id")), cell(entry.get("calls")))


def coverage_metrics_lines(report) -> list:
    """`p1c.metrics top`: the sort key it used and the first and last entries of the ranking."""
    top = report.get("top") or []
    lines = ["  by %s, top %d, source %s" % (
        cell(report.get("by")), len(top), cell(report.get("source")))]
    for entry in top[:1] + top[-1:]:
        lines.append("  top %s (%s:%s): complexity %s, statements %s, code_lines %s, max_nesting %s, "
                     "kind_of_module %s, annotation %s, exported %s" % (
                         cell(entry.get("name")), cell(entry.get("module")), cell(entry.get("line")),
                         cell(entry.get("complexity")), cell(entry.get("statements")),
                         cell(entry.get("code_lines")), cell(entry.get("max_nesting")),
                         cell(entry.get("kind_of_module")), cell(entry.get("annotation")),
                         cell(entry.get("exported"))))
    return lines


def coverage_events_lines(report) -> list:
    """`check.forms events`: the page whose event list the tool returns, and its full name list."""
    events = report.get("events") or {}
    lines = ["  page %s, count %s, events %d" % (
        cell(report.get("page")), cell(report.get("count")), len(events)),
        "  events: " + ", ".join("`%s`" % name for name in sorted(events))]
    for name in ("ActivationProcessing", "BeforeClose", "OnCreateAtServer"):
        if name in events:
            event = events[name]
            lines.append("  event %s: min_args %s, max_args %s, params %s, availability %s" % (
                cell(name), cell(event.get("min_args")), cell(event.get("max_args")),
                names_of_items([param for param in event.get("params") or []]),
                names_of_items([item for item in event.get("availability") or []])))
    absent = [name for name in ("AfterWrite", "BeforeWrite") if name not in events]
    if absent:
        lines.append("  absent from this list: " + ", ".join("`%s`" % name for name in absent))
    return lines


def coverage_form_lines(report) -> list:
    """`check.forms form`: the form header, its attributes with qualifiers, its items and events."""
    form = report.get("form") or {}
    if not form:
        return []
    lines = pair_lines("form", {key: value for key, value in form.items() if key != "events"})
    for attr in form.get("attributes") or []:
        lines.append("  form.attribute %s: type %s, qualifier %s" % (
            cell(attr.get("name")), cell(attr.get("type")),
            json.dumps(attr.get("qualifier"), ensure_ascii=False, sort_keys=True)))
    for item in form.get("items") or []:
        lines.append("  form.item %s: kind %s, data_path %s, parent %s, readonly %s" % (
            cell(item.get("name")), cell(item.get("kind")), cell(item.get("data_path")),
            cell(item.get("parent")), cell(item.get("readonly"))))
    for event in form.get("events") or []:
        lines.append("  form.event %s: handler %s, scope %s, kind %s, owner %s" % (
            cell(event.get("name")), cell(event.get("handler")), cell(event.get("scope")),
            cell(event.get("kind")), cell(event.get("owner"))))
    for command in form.get("commands") or []:
        lines.append("  form.command %s: action %s, standard %s" % (
            cell(command.get("name")), cell(command.get("action")), cell(command.get("standard"))))
    return lines


# Which detail lines each coverage run adds on top of the generic `stats`/`summary` block.
COVERAGE_RUN_DETAIL = {
    "load-model-dump": coverage_model_lines,
    "load-model-cfg": coverage_model_lines,
    "load-forms-dump": coverage_forms_lines,
    "load-object-catalog": coverage_object_lines,
    "load-qualifiers-dump": coverage_qualifiers_lines,
    "diff-model-cfg-dump": coverage_diff_lines,
    "graph-build-dump": coverage_graph_lines,
    "graph-roots-dump": coverage_graph_lines,
    "metrics-top-dump": coverage_metrics_lines,
    "forms-events-dump": coverage_events_lines,
    "forms-form-element": coverage_form_lines,
}


def coverage_run_block(label, runs) -> list:
    """One run of the coverage matrix: the recorded exit code, then the keys and counters of its report."""
    run = runs.get(label) or {}
    report = coverage_report(label)
    lines = ["%s  (exit %s%s)" % (label, run.get("code", "?"),
                                  "" if report is not None else ", нет JSON-отчёта")]
    if report is None:
        if run.get("argv"):
            lines.append("  argv: %s" % run["argv"])
        lines += ["  stderr: %s" % line.strip() for line in (run.get("stderr_text") or "").splitlines()
                  if line.strip()]
        return lines
    keys = [key for key in sorted(report) if key not in SKIP_REPORT_KEYS]
    lines.append("  keys: " + ", ".join("`%s`" % key for key in keys))
    lines += coverage_report_lines(report)
    detail = COVERAGE_RUN_DETAIL.get(label)
    if detail:
        lines += detail(report)
    return lines


def coverage_cf_lines(runs) -> list:
    """`p1c.cf info <каталог конфигурации>`: the frames of p1c itself and the error line it ends with.

    The traceback quotes paths as a Python repr, where every separator is doubled; the doubled
    separators are folded back to single ones here, so the document shows one path shape and
    `collapse_line` can shorten it.
    """
    run = runs.get(CF_RUN) or {}
    lines = ["%s  (exit %s, нет JSON-отчёта)" % (CF_RUN, run.get("code", "?"))]
    if run.get("argv"):
        lines.append("  argv: %s" % run["argv"])
    for raw in (run.get("stderr_text") or "").splitlines():
        stripped = raw.strip()
        if not (stripped and ("p1c" in stripped or "PermissionError" in stripped
                              or stripped.startswith("Traceback"))):
            continue
        lines.append("  " + BACKSLASH.join(part for part in stripped.split(BACKSLASH * 2)))
    return lines


def coverage_content_fragments() -> dict:
    """The three `OUT` blocks docs/evidence/tool-coverage.md quotes, produced from the run artifacts."""
    runs = coverage_runs()
    if not runs:
        return {}
    out = {}
    for name, labels in (("coverage-content-load", COVERAGE_LOAD_RUNS),
                         ("coverage-content-checks", COVERAGE_CHECK_RUNS)):
        lines = []
        for label in labels:
            lines += coverage_run_block(label, runs)
            lines.append("")
        out[("OUT", name)] = [collapse_line(line) for line in lines]
    out[("OUT", "coverage-cf")] = [collapse_line(line) for line in coverage_cf_lines(runs)]
    return out


def name_list(items) -> str:
    """Backticked names of a flat list of strings, in the order the report holds them."""
    return ", ".join("`%s`" % item for item in items or [])


def coverage_reconcile_lines() -> list:
    """The reconciliation keys of reports/toolcov_runs.json, as lines.

    These are the counters that tie the matrix to the gate: the class counts the layout reader of
    `p1c.load model` produced for our own layout, the same counts the gate measured independently
    from the file layout, and the three partitions of the 22 layout classes by what a tool sees.
    """
    data = json.loads(COVERAGE_RUNS.read_text(encoding="utf-8-sig"))
    runs = data.get("runs") or []
    match = data.get("layout_counts_match") or {}
    out = ["kinds_total %s" % cell(data.get("kinds_total")),
           "gate_artifact %s" % cell(data.get("gate_artifact")),
           "tools %d: %s" % (len(data.get("tools") or []), name_list(data.get("tools"))),
           "layout_counts_match: want %d classes, got %d classes, mismatch %s" % (
               len(match.get("want") or {}), len(match.get("got") or {}), cell(match.get("mismatch"))),
           "gate_tool_counts_source %d classes: %s" % (
               len(data.get("gate_tool_counts_source") or {}), ", ".join(
                   "%s %s" % (kind, count) for kind, count in
                   sorted((data.get("gate_tool_counts_source") or {}).items()))),
           "gate_tool_blind_kinds %d: %s" % (
               len(data.get("gate_tool_blind_kinds") or []), name_list(data.get("gate_tool_blind_kinds")))
           ]
    for label in sorted(data.get("reader_vs_gate") or {}):
        entry = data["reader_vs_gate"][label]
        out.append("reader_vs_gate.%s: equal_to_gate_tool_counts_source %s, diff_reader_vs_gate %s" % (
            label, cell(entry.get("equal_to_gate_tool_counts_source")),
            cell(entry.get("diff_reader_vs_gate"))))
    for key, prefix in (("kinds_seen_by_path", "path"), ("kinds_seen_by_name_only", "name only"),
                        ("kinds_seen_by_no_tool", "no tool")):
        out.append("kinds seen by %s %d: %s" % (prefix, len(data.get(key) or []), name_list(data.get(key))))
    out.append("runs %d, sum of stdout_chars %d" % (
        len(runs), sum(int(run.get("stdout_chars") or 0) for run in runs)))
    with_context = [run["label"] for run in runs
                    if any(line.strip().startswith(CONTEXT_LINE)
                           for line in (run.get("stderr_text") or "").splitlines())]
    context_texts = {line.strip() for run in runs
                     for line in (run.get("stderr_text") or "").splitlines()
                     if line.strip().startswith(CONTEXT_LINE)}
    out.append("runs logging the context line %d of %d" % (len(with_context), len(runs)))
    out += ["  %s" % text for text in sorted(context_texts)]
    out.append("  runs without it: " + ", ".join(
        "`%s`" % run["label"] for run in runs if run["label"] not in with_context))
    return [collapse_line(line) for line in out]


def fragments():
    fr = {}
    fr.update(canon_tables())
    fr.update(sdbl_tables())
    fr.update(epf_tables())
    fr.update(coverage_tables())
    fr.update(coverage_content_fragments())
    fr[("OUT", "coverage-reconcile")] = coverage_reconcile_lines()
    return fr


# An unescaped pipe is a column boundary; an escaped `\|` inside a cell is text.
PIPES = re.compile(r"(?<!\\)\|")


def table_shape_problems(fr):
    """Structural check of every generated table fragment: same column count in all its rows.

    A markdown table whose separator row has fewer cells than the header silently renders as text,
    which is how a table turns into an unreadable wall of pipes.  The separator `|---|---|` is the
    authority for the column count, and the header must match it.
    """
    problems = []
    for key, lines in fr.items():
        if key[0] != "TABLE":
            continue
        rows = [ln for ln in lines if ln.startswith("|")]
        if len(rows) < 2:
            problems.append((key, "fragment has fewer than two table rows"))
            continue
        sep = rows[1]
        if not re.match(r"^\|(-+\|)+$", sep):
            problems.append((key, "second row is not a separator: %s" % sep))
            continue
        want = len(PIPES.findall(sep)) - 1
        for ln in rows:
            if len(PIPES.findall(ln)) - 1 != want:
                problems.append((key, "%d columns expected, row: %s" % (want, ln)))
    return problems


def render(out_path):
    fr = fragments()
    lines = []
    for names in IN_DOCUMENT.values():
        for key in names:
            lines.append("<!--%s %s-->" % key)
            lines += fr[key]
            lines.append("")
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return fr


def check(out_path):
    fr = render(out_path)
    problems = [("table shape", key[1], detail) for key, detail in table_shape_problems(fr)]
    counted = 0
    for doc_name, names in IN_DOCUMENT.items():
        path = ROOT / "docs" / "evidence" / doc_name
        if not path.is_file():
            problems.append(("document missing", doc_name, ""))
            continue
        doc_lines = {line.strip() for line in path.read_text(encoding="utf-8-sig").splitlines()}
        for key in names:
            for line in fr.get(key, []):
                counted += 1
                if line.strip() not in doc_lines:
                    problems.append((doc_name, key, line))
    unused = sorted(set(fr) - {k for names in IN_DOCUMENT.values() for k in names})
    print("fragments:", len(fr), "checked lines:", counted)
    print("unused fragments:", ", ".join("%s %s" % kv for kv in unused) or "none")
    if problems:
        for doc_name, key, line in problems[:40]:
            print("  MISSING in %s [%s %s]: %s" % (doc_name, key[:1], key[1] if key[1] else "", line))
        return 1
    print("all checked lines present verbatim in the evidence documents")
    return 0


def inject(doc_path, out_path):
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
    doc_path.write_bytes(("\ufeff" if bom else "").encode("utf-8")
                         + body.join(lines).encode("utf-8") + body.encode("utf-8"))
    print("injected", len(used), "markers, missing fragments:", missing or "none")
    print("crlf", crlf, "bom", bom, "lines", len(lines))
    return 1 if missing else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(REPORTS / "query-tables.md"))
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
    for (kind, name), lines in sorted(fr.items()):
        print("  %s %-18s lines %d" % (kind, name, len(lines)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
