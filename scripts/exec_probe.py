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
(426 имён, `probe`-замер списка): `/RunScript`, `/EXECUTE`, `/authoff`, `-User`, `-PUser`,
`-CurrentUser`, `-ExternalConnection`, `CmdLine/UserName`, `CmdLine/UserPassword`,
`CmdLine/ExplAuthDlg`, `/DisableStartupDialogs`, `/DisableStartupMessages`.

Правила прогона (наблюдение контура): 1С-прогоны выполняются строго по одному. Поэтому по
умолчанию запускается один вариант; `--all` идёт последовательно.

Две лестницы наблюдения, каждая запись — тройка (режим, текст программы, кодирование), ровно
одна переменная на шаг:

* `--sweep` — лестница кодирования и способа авторизации (исключает кодирование файла программы
  как причину отказа: `runscript` при 873, 1423 и 1420 байтах программы даёт идентичный исход);
* `--programs` — лестница текстов программы при одном режиме `runscript` (битая программа,
  ошибка исполнения, отсутствующий файл программы, ASCII-only программа на английских алиасах,
  пустая программа). Она нужна потому, что «режим не принят» и «файл программы не прочитан»
  наблюдаемо неразличимы: у каждого текста свой ожидаемый след отказа.
* `--controls` — лестница заведомо известных команд (`/LoadConfigFromFiles` с аргументом, без
  аргумента и с несуществующим каталогом), чтобы различить классы исходов.
* `--negative` — лестница заведомо нераспознанных имён команд рядом с `runscript`: если исход
  совпадает, «код 1 + пустой `/Out` за секунды» есть сигнатура нераспознанной команды.

    python scripts/exec_probe.py --variant runscript
    python scripts/exec_probe.py --variant runscript-authoff --json reports/exec-runscript.json
    python scripts/exec_probe.py --all --json reports/exec-all.json
    python scripts/exec_probe.py --sweep --json reports/exec-12-sweep.json
    python scripts/exec_probe.py --programs --timeout 40 --json reports/exec-12-programs.json
    python scripts/exec_probe.py --controls --timeout 60 --json reports/exec-12-controls.json
    python scripts/exec_probe.py --negative --timeout 60 --json reports/exec-12-negative.json
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


