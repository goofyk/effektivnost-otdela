"""Независимый счётчик метаданных по раскладке файлов конфигурации.

Существует потому, что читатель `p1c.load` (`COLLECTIONS_MAP`,
`p1c/src/p1c/load/reader.py:64-125`) не читает папки `Roles`, `Subsystems`, `Languages`,
`SessionParameters`, `ChartsOfCharacteristicTypes`, `CommonPictures`, `SettingsStorages` и
содержимое `Templates`. Гейт обязан считать сам и сравнивать с ожиданием, заданным
спецификацией до сборки: иначе «инструмент молчит» и «платформа приняла» выглядят одинаково.
"""
from __future__ import annotations

import pathlib
import xml.etree.ElementTree as ET

MD_NS = "{http://v8.1c.ru/8.3/MDClasses}"

# Папка выгрузки -> вид метаданных. Имена папок взяты из реальных дампов платформы.
KIND_FOLDERS = {
    "Attributes": "common_attribute",
    "BusinessProcesses": "business_process",
    "Catalogs": "catalog",
    "ChartsOfCalculationTypes": "chart_of_calculation",
    "ChartsOfCharacteristicTypes": "chart_of_characteristics",
    "ChartsOfAccounts": "chart_of_accounts",
    "CommandGroups": "command_group",
    "CommonCommands": "common_command",
    "CommonForms": "common_form",
    "CommonModules": "common_module",
    "CommonPictures": "common_picture",
    "CommonTemplates": "common_template",
    "Constants": "constant",
    "DataProcessors": "data_processor",
    "DefinedTypes": "defined_type",
    "Documents": "document",
    "DocumentJournals": "document_journal",
    "Enums": "enum",
    "EventSubscriptions": "event_subscription",
    "ExchangePlans": "exchange_plan",
    "FilterCriteria": "filter_criteria",
    "FunctionalOptions": "functional_option",
    "HTTPServices": "http_service",
    "InformationRegisters": "information_register",
    "Languages": "language",
    "Reports": "report",
    "Roles": "role",
    "ScheduledJobs": "scheduled_job",
    "SessionParameters": "session_parameter",
    "SettingsStorages": "settings_storage",
    "SubsystemGroups": "subsystem_group",
    "Subsystems": "subsystem",
    "StyleItems": "style_item",
    "Styles": "style",
    "Tasks": "task",
    "WebServices": "web_service",
    "AccumulationRegisters": "accumulation_register",
    "AccountingRegisters": "accounting_register",
    "CalculationRegisters": "calculation_register",
}

# Тег декларации в ChildObjects корневого Configuration.xml -> вид метаданных.
TAG_KINDS = {
    "Catalog": "catalog", "Document": "document", "Enum": "enum", "Constant": "constant",
    "InformationRegister": "information_register", "AccumulationRegister": "accumulation_register",
    "AccountingRegister": "accounting_register", "CalculationRegister": "calculation_register",
    "ChartOfCharacteristicTypes": "chart_of_characteristics", "ChartOfAccounts": "chart_of_accounts",
    "ChartOfCalculationTypes": "chart_of_calculation", "ExchangePlan": "exchange_plan",
    "BusinessProcess": "business_process", "Task": "task", "CommonModule": "common_module",
    "CommonForm": "common_form", "CommonAttribute": "common_attribute",
    "CommonPicture": "common_picture", "CommonTemplate": "common_template",
    "DefinedType": "defined_type", "Role": "role", "Report": "report",
    "DataProcessor": "data_processor", "Subsystem": "subsystem", "SubsystemGroup": "subsystem_group",
    "SessionParameter": "session_parameter", "Language": "language",
    "SettingsStorage": "settings_storage", "FunctionalOption": "functional_option",
    "FilterCriterion": "filter_criteria", "EventSubscription": "event_subscription",
    "ScheduledJob": "scheduled_job", "HTTPService": "http_service", "WebService": "web_service",
    "CommandGroup": "command_group", "CommonCommand": "common_command", "DocumentJournal": "document_journal",
}

def _object_files(base: pathlib.Path, folder: pathlib.Path) -> list[pathlib.Path]:
    """Файлы объекта: `Папка/Имя.xml` (выгрузка конфигуратора) или `Папка/Имя/Имя.xml` (EDT)."""
    found = [p for p in sorted(folder.glob("*.xml"))]
    for sub in sorted(p for p in folder.iterdir() if p.is_dir()):
        if (sub / (sub.name + ".xml")).is_file():
            found.append(sub / (sub.name + ".xml"))
    return found


