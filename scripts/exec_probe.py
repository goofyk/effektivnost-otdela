"""Исполнение BSL-программы в информационной базе командой строки: наблюдение.

Зачем. Гейт умеет загружать конфигурацию (`/LoadConfigFromFiles`), проверять модули
(`/CheckModules`) и выгружать (`/DumpConfigToFiles`). Ни один из этих режимов не выполняет наш
BSL: начальные данные, тесты и отчёт нельзя проверить без исполнения программы в базе. Наблюдения
из Task 1 (`reports/obs-*.json`) дают только плохие признаки: `/RunScript` и `/EXECUTE` раньше
возвращали 0 байт вывода и зависали. Это наблюдение проверяет каждую форму запуска отдельно.

Что считается подтверждением. Программа обязана оставить след, независимый от `/Out`: файл-маркер,
записанный самой программой. Отдельно читается вывод `/Out`. Программа дополнительно читает
метаданные загруженной конфигурации (`Метаданные.Языки[0].КодЯзыка`,
`Метаданные.Справочники.Количество()`), поэтому пустой вывод при сохранённом маркере различает
«режим не выполнил программу» и «режим выполнил, но не показал вывод».

Имена флагов и ключей авторизации берутся из замера `p1c/src/p1c/data/test_cli_flags.json`
(426 имён, `probe`-замер списка) и из таблицы имён платформы (`probe/platform_name_table.py`):
`/RunScript`, `/EXECUTE`, `/authoff`, `-User`, `-Pwd`, `-CurrentUser`, `-AllUsers`,
`-ExternalConnection`, `/TESTCLIENT`, `/TESTMANAGER`, `-testFile`, `-testOut`, `-TestOnly`,
`/LoadExternalDataProcessorOrReportFromFiles`, `/AllowExecuteScheduledJobs`,
`CmdLine/UserName`, `CmdLine/UserPassword`, `CmdLine/ExplAuthDlg`, `/DisableStartupDialogs`,
`/DisableStartupMessages`. Имена, которых в замере нет (`/NoConfigChanges`, `/CmdLineParam`), в
команду не подставляются.

Форма команды каждого варианта — запись таблицы `VARIANT_COMMAND` (режим запуска + команда с
аргументами-метками) и `VARIANT_TAIL` (хвост авторизации): вариант наблюдения — это имя строки
таблицы, а не ветвление в коде.

Правила прогона (наблюдение контура): 1С-прогоны выполняются строго по одному. Поэтому по
умолчанию запускается один вариант; лестницы идут последовательно.

Лестницы наблюдения, каждая запись — тройка (вариант, текст программы, кодирование), ровно одна
изменённая позиция на шаг; фактические изменения считаются функцией `ladder_step_diffs` и
записываются в отчёт (`ladder_diffs`, `ladder_single_variable`, `ladder_single_command_part`):

* `--sweep` — лестница кодирования и способа авторизации (исключает кодирование файла программы
  как причину отказа: `runscript` при 851, 1401 и 1398 байтах программы даёт идентичный исход);
* `--programs` — лестница текстов программы при одном режиме `runscript` (битая программа,
  ошибка исполнения, отсутствующий файл программы, ASCII-only программа на английских алиасах,
  пустая программа). Она нужна потому, что «режим не принят» и «файл программы не прочитан»
  наблюдаемо неразличимы: у каждого текста свой ожидаемый след отказа.
* `--controls` — лестница заведомо известных команд рядом со спорной: `/LoadConfigFromFiles`
  (подтверждён гейтом) с аргументом, без аргумента и с несуществующим каталогом плюс `/RunScript`
  без аргумента и с файлом программы. Она даёт эталоны классов исходов и различает «имя команды
  не распознано» с «имя распознано, но аргумент не найден».
* `--negative` — лестница заведомо нераспознанных имён команд рядом с `runscript`: если исход
  совпадает, «код 1 + пустой `/Out` за секунды» есть сигнатура нераспознанной команды.
* `--auth` — лестница авторизации: рабочая команда `/LoadConfigFromFiles` с `/authoff`,
  `-AllUsers`, `-CurrentUser` и парой `-User`/`-Pwd`. Отличает «имя авторизации не принято» от
  «имя принято, но на загрузку конфигурации не влияет».
* `--test` — лестница имён тестовой группы замера и соседей `RunScript` в таблице имён платформы
  (внешняя обработка из файлов, очередь фоновых заданий), плюс сравнение режима запуска
  `DESIGNER`/`ENTERPRISE` как единственной переменной первого шага.

    python scripts/exec_probe.py --variant runscript
    python scripts/exec_probe.py --variant runscript-authoff --json reports/exec-runscript.json
    python scripts/exec_probe.py --all --json reports/exec-all.json
    python scripts/exec_probe.py --sweep --json reports/exec-12-sweep.json
    python scripts/exec_probe.py --programs --timeout 40 --json reports/exec-12-programs.json
    python scripts/exec_probe.py --controls --timeout 60 --json reports/exec-12-controls.json
    python scripts/exec_probe.py --negative --timeout 60 --json reports/exec-12-negative.json
    python scripts/exec_probe.py --auth --timeout 40 --json reports/exec-13-auth.json
    python scripts/exec_probe.py --test --timeout 30 --json reports/exec-13-test.json
"""
from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import ib_loop                                                     # noqa: E402
import paths                                                       # noqa: E402

