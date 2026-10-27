"""Замер: какой объект рукописной конфигурации не даёт загрузке `/LoadConfigFromFiles` завершиться.

Наблюдение gate-03 (платформа 8.3.27.1606): загрузка нашей конфигурации (24 файла) не завершилась
за 600 с и не вывела ни байта. Отдельная проверка процесса показала не окно ожидания, а постоянный
расход CPU (93 с CPU на 100 с wall clock). Причина — внутри состава конфигурации, и искать её надо
последовательным упрощением, а не догадками.

Вариант = копия исходника с вырезанными объектами (scripts/bisect_cfg.py: вырезание возможно
только вместе со всеми снимаемыми ссылками). Для каждого варианта: свежая файловая база
(`CREATEINFOBASE`) → загрузка копии → коды, секунды, байты вывода. За один запуск скрипт делает
ровно один вызов платформы; 1С-прогоны не перемешиваются.

Исходник `cfg/ЭффективностьОтдела` не изменяется.
"""
from __future__ import annotations

import json
import pathlib
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import bisect_cfg                                                # noqa: E402
import ib_loop                                                   # noqa: E402
import paths                                                     # noqa: E402

SOURCE = ROOT / "cfg" / "ЭффективностьОтдела"

# Порядок вариантов: сначала известный быстрый контроль (он показывает, что окружение и вызов
# платформы в порядке), затем упрощения от самого большого к самому маленькому, и в конце —
# подтверждение наблюдения gate-03 на исходной конфигурации.
VARIANTS = (
    ("control_min", [], "контроль: минимальная конфигурация спайка (7 файлов), известная быстрая загрузка"),
    ("thin", ["Report.ОтчётЗагрузки", "Document.ФактРаботы", "AccumulationRegister.ЗатратыВремени",
              "InformationRegister.ПланЗагрузки", "CommonModule.РасчётПоказателей",
              "Constant.НормаЧасовВМесяц"], "тонкий срез: справочник с формой без отчёта и регистров"),
    ("no_registers", ["Document.ФактРаботы", "AccumulationRegister.ЗатратыВремени",
                      "InformationRegister.ПланЗагрузки"], "документ и оба регистра вырезаны"),
    ("no_report", ["Report.ОтчётЗагрузки"], "отчёт с макетом СКД целиком вырезан"),
    ("no_template", ["Report.ОтчётЗагрузки.Template.ОсновнаяСхемаКомпоновкиДанных"],
     "отчёт остался, макет СКД вырезан"),
    ("no_form", ["Catalog.Сотрудники.Form.ФормаЭлемента"], "управляемая форма справочника вырезана"),
    ("full", [], "исходная конфигурация целиком — подтверждение наблюдения gate-03"),
    # Вторая лестница (после того как первая показала: зависает и 24-файловая, и 13-файловая
    # конфигурация, а выгруженная из платформы конфигурация на 239 файлов загружается за 4 с).
    # Порядок — от самого простого к более сложному: сначала только база конфигурации.
    ("only_base", ["Document.ФактРаботы", "Catalog.Сотрудники.Form.ФормаЭлемента",
                   "Catalog.Сотрудники", "Enum.ГрейдыСпециалистов", "Report.ОтчётЗагрузки",
                   "InformationRegister.ПланЗагрузки", "AccumulationRegister.ЗатратыВремени",
                   "Constant.НормаЧасовВМесяц", "CommonModule.РасчётПоказателей",
                   "Role.СотрудникОтдела", "Role.АдминистраторСистемы",
                   "Subsystem.ЭффективностьОтдела"],
     "только Configuration.xml + Languages: настоящий контроль успешной загрузки рукописных файлов"),
    ("no_catalog", ["Report.ОтчётЗагрузки", "Document.ФактРаботы",
                    "AccumulationRegister.ЗатратыВремени", "InformationRegister.ПланЗагрузки",
                    "CommonModule.РасчётПоказателей", "Constant.НормаЧасовВМесяц",
                    "Catalog.Сотрудники.Form.ФормаЭлемента", "Catalog.Сотрудники"],
     "справочника нет вовсе: остаются конфигурация, язык, перечисление, подсистема, роли"),
    ("no_roles", ["Report.ОтчётЗагрузки", "Document.ФактРаботы",
                  "AccumulationRegister.ЗатратыВремени", "InformationRegister.ПланЗагрузки",
                  "CommonModule.РасчётПоказателей", "Constant.НормаЧасовВМесяц",
                  "Role.СотрудникОтдела", "Role.АдминистраторСистемы"],
     "ролей и их прав нет: остаются справочник с формой, перечисление, подсистема"),
    # Третья лестница: no_roles загрузился за 2 с (код 0), no_catalog (роли есть, справочника нет)
    # завис. Значит причина — файлы ролей. Дальше разделяем дескриптор роли и её права.
    ("no_rights_files", ["file:Roles/СотрудникОтдела/Ext/Rights.xml",
                         "file:Roles/АдминистраторСистемы/Ext/Rights.xml"],
     "роли остались, но файлов прав нет: проверяем, что именно в правах ломает загрузку"),
    ("roles_only", ["Document.ФактРаботы", "AccumulationRegister.ЗатратыВремени",
                    "InformationRegister.ПланЗагрузки", "Report.ОтчётЗагрузки",
                    "Constant.НормаЧасовВМесяц", "CommonModule.РасчётПоказателей",
                    "Catalog.Сотрудники.Form.ФормаЭлемента", "Catalog.Сотрудники",
                    "Enum.ГрейдыСпециалистов"],
     "только роли с правами + конфигурация + язык + подсистема: изоляция отказа ролей"),
    ("only_base", ["Document.ФактРаботы", "AccumulationRegister.ЗатратыВремени",
                   "InformationRegister.ПланЗагрузки", "Report.ОтчётЗагрузки",
                   "Constant.НормаЧасовВМесяц", "CommonModule.РасчётПоказателей",
                   "Catalog.Сотрудники.Form.ФормаЭлемента", "Catalog.Сотрудники",
                   "Enum.ГрейдыСпециалистов", "Role.СотрудникОтдела",
                   "Role.АдминистраторСистемы", "Subsystem.ЭффективностьОтдела"],
     "только Configuration.xml + Languages: контроль, что рукописная база загружается"),
    ("admin_role_only", ["Report.ОтчётЗагрузки", "Document.ФактРаботы",
                         "AccumulationRegister.ЗатратыВремени", "InformationRegister.ПланЗагрузки",
                         "CommonModule.РасчётПоказателей", "Constant.НормаЧасовВМесяц",
                         "Role.СотрудникОтдела"],
     "роль сотрудников вырезана: остаётся АдминистраторСистемы с её правами"),
    ("sotrudnik_role_only", ["Report.ОтчётЗагрузки", "Document.ФактРаботы",
                             "AccumulationRegister.ЗатратыВремени",
                             "InformationRegister.ПланЗагрузки", "CommonModule.РасчётПоказателей",
                             "Constant.НормаЧасовВМесяц", "Role.АдминистраторСистемы"],
     "роль администратора вырезана: остаётся СотрудникОтдела с её правами"),
)


