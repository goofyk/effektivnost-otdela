"""Матрица покрытия нашей конфигурации инструментами p1c (замер, только чтение).

Вопрос замера: для каждого CLI p1c (читатель источников, сравнение версий, граф вызовов, метрики,
проверка BSL, проверки управляемых форм, чтение хранилища `.cf`, проверки SDBL) — файлы и имена
каких классов макета нашей конфигурации вообще появляются в отчёте инструмента. До этого замера
слепые пятна были описаны поодиночке (`docs/evidence/p1c-data-defects.md`,
`docs/evidence/sdbl-controls.md`), а сводной таблицы «инструмент × класс макета» в репозитории не
было: гейт считает только числа читателя `p1c.load` (`tool_counts_source`) и молчаливые классы
(`tool_blind_kinds`).

Две меры, которые замер разделяет сознательно:
- `path_hits` — дословный относительный путь файла макета (например `Catalogs/Сотрудники.xml`)
  встречается в отчёте инструмента. Это строгая мера: она отвечает на вопрос «инструмент назвал
  файл».
- `name_hits` — имя объекта, формы или макета (`Сотрудники`, `ФормаЭлемента`,
  `ОсновнаяСхемаКомпоновкиДанных`) встречается в отчёте. Это мягкая мера: она ловит инструменты,
  которые читают данные и называют их, но не печатают путь.

Классы макета берутся из независимого счётчика `scripts/layout.py` (тот же, что считает гейт), а
не из догадки: список файлов каждого класса проверяется по числам `layout_counts`.

Что этот замер НЕ делает:
- не запускает платформу 1С: все прогоны — Python-инструменты по файлам выгрузки и исходников;
- не исполняет изменяющих подкоманд (в список не включены `cf set`, `cf normalize`);
- не оценивает «качество инструмента»: коды возврата берутся из прогонов (отчёт `p1c.result/v1`
  ключа с кодом возврата не содержит), содержимое — из JSON-отчётов инструментов.

Абсолютных путей в этом файле нет: корни берутся из ключей `cfg`, `dump`, `p1c` файла
`local.paths.json`.

Выход замера: `reports/toolcov_<ярлык>.json` (отчёты инструментов), `reports/toolcov_runs.json`
(снимок всех прогонов и матрица), `reports/toolcov_summary.txt` (коды возврата и команды),
`reports/tool-coverage-matrix-18.md` (таблицы для документа).
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
sys.path.insert(0, str(ROOT / "scripts"))

import layout                                                # noqa: E402
import counts                                                # noqa: E402

PATHS = json.loads((ROOT / "local.paths.json").read_text(encoding="utf-8-sig"))

# Артефакт гейта, с которым сверяется матрица: независимые числа счётчика раскладки
# (`layout_source`), числа читателя `p1c.load` (`tool_counts_source`) и молчаливые для инструментов
# классы (`tool_blind_kinds`). `gate-15.json` — первый гейт, посчитанный читателем после правок
# A1 и A2 (в нём `tool_counts_source` 12 классов и `tool_blind_kinds` 10); `gate-14.json` остаётся
# артефактом того же гейта, посчитанного читателем до этих правок (10 и 12).
GATE_ARTIFACT = "gate-15.json"

# Прогоны: `label` — ярлык, `argv` — аргументы модуля CLI (ярлыки `cfg`, `dump`, `skd` подставляются
# из `local.paths.json`), `names_counted` — можно ли в этом прогоне мерить покрытие именем сущности.
# Имя или текст передаём мы сами у `sdbl-query-skd`, `load-object-catalog` и `forms-form-element`:
# имя сущности в их отчётах — эхо наших же слов, а не факт, что инструмент нашёл сущность сам,
# поэтому там засчитывается только путь файла макета (`names_counted: False`).
RUNS = [
    {"label": "load-model-dump", "argv": ["p1c.load.cli", "model", "dump"]},
    {"label": "load-model-cfg", "argv": ["p1c.load.cli", "model", "cfg"]},
    {"label": "load-forms-dump", "argv": ["p1c.load.cli", "forms", "dump"]},
    {"label": "load-object-catalog", "argv": ["p1c.load.cli", "object", "catalog.Сотрудники", "dump"],
     "names_counted": False},
    # Порядок positional-аргументов у `load object` и `check.forms form`: имя, потом корень.
    # Справка обещает сначала корень (`rest: корень выгрузки; для object — ключ <вид>.<имя>`),
    # и в этом порядке команда не работает: замер ниже.
    {"label": "load-object-wrong-order", "argv": ["p1c.load.cli", "object", "dump",
                                                  "catalog.Сотрудники"], "names_counted": False},
    {"label": "load-qualifiers-dump", "argv": ["p1c.load.cli", "qualifiers", "dump"]},
    {"label": "diff-model-cfg-dump", "argv": ["p1c.diff.cli", "model", "cfg", "dump"]},
    {"label": "graph-build-dump", "argv": ["p1c.graph.cli", "build", "dump"]},
    {"label": "graph-roots-dump", "argv": ["p1c.graph.cli", "roots", "dump"]},
    {"label": "metrics-top-dump", "argv": ["p1c.metrics.cli", "top", "dump"]},
    {"label": "bsl-check-cfg", "argv": ["p1c.check.bsl.cli", "check", "cfg", "--root", "dump"]},
    {"label": "forms-check-dump", "argv": ["p1c.check.forms.cli", "check", "dump"]},
    {"label": "forms-events-dump", "argv": ["p1c.check.forms.cli", "events", "dump"]},
    {"label": "forms-form-element", "argv": ["p1c.check.forms.cli", "form", "ФормаЭлемента", "dump"],
     "names_counted": False},
    {"label": "forms-form-wrong-order", "argv": ["p1c.check.forms.cli", "form", "dump",
                                                 "ФормаЭлемента"], "names_counted": False},
    {"label": "sdbl-check-cfg", "argv": ["p1c.check.sdbl.cli", "check", "cfg", "--root", "dump"]},
    {"label": "sdbl-query-skd", "argv": ["p1c.check.sdbl.cli", "query", "skd", "--root", "dump"],
     "names_counted": False},
    {"label": "cf-info-cfg-dir", "argv": ["p1c.cf.cli", "info", "cfg"], "writes_report": False},
]

# Относительный путь внутри cfg: текст запроса макета компоновки данных нашего отчёта.
SKD_TEMPLATE = "Reports/ОтчётЗагрузки/Templates/ОсновнаяСхемаКомпоновкиДанных/Ext/Template.xml"
QUERY_RE = re.compile(r"<query>((?s:.*))</query>")

NAMED_KIND_FOLDERS = layout.KIND_FOLDERS
OTHER_NAMED_KINDS = {"form_descriptor", "form_data", "form_module", "report_template",
                     "report_template_data"}

# Платформенные имена файлов, а не имена сущностей: `Form.xml`, `Module.bsl`, `Template.xml`.
# Имя такой сущности — каталог, в котором лежит её `Ext` (имя формы, имя макета компоновки данных).
GENERIC_STEMS = {"Form", "Module", "Template"}

# Классы, у которых нет собственного имени: их покрытие измеряется только путём файла. Имена роли
# или справочника в отчёте не доказывают, что инструмент читал `Rights.xml` или `Predefined.xml`.
PATH_ONLY_KINDS = {"role_rights", "predefined_data", "object_module", "bsl_module", "files"}

# Списочные и скалярные ключи отчёта `p1c.result/v1`, длины которых участвуют в замерах: по ним
# видно, что именно инструмент вернул (находки, формы, квалификаторы, изменения, строки рейтинга).
LIST_KEYS = ("results", "forms", "qualifiers", "changes", "top", "roots", "events",
             "queries", "modules", "count")


def layout_files(cfg_dir) -> dict:
    """Файлы каждого класса макета — теми же правилами, что `scripts/layout.py::layout_counts`.

    Возвращает {класс: [относительные posix-пути]}. Числа этого списка обязаны совпасть с
    `layout_counts`: иначе матрица покрытия считается по другому составу классов, чем гейт.
    """
    base = pathlib.Path(cfg_dir)
    files: dict[str, list[str]] = {}

    def rel(paths):
        return sorted(p.relative_to(base).as_posix() for p in paths)

    def object_files(folder):
        directory = base / folder
        if not directory.is_dir():
            return []
        return layout._object_files(base, directory)

    for folder, kind in NAMED_KIND_FOLDERS.items():
        found = rel(object_files(folder))
        if found:
            files[kind] = found

    forms = [p for p in base.rglob("Forms/*.xml") if "Ext" not in p.parts]
    form_data = list(base.rglob("Forms/*/Ext/Form.xml")) + list(base.rglob("CommonForms/*/Ext/Form.xml"))
    form_modules = list(base.rglob("Forms/*/Ext/Form/Module.bsl")) \
        + list(base.rglob("CommonForms/*/Ext/Form/Module.bsl"))
    command_defs = [p for p in base.rglob("Commands/*.xml") if "Ext" not in p.parts]
    command_modules = list(base.rglob("Commands/*/Ext/*.bsl"))
    templates = [p for p in base.rglob("Templates/*.xml") if "Ext" not in p.parts]
    template_data = list(base.rglob("Templates/*/Ext/Template.xml"))
    role_rights = list(base.rglob("Roles/*/Ext/Rights.xml"))
    predefined = list(base.rglob("*/Ext/Predefined.xml"))
    object_modules = list(base.rglob("Ext/*.bsl"))
    bsl = list(base.rglob("*.bsl"))
    all_files = [p for p in base.rglob("*") if p.is_file()]

    for kind, paths in (("form_descriptor", forms), ("form_data", form_data),
                        ("form_module", form_modules), ("command_descriptor", command_defs),
                        ("command_module", command_modules), ("report_template", templates),
                        ("report_template_data", template_data), ("role_rights", role_rights),
                        ("predefined_data", predefined), ("object_module", object_modules),
                        ("bsl_module", bsl), ("files", all_files)):
        files[kind] = rel(paths)
    return {kind: paths for kind, paths in sorted(files.items()) if paths}


def counts_match(cfg_dir, files: dict) -> dict:
    """Сверка состава классов замера с независимым счётчиком гейта (`layout_counts`)."""
    want = layout.layout_counts(cfg_dir)
    got = {kind: len(paths) for kind, paths in files.items()}
    return {"want": want, "got": got,
            "mismatch": {kind: (got.get(kind, 0), want.get(kind, 0))
                         for kind in sorted(set(want) | set(got))
                         if want.get(kind, 0) != got.get(kind, 0)}}


def entity_name(path: str) -> str:
    """Имя сущности макета по пути его файла (существует потому, что файлы форм и макетов
    платформы называются `Form.xml`, `Module.bsl`, `Template.xml`, а не именами сущностей).

    `Catalogs/Сотрудники.xml`                                          -> `Сотрудники`
    `Catalogs/Сотрудники/Forms/ФормаЭлемента/Ext/Form.xml`             -> `ФормаЭлемента`
    `Catalogs/Сотрудники/Forms/ФормаЭлемента/Ext/Form/Module.bsl`     -> `ФормаЭлемента`
    `Reports/ОтчётЗагрузки/Templates/ОсновнаяСхемаКомпоновкиДанных/Ext/Template.xml`
        -> `ОсновнаяСхемаКомпоновкиДанных`
    """
    parts = pathlib.PurePosixPath(path).parts
    if "Ext" in parts and parts.index("Ext") > 0:
        return parts[parts.index("Ext") - 1]
    return pathlib.PurePosixPath(path).stem


def names_of(files: dict) -> dict:
    """Именованные сущности каждого класса: имя объекта, имя формы, имя макета компоновки данных.

    Классы из `PATH_ONLY_KINDS` пропускаются: имя роли в отчёте не доказывает, что инструмент
    читал `Roles/<роль>/Ext/Rights.xml`, а имя справочника — что он читал `Ext/Predefined.xml`.
    """
    names: dict[str, list[str]] = {}
    named = set(NAMED_KIND_FOLDERS.values()) | OTHER_NAMED_KINDS
    for kind, paths in files.items():
        if kind in PATH_ONLY_KINDS or kind not in named:
            continue
        found = {entity_name(path) for path in paths} - GENERIC_STEMS - {""}
        if found:
            names[kind] = sorted(found)
    return names


def skd_path():
    """Путь файла макета компоновки данных нашей конфигурации (относительная часть — `SKD_TEMPLATE`)."""
    return pathlib.Path(PATHS["cfg"]) / SKD_TEMPLATE


def skd_query_text() -> str:
    """Текст `<query>` из макета компоновки данных: его подставляют вместо ярлыка `skd`.

    `check.sdbl query` принимает текст запроса аргументом, а не файл; этот текст — содержимое
    нашего макета, прочитанное в момент прогона.
    """
    match = QUERY_RE.search(skd_path().read_text(encoding="utf-8"))
    return match.group(1) if match else ""


def resolve(token):
    """Ярлык пути -> значение; `skd` — текст запроса макета компоновки данных нашей конфигурации."""
    if token == "skd":
        return skd_query_text()
    return PATHS.get(token, token)


def real_argv(argv):
    """Аргументы прогона: ярлыки путей заменяются значениями из `local.paths.json`."""
    return [resolve(token) for token in argv]


def short(argv) -> str:
    """Команда прогона в сводке — с именами ключей путей вместо абсолютных путей."""
    return " ".join("<%s>" % token if token in PATHS or token == "skd" else token
                    for token in argv)


def execute(spec) -> dict:
    """Прогон одного CLI-инструмента p1c по нашим исходникам или выгрузке (платформу не запускает)."""
    label, argv = spec["label"], spec["argv"]
    writes_report = spec.get("writes_report", True)
    report_file = REPORTS / ("toolcov_%s.json" % label)
    if report_file.is_file():
        report_file.unlink()          # снимок не должен собираться из отчёта прошлого прогона
    command = [sys.executable, "-m"] + real_argv(argv)
    if writes_report:
        command += ["--format", "json", "--out", str(report_file)]
    env = dict(os.environ)
    env["PYTHONPATH"] = PATHS["p1c"]
    env["PYTHONIOENCODING"] = "utf-8"
    proc = subprocess.run(command, cwd=str(ROOT), capture_output=True, text=True,
                          encoding="utf-8", errors="replace", env=env)
    report = None
    if report_file.is_file():
        try:
            report = json.loads(report_file.read_text(encoding="utf-8-sig"))
        except ValueError:
            report = None
    stdout = proc.stdout or ""
    return {"label": label, "argv": short(argv), "code": proc.returncode,
            "names_counted": spec.get("names_counted", True),
            "argv_chars": sum(len(token) for token in real_argv(argv)),
            "stdout_chars": len(stdout), "stdout_lines": len(stdout.splitlines()),
            "stdout_text": stdout[:4000],
            "stderr_text": (proc.stderr or "").strip(),
            "report_file": report_file.name if report_file.is_file() else None,
            "report": report}


def texts_of(run) -> dict:
    """Два разных текста прогона, в которых ищутся пути и имена.

    `report` — JSON-отчёт инструмента (то, что инструмент сообщил о содержимом).
    `console` — stdout и stderr (в них путь мог появиться только из-за печати аргументов или
    traceback'а, и это отдельный случай: он не означает, что инструмент файл прочитал).
    """
    report = run.get("report")
    report_text = json.dumps(report, ensure_ascii=False) if report else ""
    console_text = "\n".join([run.get("stdout_text") or "", run.get("stderr_text") or ""])
    return {"report": report_text.replace("\\", "/").casefold(),
            "console": console_text.replace("\\", "/").casefold()}


PATH_EDGE = frozenset("/\\")


def name_occurrences(text: str, name: str) -> tuple:
    """Сколько раз имя встречается в тексте и сколько из этих встреч — часть пути к файлу.

    Имя, стоящее вплотную к `/` или `\\`, — отражённый в отчёте путь (например
    `"root": "C:/.../cfg/ЭффективностьОтдела"` или `"file": ".../Catalogs/Сотрудники.xml"`),
    а не то, что инструмент сам назвал сущность. Такие встречи в покрытие не засчитываются и
    выносятся отдельным числом.
    """
    total = echoed = 0
    for match in re.finditer(re.escape(name), text):
        total += 1
        before = text[match.start() - 1] if match.start() else ""
        after = text[match.end()] if match.end() < len(text) else ""
        if before in PATH_EDGE or after in PATH_EDGE:
            echoed += 1
    return total, echoed


def hits_for(text: str, files: dict, names: dict) -> dict:
    """Какие файлы и какие имена какого класса встречаются в тексте отчёта инструмента."""
    out = {}
    for kind, paths in files.items():
        path_hits = [path for path in paths if path.casefold() in text]
        named, echoed = [], []
        for name in names.get(kind, []):
            total, at_path = name_occurrences(text, name.casefold())
            if total - at_path > 0:
                named.append(name)
            elif total:
                echoed.append(name)
        out[kind] = {"path_hits": path_hits, "name_hits": named, "name_hits_path_echo": echoed}
    return out


def hits_of(run, files: dict, names: dict) -> dict:
    """Хиты класса для одного прогона, разделённые по месту появления: отчёт или консоль."""
    texts = texts_of(run)
    in_report = hits_for(texts["report"], files, names)
    in_console = hits_for(texts["console"], files, names)
    hits = {}
    for kind in files:
        report, console = in_report[kind], in_console[kind]
        counted = run.get("names_counted", True)
        hits[kind] = {
            "path_hits_report": sorted(report["path_hits"]),
            "path_hits_console_only": sorted(set(console["path_hits"]) - set(report["path_hits"])),
            "name_hits_report": sorted(report["name_hits"]) if counted else [],
            "name_hits_console_only": sorted(set(console["name_hits"]) - set(report["name_hits"]))
            if counted else [],
            "name_hits_path_echo_only": (sorted((set(report["name_hits_path_echo"])
                                                 | set(console["name_hits_path_echo"]))
                                                - (set(report["name_hits"])
                                                   | set(console["name_hits"])))
                                         if counted else []),
        }
    return hits


def reader_kind_counts(report) -> dict:
    """Виды метаданных, которые назвал читатель `p1c.load` в своём отчёте (та же мера, что у гейта)."""
    if not isinstance(report, dict):
        return {}
    model = report.get("model") or report
    if not isinstance(model, dict) or "collections" not in model:
        return {}
    try:
        return counts.counts_from_model(model)
    except Exception as error:                                     # noqa: BLE001
        return {"error": type(error).__name__ + ": " + str(error)}


def report_shape(report) -> dict:
    """Форма отчёта инструмента: ключи верхнего уровня, длины списочных ключей, статистика."""
    if not isinstance(report, dict):
        return {"report": "нет JSON-отчёта"}
    shape = {"report": "p1c.result/v1", "keys": sorted(report),
             "findings": len(report.get("results") or []),
             "stats": report.get("stats") or {},
             "schema_available": report.get("schema_available")}
    for key in LIST_KEYS:
        value = report.get(key)
        if isinstance(value, list):
            shape[key] = len(value)
        elif isinstance(value, (int, str)) and key not in ("context_signature",):
            shape[key] = value
    return shape


def matrix(runs, files: dict):
    """Матрица «класс макета × инструмент».

    Инструмент засчитывается по пути файла или по имени сущности только если они появились в его
    JSON-отчёте. Хиты, найденные исключительно в stdout/stderr, вынесены в отдельный столбец:
    путь, напечатанный traceback'ом, не доказывает, что инструмент файл прочитал.
    """
    kinds = sorted(files)
    tools = sorted({run["label"].split("-")[0] for run in runs})
    by_label = {run["label"]: run for run in runs}
    rows = []
    for kind in kinds:
        path_tools, name_tools, echo_tools, console_tools = [], [], [], []
        for tool in tools:
            group = [by_label[label] for label in by_label if label.split("-")[0] == tool]
            if any(run["hits"][kind]["path_hits_report"] for run in group):
                path_tools.append(tool)
            if any(run["hits"][kind]["name_hits_report"] for run in group):
                name_tools.append(tool)
            if any(run["hits"][kind]["name_hits_path_echo_only"] for run in group):
                echo_tools.append(tool)
            if any(run["hits"][kind]["path_hits_console_only"]
                   or run["hits"][kind]["name_hits_console_only"] for run in group):
                console_tools.append(tool)
        rows.append({"kind": kind, "files": len(files[kind]),
                     "tools_by_path": path_tools, "tools_by_name": name_tools,
                     "tools_name_echo_only": echo_tools, "tools_console_only": console_tools})
    return rows, tools


def tables(runs, kind_rows, gate):
    runs_table = ["| прогон | команда прогона (ярлыки путей) | код возврата | находок в JSON-отчёте | "
                  "файлов cfg в JSON-отчёте | имён cfg в JSON-отчёте | имён только как часть пути | "
                  "хитов только в консоли |",
                  "|---|---|---|---|---|---|---|---|"]
    for run in runs:
        hits = run["hits"]
        report_paths = {path for kind in hits for path in hits[kind]["path_hits_report"]}
        report_names = {name for kind in hits for name in hits[kind]["name_hits_report"]}
        echo_names = {name for kind in hits for name in hits[kind]["name_hits_path_echo_only"]}
        console_hits = {path for kind in hits for path in hits[kind]["path_hits_console_only"]}
        console_hits |= {name for kind in hits for name in hits[kind]["name_hits_console_only"]}
        runs_table.append("| `%s` | `%s` | %d | %s | %d | %d | %d | %d |" % (
            run["label"], run["argv"], run["code"],
            run["shape"].get("findings", "**нет JSON-отчёта**"),
            len(report_paths), len(report_names), len(echo_names), len(console_hits)))
    kinds_table = ["| класс макета (гейт `layout_source`) | файлов в cfg | инструментов видят путь "
                   "файла | инструментов видят имя сущности | инструментов видят имя только как "
                   "часть пути | какие инструменты (по пути файла) |",
                   "|---|---|---|---|---|---|"]
    for row in kind_rows:
        kinds_table.append("| `%s` | %d | %d | %d | %s | %s |" % (
            row["kind"], row["files"], len(row["tools_by_path"]), len(row["tools_by_name"]),
            len(row["tools_name_echo_only"]) or "0",
            ", ".join("`%s`" % tool for tool in row["tools_by_path"]) or "**ни один инструмент**"))
    return runs_table, kinds_table


def main() -> int:
    REPORTS.mkdir(exist_ok=True)
    cfg = PATHS["cfg"]
    files = layout_files(cfg)
    names = names_of(files)
    gate = json.loads((REPORTS / GATE_ARTIFACT).read_text(encoding="utf-8-sig"))

    runs = []
    for spec in RUNS:
        runs.append(execute(spec))
    for run in runs:
        run["hits"] = hits_of(run, files, names)
        run["shape"] = report_shape(run.get("report"))
        if run["label"].startswith("load-model"):
            run["reader_kind_counts"] = reader_kind_counts(run.get("report"))
        if run["label"] == "sdbl-query-skd":
            run["skd_query_chars"] = len(skd_query_text())
            run["skd_template_file"] = SKD_TEMPLATE

    kind_rows, tools = matrix(runs, files)
    seen_by_path = {row["kind"] for row in kind_rows if row["tools_by_path"]}
    seen_by_name = {row["kind"] for row in kind_rows if row["tools_by_name"]}
    no_tool_at_all = set(files) - seen_by_path - seen_by_name
    runs_table, kinds_table = tables(runs, kind_rows, gate)

    reader = {run["label"]: run["reader_kind_counts"] for run in runs
              if run.get("reader_kind_counts")}
    gate_counts = gate["tool_counts_source"]
    reader_vs_gate = {}
    for label, got in sorted(reader.items()):
        reader_vs_gate[label] = {
            "equal_to_gate_tool_counts_source": got == gate_counts,
            "diff_reader_vs_gate": {kind: [got.get(kind, 0), gate_counts.get(kind, 0)]
                                    for kind in sorted(set(got) | set(gate_counts))
                                    if got.get(kind, 0) != gate_counts.get(kind, 0)},
        }

    summary = ["# Сводка прогонов матрицы покрытия (коды возврата живут только здесь)"]
    for run in runs:
        summary.append("=== %s: exit %d" % (run["label"], run["code"]))
        summary.append("argv: %s" % run["argv"])
        summary.append("report file: %s" % (run["report_file"] or "(не записан)"))
        summary.append("shape: %s" % json.dumps(run["shape"], ensure_ascii=False)[:400])
        if run.get("stderr_text"):
            summary.append("stderr: %s" % run["stderr_text"][:400])
        summary.append("")

    summary.append("=== покрытие классов макета (засчитаны только JSON-отчёты инструментов)")
    for row in kind_rows:
        summary.append("%-24s files=%d by_path=%s by_name=%s name_echo_only=%s console_only=%s"
                       % (row["kind"], row["files"], row["tools_by_path"] or "-",
                          row["tools_by_name"] or "-", row["tools_name_echo_only"] or "-",
                          row["tools_console_only"] or "-"))
    summary.append("")
    summary.append("=== читатель p1c.load против гейта %s (`tool_counts_source`)" % GATE_ARTIFACT)
    for label, verdict in sorted(reader_vs_gate.items()):
        summary.append("%s: equal=%s diff(reader,gate)=%s"
                       % (label, verdict["equal_to_gate_tool_counts_source"],
                          json.dumps(verdict["diff_reader_vs_gate"], ensure_ascii=False)))

    payload = {"cfg_files_by_kind": files, "cfg_names_by_kind": names,
               "layout_counts_match": counts_match(cfg, files),
               "runs": [{k: v for k, v in run.items() if k not in ("report",)} for run in runs],
               "matrix_by_kind": kind_rows, "tools": tools,
               "gate_artifact": GATE_ARTIFACT,
               "gate_layout_source": gate["layout_source"],
               "gate_tool_counts_source": gate["tool_counts_source"],
               "gate_tool_blind_kinds": gate["tool_blind_kinds"],
               "reader_kind_counts": reader,
               "reader_vs_gate": reader_vs_gate,
               "kinds_seen_by_path": sorted(seen_by_path),
               "kinds_seen_by_name_only": sorted(seen_by_name - seen_by_path),
               "kinds_seen_by_no_tool": sorted(no_tool_at_all),
               "kinds_total": len(files)}
    (REPORTS / "toolcov_runs.json").write_text(json.dumps(payload, ensure_ascii=False, indent=1),
                                               encoding="utf-8")
    (REPORTS / "toolcov_summary.txt").write_text("\n".join(summary), encoding="utf-8")
    markdown = ["<!--TABLE coverage-runs-->"] + runs_table + ["", "<!--TABLE coverage-kinds-->"] \
        + kinds_table
    (REPORTS / "tool-coverage-matrix-18.md").write_text("\n".join(markdown) + "\n", encoding="utf-8")
    (REPORTS / "tool-coverage-matrix-18.json").write_text(json.dumps(payload, ensure_ascii=False,
                                                                    indent=1), encoding="utf-8")

    print("runs", len(runs), "tools", len(tools))
    for run in runs:
        hits = run["hits"]
        paths = sum(len(hits[kind]["path_hits_report"]) for kind in hits)
        names_hit = sum(len(hits[kind]["name_hits_report"]) for kind in hits)
        console = sum(len(hits[kind]["path_hits_console_only"])
                      + len(hits[kind]["name_hits_console_only"]) for kind in hits)
        print("  %-22s exit %d  findings %-4s paths %-3d names %-3d console %-3d"
              % (run["label"], run["code"], run["shape"].get("findings", "-"),
                 paths, names_hit, console))
    print("kinds", len(files), "by path", len(seen_by_path), "by name only",
          len(seen_by_name - seen_by_path), "no tool", len(no_tool_at_all),
          "mismatch", payload["layout_counts_match"]["mismatch"])
    for label, verdict in sorted(reader_vs_gate.items()):
        print("reader vs gate:", label, verdict["equal_to_gate_tool_counts_source"],
              json.dumps(verdict["diff_reader_vs_gate"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