MARKER_NAME = "exec_marker.txt"
# Кодирование файла программы — переменная наблюдения, а не деталь: платформа читает внешний
# текстовый файл, и `utf-8` без BOM для кириллических ключевых слов — уже hypothesis, а не факт.
ENCODINGS = {"utf-8": "utf8", "utf-8-sig": "utf8bom", "cp1251": "cp1251"}
PROGRAM = """// Программа оставляет след сама, независимо от /Out: маркерный файл.
// Читает метаданные загруженной конфигурации, чтобы отличить "не выполнилось" от "не показали".
Путь = "$marker$";
Язык = "";
Справочники = 0;
Попытка
    Язык = Метаданные.Языки[0].КодЯзыка;
    Справочники = Метаданные.Справочники.Количество();
Исключение
    Язык = "ошибка: " + ОписаниеОшибки();
КонецПопытки;
Текст = "ВЫПОЛНЕНО|язык=" + Язык + "|справочников=" + Формат(Справочники, "ЧН=0") + "|версия=" + Метаданные.Версия;
Сообщить(Текст);
Попытка
    Документ = Новый ТекстовыйДокумент;
    Документ.УстановитьТекст(Текст);
    Документ.Записать(Путь, КодировкаТекста.UTF8);
Исключение
    Файл = Новый ЗаписьТекста(Путь, КодировкаТекста.UTF8);
    Файл.Записать(Текст);
    Файл.Закрыть();
КонецПопытки;
"""


# Различающие тексты программы. Наблюдение `runscript` (код 1 за 2.0 с, 3 байта `/Out` = пусто,
# ни строки в собственном stdout/stderr процесса, следа нет) одинаково объясняется двумя
# утверждениями: «режим не принят» и «файл программы не прочитан». Поэтому меняется не режим и не
# кодирование, а сама программа: у каждого текста свой ожидаемый след отказа, и они различимы.
#   broken  — незакрытая скобка: если файл прочитан, ошибка синтаксиса обязана появиться в `/Out`;
#   runtime — ссылка на несуществующее имя: читается ли программа вообще;
#   missing — файл не создаётся вовсе: контроль «несуществующий путь программы»;
#   ascii   — только английские алиасы, в файле нет ни одного байта кириллицы: снимает
#             hypothesis о кодировании без её перебора;
#   empty   — только комментарий: пустая программа (ожидаемый исход — выполниться без вывода).
PROGRAMS = {
    "marker": PROGRAM,
    "broken": """// Программа с заведомой синтаксической ошибкой: незакрытая скобка вызова.
Сообщить("файл прочитан";
""",
    "runtime": """// Программа с ошибкой исполнения: имя не определено.
Сообщить(ИмениКоторогоНетВПрироде);
""",
    "ascii": """// ASCII-only program: English aliases only, no Cyrillic bytes in the file.
Text = "ASCII-RUNSCRIPT";
Try
    Text = Text + "|lang=" + Metadata.Languages[0].LanguageCode;
Except
    Text = Text + "|metadata-failed";
EndTry;
Message(Text);
Try
    Doc = New TextDocument;
    Doc.SetText(Text);
    Doc.Write("$marker$");
Except
    Message("marker-write-failed");
EndTry;
""",
    "empty": """// Пустая программа: только комментарий, ни одного оператора.
""",
    # `missing` — не текст, а отсутствие файла: `prepare_script` его не создаёт.
    "missing": "",
}


def prepare_script(work: pathlib.Path, variant: str, label: str, program: str,
                   encoding: str, marker: pathlib.Path, write_script: bool) -> tuple:
    """Файл программы прогона: путь и создан ли он. Платформу не запускает.

    Для `missing` файл не пишется и удаляется, если остался от прежнего прогона: иначе прогон
    «несуществующего пути» молча использует чужую программу, и наблюдение теряет смысл.
    """
    script = work / f"exec_{variant}_{label}.txt"
    if not write_script:
        if script.exists():
            script.unlink()
        return script, False
    work.mkdir(parents=True, exist_ok=True)
    # Перевод строки фиксируем `\n`, а не берём системный: байты файла программы тогда ровно
    # равны `program_text(...).encode(encoding)`, и учёт байт в отчёте сходится (иначе к каждому
    # шагу лестницы добавлялся бы неучтённый CR, и размеры шагов, различающихся только
    # кодированием, не сходились бы).
    script.write_text(program_text(program, marker), encoding=encoding, newline="\n")
    return script, True


# Аргументы команды наблюдения, которые подставляет `variant_argv`: каталог конфигурации
# (`--cfg`), файл BSL-программы прогона и несуществующий каталог (контроль `load-baddir`).
CFG_ARG, SCRIPT_ARG, BADDIR_ARG = "cfg", "script", "baddir"