def layout_counts(cfg_dir, ignore: tuple = ()) -> dict:
    """Числа по видам метаданных и по парам файлов, независимые от инструментов p1c.

    `ignore` — относительные пути файлов, которые добавляет сама платформа (выгрузка:
    `ConfigDumpInfo.xml`), иначе выгрузка всегда оказывается на файл «длиннее» исходника.
    """
    base = pathlib.Path(cfg_dir)
    skipped = set(ignore)
    counts: dict[str, int] = {}
    for folder, kind in KIND_FOLDERS.items():
        directory = base / folder
        if not directory.is_dir():
            continue
        counts[kind] = len(_object_files(base, directory))

    forms = [p for p in base.rglob("Forms/*.xml") if "Ext" not in p.parts]
    form_data = [p for p in base.rglob("Forms/*/Ext/Form.xml")] + list(base.rglob("CommonForms/*/Ext/Form.xml"))
    form_modules = [p for p in base.rglob("Forms/*/Ext/Form/Module.bsl")] + list(base.rglob("CommonForms/*/Ext/Form/Module.bsl"))
    command_defs = [p for p in base.rglob("Commands/*.xml") if "Ext" not in p.parts]
    command_modules = [p for p in base.rglob("Commands/*/Ext/*.bsl")]
    report_templates = [p for p in base.rglob("Templates/*.xml") if "Ext" not in p.parts]
    report_template_data = list(base.rglob("Templates/*/Ext/Template.xml"))
    role_rights = list(base.rglob("Roles/*/Ext/Rights.xml"))
    # Предопределённые данные справочников (замер корпусов `corpora_*`: файлы
    # `Папка/Имя/Ext/Predefined.xml` с записями `<Item>`). Ни одна папка предопределённых данных
    # в `COLLECTIONS_MAP` не описана, и ни один дескриптор метаданных их не содержит: это класс,
    # о котором инструменты молчат даже когда файл потерян.
    predefined_data = list(base.rglob("*/Ext/Predefined.xml"))
    object_modules = [p for p in base.rglob("Ext/*.bsl")]
    bsl = [p for p in base.rglob("*.bsl")]

    # Классы содержимого, у которых нет отдельной папки-папки: величина задаётся отдельной
    # чертой по образцу `form_data`, `report_template_data`, `role_rights` и `predefined_data`.
    # Имена папок и файлов взяты из дампа фикстуры `p1c/examples/reader_gaps` (мера
    # `t17_layout_counts.py`), а не из манифеста наугад: черта обязана описывать раскладку,
    # которую платформа действительно делает. Ожидание — в `tests/test_layout_counts.py`
    # (оно записано до этой правки).
    common_command_modules = list(base.rglob("CommonCommands/*/Ext/CommandModule.bsl"))
    picture_data = list(base.rglob("CommonPictures/*/Ext/Picture.xml"))
    picture_content = [p for p in base.rglob("CommonPictures/*/Ext/Picture/**") if p.is_file()]
    common_template_contents = [p for p in base.rglob("CommonTemplates/*/Ext/*") if p.is_file()]
    style_contents = [p for p in base.rglob("Styles/*/Ext/*") if p.is_file()]
    style_item_contents = [p for p in base.rglob("StyleItems/*/Ext/*") if p.is_file()]
    help_pages = (list(base.rglob("*/Ext/Help.xml")) +
                  [p for p in base.rglob("*/Ext/Help/**") if p.is_file()])

    counts["form_descriptor"] = len(forms)
    counts["form_data"] = len(form_data)
    counts["form_module"] = len(form_modules)
    counts["command_descriptor"] = len(command_defs)
    counts["command_module"] = len(command_modules)
    counts["report_template"] = len(report_templates)
    counts["report_template_data"] = len(report_template_data)
    counts["role_rights"] = len(role_rights)
    counts["predefined_data"] = len(predefined_data)
    counts["object_module"] = len(object_modules)
    counts["bsl_module"] = len(bsl)
    counts["common_command_module"] = len(common_command_modules)
    counts["common_picture_data"] = len(picture_data)
    counts["common_picture_content"] = len(picture_content)
    counts["common_template_data"] = len(common_template_contents)
    counts["style_data"] = len(style_contents)
    counts["style_item_data"] = len(style_item_contents)
    counts["help"] = len(help_pages)
    counts["files"] = sum(1 for p in base.rglob("*")
                          if p.is_file() and p.relative_to(base).as_posix() not in skipped)
    return {kind: count for kind, count in sorted(counts.items()) if count}


def declared_children(cfg_dir) -> dict:
    """Декларация состава в корневом `Configuration.xml`: вид -> число объявленных объектов."""
    root_file = pathlib.Path(cfg_dir) / "Configuration.xml"
    if not root_file.is_file():
        return {}
    root = ET.fromstring(root_file.read_bytes().decode("utf-8-sig", "replace"))
    counts: dict[str, int] = {}
    for child in root.iter(MD_NS + "ChildObjects"):
        for tag in child:
            name = tag.tag.replace(MD_NS, "")
            kind = TAG_KINDS.get(name)
            if kind:
                counts[kind] = counts.get(kind, 0) + 1
        break
    return {kind: count for kind, count in sorted(counts.items()) if count}


def shape_problems(cfg_dir, counts: dict | None = None) -> list:
    """Правила парности файлов, нарушение которых роняет загрузку целиком."""
    base = pathlib.Path(cfg_dir)
    counts = counts or layout_counts(base)
    problems = []

    for form in base.rglob("Forms/*.xml"):
        if "Ext" in form.parts:
            continue
        data = form.parent / form.stem / "Ext" / "Form.xml"
        if not data.is_file():
            problems.append("нет данных формы " + data.relative_to(base).as_posix() +
                            " при дескрипторе " + form.relative_to(base).as_posix())

    for role in _object_files(base, base / "Roles") if (base / "Roles").is_dir() else []:
        rights = role.parent / role.stem / "Ext" / "Rights.xml"
        if not rights.is_file():
            problems.append("нет прав роли " + role.stem + ": " + rights.relative_to(base).as_posix())

    for report in _object_files(base, base / "Reports") if (base / "Reports").is_dir() else []:
        directory = report.parent / report.stem
        if not (directory / "Templates").is_dir():
            problems.append("у отчёта " + report.stem + " нет каталога Templates (основная схема компоновки данных)")

    if (base / "Configuration.xml").is_file():
        declared = declared_children(base)
        for kind, declared_count in declared.items():
            got = counts.get(kind, 0)
            if got < declared_count:
                problems.append("в ChildObjects объявлено " + kind + ": " + str(declared_count) +
                                ", файлов объекта: " + str(got))
    return problems


def compare_expected(counts: dict, expected: dict) -> dict:
    """{вид: (получили, ожидали)} для всех расхождений; пустой словарь — совпало."""
    diff = {}
    for kind, want in (expected or {}).items():
        got = counts.get(kind, 0)
        if got != want:
            diff[kind] = (got, want)
    return diff