def build(work: pathlib.Path, name: str, drops: list, timeout: int, local: dict) -> dict:
    if name == "control_min":
        source = pathlib.Path(local["spikes"]) / "cfg_min"
        variant = bisect_cfg.build_variant(source, str(work / ("variant-" + name)), [])
    else:
        variant = bisect_cfg.build_variant(SOURCE, str(work / ("variant-" + name)), drops)
    variant["variant"] = name
    variant["timeout"] = timeout
    return variant


def measure(work: pathlib.Path, variant: dict, local: dict) -> dict:
    name = variant["variant"]
    if variant["code"] != 0:
        return variant
    ib = work / ("ib-" + name)
    if ib.exists():
        shutil.rmtree(ib)
    out_dir = work / ("out-" + name)
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    opts = {"bin": local["bin"], "ib": str(ib), "cfg": variant["cfg"], "out": "",
            "timeout": variant["timeout"]}
    for step in ("create", "load"):
        opts["out"] = str(out_dir / (step + ".txt"))
        result = ib_loop.run_step(step, opts)
        variant[step + "_code"] = result["code"]
        variant[step + "_seconds"] = result.get("seconds")
        variant[step + "_bytes"] = result.get("bytes")
        variant[step + "_timed_out"] = result.get("timed_out")
        if step == "load":
            variant["load_head"] = [line for line in result.get("lines", []) if line.strip()][:8]
    return variant


def parse_args(argv: list) -> tuple:
    """`--variant <имя>` и `--timeout <сек>`; позиционно допустимы `имя [сек]` и `сек`.

    Наблюдение: первый запуск лестницы (`python probe/load_bisect.py 90`) дал отказ разбора,
    потому что таймаут читался как имя варианта. Порядок аргументов не должен иметь значения.
    """
    only, timeout, problem = "", 90, ""
    positional = []
    index = 0
    while index < len(argv):
        arg = argv[index]
        if arg in ("--variant", "--timeout"):
            if index + 1 >= len(argv):
                return "", 0, arg + " без значения"
            index += 1
            value = argv[index]
            if arg == "--variant":
                only = value
            else:
                timeout = _as_int(value)
                if timeout is None:
                    return "", 0, "--timeout должен быть целым числом секунд: " + value
        elif arg.startswith("--variant="):
            only = arg.split("=", 1)[1]
        elif arg.startswith("--timeout="):
            timeout = _as_int(arg.split("=", 1)[1])
            if timeout is None:
                return "", 0, "--timeout должен быть целым числом секунд: " + arg
        else:
            positional.append(arg)
        index += 1
    for arg in positional:
        number = _as_int(arg)
        if number is not None:
            timeout = number
        elif not only:
            only = arg
        else:
            problem = "лишний аргумент: " + arg
    return only, timeout, problem


def _as_int(value: str):
    try:
        return int(value)
    except ValueError:
        return None


def main(argv: list) -> int:
    local = paths.load_local(str(ROOT / "local.paths.json"))
    work = pathlib.Path(local["work"]) / "bisect"
    work.mkdir(exist_ok=True)
    only, timeout, problem = parse_args(argv)
    names = [name for name, _, _ in VARIANTS]
    if problem:
        print("отказ разбора:", problem)
        print("варианты:", ", ".join(names))
        return 2
    if only and only not in names:
        print("варианты:", ", ".join(names))
        return 2
    print("замер вариантов:", only or ", ".join(names), "| ожидание на загрузку:", timeout, "с")
    sys.stdout.flush()
    for name, drops, comment in VARIANTS:
        if only and only != name:
            continue
        variant = build(work, name, drops, timeout, local)
        variant["comment"] = comment
        variant["drops"] = drops
        measured = measure(work, variant, local)
        summary = {key: value for key, value in measured.items() if key != "dropped"}
        print(json.dumps(summary, ensure_ascii=False))
        sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