# Вариант наблюдения -> (режим запуска, команда с аргументом). Имена команд взяты из замера
# `p1c/src/p1c/data/test_cli_flags.json`; варианта без имени команды нет: платформа без команды
# запускает графический интерфейс, и это не наблюдение.
VARIANT_COMMAND = {
    # Контроль на заведомо рабочей команде (`--controls`).
    "load-ok": ("DESIGNER", ["/LoadConfigFromFiles", CFG_ARG]),
    "load-noarg": ("DESIGNER", ["/LoadConfigFromFiles"]),
    "load-baddir": ("DESIGNER", ["/LoadConfigFromFiles", BADDIR_ARG]),
    # Лестница авторизации: команда та же, меняется только способ входа.
    "load-authoff": ("DESIGNER", ["/LoadConfigFromFiles", CFG_ARG]),
    "load-allusers": ("DESIGNER", ["/LoadConfigFromFiles", CFG_ARG]),
    "load-currentuser": ("DESIGNER", ["/LoadConfigFromFiles", CFG_ARG]),
    "load-credentials": ("DESIGNER", ["/LoadConfigFromFiles", CFG_ARG]),
    # Исполнение BSL-программы (Task 12).
    "runscript": ("DESIGNER", ["/RunScript", SCRIPT_ARG]),
    "runscript-noarg": ("DESIGNER", ["/RunScript"]),
    "runscript-authoff": ("DESIGNER", ["/RunScript", SCRIPT_ARG]),
    "runscript-credentials": ("DESIGNER", ["/RunScript", SCRIPT_ARG]),
    "runscript-currentuser": ("DESIGNER", ["/RunScript", SCRIPT_ARG]),
    "runscript-external": ("DESIGNER", ["/RunScript", SCRIPT_ARG]),
    "execute": ("DESIGNER", ["/EXECUTE", SCRIPT_ARG]),
    "execute-authoff": ("DESIGNER", ["/EXECUTE", SCRIPT_ARG]),
    # Тестовая группа имён (Task 13): ровно те имена, которые даёт правило группы замера.
    # `CmdLine/TestClientFile` и подобные — ключи, а не флаги: в argv их не подставляют.
    "testclient-plain": ("DESIGNER", ["/TESTCLIENT"]),
    "testclient-file": ("DESIGNER", ["/TESTCLIENT", SCRIPT_ARG]),
    "testmanager-plain": ("DESIGNER", ["/TESTMANAGER"]),
    "testmanager-file": ("DESIGNER", ["/TESTMANAGER", SCRIPT_ARG]),
    "testfile-flag": ("DESIGNER", ["-testFile", SCRIPT_ARG]),
    "testout-flag": ("DESIGNER", ["-testOut", SCRIPT_ARG]),
    "testonly-flag": ("DESIGNER", ["-TestOnly"]),
    # Соседи `RunScript` в таблице имён платформы (Task 12/13): загрузка внешней обработки
    # из файлов и разрешение очереди фоновых заданий.
    "extproc-file": ("DESIGNER", ["/LoadExternalDataProcessorOrReportFromFiles", SCRIPT_ARG]),
    # Та же команда без аргумента: по контролю `load-noarg` («Файл не обнаружен ''») это различает
    # «имя команды распознано, но аргумента нет» и «имя команды не распознано молча».
    "extproc-noarg": ("DESIGNER", ["/LoadExternalDataProcessorOrReportFromFiles"]),
    # Наблюдение `extproc-file`/`extproc-noarg` показало: команда читает аргумент (печатает
    # «Файл 'file://<путь>' не является файлом обработки или отчета»), а при отсутствии
    # аргументов печатает мусорные строки в обеих — «Корневой файл выгрузки» и «Целевой каталог
    # или файл». Значит аргумента два, и их наличие платформа не проверяет.
    "extproc-twoargs": ("DESIGNER", ["/LoadExternalDataProcessorOrReportFromFiles",
                                     SCRIPT_ARG, BADDIR_ARG]),
    # Обратная команда — выгрузка внешней обработки/отчёта в файлы. Печатные строки платформы
    # подписывают аргументы по позициям: arg1 -> «Каталог или корневой файл выгрузки»,
    # arg2 -> «Входной бинарный файл» (замер `reports/exec-14-dumpproc-args.json`, где arg1 —
    # файл программы, arg2 — несуществующий каталог). Подтверждённая рабочая форма
    # `/DumpExternalDataProcessorOrReportToFiles <каталог или корневой файл выгрузки>
    # <входной бинарный файл .epf>` с кодом 0 — в замере `probe/epf_roundtrip.py`
    # (`reports/epf-15-roundtrip.json`); обратный порядок даёт «... является путем к директории,
    # в то время как ожидается путь к файлу».
    "dumpproc-args": ("DESIGNER", ["/DumpExternalDataProcessorOrReportToFiles",
                                   SCRIPT_ARG, BADDIR_ARG]),
    "jobs-allow": ("DESIGNER", ["/AllowExecuteScheduledJobs"]),
    # Тот же `/RunScript`, но в режиме `1С:Предприятие`: различие только в режиме запуска.
    "enterprise-runscript": ("ENTERPRISE", ["/RunScript", SCRIPT_ARG]),
    # Режим `1С:Предприятие` без команды: проверка, есть ли в ИБ зарегистрированные пользователи.
    "enterprise-plain": ("ENTERPRISE", []),
}

# Хвост авторизации варианта. Имена `-User`, `-Pwd`, `-PUser`, `-CurrentUser`, `-AllUsers` и
# `/authoff` — из замера 426 имён; `-User`/`-Pwd` соответствуют ключам `CmdLine/UserName` и
# `CmdLine/UserPassword`. Значение присоединяется через `=`, как в других измеренных именах.
VARIANT_TAIL = {
    "load-authoff": ["/authoff"],
    "load-allusers": ["-AllUsers"],
    "load-currentuser": ["-CurrentUser"],
    "load-credentials": ["-User=1CTest", "-Pwd=1CTest"],
    "runscript-authoff": ["/authoff"],
    "runscript-credentials": ["-User=1CTest", "-Pwd=1CTest"],
    "runscript-currentuser": ["-CurrentUser"],
    "runscript-external": ["-ExternalConnection"],
    "execute-authoff": ["/authoff"],
    "enterprise-plain": ["/authoff"],
}

VARIANTS = tuple(VARIANT_COMMAND)

# Варианты без имени команды: они наблюдают, что делает режим запуска без команды (режим
# `1С:Предприятие` без авторизованного пользователя в ИБ). Названы списком, чтобы «забыли имя
# команды» не выглядело нормой: тест сверяет пустые команды таблиц с этим списком.
NO_COMMAND_VARIANTS = ("enterprise-plain",)


def needs_script(variant: str) -> bool:
    """Нужен ли прогону файл BSL-программы: только если команда подставляет его аргументом."""
    command = VARIANT_COMMAND.get(variant)
    return bool(command) and SCRIPT_ARG in command[1]


