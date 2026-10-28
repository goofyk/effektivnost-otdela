"""Лестница `p1c.check.forms events --kind <вид>` (замер, только чтение, платформу не запускает).

Флаг `--kind` в справке описан как «вид объекта метаданных для событий уровня формы», но список
допустимых значений справка не перечисляет, а расположение флага в командной строке не измерено:
`p1c.check.forms` объявляет его на уровне главного аргументпарсера (`p1c/src/p1c/check/forms/cli.py`),
поэтому замеряют обе формы записи — флаг после подкоманды и флаг перед ней.

Замер делает три вещи:
- прогоняет подкоманду `events` без флага и с каждым видом из справочника `OBJECT_PAGE`
  (14 видов) плюс вид, которого в справочнике нет, — чтобы увидеть, проверяет ли инструмент
  переданное имя;
- считает, какие имена событий добавляет и убирает каждый вид относительно списка без флага;
- отдельно читает сам справочник `EVENT_SIGNATURES` (`pages_total`, число страниц с именем вида
  `… form extension`, число событий на странице вида, признак управляемого приложения по
  harvested-доступности), потому что именно из него CLI берёт список событий.

Выход: `reports/forms-events-kind-19.json`, `reports/forms-events-kind-19.txt`.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
MODULE = "p1c.check.forms.cli"
NO_SUCH_KIND = "zzz-netakogo-vida"
PLACE_BEFORE = ("catalog", "document", "report", "data_processor", "accumulation_register")


def _run(py, argv_tail, env) -> dict:
    """Один прогон CLI: код, страница, список имён событий, присутствие событий записи."""
    proc = subprocess.run([py, "-m", MODULE] + argv_tail, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", env=env)
    out = proc.stdout or ""
    try:
        rep = json.loads(out)
    except Exception:
        rep = {}
    if not isinstance(rep, dict):
        rep = {}
    ev = rep.get("events")
    if isinstance(ev, dict):
        names = sorted(str(key) for key in ev.keys())
    elif isinstance(ev, list):
        named = sorted({(e.get("event") or e.get("name")) for e in ev if isinstance(e, dict)} - {None})
        names = named or sorted(str(e) for e in ev)
    else:
        names = []
    return {"code": proc.returncode, "page": rep.get("page"), "count": rep.get("count"),
            "events": names, "AfterWrite": "AfterWrite" in names, "BeforeWrite": "BeforeWrite" in names,
            "stdout_chars": len(out), "stderr_len": len(proc.stderr or ""),
            "stderr_tail": (proc.stderr or "").strip()[-200:]}


def _reference(checks) -> dict:
    """Справочник, из которого CLI берёт события: прочитан напрямую из `p1c`."""
    sigs = checks.EVENT_SIGNATURES
    ext_pages = sorted(page for page in sigs if "form extension" in page.lower())
    mapping = {}
    for kind, page in sorted(checks.OBJECT_PAGE.items()):
        names = checks.event_names(kind)
        mapping[kind] = {"page": page, "known_page_in_data": page in sigs,
                         "data_events": len(sigs.get(page, {})),
                         "managed_page": checks.is_managed_page(page),
                         "event_names_len": len(names),
                         "AfterWrite": "AfterWrite" in names, "BeforeWrite": "BeforeWrite" in names}
    return {"data_source": "p1c/src/p1c/data/platform_arities.py::EVENT_SIGNATURES",
            "pages_total": len(sigs), "form_extension_pages": len(ext_pages),
            "form_extension_page_names": ext_pages, "FORM_PAGE": checks.FORM_PAGE,
            "base_event_names_len": len(checks.event_names("")), "kind_mapping": mapping}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=None)
    ap.add_argument("--out", default=str(REPO / "reports" / "forms-events-kind-19.json"))
    args = ap.parse_args(argv)
    local = json.loads((REPO / "local.paths.json").read_text("utf-8-sig"))
    root = args.root or local["dump"]
    py = sys.executable
    env = dict(os.environ)
    env["PYTHONPATH"] = local["p1c"]
    env["PYTHONIOENCODING"] = "utf-8"

    sys.path.insert(0, local["p1c"] + "/src")
    from p1c.check.forms import checks  # noqa: E402

    ref = _reference(checks)
    kinds = sorted(checks.OBJECT_PAGE) + [NO_SUCH_KIND]

    base = _run(py, ["events", root], env)
    runs = [{"kind": "", **base}]
    for kind in kinds:
        runs.append({"kind": kind, **_run(py, ["events", root, "--kind", kind], env)})
    placed = []
    for kind in PLACE_BEFORE:
        placed.append({"kind": kind, "placement": "перед подкомандой",
                       **_run(py, ["--kind", kind, "events", root], env)})

    base_names = set(base["events"])
    lines = ["# `p1c.check.forms events --kind <вид>` (только чтение, без платформы)", "",
             "корень выгрузки: `<dump>`; модуль: `%s`; флаг `--kind` объявлен на уровне "
             "главного аргументпарсера." % MODULE, "",
             "базовый прогон без флага: exit %d, страница `%s`, событий %d, `AfterWrite` в списке: %s, "
             "`BeforeWrite` в списке: %s" % (base["code"], base["page"], len(base["events"]),
                                             base["AfterWrite"], base["BeforeWrite"]),
             "базовый список имён: %s" % ", ".join(base["events"]), "",
             "справочник: страниц %d, из них с именем вида `… form extension` %d; источник `%s`"
             % (ref["pages_total"], ref["form_extension_pages"], ref["data_source"]), ""]
    lines.append("| вид | exit | страница | событий | добавлено имён | убрано имён | "
                 "`AfterWrite` | `BeforeWrite` | страница в справочнике | событий на странице |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|")
    for r in runs[1:]:
        added = sorted(set(r["events"]) - base_names)
        removed = sorted(base_names - set(r["events"]))
        map_entry = ref["kind_mapping"].get(r["kind"], {})
        lines.append("| %s | %d | %s | %d | %d | %d | %s | %s | %s | %s |" % (
            r["kind"], r["code"], r["page"], len(r["events"]), len(added), len(removed),
            r["AfterWrite"], r["BeforeWrite"], map_entry.get("known_page_in_data", "нет такой страницы"),
            map_entry.get("data_events", "-")))
    lines.append("")
    lines.append("| вид | расположение флага | exit | страница | событий | "
                 "совпадает со списком после подкоманды |")
    lines.append("|---|---|---|---|---|---|")
    after_by_kind = {r["kind"]: r for r in runs[1:]}
    for r in placed:
        same = after_by_kind.get(r["kind"], {}).get("events") == r["events"]
        lines.append("| %s | %s | %d | %s | %d | %s |"
                     % (r["kind"], r["placement"], r["code"], r["page"], len(r["events"]), same))
    lines.append("")
    lines.append("| вид | страница в `EVENT_SIGNATURES` | событий на странице | управляемая страница | "
                 "событий в списке | `AfterWrite` | `BeforeWrite` |")
    lines.append("|---|---|---|---|---|---|---|")
    for kind, entry in sorted(ref["kind_mapping"].items()):
        lines.append("| %s | %s | %d | %s | %d | %s | %s |" % (
            kind, entry["page"], entry["data_events"], entry["managed_page"],
            entry["event_names_len"], entry["AfterWrite"], entry["BeforeWrite"]))
    text = "\n".join(lines) + "\n"

    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(ref)
    payload["platform_started"] = False
    payload["runs"] = runs
    payload["flag_placement"] = placed
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", "utf-8")
    out.with_suffix(".txt").write_text(text, "utf-8")
    print(text)
    print("wrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