def variant_argv(variant: str, bin_path: str, ib: str, script: pathlib.Path,
                 out_file: pathlib.Path, marker: pathlib.Path, cfg: str = "",
                 work: pathlib.Path | None = None) -> list:
    """Команда платформы для одного варианта наблюдения.

    Все варианты начинаются с имени режима запуска (наблюдение Task 1: иначе платформа сообщает
    «Неопределен режим запуска», код 1) и всегда дают `/Out` в файл. Имена команд берутся из
    замера имён; путь конфигурации (`--cfg`) и рабочий каталог (`--work`) даются аргументами.
    """
    base = [bin_path, "DESIGNER", "/F", ib, "/Out", str(out_file), "/DisableStartupDialogs"]
    # Форма команды выбирается по имени варианта: варианты `runscript-*` и `execute-*` различаются
    # только хвостом (способ авторизации), поэтому режим берут по префиксу.
    if variant in NEGATIVE_CONTROLS:
        program = [NEGATIVE_CONTROLS[variant]]
    elif variant == "load-ok":
        program = ["/LoadConfigFromFiles", cfg]
    elif variant == "load-noarg":
        program = ["/LoadConfigFromFiles"]
    elif variant == "load-baddir":
        program = ["/LoadConfigFromFiles", str((work or pathlib.Path("work"))
                                               / "no-such-directory")]
    elif variant == "runscript-noarg":
        program = ["/RunScript"]
    elif variant.startswith("execute"):
        program = ["/EXECUTE", str(script)]
    elif variant.startswith("runscript"):
        program = ["/RunScript", str(script)]
    else:
        raise KeyError(f"нет формы команды для варианта {variant}")
    tail = {
        "runscript": [],
        "runscript-noarg": [],
        "execute": [],
        "load-ok": [],
        "load-noarg": [],
        "load-baddir": [],
        "runscript-authoff": ["/authoff"],
        "execute-authoff": ["/authoff"],
        # `-User` и `-PUser` — имена из замера 426 имён (`p1c/src/p1c/data/test_cli_flags.json`),
        # соответствующий ключам `CmdLine/UserName` и `CmdLine/UserPassword`. Значение даётся
        # через `=`, как в остальных измеренных именах вида `-Имя`.
        "runscript-credentials": ["-User=1CTest", "-PUser=1CTest"],
        "runscript-currentuser": ["-CurrentUser"],
        "runscript-external": ["-ExternalConnection"],
    }.get(variant, [])
    # Отрицательные контроли хвоста авторизации не имеют: иначе шаг менял бы и имя команды, и
    # способ входа сразу.
    return base + program + tail


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
    if args.controls and not cfg:
        # Контрольные прогоны строятся на команде, исход которой известен (`/LoadConfigFromFiles`
        # даёт код 0 на рабочем каталоге конфигурации — подтверждение гейта). Без каталога контроль
        # не является контролем.
        print("exec_probe: для --controls нужен --cfg (или local.paths.json: cfg)",
              file=sys.stderr)
        return 2
    # Лестницы — тройки (режим, текст программы, кодирование): ровно одна переменная на шаг.
    if args.controls:
        ladder = CONTROLS
    elif args.negative:
        # `runscript` входит в лестницу: сравнение «нераспознанное имя команды» и `runscript`
        # должно жить в одном замере, а не сводиться из двух отчётов.
        ladder = NEGATIVE_LADDER
    elif args.sweep:
        ladder = SWEEP
    elif args.programs:
        ladder = PROGRAM_LADDER
    elif args.all:
        ladder = [(variant, "marker", args.encoding) for variant in VARIANTS]
    else:
        ladder = [(args.variant, args.program, args.encoding)]
    if not cfg and any(variant.startswith("load") for variant, _, _ in ladder):
        # Команда контроля с пустым аргументом — не наблюдение, а артефакт запуска.
        print("exec_probe: вариантам /LoadConfigFromFiles нужен --cfg (или local.paths.json: cfg)",
              file=sys.stderr)
        return 2
    # Прогон строго последовательный: 1С-прогоны не выполняются параллельно (наблюдение контура),
    # поэтому лестница идёт в этом цикле, а не через параллельный запуск.
    results = [run(bin_path, ib, PROGRAMS[kind], variant, work, args.timeout, encoding,
                   program_kind=kind,
                   # Файл программы пишется только там, где его читает команда: контрольные прогоны
                   # `/LoadConfigFromFiles` его не принимают, и лишний файл в рабочем каталоге
                   # лишь размывает границу наблюдения.
                   write_script=kind != "missing" and not variant.startswith("load")
                   and variant not in NEGATIVE_CONTROLS,
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
    if args.controls:
        # Контролем служит сам факт различимости: если все четыре исхода совпали, контроль
        # ничего не утверждает, и вывод `runscript` остаётся двусмысленным.
        classes = sorted({outcome_key(r) for r in results})
        report["controls_classes"] = [list(key) for key in classes]
        report["controls_distinct"] = len(classes) > 1
        print("классы исходов контроля:", len(classes), classes)
    if args.negative:
        # Сравнение живёт в одном замере: `runscript` и нераспознанные имена. Совпадение класса
        # означает, что наблюдение `runscript` — сигнатура нераспознанной команды.
        classes = {r["variant"]: outcome_key(r) for r in results}
        run_class = classes.get("runscript")
        bogus = [value for name, value in classes.items() if name in NEGATIVE_CONTROLS]
        report["negative_classes"] = {name: list(value) for name, value in classes.items()}
        report["negative_matches_runscript"] = bool(run_class) and all(
            value == run_class for value in bogus)
        # Зависание шага делает сравнение бессмысленным: у зависшего прогона нет кода.
        report["negative_clean"] = all(not r["timed_out"] for r in results)
        print("классы нераспознанных имён:", report["negative_classes"])
        print("совпадает с runscript:", report["negative_matches_runscript"])
    if args.json:
        out = pathlib.Path(args.json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                       encoding="utf-8")
        print("замер записан:", out.as_posix())
    if args.controls:
        return 0 if report["controls_distinct"] else 1
    if args.negative:
        return 0 if report["negative_clean"] else 1
    return 0 if executed else 1


VARIANTS = ("load-ok", "load-noarg", "load-baddir", "runscript", "runscript-noarg", "execute",
            "runscript-authoff", "execute-authoff", "runscript-credentials",
            "runscript-currentuser", "runscript-external")

# Контрольные прогоны. Наблюдение `--programs` показало: `runscript` даёт код 1 за 2.0 с и пустой
# `/Out` одинаково для битой программы, ошибки исполнения, отсутствующего файла и пустой программы.
# Это одно наблюдение на два разных объяснения: «команда не принята платформой» и «команда принята,
# но файл программы не прочитан». Контроль различает их на команде, исход которой известен:
# `/LoadConfigFromFiles` (гейт подтверждает код 0) с отсутствующим аргументом и с аргументом,
# указывающим на несуществующий каталог.
CONTROLS = (("load-ok", "marker", "cp1251"), ("load-noarg", "marker", "cp1251"),
            ("load-baddir", "marker", "cp1251"), ("runscript-noarg", "marker", "cp1251"))

# Отрицательные контроли (вне `VARIANTS`): имена команд, которых нет в замере 426 имён
# `p1c/src/p1c/data/test_cli_flags.json`. Наблюдение `runscript` (код 1 за 2.0 с, пустой `/Out`)
# одинаково похоже и на «режим не принят», и на «файл программы не прочитан». Если заведомо
# отсутствующее имя даёт ровно тот же класс исхода, сигнатура «код 1 + пустой `/Out` за секунды»
# описывает нераспознанную команду, и `/RunScript` в этом режиме не исключение.
NEGATIVE_CONTROLS = {"bogus-slash": "/ZzzNetakoyKomandyNet",
                     "bogus-dash": "-ZzzNetakoyKomandyNet"}

NEGATIVE_LADDER = (("runscript", "marker", "cp1251"),
                   ("bogus-slash", "marker", "cp1251"),
                   ("bogus-dash", "marker", "cp1251"))


def outcome_key(result: dict) -> tuple:
    """Класс исхода прогона: код, зависание, непустой ли `/Out`.

    Секунды в ключ не входят (2.0 с и 4.0 с — один и тот же исход), но зависят от зависания:
    наблюдение контура — отказ класса «неканоническое содержимое» даёт отсутствие кода.
    """
    return (result["code"], result["timed_out"],
            "непустой" if result["bytes"] > 3 else "пустой")


# Лестницы наблюдения (`--sweep`, `--programs`), прогоняются последовательно, по одному
# 1С-процессу за раз. Каждая запись — тройка (режим, текст программы, кодирование): ровно одна
# позиция отличается от шага к шагу (закреплено тестом
# `tests/test_exec_probe.py::TestLadders::test_consecutive_steps_change_exactly_one_variable`).
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
         ("runscript-authoff", "marker", "utf-8"),
         ("runscript-credentials", "marker", "utf-8"),
         ("runscript-currentuser", "marker", "utf-8"),
         ("runscript-external", "marker", "utf-8"))

PROGRAM_LADDER = (("runscript", "broken", "cp1251"), ("runscript", "runtime", "cp1251"),
                  ("runscript", "missing", "cp1251"), ("runscript", "ascii", "cp1251"),
                  ("runscript", "empty", "cp1251"))

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