def variant_signature(variant: str) -> dict:
    """Форма команды варианта: режим, имена команд, вид аргументов, хвост авторизации.

    Пути (каталог конфигурации, файл программы, несуществующий каталог) заменяются метками
    `cfg`/`script`/`baddir`, чтобы сравнивать форму команды, а не конкретные пути прогона.
    """
    if variant in VARIANT_COMMAND:
        mode, template = VARIANT_COMMAND[variant]
    elif variant in NEGATIVE_CONTROLS:
        mode, template = "DESIGNER", [NEGATIVE_CONTROLS[variant]]
    else:
        raise KeyError(f"нет формы команды для варианта {variant}")
    placeholders = (CFG_ARG, SCRIPT_ARG, BADDIR_ARG)
    return {"mode": mode,
            "names": tuple(item for item in template if item not in placeholders),
            "args": tuple(item for item in template if item in placeholders),
            "tail": tuple(VARIANT_TAIL.get(variant, ()))}


def signature_diff(left: dict, right: dict) -> list:
    """Какие части формы команды различаются: `mode`, `names`, `args`, `tail`."""
    return sorted(key for key in ("args", "mode", "names", "tail") if left[key] != right[key])


def ladder_step_diffs(ladder: tuple) -> list:
    """Соседние шаги лестницы: что изменено в тройке и что сдвинулось в форме команды.

    Лестница строится так, чтобы на шаг менялась ровно одна позиция тройки (текст программы,
    кодирование или вариант — режим наблюдения). Если менялся вариант, отдельно показывается,
    какая ровно часть формы команды (`mode`/`names`/`args`/`tail`) при этом сдвинулась: у лестниц
    команд (`TEST_LADDER`, `AUTH_LADDER`) она тоже одиночная, иначе наблюдение нельзя отнести на
    счёт одного изменения.
    """
    triples = [(variant, program, encoding) for variant, program, encoding in ladder]
    steps = []
    for index, triple in enumerate(triples):
        variant = triple[0]
        signature = variant_signature(variant)
        if index == 0:
            # Базовый шаг: сравнивать не с чем, он и есть эталон сравнения.
            changed_triple, changed_command = [], []
        else:
            previous_triple = triples[index - 1]
            changed_triple = [name for name, position in zip(("variant", "program", "encoding"),
                                                              range(3))
                              if previous_triple[position] != triple[position]]
            changed_command = signature_diff(steps[-1]["signature"], signature)
        steps.append({"from": triples[index - 1][0] if index else "",
                      "to": variant,
                      "changed_triple": changed_triple,
                      "changed_command": changed_command,
                      "single_variable": index == 0 or len(changed_triple) == 1,
                      "single_command_part": index == 0 or len(changed_command) <= 1,
                      "signature": signature})
    return [{key: value for key, value in step.items() if key != "signature"} for step in steps]


def variant_argv(variant: str, bin_path: str, ib: str, script: pathlib.Path,
                 out_file: pathlib.Path, marker: pathlib.Path, cfg: str = "",
                 work: pathlib.Path | None = None) -> list:
    """Команда платформы для одного варианта наблюдения.

    Все варианты начинаются с имени режима запуска (наблюдение Task 1: иначе платформа сообщает
    «Неопределен режим запуска», код 1) и всегда дают `/Out` в файл. Имена команд берутся из
    замера имён; путь конфигурации (`--cfg`) и рабочий каталог (`--work`) даются аргументами.
    """
    if variant in VARIANT_COMMAND:
        mode, template = VARIANT_COMMAND[variant]
    elif variant in NEGATIVE_CONTROLS:
        # Отрицательный контроль: нераспознанное имя команды, без аргумента и без хвоста
        # авторизации — иначе шаг менял бы и имя команды, и способ входа сразу.
        mode, template = "DESIGNER", [NEGATIVE_CONTROLS[variant]]
    else:
        raise KeyError(f"нет формы команды для варианта {variant}")
    program = []
    for item in template:
        if item == CFG_ARG:
            program.append(cfg)
        elif item == SCRIPT_ARG:
            program.append(str(script))
        elif item == BADDIR_ARG:
            program.append(str((work or pathlib.Path("work")) / "no-such-directory"))
        else:
            program.append(item)
    base = [bin_path, mode, "/F", ib, "/Out", str(out_file), "/DisableStartupDialogs"]
    return base + program + VARIANT_TAIL.get(variant, [])


def program_text(program: str, marker: pathlib.Path) -> str:
    """Текст BSL-программы: путь маркера вписан прямыми слешами (в строке BSL обратный слеш —
    escape-символ), подстановочная метка `$marker$` заменена полностью.

    Вынесено отдельно, чтобы это было тестируемо без запуска платформы: программа, в которой
    метка осталась, ничего не записывает, и «режим не подтверждён» оказалось бы неверным
    утверждением о платформе.
    """
    return program.replace("$marker$", str(marker).replace("\\", "/"))


def run(bin_path: str, ib: str, program: str, variant: str, work: pathlib.Path,
        timeout: int = 120, encoding: str = "utf-8", program_kind: str = "marker",
        write_script: bool = True, cfg: str = "") -> dict:
    """Один прогон платформы: возвращает код, секунды, байт и строки вывода, след программы.

    Ждём циклом с `poll`, как в `ib_loop.run_step`: зависание здесь — ожидаемый исход одного из
    вариантов, и `subprocess.run(timeout=...)` его не переживает (файл вывода при этом остаётся
    непрочитанным).

    Кодирование файла программы — отдельная проверяемая переменная, а не деталь: наблюдение
    `runscript` дало код 1 за 2.0 с при пустом выводе, а это одинаково похоже и на «режим не
    принят», и на «файл программы не прочитан» (в программе кирилличные ключевые слова).
    """
    work.mkdir(parents=True, exist_ok=True)
    # Метка файла содержит и кодирование, и текст программы: прогон `missing` не должен
    # использовать файл программы от прежнего шага лестницы.
    label = f"{program_kind}_{ENCODINGS[encoding]}"
    out_file, marker = work / f"exec_{variant}_{label}_out.txt", work / MARKER_NAME
    if marker.exists():
        marker.unlink()
    if out_file.exists():
        out_file.unlink()
    script, script_written = prepare_script(work, variant, label, program, encoding,
                                            marker, write_script)
    argv = variant_argv(variant, bin_path, ib, script, out_file, marker, cfg, work)
    # Собственный stdout/stderr процесса пишутся в отдельные файлы: у отказа класса «код 1 без
    # сообщения в /Out» (наблюдение runscript) больше нигде оставаться не должно.
    console_out, console_err = (work / f"exec_{variant}_{label}_stdout.txt"), \
        (work / f"exec_{variant}_{label}_stderr.txt")
    started = time.monotonic()
    with console_out.open("wb") as stdout_handle, console_err.open("wb") as stderr_handle:
        proc = subprocess.Popen(argv, stdout=stdout_handle, stderr=stderr_handle)
    timed_out = False
    while time.monotonic() - started < timeout:
        if proc.poll() is not None:
            break
        time.sleep(1)
    else:
        timed_out = True
        proc.terminate()
        try:
            proc.wait(timeout=30)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=30)
    code = proc.returncode
    seconds = round(time.monotonic() - started, 1)
    out_bytes = out_file.read_bytes() if out_file.exists() else b""
    console = [ib_loop.decode_output(handle.read_bytes())
               for handle in (console_out, console_err)]
    return {
        "variant": variant,
        "argv": argv,
        "code": code,
        "timed_out": timed_out,
        "seconds": seconds,
        "bytes": len(out_bytes),
        "lines": ib_loop.decode_output(out_bytes).splitlines(),
        "stdout_bytes": console_out.stat().st_size if console_out.exists() else 0,
        "stderr_bytes": console_err.stat().st_size if console_err.exists() else 0,
        "console_lines": [line.strip() for chunk in console for line in chunk.splitlines() if line.strip()],
        "marker_exists": marker.is_file(),
        "marker_text": marker.read_text(encoding="utf-8-sig", errors="replace").strip()
        if marker.is_file() else "",
        "script_encoding": encoding,
        "script_encoding_bytes": len(program_text(program, marker).encode(encoding))
        if write_script else 0,
        "script_written": script_written,
        "script_bytes": script.stat().st_size if script.exists() else 0,
        "script_path": script.as_posix(),
        "program_kind": program_kind,
    }


def ladder_ok(report: dict) -> bool:
    """Лестница выдержана: на каждом шаге ровно одна позиция тройки и ровно одна часть формы команды.

    Состав исходов (зависание, пустой или непустой `/Out`) в код возврата не входит: код отвечает
    только за дисциплину наблюдения, а исходы живут в ключах отчёта (`confirmed_modes`,
    `negative_clean`, `test_classes`). Иначе находка класса «имя принято, но процесс зависает»
    ломала бы код лестницы, на которой эту находку сделали.
    """
    return bool(report.get("ladder_single_variable")) and bool(
        report.get("ladder_single_command_part", True))


def main(argv: list | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--local", default=str(ROOT / "local.paths.json"))
    parser.add_argument("--bin", default="")
    parser.add_argument("--ib", default="")
    parser.add_argument("--work", default="")
    parser.add_argument("--cfg", default="",
                        help="каталог конфигурации для контрольных прогонов /LoadConfigFromFiles")
    parser.add_argument("--variant", default="runscript", choices=sorted(VARIANTS))
    parser.add_argument("--program", default="marker", choices=sorted(PROGRAMS),
                        help="текст программы (переменная наблюдения)")
    parser.add_argument("--encoding", default="utf-8", choices=sorted(ENCODINGS),
                        help="кодирование файла программы (переменная наблюдения)")
    parser.add_argument("--all", action="store_true",
                        help="прогнать все варианты (последовательно, с --encoding)")
    parser.add_argument("--sweep", action="store_true",
                        help="лестница наблюдения SWEEP: вариант + кодирование (последовательно)")
    parser.add_argument("--programs", action="store_true",
                        help="лестница PROGRAM_LADDER: разные тексты программы при одном режиме")
    parser.add_argument("--controls", action="store_true",
                        help="лестница CONTROLS: заведомо известные команды, чтобы отличить "
                             "«команда не принята» от «команда принята, но файл не прочитан»")
    parser.add_argument("--negative", action="store_true",
                        help="лестница NEGATIVE_CONTROLS: заведомо нераспознанные имена команд "
                             "(сравнение сигнатуры отказа)")
    parser.add_argument("--auth", action="store_true",
                        help="лестница AUTH_LADDER: один и тот же рабочий `/LoadConfigFromFiles` "
                             "с разным способом входа (принимает ли платформа имена авторизации)")
    parser.add_argument("--test", action="store_true",
                        help="лестница TEST_LADDER: имена тестовой группы замера (`/TESTCLIENT`, "
                             "`/TESTMANAGER`, `-testFile`, `-testOut`, `-TestOnly`) и соседи "
                             "`RunScript` в таблице имён платформы")
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--json", default="")
    args = parser.parse_args(argv)

    local = paths.load_local(args.local)
    bin_path = args.bin or local.get("bin", "")
    ib = args.ib or local.get("ib", "")
    work = pathlib.Path(args.work or local.get("work", str(ROOT / "work")))
    cfg = args.cfg or local.get("cfg", "")
    if not bin_path or not ib:
        print("exec_probe: нужны --bin и --ib (или local.paths.json)", file=sys.stderr)
        return 2
    if (args.controls or args.auth) and not cfg:
        # Контрольные прогоны строятся на команде, исход которой известен (`/LoadConfigFromFiles`
        # даёт код 0 на рабочем каталоге конфигурации — подтверждение гейта). Без каталога контроль
        # не является контролем.
        print("exec_probe: для --controls и --auth нужен --cfg (или local.paths.json: cfg)",
              file=sys.stderr)
        return 2
    # Лестницы — тройки (режим, текст программы, кодирование): ровно одна переменная на шаг.
    if args.controls:
        ladder, ladder_name = CONTROLS, "CONTROLS"
    elif args.negative:
        # `runscript` входит в лестницу: сравнение «нераспознанное имя команды» и `runscript`
        # должно жить в одном замере, а не сводиться из двух отчётов.
        ladder, ladder_name = NEGATIVE_LADDER, "NEGATIVE_LADDER"
    elif args.auth:
        ladder, ladder_name = AUTH_LADDER, "AUTH_LADDER"
    elif args.test:
        ladder, ladder_name = TEST_LADDER, "TEST_LADDER"
    elif args.sweep:
        ladder, ladder_name = SWEEP, "SWEEP"
    elif args.programs:
        ladder, ladder_name = PROGRAM_LADDER, "PROGRAM_LADDER"
    elif args.all:
        ladder = [(variant, "marker", args.encoding) for variant in VARIANTS]
        ladder_name = "ALL_VARIANTS"
    else:
        ladder, ladder_name = [(args.variant, args.program, args.encoding)], "single"
    if not cfg and any(variant.startswith("load") for variant, _, _ in ladder):
        # Команда контроля с пустым аргументом — не наблюдение, а артефакт запуска.
        print("exec_probe: вариантам /LoadConfigFromFiles нужен --cfg (или local.paths.json: cfg)",
              file=sys.stderr)
        return 2
    # Прогон строго последовательный: 1С-прогоны не выполняются параллельно (наблюдение контура),
    # поэтому лестница идёт в этом цикле, а не через параллельный запуск.
    results = [run(bin_path, ib, PROGRAMS[kind], variant, work, args.timeout, encoding,
                   program_kind=kind,
                   # Файл программы пишется только там, где команда подставляет его аргументом:
                   # `/LoadConfigFromFiles`, `-TestOnly` и `/AllowExecuteScheduledJobs` файл
                   # программы не читают, и лишний файл в рабочем каталоге размывает границу.
                   write_script=kind != "missing" and needs_script(variant),
                   cfg=cfg)
               for variant, kind, encoding in ladder]
    for result in results:
        print("==", result["variant"], "|", result["program_kind"], "|",
              result["script_encoding"], "| код", result["code"], "|", result["seconds"], "с",
              "| байт", result["bytes"], "| файл:", result["script_bytes"],
              "| след:", result["marker_exists"], result["marker_text"][:120],
              "| исход:", outcome_key(result))
        for line in result["lines"][:12]:
            print("    вывод:", line)
        for line in result["console_lines"][:12]:
            print("    консоль:", line)
    executed = [r["variant"] for r in results if r["marker_exists"]]
    print("подтверждённые режимы:", executed or "ни один режим не подтверждён")
    report = {"results": results, "executed_variants": executed}
    # Дисциплина лестницы проверяется по самому замеру: соседние шаги должны различаться ровно
    # одной позицией тройки (текст программы, кодирование, вариант). Отдельно смотрят форму
    # команды: у лестниц команд (`--auth`, `--test`) изменение варианта должно затрагивать ровно
    # одну её часть, иначе наблюдение нельзя приписать одному изменению.
    report["ladder_name"] = ladder_name
    report["ladder_diffs"] = ladder_step_diffs(ladder)
    report["ladder_single_variable"] = all(step["single_variable"]
                                           for step in report["ladder_diffs"])
    report["ladder_single_command_part"] = all(step["single_command_part"]
                                               for step in report["ladder_diffs"])
    print("лестница:", ladder_name, "| одна позиция тройки на шаг:",
          report["ladder_single_variable"], "| одна часть команды на шаг:",
          report["ladder_single_command_part"])
    for step in report["ladder_diffs"][1:]:
        print("   шаг:", step["from"], "->", step["to"],
              "| тройка:", step["changed_triple"], "| команда:", step["changed_command"])
    if args.controls:
        # Контролем служит сам факт различимости: если все исходы совпали, контроль ничего не
        # утверждает, и вывод `runscript` остаётся двусмысленным.
        classes = sorted({outcome_key(r) for r in results})
        report["controls_classes"] = [list(key) for key in classes]
        report["controls_distinct"] = len(classes) > 1
        print("классы исходов контроля:", len(classes), classes)
        # Различение двух объяснений отказа `runscript`: совпал ли его исход с исходом
        # распознанной команды, у которой не найден аргумент (`load-noarg` -> «Файл не обнаружен
        # ''»), и отличается ли он от рабочего прогона (`load-ok` -> код 0).
        by_variant = {r["variant"]: outcome_key(r) for r in results}
        report["controls_classes_by_variant"] = {name: list(value)
                                                 for name, value in by_variant.items()}
        for name in ("runscript", "runscript-noarg"):
            if name in by_variant:
                report[f"{name}_matches_load_noarg"] = by_variant[name] == by_variant.get("load-noarg")
                report[f"{name}_matches_load_ok"] = by_variant[name] == by_variant.get("load-ok")
        print("исходы по вариантам:", report["controls_classes_by_variant"])
        for name in ("runscript", "runscript-noarg"):
            print(f"  {name}: как load-noarg =", report.get(f"{name}_matches_load_noarg"),
                  "| как load-ok =", report.get(f"{name}_matches_load_ok"))
    if args.negative:
        # Сравнение живёт в одном замере: `runscript` и нераспознанные имена. Совпадение класса
        # означает, что наблюдение `runscript` — сигнатура нераспознанной команды.
        classes = {r["variant"]: outcome_key(r) for r in results}
        run_class = classes.get("runscript")
        noarg_class = classes.get("runscript-noarg")
        bogus = [value for name, value in classes.items() if name in NEGATIVE_CONTROLS]
        report["negative_classes"] = {name: list(value) for name, value in classes.items()}
        report["negative_matches_runscript"] = bool(run_class) and all(
            value == run_class for value in bogus)
        # `runscript-noarg` имеет ту же форму команды, что и нераспознанные имена (имя + пустой
        # набор аргументов): если нераспознанные имена совпадают с ним, отказ `/RunScript`
        # описывает форму «имя команды без аргумента», а не только `/RunScript`.
        report["negative_matches_runscript_noarg"] = bool(noarg_class) and all(
            value == noarg_class for value in bogus)
        # Зависание шага делает сравнение бессмысленным: у зависшего прогона нет кода.
        report["negative_clean"] = all(not r["timed_out"] for r in results)
        print("классы нераспознанных имён:", report["negative_classes"])
        print("совпадает с runscript:", report["negative_matches_runscript"])
    if args.auth:
        # Класс исхода эталона (`load-ok` — код 0) против класса каждого способа входа:
        # совпал — имя принято и на загрузку конфигурации не повлияло; отличается — имя влияет
        # (или не принято и платформа ушла в интерактивный режим / отказ).
        classes = {r["variant"]: outcome_key(r) for r in results}
        baseline = classes.get("load-ok")
        report["auth_classes"] = {name: list(value) for name, value in classes.items()}
        report["auth_same_as_baseline"] = [name for name, value in classes.items()
                                           if value == baseline]
        report["auth_differs_from_baseline"] = [name for name, value in classes.items()
                                                if value != baseline]
        report["auth_timed_out"] = [r["variant"] for r in results if r["timed_out"]]
        print("классы авторизации:", report["auth_classes"])
        print("совпали с эталоном load-ok:", report["auth_same_as_baseline"])
        print("отличаются от эталона:", report["auth_differs_from_baseline"])
    if args.test:
        # Для каждого имени тестовой группы фиксируется, дало ли оно вывод: по контролю
        # `load-noarg` («Файл не обнаружен ''») непустой `/Out` означает распознанную команду,
        # а пустой за секунды — сигнатуру нераспознанной (наблюдение `bogus-slash`).
        classes = {r["variant"]: outcome_key(r) for r in results}
        report["test_classes"] = {name: list(value) for name, value in classes.items()}
        report["test_output_variants"] = [r["variant"] for r in results
                                          if r["bytes"] > 3 or r["console_lines"]]
        report["test_silent_variants"] = [r["variant"] for r in results
                                          if not (r["bytes"] > 3 or r["console_lines"])]
        report["test_timed_out"] = [r["variant"] for r in results if r["timed_out"]]
        print("классы тестовой группы:", report["test_classes"])
        print("вывод платформы дал:", report["test_output_variants"])
        print("молчат:", report["test_silent_variants"])
        print("зависли:", report["test_timed_out"])
    if args.json:
        out = pathlib.Path(args.json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                       encoding="utf-8")
        print("замер записан:", out.as_posix())
    if args.controls:
        return 0 if report["controls_distinct"] else 1
    if args.negative:
        # Код отвечает за дисциплину лестницы, а не за состав исходов: наблюдение `bogus-dash`
        # (зависание 40 с) — это находка, она живёт в ключе `negative_clean`, а не в коде.
        return 0 if ladder_ok(report) else 1
    if args.auth or args.test:
        # Наблюдение этих лестниц не имеет «правильного» исхода: код говорит только о том, что
        # лестница выдержана (одно изменение на шаг). Состав наблюдения — в JSON-отчёте.
        return 0 if ladder_ok(report) else 1
    report["execution_confirmed"] = bool(executed)
    return 0 if ladder_ok(report) else 1


# Контрольные прогоны. Наблюдение `--programs` показало: `runscript` даёт код 1 за 2.0 с и пустой
# `/Out` одинаково для битой программы, ошибки исполнения, отсутствующего файла и пустой программы.
# Это одно наблюдение на два разных объяснения: «команда не принята платформой» и «команда принята,
# но файл программы не прочитан».
# Контроль различает их на команде, исход которой известен: `/LoadConfigFromFiles` (гейт
# подтверждает код 0) с аргументом, без аргумента и с несуществующим каталогом. Порядок шагов
# подобран так, чтобы спорная команда `/RunScript` (без аргумента и с файлом программы) стояла
# рядом с распознанной командой без аргумента: у соседних шагов меняется ровно одна часть формы
# команды (`names` или `args`), поэтому класс исхода нельзя приписать сразу двум изменениям.
CONTROLS = (("runscript", "marker", "cp1251"), ("runscript-noarg", "marker", "cp1251"),
            ("load-noarg", "marker", "cp1251"), ("load-ok", "marker", "cp1251"),
            ("load-baddir", "marker", "cp1251"))

# Отрицательные контроли (вне `VARIANTS`): имена команд, которых нет в замере 426 имён
# `p1c/src/p1c/data/test_cli_flags.json`. Наблюдение `runscript` (код 1 за 2.0 с, пустой `/Out`)
# одинаково похоже и на «режим не принят», и на «файл программы не прочитан». Если заведомо
# отсутствующее имя даёт ровно тот же класс исхода, сигнатура «код 1 + пустой `/Out` за секунды»
# описывает нераспознанную команду, и `/RunScript` в этом режиме не исключение.
NEGATIVE_CONTROLS = {"bogus-slash": "/ZzzNetakoyKomandyNet",
                     "bogus-dash": "-ZzzNetakoyKomandyNet"}

NEGATIVE_LADDER = (("runscript", "marker", "cp1251"),
                   # `runscript-noarg` вставлен как отдельный шаг: переход `runscript ->
                   # bogus-slash` менял бы имя команды и набор аргументов сразу.
                   ("runscript-noarg", "marker", "cp1251"),
                   ("bogus-slash", "marker", "cp1251"),
                   ("bogus-dash", "marker", "cp1251"))

# Лестница авторизации (Task 13). Команда остаётся заведомо рабочей (`/LoadConfigFromFiles`,
# гейт подтверждает код 0), меняется только способ входа. Это позволяет отличить «имя авторизации
# не принято платформой» (код или зависание появились) от «имя принято, но на загрузку конфигурации
# не влияет» (исход тот же, что у `load-ok`).
# Наблюдение `bogus-slash` показало, что после нераспознанной `/`-команды платформа сообщает
# «Пользователь ИБ не идентифицирован» — значит часть исходов зависит от зарегистрированных
# пользователей ИБ, а не от самого флага.
AUTH_LADDER = (("load-ok", "marker", "cp1251"),
               ("load-authoff", "marker", "cp1251"),
               ("load-allusers", "marker", "cp1251"),
               ("load-currentuser", "marker", "cp1251"),
               ("load-credentials", "marker", "cp1251"))

# Лестница тестовой группы (Task 13). Имена взяты из группы `test` замера (12 имён): флаги
# `/TESTCLIENT`, `/TESTMANAGER`, `-testFile`, `-testOut`, `-TestOnly`; ключи `CmdLine/Test*` в argv
# не подставляют — наблюдение дефекта `p1c.test.run.command()` показало, что подстановка всех 12
# имён разом (10 ключей + взаимоисключающие `/TESTCLIENT` и `/TESTMANAGER`) даёт код 1 за секунды.
# Порядок подобран так, что соседние шаги отличаются ровно одной позицией тройки и ровно одной
# частью формы команды: первые два шага сравнивают режим запуска (`DESIGNER` -> `ENTERPRISE` и
# обратно), дальше идёт цепочка имён команды (аргумент программы убран одним отдельным шагом
# `extproc-file` -> `extproc-noarg`).
TEST_LADDER = (("runscript", "marker", "cp1251"),
               ("enterprise-runscript", "marker", "cp1251"),
               ("runscript", "marker", "cp1251"),
               ("testclient-file", "marker", "cp1251"),
               ("testfile-flag", "marker", "cp1251"),
               ("testout-flag", "marker", "cp1251"),
               ("testmanager-file", "marker", "cp1251"),
               ("extproc-file", "marker", "cp1251"),
               ("extproc-noarg", "marker", "cp1251"),
               ("jobs-allow", "marker", "cp1251"),
               ("testonly-flag", "marker", "cp1251"),
               ("testclient-plain", "marker", "cp1251"),
               ("testmanager-plain", "marker", "cp1251"))


def outcome_key(result: dict) -> tuple:
    """Класс исхода прогона: код, зависание, непустой ли `/Out`.

    Секунды в ключ не входят (2.0 с и 4.0 с — один и тот же исход), но зависят от зависания:
    наблюдение контура — отказ класса «неканоническое содержимое» даёт отсутствие кода.
    """
    return (result["code"], result["timed_out"],
            "непустой" if result["bytes"] > 3 else "пустой")


# Лестницы наблюдения (`--sweep`, `--programs`). Прогоняются последовательно, по одному
# 1С-процессу за раз. Каждая запись — тройка (вариант, текст программы, кодирование): ровно одна
# позиция отличается от шага к шагу, а смена варианта затрагивает ровно одну часть формы команды
# (`mode`, `names`, `args` или `tail`). Дисциплину считает `ladder_step_diffs`, она же попадает
# в JSON-отчёт (`ladder_diffs`, `ladder_single_variable`, `ladder_single_command_part`) и закреплена
# тестом `tests/test_exec_probe.py::TestLadders`.
#
# Первая лестница меняет кодирование файла программы, затем режим и способ авторизации.
# Наблюдение `runscript` (код 1, 2.0 с, 3 байта `/Out`, следа нет) при 851, 1401 и 1398 байтах
# программы даёт идентичный исход: кодирование исключено как причина отказа. Поэтому шаги
# `execute` идут при том же кодировании, на котором это измерено, — иначе шаг менял бы и режим,
# и кодирование сразу.
#
# Вторая лестница меняет текст программы при одном режиме. Она нужна потому, что отказ
# `runscript` неразличим: «режим не принят» и «файл программы не прочитан» дают одно и то же.
# У каждого текста свой различимый исход, поэтому лестница отвечает на вопрос, где именно
# обрывается исполнение. Текст `ascii` идёт при `cp1251`: в ascii-программе нет ни одного байта
# кириллицы, поэтому оба кодирования дают один и тот же файл, и переменой остаётся только текст.
SWEEP = (("runscript", "marker", "cp1251"), ("runscript", "marker", "utf-8-sig"),
         ("runscript", "marker", "utf-8"), ("execute", "marker", "utf-8"),
         # `execute-authoff` вставлен как отдельный шаг: переход `execute -> runscript-authoff`
         # менял бы имя команды и хвост авторизации сразу (наблюдение нельзя было бы отнести на
         # одно изменение). Шаг отвечает и на собственный вопрос: зависание `/EXECUTE` может быть
         # запросом авторизации ИБ, тогда `/authoff` даёт быстрый исход.
         ("execute-authoff", "marker", "utf-8"),
         ("runscript-authoff", "marker", "utf-8"),
         ("runscript-credentials", "marker", "utf-8"),
         ("runscript-currentuser", "marker", "utf-8"),
         ("runscript-external", "marker", "utf-8"))

PROGRAM_LADDER = (("runscript", "broken", "cp1251"), ("runscript", "runtime", "cp1251"),
                  ("runscript", "missing", "cp1251"), ("runscript", "ascii", "cp1251"),
                  ("runscript", "empty", "cp1251"))

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
