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

Лестницы модификаторов `/LoadConfigFromFiles`, режимов обновления и режимов запуска (Task 16). Все
они начинаются с заведомо рабочего шага `load-ok` (гейт подтверждает код 0) и дальше меняют только
хвост команды или только режим запуска, поэтому исход каждого шага приписывается ровно одному
изменённому токену (`command_tokens` в `ladder_diffs`, ключ отчёта `ladder_single_command_token`):

* `--predefined` — `/SetPredefinedDataUpdate`: форма с `=` и форма с отдельным значением, затем
  значения `Auto`, `AutoUpdate`, `DontAutoUpdate` (замер значений свойства в корпусах) и вымышленное
  значение. Отвечает на вопрос, читает ли вообще платформа этот модификатор;
* `--extensions` — `-Extension`, `-AllExtensions`, `-RebuildConfigurationExtensions`,
  `/CheckCanApplyConfigurationExtensions`; смысл опций подписан корпусом БСП (запись `PREDICTIONS`);
* `--loadopts` — `-files`, `-listFile`, `-Format` (`Hierarchical`/`Plain`): частичная загрузка по
  списку файлов. Файл списка пишет `write_loadlist` в канонической форме (UTF-8, имена через
  перенос; список — абсолютные пути корневых XML-файлов, стр. 843-844 канона);
* `--update` — `/UpdateCfg`, `/UpdateDBCfg`, модификатор `-Server` и режим запуска `CONFIG`
  (CONFIG-форма того же канонического макета обновления в УХ);
* `--modes` — режим запуска как единственная переменная: `DESIGNER` (`load-ok`, код 0 подтверждён
  прогонами гейта) -> `CONFIG` (`config-load-ok`, ровно та же команда загрузки). Отвечает на вопрос,
  принимает ли канонический CONFIG-режим макета обновления (`CONFIG {0} {1} /UpdateDBCfg -server`)
  команду `/LoadConfigFromFiles` так же, как `DESIGNER`. Без этого шага вариант `config-load-ok` не
  был бы достижим ни одной названной лестницей и остался бы «вне наблюдения».

Эти лестницы способны изменить состояние ИБ (загрузить конфигурацию целиком или по списку, создать
расширение, сменить режим обновления предопределённых данных, обновить конфигурацию или структуру
базы, загрузить конфигурацию в режиме `CONFIG`). Такие варианты перечислены в `MUTATING_VARIANTS`, не
входят в `--all` (`all_observation_variants`), и без `--allow-mutating` не запускаются вовсе (код 2).
Прогонывать их можно только на отдельной временной ИБ, созданной `scripts/ib_loop.py create`, а не на
ИБ гейта.

Предсказания (`PREDICTIONS`) записаны до прогона и имеют проверяемый источник: файл корпуса из
`local.paths.json` с цитируемым именем или отчёт контура с названным ключом; читаемость источника
проверяет `verify_prediction_sources`, а не человек. Сбывшееся предсказание требует кода возврата:
у зависшего прогона кода нет, поэтому он идёт в `predictions_unresolved`, а не в опровергнутые.

     python scripts/exec_probe.py --variant runscript
     python scripts/exec_probe.py --variant runscript-authoff --json reports/exec-runscript.json
     python scripts/exec_probe.py --all --json reports/exec-all.json
     python scripts/exec_probe.py --sweep --json reports/exec-12-sweep.json
     python scripts/exec_probe.py --programs --timeout 40 --json reports/exec-12-programs.json
     python scripts/exec_probe.py --controls --timeout 60 --json reports/exec-12-controls.json
     python scripts/exec_probe.py --negative --timeout 60 --json reports/exec-12-negative.json
     python scripts/exec_probe.py --auth --timeout 40 --json reports/exec-13-auth.json
     python scripts/exec_probe.py --test --timeout 30 --json reports/exec-13-test.json
     # Лестницы модификаторов: только на отдельной временной ИБ и только с --allow-mutating
     python scripts/exec_probe.py --predefined --allow-mutating --timeout 90 \
         --json reports/exec-16-predefined.json
     python scripts/exec_probe.py --extensions --allow-mutating --timeout 90 \
         --json reports/exec-16-extensions.json
     python scripts/exec_probe.py --loadopts --allow-mutating --timeout 90 \
         --json reports/exec-16-loadopts.json
     python scripts/exec_probe.py --update --allow-mutating --timeout 90 \
         --json reports/exec-16-update.json
     python scripts/exec_probe.py --modes --allow-mutating --timeout 90 \
         --json reports/exec-16-modes.json
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
# (`--cfg`), файл BSL-программы прогона, несуществующий каталог (контроль `load-baddir`) и файл
# списка загрузки (`-listFile`). Метки подставляются и в шаблон команды, и в хвост варианта:
# `-Extension <имя>`, `-listFile <файл>`, `-Format <значение>`. Иначе лестница не могла бы менять
# значение хвоста отдельным шагом, а тест требует ровно одной изменённой части формы команды.
CFG_ARG, SCRIPT_ARG, BADDIR_ARG, LIST_ARG, REPORT_ARG = "cfg", "script", "baddir", "listfile", "reportfile"
PLACEHOLDER_ARGS = (CFG_ARG, SCRIPT_ARG, BADDIR_ARG, LIST_ARG, REPORT_ARG)
LOADLIST_NAME = "exec_loadlist.txt"

# Имя корневого файла каталога конфигурации: оно измерено раскладкой (класс `configuration` в
# `scripts/layout.py`, проверка `corpora._looks_like_dump`) и есть в каждой выгрузке
# конфигуратора, поэтому служит значением `-files` как измеренное, а не придуманное.
LOAD_FILE_ARG = "Configuration.xml"

# Значения `-Format` взяты из канонического описания опций `/LoadConfigFromFiles` в БСП
# (запись `PREDICTIONS`): `Hierarchical` (по умолчанию) и `Plain`.
FORMAT_VALUES = ("Hierarchical", "Plain")

# Значения `/SetPredefinedDataUpdate` взяты из замера значений свойства `PredefinedDataUpdate`
# в корпусах (`docs/evidence/corpora-predefined-samples.md`: Auto 286, DontAutoUpdate 41,
# AutoUpdate 10). Канонного употребления самого имени в командной строке корпуса не дают
# (обход `probe/corpora_cli_usage.py`, отчёт `reports/corpora-cli-usage-16.json`: 242 233
# прочитанных файла, 0 вхождений `SetPredefinedDataUpdate`),
# поэтому замер значений свойства — единственный доступный источник этих значений.
PREDEFINED_VALUES = ("Auto", "AutoUpdate", "DontAutoUpdate")

# Отрицательные значения внутри лестниц: имя флага принято, но его значение вымышлено. Если итог
# совпадает с итогом при настоящем значении, платформа значение не проверяет вовсе.
BOGUS_VALUE = "ZzzNetakogoZnacheniyaNet"
BOGUS_EXTENSION_NAME = "ZzzNetakogoRasshireniyaNet"

# Имена группы проверки конфигурации, которые до этой итерации не прогоняла ни одна лестница.
# Все они измерены замером 426 имён (`p1c/src/p1c/data/test_cli_flags.json`); канон их группировки
# подписывает корпус БСП: обработчик `ПроверкаБСППередСборкой` собирает команду проверки
# (`corpora_ssl/DataProcessors/ПроверкаБСППередСборкой/Forms/Форма/Ext/Form/Module.bsl`,
# стр. 2944-2973)
#   1cv8.exe DESIGNER /IBConnectionString <строка> /N <имя> /P <пароль> /CheckConfig
#     -ConfigLogIntegrity -IncorrectReferences -ThinClient -WebClient -Server -ExternalConnection
#     -ExternalConnectionServer -ThickClientManagedApplication -ThickClientServerManagedApplication
#     -ThickClientOrdinaryApplication -ThickClientServerOrdinaryApplication -DistributiveModules
#     -UnreferenceProcedures -HandlersExistence -EmptyHandlers -ExtendedModulesCheck /Out <файл>
#   и дальше (стр. 2975-3034) НЕ смотрит на код возврата: ждёт файл отчёта и разбирает его строки
#   вида `ВидОбъекта.ИмяОбъекта`. Отчётность — наблюдение самой платформы, поэтому для этих семи
#   имён источник предсказания читается из файла корпуса.
CHECK_CORPORA_FLAGS = ("-ConfigLogIntegrity", "-IncorrectReferences", "-DistributiveModules",
                       "-UnreferenceProcedures", "-HandlersExistence", "-EmptyHandlers",
                       "-ExtendedModulesCheck")
# Остальные имена группы измерены только таблицей имён: канонического употребления в корпусах нет
# (обход `corpora_cli_usage` и `rg` по шести корпусам: 0 вхождений `-WarningsAsErrors`, `-noCheck`,
# `-Module`, `-NBegin`, `-NEnd`, `-ReportFile`, `-ReportFormat`, `-ReportType` в командной строке).
# Соседство в таблице имён (`reports/flags-24-checkgroups.json`) подписывает их принадлежность к
# группе: `-noCheck` стоит сразу после `CheckModules`/`CheckConfig`/`UpdateDBCfg`,
# `-WarningsAsErrors` — рядом с `Server`, `Right`, `Module`, `Template`, `Help`.
CHECK_UNCITED_NAMES = ("-WarningsAsErrors", "-noCheck", "-Module", "-NBegin", "-NEnd",
                       "-ReportFile", "-ReportFormat", "-ReportType")
CHECK_COMMAND_NAMES = ("/CheckModules", "/CheckConfig")
CHECK_OPTION_NAMES = CHECK_COMMAND_NAMES + CHECK_CORPORA_FLAGS + CHECK_UNCITED_NAMES

# Значения отчётных опций — только из соседства имени в таблице имён (окно `-ReportFile` замера
# `reports/flags-24-checkgroups.json`): `... SignCfg ConfigurationType mxl ReportFile ReportFormat
# txt IncludeDeletedObjects IncludeAddedObjects Full IncludeChangedObjects ReportType Brief
# ByObjectNames ByObjectIDs SecondFile MappingRule ...`. Иных значений эти имена нигде не подписаны,
# поэтому третий вариант каждого значения — заведомо вымышленный (`BOGUS_VALUE`).
REPORT_FORMAT_VALUES = ("mxl", "txt")
REPORT_TYPE_VALUES = ("Brief", "ByObjectNames", "ByObjectIDs")
# Имя файла отчёта без расширения: иначе значение `-ReportFormat` спорило бы с именем файла, и
# «отчёт создан» нельзя было бы отличить от «отчёт создан с другим расширением».
CHECK_REPORT_NAME = "exec_check_report"
# Сколько строк отчёта проверки попадает в JSON-замер: полный файл остаётся на диске, в отчёте
# нужен признак («есть строки вида `ВидОбъекта.ИмяОбъекта»»), а не весь текст.
REPORT_LINE_LIMIT = 40
# Имя модуля для значения `-Module`: измерено раскладкой нашей конфигурации
# (`cfg/CommonModules/РасчётПоказателей/Ext/Module.bsl`).
CHECK_MODULE_NAME = "РасчётПоказателей"

# Код возврата группы проверки несёт вердикт, а не отказ имени. Замер 44 прогонов на чистой ИБ
# (`reports/check-24-clean*.json`): код 0 стоит рядом со строкой `Ошибок не обнаружено`
# (`/CheckConfig`, 43 байта) и `Синтаксических ошибок не обнаружено!` (`/CheckModules`, 73 байта);
# код 101 стоит рядом со строками вида `Документ.ФактРаботы.МодульОбъекта Возможно ошибочный
# метод: "Заполнять"` (340 байт) на всех 15 шагах, следующих за первым `-ExtendedModulesCheck`.
# Отказ имени выглядит иначе: `bogus-slash` (`/ZzzNetakoyKomandyNet`) даёт код 1 и 70 байт
# `Пользователь ИБ не идентифицирован`, `bogus-dash` — зависание. Поэтому 101 читается как
# «дефекты найдены», и называть его «имя отвергнуто» нельзя.
CHECK_CLEAN_CODE = 0
CHECK_DEFECT_CODE = 101

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
    # Модификаторы `/LoadConfigFromFiles` (группы `--predefined`, `--extensions`, `--loadopts`).
    # Их смысл взят не из догадок, а из канонического описания опций в корпусе БСП (SSL): стр.
    # 469–492 файла `DataProcessors/ВстраиваниеПодсистемыРаботаСФайлами/Forms/Форма/Ext/Form/
    # Module.bsl`, дословные цитаты — `docs/evidence/cli-canonical-usage.md`:
    #   стр. 473–475 «Extension <Имя расширения> - обработка расширения с указанным именем.
    #     Если расширение успешно обработано возвращает код возврата 0. В противном случае (если
    #     расширение с указанным именем не существует или в процессе работы произошли ошибки) - 1.»
    #   стр. 476–479 «AllExtensions - загрузка только расширений (всех). Если требуемое
    #     расширение не существует, оно будет создано. ... При попытке загрузить расширение в
    #     основную конфигурацию или наоборот, будет выведена ошибка.»
    #   стр. 480–483 «files - содержит список файлов, которые требуется загрузить. Список
    #     разделяется запятыми. Не используется, если указана опция-listfile.» (и наоборот для
    #     `listfile`); стр. 485–488 — файл списка: кодировка UTF-8, имена через перенос строки,
    #     без пустых строк между именами; стр. 489–492 «format ... По умолчанию загрузка
    #     производится в иерархическом формате: Hierarchical ... Plain».
    # Там же (стр. 494–512) собрана команда: `DESIGNER /IBConnectionString <иб> /N <пользователь>
    # /P <пароль> /LoadConfigFromFiles <каталог> -listFile <файл списка> /Out <файл>
    # /DisableStartupMessages /DisableStartupDialogs`, и та же команда пишется в `load.cmd`
    # (стр. 514–517) как способ ручной загрузки.
    # Модификатор режима обновления предопределённых данных (`--predefined`). Имя команды остаётся
    # заведомо рабочим, меняется только хвост: `/SetPredefinedDataUpdate` — единственное измеренное
    # имя, содержащее `Predefined` (замер 426 имён). Канонного употребления этого имени корпуса не
    # дают (обход `probe/corpora_cli_usage.py`: 0 вхождений), поэтому лестница проверяет и имя, и
    # форму (`<имя> <значение>` против `<имя>=<значение>`), а значения берёт из замера значений
    # свойства `PredefinedDataUpdate` в корпусах.
    "load-predefined-equals-dontupdate": ("DESIGNER", ["/LoadConfigFromFiles", CFG_ARG]),
    "load-predefined-flag": ("DESIGNER", ["/LoadConfigFromFiles", CFG_ARG]),
    "load-predefined-auto": ("DESIGNER", ["/LoadConfigFromFiles", CFG_ARG]),
    "load-predefined-autoupdate": ("DESIGNER", ["/LoadConfigFromFiles", CFG_ARG]),
    "load-predefined-dontupdate": ("DESIGNER", ["/LoadConfigFromFiles", CFG_ARG]),
    "load-predefined-bogus-value": ("DESIGNER", ["/LoadConfigFromFiles", CFG_ARG]),
    # Расширения конфигурации (`--extensions`): `-Extension`, `-AllExtensions`,
    # `-RebuildConfigurationExtensions`, `/CheckCanApplyConfigurationExtensions` — все четыре имени
    # есть в замере 426 имён (дефисная форма первых трёх). Смысл опций описан корпусом БСП
    # (запись `PREDICTIONS`): `-Extension` берёт **имя расширения**, а не путь; `-AllExtensions`
    # значения не берёт и создаёт недостающие расширения по подкаталогам каталога загрузки.
    "load-extension-flag": ("DESIGNER", ["/LoadConfigFromFiles", CFG_ARG]),
    "load-extension-bogus-name": ("DESIGNER", ["/LoadConfigFromFiles", CFG_ARG]),
    "load-extension-cfgdir": ("DESIGNER", ["/LoadConfigFromFiles", CFG_ARG]),
    "load-extension-baddir": ("DESIGNER", ["/LoadConfigFromFiles", CFG_ARG]),
    "load-allextensions-baddir": ("DESIGNER", ["/LoadConfigFromFiles", CFG_ARG]),
    "load-allextensions-flag": ("DESIGNER", ["/LoadConfigFromFiles", CFG_ARG]),
    "load-rebuild-extensions": ("DESIGNER", ["/LoadConfigFromFiles", CFG_ARG]),
    "load-check-can-apply": ("DESIGNER", ["/LoadConfigFromFiles", CFG_ARG]),
    # Опции частичной загрузки (`--loadopts`): `-files`, `-listFile`, `-Format` — три имени из
    # замера 426, которые корпус БСП подписывает как опции именно `/LoadConfigFromFiles`
    # (стр. 480–492 канонического описания выше). Для p1c это самый практичный вывод: загрузка не
    # всей конфигурации, а перечисленных файлов.
    "load-files-flag": ("DESIGNER", ["/LoadConfigFromFiles", CFG_ARG]),
    "load-files-onefile": ("DESIGNER", ["/LoadConfigFromFiles", CFG_ARG]),
    "load-listfile-onefile": ("DESIGNER", ["/LoadConfigFromFiles", CFG_ARG]),
    "load-listfile-ok": ("DESIGNER", ["/LoadConfigFromFiles", CFG_ARG]),
    "load-format-flag": ("DESIGNER", ["/LoadConfigFromFiles", CFG_ARG]),
    "load-format-hierarchical": ("DESIGNER", ["/LoadConfigFromFiles", CFG_ARG]),
    "load-format-plain": ("DESIGNER", ["/LoadConfigFromFiles", CFG_ARG]),
    "load-format-bogus": ("DESIGNER", ["/LoadConfigFromFiles", CFG_ARG]),
    # Обновление конфигурации и структуры ИБ (`--update`). Канон употребления подтверждён
    # корпусом: `Пульсар/SRC/DataProcessors/УстановкаОбновлений/Templates/
    # МакетФайлаОбновленияКонфигурации/Ext/Template.txt` —
    #   CONFIG <иб> /UpdateCfg "<cf|cfu>" /Out <файл> ...  (обновление конфигурации на поддержке)
    #   CONFIG <иб> /UpdateDBCfg -Server /Out <файл> ...   (обновление конфигурации базы данных)
    # Тот же макет использует `/LoadCfg "<cf>"` и `/IBCheckAndRepair -IBCompression`.
    "update-cfg-noarg": ("DESIGNER", ["/UpdateCfg"]),
    "update-dbcfg": ("DESIGNER", ["/UpdateDBCfg"]),
    "update-dbcfg-server": ("DESIGNER", ["/UpdateDBCfg"]),
    "config-update-dbcfg-server": ("CONFIG", ["/UpdateDBCfg"]),
    # Тот же рабочий `/LoadConfigFromFiles` в режиме `CONFIG` — режиме макета обновления.
    "config-load-ok": ("CONFIG", ["/LoadConfigFromFiles", CFG_ARG]),
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
    # Группа проверки конфигурации и модулей (Task 24). Два имени команды, измеренные замером:
    # `/CheckModules` (именован лестницей `--checkkeys`) и `/CheckConfig` (`--checkconfig`).
    # Базовый шаг каждой лестницы несёт ровно канон шага `check` из `scripts/ib_loop.py`
    # (`DESIGNER` + `/CheckModules` + `-Server -ThinClient -WebClient -ExternalConnection
    # -ThickClientOrdinaryApplication` + `/Out`), исход которого подтверждён прогоном контура
    # (`check_code` = 0 в `reports/gate-14.json`).
    "check-modules-base": ("DESIGNER", ["/CheckModules"]),
    # Корпусные флаги проверки (канон БСП, см. комментарий `CHECK_CORPORA_FLAGS`): добавляются по
    # одному к тому же хвосту, в том же порядке, что и в команде корпуса.
    "check-modules-configlog": ("DESIGNER", ["/CheckModules"]),
    "check-modules-references": ("DESIGNER", ["/CheckModules"]),
    "check-modules-distributive": ("DESIGNER", ["/CheckModules"]),
    "check-modules-unreferenced": ("DESIGNER", ["/CheckModules"]),
    "check-modules-handlers": ("DESIGNER", ["/CheckModules"]),
    "check-modules-emptyhandlers": ("DESIGNER", ["/CheckModules"]),
    "check-modules-extended": ("DESIGNER", ["/CheckModules"]),
    # Остальные имена группы: шаг, который заводит файл отчёта, и по одному имени группы поверх
    # него. Порядок совпадает с порядком лестницы (`CHECK_LADDER`): вымышленное значение стоит
    # перед настоящим той же опции, а внутри группы отчётных типов первым идёт вымышленное.
    "check-modules-reportfile": ("DESIGNER", ["/CheckModules"]),
    "check-modules-warnings-as-errors": ("DESIGNER", ["/CheckModules"]),
    "check-modules-nocheck": ("DESIGNER", ["/CheckModules"]),
    "check-modules-nbegin": ("DESIGNER", ["/CheckModules"]),
    "check-modules-nend": ("DESIGNER", ["/CheckModules"]),
    "check-modules-module-bogus": ("DESIGNER", ["/CheckModules"]),
    "check-modules-module": ("DESIGNER", ["/CheckModules"]),
    "check-modules-reportformat-bogus": ("DESIGNER", ["/CheckModules"]),
    "check-modules-reportformat-mxl": ("DESIGNER", ["/CheckModules"]),
    "check-modules-reportformat-txt": ("DESIGNER", ["/CheckModules"]),
    "check-modules-reporttype-bogus": ("DESIGNER", ["/CheckModules"]),
    "check-modules-reporttype-names": ("DESIGNER", ["/CheckModules"]),
    "check-modules-reporttype-ids": ("DESIGNER", ["/CheckModules"]),
    "check-modules-reporttype-brief": ("DESIGNER", ["/CheckModules"]),
    # Та же цепь имён, но при команде `/CheckConfig`: лестница `--checkconfig` обязана быть
    # зеркалом `--checkkeys` — тот же хвост на той же позиции, другое только имя команды. Иначе
    # «одно имя команды» нельзя сравнить с «тем же набором флагов»: корпусный канон пишет именно
    # `/CheckConfig` (стр. 2953), а контур проверяет именно `/CheckModules` (`scripts/ib_loop.py`),
    # и без зеркала осталось бы неизвестным, какой из двух наборов к какой команде относится.
    "check-config-base": ("DESIGNER", ["/CheckConfig"]),
    "check-config-configlog": ("DESIGNER", ["/CheckConfig"]),
    "check-config-references": ("DESIGNER", ["/CheckConfig"]),
    "check-config-distributive": ("DESIGNER", ["/CheckConfig"]),
    "check-config-unreferenced": ("DESIGNER", ["/CheckConfig"]),
    "check-config-handlers": ("DESIGNER", ["/CheckConfig"]),
    "check-config-emptyhandlers": ("DESIGNER", ["/CheckConfig"]),
    "check-config-extended": ("DESIGNER", ["/CheckConfig"]),
    "check-config-reportfile": ("DESIGNER", ["/CheckConfig"]),
    "check-config-warnings-as-errors": ("DESIGNER", ["/CheckConfig"]),
    "check-config-nocheck": ("DESIGNER", ["/CheckConfig"]),
    "check-config-nbegin": ("DESIGNER", ["/CheckConfig"]),
    "check-config-nend": ("DESIGNER", ["/CheckConfig"]),
    "check-config-module-bogus": ("DESIGNER", ["/CheckConfig"]),
    "check-config-module": ("DESIGNER", ["/CheckConfig"]),
    "check-config-reportformat-bogus": ("DESIGNER", ["/CheckConfig"]),
    "check-config-reportformat-mxl": ("DESIGNER", ["/CheckConfig"]),
    "check-config-reportformat-txt": ("DESIGNER", ["/CheckConfig"]),
    "check-config-reporttype-bogus": ("DESIGNER", ["/CheckConfig"]),
    "check-config-reporttype-names": ("DESIGNER", ["/CheckConfig"]),
    "check-config-reporttype-ids": ("DESIGNER", ["/CheckConfig"]),
    "check-config-reporttype-brief": ("DESIGNER", ["/CheckConfig"]),
}

# Хвост шагов группы проверки. Устройство такое: измеренный префикс (канон `check` из
# `scripts/ib_loop.py`, затем семь корпусных флагов, затем `-ReportFile`) плюс РОВНО ОДНО имя
# группы. Каждый шаг после `-ReportFile` добавляет один токен поверх того же префикса, а соседний
# шаг этот токен заменяет: хвосты соседних шагов имеют одинаковую длину, и позиционное сравнение
# (`signature_tokens`) даёт ровно один изменённый токен, поэтому новая запись в
# `TOKEN_MULTI_REASON` этим лестницам не нужна.
# Такая форма важна не только для дисциплины: флаг предыдущего шага НЕ наследуется следующим. Иначе
# `-noCheck` (правдоподобно отключает проверку) или вымышленное значение `-ReportFormat` отравили бы
# наблюдение всех последующих шагов, и «имя принято» нельзя было бы отличить от «предыдущий шаг
# сломал проверку».
# Форма флагов со значением — `=`-сцепка (`-ReportFormat=mxl`), как у уже измеренных `-User=1CTest`
# и `/SetPredefinedDataUpdate=DontAutoUpdate`: флаг и значение одним токеном. Форма «флаг, затем
# значение следующим токеном» добавила бы два токена за шаг, а лестница модификаторов требует одного.
# Голые имена (`-ReportFormat` без значения) остаются неиспробованными кандидатами.
# Клиентские имена канона БСП (`-ThinClient`, `-WebClient`, `-ExternalConnection`,
# `-ThickClientServerOrdinaryApplication`) в хвост не добавлены: хвост остаётся ровно тем, что
# уже измерено прогоном контура в шаге `check` (`scripts/ib_loop.py`: `-Server`, `-ThinClient`,
# `-WebClient`, `-ExternalConnection`, `-ThickClientOrdinaryApplication`), иначе базовый шаг
# лестницы отличался бы от уже замеренного, а две лестницы — друг от друга.
CHECK_TAIL_BASE = tuple(ib_loop.CHECK_KEYS)
CHECK_TAIL_CONFIGLOG = CHECK_TAIL_BASE + ("-ConfigLogIntegrity",)
CHECK_TAIL_REFERENCES = CHECK_TAIL_CONFIGLOG + ("-IncorrectReferences",)
CHECK_TAIL_DISTRIBUTIVE = CHECK_TAIL_REFERENCES + ("-DistributiveModules",)
CHECK_TAIL_UNREFERENCED = CHECK_TAIL_DISTRIBUTIVE + ("-UnreferenceProcedures",)
CHECK_TAIL_HANDLERS = CHECK_TAIL_UNREFERENCED + ("-HandlersExistence",)
CHECK_TAIL_EMPTYHANDLERS = CHECK_TAIL_HANDLERS + ("-EmptyHandlers",)
CHECK_TAIL_EXTENDED = CHECK_TAIL_EMPTYHANDLERS + ("-ExtendedModulesCheck",)
CHECK_TAIL_REPORTFILE = CHECK_TAIL_EXTENDED + ("-ReportFile=" + REPORT_ARG,)
# Имена без значения: принято имя или нет — видно по коду возврата и строкам вывода.
CHECK_TAIL_WARNINGS = CHECK_TAIL_REPORTFILE + ("-WarningsAsErrors",)
CHECK_TAIL_NOCHECK = CHECK_TAIL_REPORTFILE + ("-noCheck",)
# Имена со значением: измеренные значения отчётных опций и заведомо вымышленное (`BOGUS_VALUE`).
CHECK_TAIL_NBEGIN = CHECK_TAIL_REPORTFILE + ("-NBegin=" + BOGUS_VALUE,)
CHECK_TAIL_NEND = CHECK_TAIL_REPORTFILE + ("-NEnd=" + BOGUS_VALUE,)
CHECK_TAIL_MODULE_BOGUS = CHECK_TAIL_REPORTFILE + ("-Module=" + BOGUS_VALUE,)
CHECK_TAIL_MODULE = CHECK_TAIL_REPORTFILE + ("-Module=" + CHECK_MODULE_NAME,)
CHECK_TAIL_FORMAT_BOGUS = CHECK_TAIL_REPORTFILE + ("-ReportFormat=" + BOGUS_VALUE,)
CHECK_TAIL_FORMAT_MXL = CHECK_TAIL_REPORTFILE + ("-ReportFormat=" + REPORT_FORMAT_VALUES[0],)
CHECK_TAIL_FORMAT_TXT = CHECK_TAIL_REPORTFILE + ("-ReportFormat=" + REPORT_FORMAT_VALUES[1],)
CHECK_TAIL_TYPE_BOGUS = CHECK_TAIL_REPORTFILE + ("-ReportType=" + BOGUS_VALUE,)
CHECK_TAIL_TYPE_NAMES = CHECK_TAIL_REPORTFILE + ("-ReportType=" + REPORT_TYPE_VALUES[1],)
CHECK_TAIL_TYPE_IDS = CHECK_TAIL_REPORTFILE + ("-ReportType=" + REPORT_TYPE_VALUES[2],)
CHECK_TAIL_TYPE_BRIEF = CHECK_TAIL_REPORTFILE + ("-ReportType=" + REPORT_TYPE_VALUES[0],)

# Хвост авторизации варианта. Имена `-User`, `-Pwd`, `-PUser`, `-CurrentUser`, `-AllUsers` и
# `/authoff` — из замера 426 имён; `-User`/`-Pwd` соответствуют ключам `CmdLine/UserName` и
# `CmdLine/UserPassword`. Значение присоединяется через `=`, как в других измеренных именах.
# Хвост шагов проверки (`check-*`) задан именованной цепью выше и в таблице ниже только
# пересчитывается: базовый шаг обеих лестниц ровно равен канону `check` из `scripts/ib_loop.py`.
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
    # Модификатор режима предопределённых данных: имя и значение живут в хвосте, а не в шаблоне
    # команды. Причина: вариант наблюдения обязан нести ровно одно имя команды (тест
    # `test_every_variant_carries_exactly_one_command`), а лестница при этом меняется одной
    # частью формы команды — хвостом.
    "load-predefined-flag": ["/SetPredefinedDataUpdate"],
    "load-predefined-auto": ["/SetPredefinedDataUpdate", "Auto"],
    "load-predefined-autoupdate": ["/SetPredefinedDataUpdate", "AutoUpdate"],
    "load-predefined-dontupdate": ["/SetPredefinedDataUpdate", "DontAutoUpdate"],
    "load-predefined-equals-dontupdate": ["/SetPredefinedDataUpdate=DontAutoUpdate"],
    # Значение, которого нет в замере значений свойства: отрицательный контроль внутри лестницы.
    "load-predefined-bogus-value": ["/SetPredefinedDataUpdate", BOGUS_VALUE],
    "load-extension-flag": ["-Extension"],
    # Имя расширения, которого нет: корпус предсказывает код возврата 1 (запись `PREDICTIONS`).
    "load-extension-bogus-name": ["-Extension", BOGUS_EXTENSION_NAME],
    "load-extension-cfgdir": ["-Extension", CFG_ARG],
    "load-extension-baddir": ["-Extension", BADDIR_ARG],
    # `-AllExtensions` с путём — вне описания опций (оно значения не берёт); шаг оставлен как
    # наблюдение того, что платформа делает с лишним positional-аргументом.
    "load-allextensions-baddir": ["-AllExtensions", BADDIR_ARG],
    "load-allextensions-flag": ["-AllExtensions"],
    "load-rebuild-extensions": ["-RebuildConfigurationExtensions"],
    "load-check-can-apply": ["/CheckCanApplyConfigurationExtensions"],
    "load-files-flag": ["-files"],
    "load-files-onefile": ["-files", LOAD_FILE_ARG],
    # `-listFile` с файлом, который списком файлов не является (корневой XML конфигурации):
    # наблюдение требования «перечисление имён через перенос строки».
    "load-listfile-onefile": ["-listFile", LOAD_FILE_ARG],
    "load-listfile-ok": ["-listFile", LIST_ARG],
    "load-format-flag": ["-listFile", LIST_ARG, "-Format"],
    "load-format-hierarchical": ["-listFile", LIST_ARG, "-Format", "Hierarchical"],
    "load-format-plain": ["-listFile", LIST_ARG, "-Format", "Plain"],
    "load-format-bogus": ["-listFile", LIST_ARG, "-Format", BOGUS_VALUE],
    # `-Server` (имя из замера) — форма канонического макета обновления: `/UpdateDBCfg -server`.
    "update-dbcfg-server": ["-Server"],
    "config-update-dbcfg-server": ["-Server"],
    # Группа проверки (`--checkkeys`, `--checkconfig`): одна и та же цепь хвостов у обеих лестниц.
    "check-modules-base": list(CHECK_TAIL_BASE),
    "check-modules-configlog": list(CHECK_TAIL_CONFIGLOG),
    "check-modules-references": list(CHECK_TAIL_REFERENCES),
    "check-modules-distributive": list(CHECK_TAIL_DISTRIBUTIVE),
    "check-modules-unreferenced": list(CHECK_TAIL_UNREFERENCED),
    "check-modules-handlers": list(CHECK_TAIL_HANDLERS),
    "check-modules-emptyhandlers": list(CHECK_TAIL_EMPTYHANDLERS),
    "check-modules-extended": list(CHECK_TAIL_EXTENDED),
    "check-modules-reportfile": list(CHECK_TAIL_REPORTFILE),
    "check-modules-warnings-as-errors": list(CHECK_TAIL_WARNINGS),
    "check-modules-nocheck": list(CHECK_TAIL_NOCHECK),
    "check-modules-nbegin": list(CHECK_TAIL_NBEGIN),
    "check-modules-nend": list(CHECK_TAIL_NEND),
    "check-modules-module-bogus": list(CHECK_TAIL_MODULE_BOGUS),
    "check-modules-module": list(CHECK_TAIL_MODULE),
    "check-modules-reportformat-bogus": list(CHECK_TAIL_FORMAT_BOGUS),
    "check-modules-reportformat-mxl": list(CHECK_TAIL_FORMAT_MXL),
    "check-modules-reportformat-txt": list(CHECK_TAIL_FORMAT_TXT),
    "check-modules-reporttype-bogus": list(CHECK_TAIL_TYPE_BOGUS),
    "check-modules-reporttype-names": list(CHECK_TAIL_TYPE_NAMES),
    "check-modules-reporttype-ids": list(CHECK_TAIL_TYPE_IDS),
    "check-modules-reporttype-brief": list(CHECK_TAIL_TYPE_BRIEF),
    "check-config-base": list(CHECK_TAIL_BASE),
    "check-config-configlog": list(CHECK_TAIL_CONFIGLOG),
    "check-config-references": list(CHECK_TAIL_REFERENCES),
    "check-config-distributive": list(CHECK_TAIL_DISTRIBUTIVE),
    "check-config-unreferenced": list(CHECK_TAIL_UNREFERENCED),
    "check-config-handlers": list(CHECK_TAIL_HANDLERS),
    "check-config-emptyhandlers": list(CHECK_TAIL_EMPTYHANDLERS),
    "check-config-extended": list(CHECK_TAIL_EXTENDED),
    "check-config-reportfile": list(CHECK_TAIL_REPORTFILE),
    "check-config-warnings-as-errors": list(CHECK_TAIL_WARNINGS),
    "check-config-nocheck": list(CHECK_TAIL_NOCHECK),
    "check-config-nbegin": list(CHECK_TAIL_NBEGIN),
    "check-config-nend": list(CHECK_TAIL_NEND),
    "check-config-module-bogus": list(CHECK_TAIL_MODULE_BOGUS),
    "check-config-module": list(CHECK_TAIL_MODULE),
    "check-config-reportformat-bogus": list(CHECK_TAIL_FORMAT_BOGUS),
    "check-config-reportformat-mxl": list(CHECK_TAIL_FORMAT_MXL),
    "check-config-reportformat-txt": list(CHECK_TAIL_FORMAT_TXT),
    "check-config-reporttype-bogus": list(CHECK_TAIL_TYPE_BOGUS),
    "check-config-reporttype-names": list(CHECK_TAIL_TYPE_NAMES),
    "check-config-reporttype-ids": list(CHECK_TAIL_TYPE_IDS),
    "check-config-reporttype-brief": list(CHECK_TAIL_TYPE_BRIEF),
}

# Варианты, которые могут изменить состояние ИБ: обновить конфигурацию или структуру базы данных,
# создать или применить расширение, загрузить конфигурацию частично (не все файлы) либо сменить
# режим обновления предопределённых данных. В `--all` они не входят: `--all` обязан оставаться
# наблюдением без побочных изменений. Лестница, которая их прогоняет, названа явно (`--predefined`,
# `--extensions`, `--loadopts`, `--update`), требует `--allow-mutating` и идёт на отдельной
# временной ИБ, а не на ИБ гейта.
MUTATING_VARIANTS = (
    "load-predefined-equals-dontupdate", "load-predefined-flag", "load-predefined-auto",
    "load-predefined-autoupdate", "load-predefined-dontupdate", "load-predefined-bogus-value",
    "load-extension-flag", "load-extension-bogus-name", "load-extension-cfgdir",
    "load-extension-baddir", "load-allextensions-baddir", "load-allextensions-flag",
    "load-rebuild-extensions",
    "load-files-flag", "load-files-onefile", "load-listfile-onefile", "load-listfile-ok",
    "load-format-flag", "load-format-hierarchical", "load-format-plain", "load-format-bogus",
    "update-cfg-noarg", "update-dbcfg", "update-dbcfg-server", "config-update-dbcfg-server",
    "config-load-ok",
)

# Остальные варианты группы `load-*` в `MUTATING_VARIANTS` не стоят, и причина записана здесь,
# а не в голове наблюдателя. Эталонный `load-ok` (и вся лестница авторизации на той же команде)
# перезагружает ровно ту конфигурацию, которая уже загружена в ИБ: это делает гейт на каждом
# прогоне, и повторимость измерения подтверждена (`reports/gate-*.json`). Прогонять их можно на
# ИБ гейта. Остальные — загрузка не начинается (аргумента нет или каталога нет) либо чтение.
NON_MUTATING_LOAD_REASONS = {
    "load-ok": "эталон: перезагрузка той же конфигурации, повторимость подтверждена прогонами гейта",
    "load-authoff": "та же команда, что `load-ok`, меняется только способ входа",
    "load-allusers": "та же команда, что `load-ok`, меняется только способ входа",
    "load-currentuser": "та же команда, что `load-ok`, меняется только способ входа",
    "load-credentials": "та же команда, что `load-ok`, меняется только способ входа",
    "load-noarg": "загрузка не начинается: «Файл не обнаружен ''» (подтверждено `--controls`)",
    "load-baddir": "загрузка не начинается: каталога нет (подтверждено `--controls`)",
    "load-check-can-apply": "проверка возможности применить расширения: состояние не меняется; "
                            "если наблюдение покажет обратное, вариант уедет в MUTATING_VARIANTS",
}

# Разрешённые режимы запуска и их происхождение. `DESIGNER` и `ENTERPRISE` подтверждены прогонами
# контура; `CONFIG` — из канонического макета обновления корпуса (см. комментарий к
# `update-cfg-noarg`), а не придуман: макет УХ пишет `CONFIG {0} {1} /UpdateDBCfg -server ...`.
# Наблюдение корпусов (`probe/corpora_cli_usage.py`): ERP-версия того же макета пишет
# `DESIGNER {0} {1} /UpdateDBCfg -server ...` (стр. 852), УХ-версия — `CONFIG ...` (стр. 817).
# Оба режима каноничны; `{0}` — путь к ИБ без `/F`, `{1}` — `/N"<имя>" /P"<пароль>" /WA-`
# (стр. 1143 макета ERP). Наш контур держит `/F <иб>`: эта форма подтверждена прогонами гейта.
LAUNCH_MODES = {"DESIGNER": "подтверждено прогонами контура (гейт, лестницы); канон ERP-макета",
                "ENTERPRISE": "подтверждено прогонами контура (наблюдение о окнах)",
                "CONFIG": "канон корпуса: CONFIG-форма макета ОбновленияКонфигурации (УХ)"}

VARIANTS = tuple(VARIANT_COMMAND)


def all_observation_variants() -> tuple:
    """`VARIANTS` без `MUTATING_VARIANTS`: из них состоит `--all`, оно не меняет состояние ИБ."""
    return tuple(variant for variant in VARIANTS if variant not in MUTATING_VARIANTS)


# Предсказания, записанные ДО прогона, и их источник. Смысл: лестница проверяет не «что вышло», а
# «сбылось ли написанное разработчиком платформы». Источник обязан быть читаемым: файл корпуса из
# `local.paths.json` (ключ `corpora_*`) или отчёт контура в `reports/`; его проверяет
# `verify_prediction_sources`, а не мы на глаз.
#   kind = `corpora` — цитата из файла корпуса (`PREDICTION_SOURCE`), `needle` обязана в нём
#     встречаться; kind = `kontur` — цитата из отчёта контура (`source_key` обязан дать 0).
#   predicts = `code0` (ожидаем код возврата 0) или `nonzero` (ожидаем не 0, зависание не считается
#     сбывшимся предсказанием: код при зависании отсутствует).
PREDICTION_SOURCE = ("corpora_ssl",
                     "DataProcessors/ВстраиваниеПодсистемыРаботаСФайлами/Forms/Форма/Ext/Form/"
                     "Module.bsl")
PREDICTION_KINDS = ("corpora", "kontur")
PREDICTION_OUTCOMES = ("code0", "nonzero")

# Источник предсказаний группы проверки (Task 24) — обработчик `ПроверкаБСППередСборкой`: он сам
# собирает команду проверки (стр. 2944-2973) и сам читает её отчёт (стр. 2996-3032). Это единственный
# доступный источник, который связывает имена группы проверки с рабочей командой платформы.
CHECK_PREDICTION_SOURCE = ("corpora_ssl",
                           "DataProcessors/ПроверкаБСППередСборкой/Forms/Форма/Ext/Form/Module.bsl")


def prediction_source(record: dict) -> tuple:
    """Путь источника корпусного предсказания: общий `PREDICTION_SOURCE` либо источник, записанный
    в самой предсказании (`corpora_source`) — у группы проверки он свой, со своей цитатой."""
    return record.get("corpora_source", PREDICTION_SOURCE)


# Предсказания группы проверки (Task 24). Смысл предсказания здесь — «имя принято платформой», а не
# «дефект найден»: канон корпуса добавляет все эти имена в одну команду (`/CheckConfig` и флаги),
# значит отказ имени делает каноническую проверку корпуса нерабочей. Отчёт корпуса при этом НЕ
# проверяет код процесса: исход «нашёл прогон дефект или нет» живёт в строках отчёта и в ключах
# `check_object_names` замера, а не в предсказании.
# Базовый шаг `--checkkeys` предсказан прогоном контура: `check_code` = 0 (гейт). Базовый шаг
# `--checkconfig` предсказан корпусом: он называет это имя команды в своей команде проверки.
PREDICTIONS = {
    "load-ok": {"kind": "kontur", "predicts": "code0", "source": "reports/gate-11.json",
                "source_key": "load_code", "needle": "load_code",
                "quote": "гейт: `load_code` = 0 при загрузке этой же конфигурации (5.1 с)",
                "note": "этот шаг — эталон сравнения всех лестниц модификаторов"},
    "load-extension-bogus-name": {"kind": "corpora", "predicts": "nonzero", "needle": "-Extension",
                                  "quote": "«если расширение с указанным именем не существует или "
                                           "в процессе работы произошли ошибки) - 1» (стр. 475)",
                                  "note": "расширения с таким именем в ИБ нет"},
    "load-allextensions-flag": {"kind": "corpora", "predicts": "nonzero", "needle": "AllExtensions",
                                "quote": "«При попытке загрузить расширение в основную "
                                         "конфигурацию или наоборот, будет выведена ошибка» "
                                         "(стр. 479)",
                                "note": "каталог загрузки — основная конфигурация, не расширение"},
    "load-listfile-ok": {"kind": "corpora", "predicts": "code0", "needle": "listfile",
                         "quote": "«listfile - указывает файл, в котором перечислены файлы, "
                                  "которые требуется загрузить» (стр. 482)",
                         "note": "файл списка содержит ровно те же 31 имя, что загружает `load-ok`"},
    "load-format-hierarchical": {"kind": "corpora", "predicts": "code0", "needle": "format",
                                 "quote": "«По умолчанию загрузка производится в иерархическом "
                                          "формате: Hierarchical» (стр. 490-491)",
                                 "note": "значение из канона БСП"},
    "load-format-plain": {"kind": "corpora", "predicts": "code0", "needle": "Plain",
                          "quote": "«Plain - загрузка выполняется в линейном формате» (стр. 492)",
                          "note": "значение из канона БСП"},
    # Группа проверки (`--checkkeys`, `--checkconfig`). Базовый шаг первой лестницы — эталон,
    # подтверждённый прогоном контура; остальные предсказаны цитатой корпуса.
    "check-modules-base": {"kind": "kontur", "predicts": "code0", "source": "reports/gate-14.json",
                           "source_key": "check_code", "needle": "check_code",
                           "quote": "гейт: `check_code` = 0 при `DESIGNER /CheckModules` с "
                                    "модификаторами `CHECK_KEYS` (2.0 с, 73 байта `/Out`)",
                           "note": "этот шаг — эталон сравнения обеих лестниц группы проверки"},
    "check-config-base": {"kind": "corpora", "predicts": "code0",
                          "corpora_source": CHECK_PREDICTION_SOURCE, "needle": "/CheckConfig",
                          "quote": "канон корпуса добавляет в команду проверки «/CheckConfig» "
                                   "(стр. 2953)",
                          "note": "предсказание отвечает только на «имя принято»: код процесса "
                                  "канон не разбирает, отчёт он читает из файла `/Out`"},
    "check-modules-configlog": {"kind": "corpora", "predicts": "code0",
                                "corpora_source": CHECK_PREDICTION_SOURCE,
                                "needle": "-ConfigLogIntegrity",
                                "quote": "канон корпуса добавляет в команду проверки "
                                         "«-ConfigLogIntegrity» (стр. 2954)",
                                "note": "корпус называет этот флаг при `/CheckConfig`, здесь он "
                                        "идёт при `/CheckModules`"},
    "check-config-configlog": {"kind": "corpora", "predicts": "code0",
                               "corpora_source": CHECK_PREDICTION_SOURCE,
                               "needle": "-ConfigLogIntegrity",
                               "quote": "канон корпуса добавляет в команду проверки "
                                        "«-ConfigLogIntegrity» (стр. 2954)",
                               "note": "тот же флаг при той же команде, что и в каноне"},
    "check-modules-references": {"kind": "corpora", "predicts": "code0",
                                 "corpora_source": CHECK_PREDICTION_SOURCE,
                                 "needle": "-IncorrectReferences",
                                 "quote": "канон корпуса добавляет в команду проверки "
                                          "«-IncorrectReferences» (стр. 2955)",
                                 "note": "корпус называет этот флаг при `/CheckConfig`, здесь он "
                                         "идёт при `/CheckModules`"},
    "check-config-references": {"kind": "corpora", "predicts": "code0",
                                "corpora_source": CHECK_PREDICTION_SOURCE,
                                "needle": "-IncorrectReferences",
                                "quote": "канон корпуса добавляет в команду проверки "
                                         "«-IncorrectReferences» (стр. 2955)",
                                "note": "тот же флаг при той же команде, что и в каноне"},
    "check-modules-distributive": {"kind": "corpora", "predicts": "code0",
                                   "corpora_source": CHECK_PREDICTION_SOURCE,
                                   "needle": "-DistributiveModules",
                                   "quote": "канон корпуса добавляет в команду проверки "
                                            "«-DistributiveModules» (стр. 2965)",
                                   "note": "корпус называет этот флаг при `/CheckConfig`, здесь "
                                           "он идёт при `/CheckModules`"},
    "check-config-distributive": {"kind": "corpora", "predicts": "code0",
                                  "corpora_source": CHECK_PREDICTION_SOURCE,
                                  "needle": "-DistributiveModules",
                                  "quote": "канон корпуса добавляет в команду проверки "
                                           "«-DistributiveModules» (стр. 2965)",
                                  "note": "тот же флаг при той же команде, что и в каноне"},
    "check-modules-unreferenced": {"kind": "corpora", "predicts": "code0",
                                   "corpora_source": CHECK_PREDICTION_SOURCE,
                                   "needle": "-UnreferenceProcedures",
                                   "quote": "канон корпуса добавляет в команду проверки "
                                            "«-UnreferenceProcedures» (стр. 2966)",
                                   "note": "корпус называет этот флаг при `/CheckConfig`, здесь "
                                           "он идёт при `/CheckModules`"},
    "check-config-unreferenced": {"kind": "corpora", "predicts": "code0",
                                  "corpora_source": CHECK_PREDICTION_SOURCE,
                                  "needle": "-UnreferenceProcedures",
                                  "quote": "канон корпуса добавляет в команду проверки "
                                           "«-UnreferenceProcedures» (стр. 2966)",
                                  "note": "тот же флаг при той же команде, что и в каноне"},
    "check-modules-handlers": {"kind": "corpora", "predicts": "code0",
                               "corpora_source": CHECK_PREDICTION_SOURCE,
                               "needle": "-HandlersExistence",
                               "quote": "канон корпуса добавляет в команду проверки "
                                        "«-HandlersExistence» (стр. 2967)",
                               "note": "корпус называет этот флаг при `/CheckConfig`, здесь он "
                                       "идёт при `/CheckModules`"},
    "check-config-handlers": {"kind": "corpora", "predicts": "code0",
                              "corpora_source": CHECK_PREDICTION_SOURCE,
                              "needle": "-HandlersExistence",
                              "quote": "канон корпуса добавляет в команду проверки "
                                       "«-HandlersExistence» (стр. 2967)",
                              "note": "тот же флаг при той же команде, что и в каноне"},
    "check-modules-emptyhandlers": {"kind": "corpora", "predicts": "code0",
                                    "corpora_source": CHECK_PREDICTION_SOURCE,
                                    "needle": "-EmptyHandlers",
                                    "quote": "канон корпуса добавляет в команду проверки "
                                             "«-EmptyHandlers» (стр. 2968)",
                                    "note": "корпус называет этот флаг при `/CheckConfig`, здесь "
                                            "он идёт при `/CheckModules`"},
    "check-config-emptyhandlers": {"kind": "corpora", "predicts": "code0",
                                   "corpora_source": CHECK_PREDICTION_SOURCE,
                                   "needle": "-EmptyHandlers",
                                   "quote": "канон корпуса добавляет в команду проверки "
                                            "«-EmptyHandlers» (стр. 2968)",
                                   "note": "тот же флаг при той же команде, что и в каноне"},
    "check-modules-extended": {"kind": "corpora", "predicts": "code0",
                               "corpora_source": CHECK_PREDICTION_SOURCE,
                               "needle": "-ExtendedModulesCheck",
                               "quote": "канон корпуса добавляет в команду проверки "
                                        "«-ExtendedModulesCheck» (стр. 2969)",
                               "note": "корпус называет этот флаг при `/CheckConfig`, здесь он "
                                       "идёт при `/CheckModules`"},
    "check-config-extended": {"kind": "corpora", "predicts": "code0",
                              "corpora_source": CHECK_PREDICTION_SOURCE,
                              "needle": "-ExtendedModulesCheck",
                              "quote": "канон корпуса добавляет в команду проверки "
                                       "«-ExtendedModulesCheck» (стр. 2969)",
                              "note": "тот же флаг при той же команде, что и в каноне"},
}


def verify_prediction_sources(local_file: str, root_dir: pathlib.Path) -> dict:
    """Каждое предсказание прочитано из источника, а не пересказано по памяти.

    `root_dir` — каталог проекта: путь источника отчёта контура записан относительно него
    (`reports/gate-11.json`), путь корпуса — относительно значения ключа `corpora_*` из
    `local.paths.json`. У корпусных предсказаний группы проверки путь свой (`prediction_source`).

    Возвращает по варианту `{source, file_found, needle_found}`: `file_found` — файл источника
    есть, `needle_found` — в файле корпуса есть цитируемое имя (для `kontur` — отчёт есть и
    названный ключ в нём равен 0). Предсказание без источника не считается предсказанием.
    """
    local = paths.load_local(local_file)
    result = {}
    for variant, record in sorted(PREDICTIONS.items()):
        if record["kind"] == "corpora":
            key, relative = prediction_source(record)
            root = local.get(key, "")
            path = pathlib.Path(root) / relative if root else None
            found = bool(path and path.is_file())
            text = path.read_text(encoding="utf-8-sig", errors="replace") if found else ""
            result[variant] = {"source": key + "/" + relative, "file_found": found,
                               "needle_found": record["needle"] in text}
        else:
            path = root_dir / record["source"]
            found = path.is_file()
            value = None
            if found:
                try:
                    value = json.loads(path.read_text(encoding="utf-8")).get(record["source_key"])
                except json.JSONDecodeError:
                    value = None
            result[variant] = {"source": record["source"], "file_found": found,
                               "needle_found": value == 0}
    return result


# Варианты без имени команды: они наблюдают, что делает режим запуска без команды (режим
# `1С:Предприятие` без авторизованного пользователя в ИБ). Названы списком, чтобы «забыли имя
# команды» не выглядело нормой: тест сверяет пустые команды таблиц с этим списком.
NO_COMMAND_VARIANTS = ("enterprise-plain",)


def needs_script(variant: str) -> bool:
    """Нужен ли прогону файл BSL-программы: только если команда подставляет его аргументом."""
    command = VARIANT_COMMAND.get(variant)
    return bool(command) and SCRIPT_ARG in command[1]


def variant_signature(variant: str) -> dict:
    """Форма команды варианта: режим, имена команд, вид аргументов, хвост модификаторов.

    Пути (каталог конфигурации, файл программы, несуществующий каталог, файл списка загрузки)
    заменяются метками `cfg`/`script`/`baddir`/`listfile`, чтобы сравнивать форму команды, а не
    конкретные пути прогона. Хвост сравнивается как список токенов: шаг, который меняет только
    значение модификатора (`Auto` -> `AutoUpdate`), сдвигает ровно часть `tail`.
    """
    if variant in VARIANT_COMMAND:
        mode, template = VARIANT_COMMAND[variant]
    elif variant in NEGATIVE_CONTROLS:
        mode, template = "DESIGNER", [NEGATIVE_CONTROLS[variant]]
    else:
        raise KeyError(f"нет формы команды для варианта {variant}")
    return {"mode": mode,
            "names": tuple(item for item in template if item not in PLACEHOLDER_ARGS),
            "args": tuple(item for item in template if item in PLACEHOLDER_ARGS),
            "tail": tuple(VARIANT_TAIL.get(variant, ()))}


def signature_diff(left: dict, right: dict) -> list:
    """Какие части формы команды различаются: `mode`, `names`, `args`, `tail`."""
    return sorted(key for key in ("args", "mode", "names", "tail") if left[key] != right[key])


def signature_tokens(left: dict, right: dict) -> list:
    """Изменённые токены формы команды по позициям — не только имя изменённой части.

    `signature_diff` отвечает лишь на вопрос «какая часть сдвинулась». Для лестниц модификаторов
    этого мало: шаг должен менять ровно ОДИН токен (значение `-Format`, имя после `-Extension`,
    добавленное или снятое имя флага). Иначе наблюдение нельзя приписать одному изменению, и
    вывод «имя принято, но значение не проверили» повисает.
    """
    entries = []
    for part in ("args", "mode", "names", "tail"):
        before = (left["mode"],) if part == "mode" else left[part]
        after = (right["mode"],) if part == "mode" else right[part]
        if before == after:
            continue
        for position in range(max(len(before), len(after))):
            token_from = before[position] if position < len(before) else ""
            token_to = after[position] if position < len(after) else ""
            if token_from != token_to:
                entries.append({"part": part, "position": position,
                                "from": token_from, "to": token_to})
    return entries


def ladder_step_diffs(ladder: tuple) -> list:
    """Соседние шаги лестницы: что изменено в тройке и что сдвинулось в форме команды.

    Лестница строится так, чтобы на шаг менялась ровно одна позиция тройки (текст программы,
    кодирование или вариант — режим наблюдения). Если менялся вариант, отдельно показывается,
    какая ровно часть формы команды (`mode`/`names`/`args`/`tail`) при этом сдвинулась: у лестниц
    команд (`TEST_LADDER`, `AUTH_LADDER`) она тоже одиночная, иначе наблюдение нельзя отнести на
    счёт одного изменения. И сверх этого — список изменённых токенов (`command_tokens`): для
    лестниц модификаторов он обязан содержать ровно одну запись.
    """
    triples = [(variant, program, encoding) for variant, program, encoding in ladder]
    steps = []
    for index, triple in enumerate(triples):
        variant = triple[0]
        signature = variant_signature(variant)
        if index == 0:
            # Базовый шаг: сравнивать не с чем, он и есть эталон сравнения.
            changed_triple, changed_command, tokens = [], [], []
        else:
            previous_triple = triples[index - 1]
            changed_triple = [name for name, position in zip(("variant", "program", "encoding"),
                                                              range(3))
                              if previous_triple[position] != triple[position]]
            previous_signature = steps[-1]["signature"]
            changed_command = signature_diff(previous_signature, signature)
            tokens = signature_tokens(previous_signature, signature)
        steps.append({"from": triples[index - 1][0] if index else "",
                      "to": variant,
                      "changed_triple": changed_triple,
                      "changed_command": changed_command,
                      "command_tokens": tokens,
                      "single_variable": index == 0 or len(changed_triple) == 1,
                      "single_command_part": index == 0 or len(changed_command) <= 1,
                      # Ровно один изменённый токен команды (или ни одного, если шаг меняет только
                      # текст программы или кодирование). `<= 1`, а не `== 1`: у лестниц
                      # кодирования (`SWEEP`, `PROGRAM_LADDER`) форма команды не меняется вовсе.
                      "single_command_token": index == 0 or len(tokens) <= 1,
                      "signature": signature})
    return [{key: value for key, value in step.items() if key != "signature"} for step in steps]


def variant_argv(variant: str, bin_path: str, ib: str, script: pathlib.Path,
                 out_file: pathlib.Path, marker: pathlib.Path, cfg: str = "",
                 work: pathlib.Path | None = None, loadlist: str = "") -> list:
    """Команда платформы для одного варианта наблюдения.

    Все варианты начинаются с имени режима запуска (наблюдение Task 1: иначе платформа сообщает
    «Неопределен режим запуска», код 1) и всегда дают `/Out` в файл. Имена команд берутся из
    замера имён; путь конфигурации (`--cfg`), рабочий каталог (`--work`) и файл списка загрузки
    даются аргументами.

    Метки подставляются и в шаблон команды, и в хвост: `-Extension <имя>`, `-listFile <файл>`,
    `-Format <значение>` — иначе модификатор нельзя было бы передать вовсе. Метка стоит и внутри
    `=`-сцепки (`-ReportFile=reportfile` -> `-ReportFile=<каталог прогона>/exec_check_report`).
    """
    if variant in VARIANT_COMMAND:
        mode, template = VARIANT_COMMAND[variant]
    elif variant in NEGATIVE_CONTROLS:
        # Отрицательный контроль: нераспознанное имя команды, без аргумента и без хвоста
        # авторизации — иначе шаг менял бы и имя команды, и способ входа сразу.
        mode, template = "DESIGNER", [NEGATIVE_CONTROLS[variant]]
    else:
        raise KeyError(f"нет формы команды для варианта {variant}")
    values = {CFG_ARG: cfg,
              SCRIPT_ARG: str(script),
              BADDIR_ARG: str((work or pathlib.Path("work")) / "no-such-directory"),
              LIST_ARG: loadlist,
              REPORT_ARG: str(report_file_for(work))}
    program = [substitute_placeholders(item, values) for item in template]
    tail = [substitute_placeholders(item, values) for item in VARIANT_TAIL.get(variant, ())]
    base = [bin_path, mode, "/F", ib, "/Out", str(out_file), "/DisableStartupDialogs"]
    return base + program + tail


def needs_loadlist(variant: str) -> bool:
    """Подставляет ли вариант метку файла списка загрузки (`-listFile <файл>`)."""
    signature = variant_signature(variant)
    return LIST_ARG in signature["names"] or LIST_ARG in signature["args"] \
        or LIST_ARG in signature["tail"]


def loadlist_paths(cfg: pathlib.Path) -> list:
    r"""Имена файлов для `-listFile`: абсолютные пути **корневых** XML-файлов конфигурации.

    Форма взята из канона БСП, а не придумана: обработчик добавляет в список корневой файл
    объекта (`...\Forms\ИмяФормы\Ext\` -> `...\Forms\ИмяФормы.xml`, стр. 843-844) и держит его
    полным путём от каталога выгрузки (`РабочийКаталог + "[ВидОбъекта]\[ИмяОбъекта]\Forms\..."`,
    стр. 698-729). Файлы каталога `Ext/` (модули, макеты, предопределённые данные) в списке не
    перечисляют: их подтягивает иерархический формат вместе с корневым файлом объекта (стр.
    489-491).
    """
    # Обратные слеши, как в каноне (`РабочийКаталог + "[ВидОбъекта]\[ИмяОбъекта]\Forms\..."`), а не
    # `as_posix()`: список читает платформа, и её собственный способ записи имён — Windows-разделитель.
    return [str(path) for path in sorted(cfg.rglob("*.xml")) if "Ext" not in path.parts]


def write_loadlist(cfg: pathlib.Path, work: pathlib.Path) -> tuple:
    r"""Файл списка загрузки в канонической форме: UTF-8, имена через `\r\n`, без пустых строк.

    Требования канона (стр. 485-488): «Файл должен быть в кодировке UTF-8. Имена файлов должны быть
    указаны через перенос. Поддерживаются символы переноса \r\n ("следующая строка") и \r ("возврат
    каретки"). Файл не должен содержать пустые строки между именами файлов.» Одиночный `\n` в
    списке поддерживаемых переносов нет, поэтому пишем `\r\n` и переводим запись прямо (`newline=""`),
    чтобы байты файла совпадали с записанным содержимым.
    """
    work.mkdir(parents=True, exist_ok=True)
    path = work / LOADLIST_NAME
    names = loadlist_paths(cfg)
    path.write_text("\r\n".join(names), encoding="utf-8", newline="")
    return path, names


def program_text(program: str, marker: pathlib.Path) -> str:
    """Текст BSL-программы: путь маркера вписан прямыми слешами (в строке BSL обратный слеш —
    escape-символ), подстановочная метка `$marker$` заменена полностью.

    Вынесено отдельно, чтобы это было тестируемо без запуска платформы: программа, в которой
    метка осталась, ничего не записывает, и «режим не подтверждён» оказалось бы неверным
    утверждением о платформе.
    """
    return program.replace("$marker$", str(marker).replace("\\", "/"))


def report_file_for(work: pathlib.Path | None) -> pathlib.Path:
    """Каталог прогона + имя отчёта проверки: то, чем платформа заменяет метку `reportfile`."""
    return (work or pathlib.Path("work")) / CHECK_REPORT_NAME


def substitute_placeholders(token: str, values: dict) -> str:
    """Подстановка метки в токен argv: отдельным токеном (`-listFile listfile`) или внутри `=`
    (`-ReportFile=reportfile`). Имя флага подстановка не меняет: тест имён сверяет часть токена
    до `=`, а `variant_signature` держит токен как есть, чтобы сравнение шагов лестницы осталось
    позиционным."""
    name, sep, value = token.partition("=")
    if not sep:
        return values.get(token, token)
    return name + "=" + values.get(value, value)


def report_arg_from_argv(argv: list) -> pathlib.Path | None:
    """Путь отчёта из argv: `=`-форма (`-ReportFile=<путь>`) и форма со следующим токеном
    (`-ReportFile <путь>`), потому что обе формы имени измерены таблицей, а какая принимается —
    как раз предмет замера."""
    for index, token in enumerate(argv):
        name, _sep, value = token.partition("=")
        if name != "-ReportFile":
            continue
        if value:
            return pathlib.Path(value)
        if index + 1 < len(argv):
            return pathlib.Path(argv[index + 1])
    return None


def capture_report(path: pathlib.Path | None, work: pathlib.Path) -> dict:
    """Наблюдение за файлом отчёта проверки: создан ли, сколько в нём байт и строк, и не появился
    ли рядом файл с тем же именем, но другим расширением.

    Отчётность здесь — отдельное наблюдение, а не деталь кода возврата: канон корпуса БСП исход
    проверки определяет именно по файлу отчёта (стр. 2975-3034 обработчика
    `ПроверкаБСППередСборкой`), а не по коду. Строки отчёта ограничены первыми
    `REPORT_LINE_LIMIT`: полный текст остаётся на диске, в отчёте замеров он не нужен целиком.
    """
    if path is None:
        return {"report_asked": False, "report_exists": False, "report_bytes": 0,
                "report_lines": [], "report_line_count": 0, "report_siblings": []}
    exists = path.is_file()
    siblings = sorted(item.name for item in work.glob(path.name + ".*")
                      if item.is_file() and item != path)
    if not exists:
        return {"report_asked": True, "report_path": path.as_posix(), "report_exists": False,
                "report_bytes": 0, "report_lines": [], "report_line_count": 0,
                "report_siblings": siblings}
    text = ib_loop.decode_output(path.read_bytes())
    lines = [line for line in text.splitlines() if line.strip()]
    return {"report_asked": True, "report_path": path.as_posix(), "report_exists": True,
            "report_bytes": path.stat().st_size, "report_lines": lines[:REPORT_LINE_LIMIT],
            "report_line_count": len(lines), "report_siblings": siblings}


# Как канон корпуса читает отчёт проверки (стр. 2996-3027 обработчика `ПроверкаБСППередСборкой`):
# строки «Соединение с хранилищем конфигурации не установлено» и содержащие `Подключаемый_`
# пропускаются (стр. 2998-2999), из остальных снимается `{` (стр. 3004-3008), первый токен делится
# по точке, и если частей меньше двух — строка не относится к объекту конфигурации (стр. 3010-3015).
# Отчётность группы проверки живёт именно здесь, а не в коде возврата: код отвечает на вопрос,
# принято ли имя, а «нашёл ли прогон дефект» видно по строкам с полным именем объекта.
CHECK_REPORT_SKIP_MARKERS = ("Соединение с хранилищем конфигурации не установлено", "Подключаемый_")


def object_lines(lines) -> list:
    """Полные имена объектов из строк отчёта проверки: `ВидОбъекта.ИмяОбъекта`, как в каноне.

    Строка без точки в первом токене — служебное сообщение, а не дефект объекта: канон её
    отбрасывает (стр. 3013-3015). Порядок сохраняется, повтор не схлопывается: повторная строка
    того же объекта — отдельный дефект. Полные строки остаются в `lines`, `console_lines` и
    `report_lines`, поэтому спорную строку можно перечитать глазами, а не довериться правилу.
    """
    names = []
    for raw in lines:
        line = raw.strip()
        if not line or any(marker in line for marker in CHECK_REPORT_SKIP_MARKERS):
            continue
        parts = line.replace("{", "").split(" ")[0].split(".")
        if len(parts) < 2:
            continue
        names.append(parts[0] + "." + parts[1])
    return names


def check_verdict(code: int, object_line_count: int) -> str:
    """Вердикт шага группы проверки, отделённый от отказа в имени.

    Разделение нужно потому, что один ключ `code` отвечает на два разных вопроса, и ответы на них
    дают разные вещи: код процесса и строки отчёта. `defects` — есть строки вида
    `ВидОбъекта.ИмяОбъекта` (в замере чистой ИБ это код 101); `clean` — код 0 без таких строк
    (в замере это `Ошибок не обнаружено` / `Синтаксических ошибок не обнаружено!`); `no_verdict`
    — код 101 без строк объекта: платформа вернула вердикт «есть ошибки», но прочесть, о чём
    именно они, по этому шагу нельзя; `refused` — прочие коды (в замере: код 1 и строка о
    идентификаторе ИБ у заведомо отсутствующего имени).
    """
    if object_line_count:
        return "defects"
    if code == CHECK_CLEAN_CODE:
        return "clean"
    if code == CHECK_DEFECT_CODE:
        return "no_verdict"
    return "refused"


def check_observation(result: dict) -> dict:
    """Наблюдение одного шага группы проверки: принят ли флаг (код) и найден ли дефект (строки).

    Смотрят три места, куда платформа способна записать сообщение проверки, разом: `/Out` (канон
    корпуса передаёт именно его, стр. 2970-2971), собственный stdout/stderr процесса и файл,
    названный `-ReportFile`. Ни одно из них не объявлено «правильным» заранее, поэтому наблюдение
    не выбирает одно наугад: пустой исход означает «ни в одном из трёх мест строки объекта нет».

    `accepted` читается из вердикта, а не из кода напрямую: код 101 — это принятая команда,
    нашедшая дефекты, и `accepted` для неё истина.
    """
    names = object_lines(list(result["lines"]) + list(result["console_lines"]))
    report = result["report"]
    report_names = object_lines(report["report_lines"])
    line_count = len(names) + len(report_names)
    verdict = check_verdict(result["code"], line_count)
    return {"code": result["code"], "timed_out": result["timed_out"], "verdict": verdict,
            "accepted": verdict in ("clean", "defects"),
            "out_lines": len(result["lines"]), "console_line_count": len(result["console_lines"]),
            "report_exists": report["report_exists"], "report_bytes": report["report_bytes"],
            "report_line_count": report["report_line_count"],
            "report_siblings": report["report_siblings"],
            "object_names": (names + report_names)[:REPORT_LINE_LIMIT],
            "object_line_count": line_count}


def run(bin_path: str, ib: str, program: str, variant: str, work: pathlib.Path,
        timeout: int = 120, encoding: str = "utf-8", program_kind: str = "marker",
        write_script: bool = True, cfg: str = "", loadlist: str = "") -> dict:
    """Один прогон платформы: возвращает код, секунды, байт и строки вывода, след программы.

    Ждём циклом с `poll`, как в `ib_loop.run_step`: зависание здесь — ожидаемый исход одного из
    вариантов, и `subprocess.run(timeout=...)` его не переживает (файл вывода при этом остаётся
    непрочитанным).

    Кодирование файла программы — отдельная проверяемая переменная, а не деталь: наблюдение
    `runscript` дало код 1 за 2.0 с при пустом выводе, а это одинаково похоже и на «режим не
    принят», и на «файл программы не прочитан» (в программе кирилличные ключевые слова).

    `loadlist` — путь файла списка загрузки для `-listFile`; его содержимое пишет
    `write_loadlist` (каноническая форма — UTF-8, имена через перенос строки).
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
    argv = variant_argv(variant, bin_path, ib, script, out_file, marker, cfg, work, loadlist)
    # Файл отчёта проверки снимается ДО прогона: «отчёт создан» должно означать «создан этим
    # прогоном», иначе наблюдение `-ReportFile` наследует след прежнего шага лестницы (в лестнице
    # он стоит уже добавленным флагом).
    report_path = report_arg_from_argv(argv)
    if report_path is not None and report_path.is_file():
        report_path.unlink()
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
        "report": capture_report(report_path, work),
    }


def ladder_ok(report: dict) -> bool:
    """Лестница выдержана: на каждом шаге ровно одна позиция тройки и ровно одна часть формы команды.

    Состав исходов (зависание, пустой или непустой `/Out`) в код возврата не входит: код отвечает
    только за дисциплину наблюдения, а исходы живут в ключах отчёта (`confirmed_modes`,
    `negative_clean`, `test_classes`). Иначе находка класса «имя принято, но процесс зависает»
    ломала бы код лестницы, на которой эту находку сделали.

    Шаг, который меняет два токена команды, допускается только если он записан в
    `TOKEN_MULTI_REASON` (смена способа входа `-User`/`-Pwd` — одна переменная, два токена);
    необъяснённый шаг с двумя токенами дисциплину ломает.
    """
    return bool(report.get("ladder_single_variable")) and bool(
        report.get("ladder_single_command_part", True)) and bool(
        report.get("ladder_multi_token_documented", True))


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
    parser.add_argument("--predefined", action="store_true",
                        help="лестница PREDEFINED_LADDER: `/SetPredefinedDataUpdate` и его значения "
                             "(измеренные значения свойства `PredefinedDataUpdate` в корпусах)")
    parser.add_argument("--extensions", action="store_true",
                        help="лестница EXTENSION_LADDER: `-Extension`, `-AllExtensions`, "
                             "`-RebuildConfigurationExtensions`, "
                             "`/CheckCanApplyConfigurationExtensions`")
    parser.add_argument("--loadopts", action="store_true",
                        help="лестница LOADOPTS_LADDER: `-files`, `-listFile`, `-Format` — опции "
                             "частичной загрузки, подписанные корпусом БСП как опции "
                             "`/LoadConfigFromFiles`")
    parser.add_argument("--update", action="store_true",
                        help="лестница UPDATE_LADDER: `/UpdateCfg`, `/UpdateDBCfg`, `-Server` и "
                             "CONFIG-форма канонического макета обновления корпуса")
    parser.add_argument("--modes", action="store_true",
                        help="лестница MODE_LADDER: один шаг, меняющий только режим запуска "
                             "(`DESIGNER` -> `CONFIG`) при неизменной команде загрузки; делает "
                             "вариант `config-load-ok` достижимым названной лестницей")
    parser.add_argument("--checkkeys", action="store_true",
                        help="лестница CHECK_LADDER: команда `/CheckModules` и имена группы "
                             "проверки замера — семь корпусных флагов (`-ConfigLogIntegrity`, "
                             "`-IncorrectReferences`, `-DistributiveModules`, "
                             "`-UnreferenceProcedures`, `-HandlersExistence`, `-EmptyHandlers`, "
                             "`-ExtendedModulesCheck`) и отчётные опции (`-ReportFile`, "
                             "`-ReportFormat`, `-ReportType`, `-Module`, `-noCheck`)")
    parser.add_argument("--checkconfig", action="store_true",
                        help="лестница CHECKCMD_LADDER: полное зеркало `CHECK_LADDER` (те же 22 "
                             "шага и те же хвосты), но команда `/CheckConfig` — та, которую в своей "
                             "команде проверки пишет корпус БСП")
    parser.add_argument("--allow-mutating", action="store_true",
                        help="разрешить варианты из MUTATING_VARIANTS: они способны изменить "
                             "состояние ИБ. Без этого флага такая лестница не запускается (код 2). "
                             "Прогон делать только на отдельной временной ИБ, не на ИБ гейта.")
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
    MUTATING_LADDERS = (args.predefined, args.extensions, args.loadopts, args.update, args.modes)
    if (args.controls or args.auth or any(MUTATING_LADDERS)) and not cfg:
        # Контрольные прогоны строятся на команде, исход которой известен (`/LoadConfigFromFiles`
        # даёт код 0 на рабочем каталоге конфигурации — подтверждение гейта). Без каталога контроль
        # не является контролем.
        print("exec_probe: для --controls, --auth и лестниц Task 16 (--predefined, --extensions, "
              "--loadopts, --update, --modes) нужен --cfg (или local.paths.json: cfg)",
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
    elif args.predefined:
        ladder, ladder_name = PREDEFINED_LADDER, "PREDEFINED_LADDER"
    elif args.extensions:
        ladder, ladder_name = EXTENSION_LADDER, "EXTENSION_LADDER"
    elif args.loadopts:
        ladder, ladder_name = LOADOPTS_LADDER, "LOADOPTS_LADDER"
    elif args.update:
        ladder, ladder_name = UPDATE_LADDER, "UPDATE_LADDER"
    elif args.modes:
        ladder, ladder_name = MODE_LADDER, "MODE_LADDER"
    elif args.checkkeys:
        ladder, ladder_name = CHECK_LADDER, "CHECK_LADDER"
    elif args.checkconfig:
        ladder, ladder_name = CHECKCMD_LADDER, "CHECKCMD_LADDER"
    elif args.sweep:
        ladder, ladder_name = SWEEP, "SWEEP"
    elif args.programs:
        ladder, ladder_name = PROGRAM_LADDER, "PROGRAM_LADDER"
    elif args.all:
        # `--all` остаётся наблюдением без побочных изменений: варианты из `MUTATING_VARIANTS`
        # в него не входят (они прогоняются только явно названной лестницей и с
        # `--allow-mutating`), а оставшиеся `load-*` причины перечислены в
        # `NON_MUTATING_LOAD_REASONS`.
        ladder = [(variant, "marker", args.encoding)
                  for variant in all_observation_variants()]
        ladder_name = "ALL_VARIANTS"
    else:
        ladder, ladder_name = [(args.variant, args.program, args.encoding)], "single"
    if not cfg and any(variant.startswith("load") for variant, _, _ in ladder):
        # Команда контроля с пустым аргументом — не наблюдение, а артефакт запуска.
        print("exec_probe: вариантам /LoadConfigFromFiles нужен --cfg (или local.paths.json: cfg)",
              file=sys.stderr)
        return 2
    mutating = [variant for variant, _, _ in ladder if variant in MUTATING_VARIANTS]
    report_mutating = {"ladder_mutating_variants": mutating,
                       "mutating_allowed": bool(args.allow_mutating),
                       "ib_side_effects_possible": bool(mutating)}
    if mutating and not args.allow_mutating:
        print(f"exec_probe: лестница {ladder_name} содержит варианты, способные изменить состояние "
              f"ИБ ({', '.join(mutating)}). Нужен --allow-mutating, и прогон делать на отдельной "
              "временной ИБ, а не на ИБ гейта.", file=sys.stderr)
        return 2
    # Файл списка загрузки пишется только там, где команда подставляет его аргументом (`-listFile`).
    # Содержимое каноническое: абсолютные пути корневых XML-файлов, UTF-8, имена через перенос.
    loadlist = ""
    if any(needs_loadlist(variant) for variant, _, _ in ladder):
        if not cfg:
            print("exec_probe: для -listFile нужен --cfg (список строится из каталога конфигурации)",
                  file=sys.stderr)
            return 2
        list_path, list_names = write_loadlist(pathlib.Path(cfg), work)
        loadlist = str(list_path)
        print(f"файл списка загрузки: {list_path.as_posix()} ({len(list_names)} имён)")
    # Прогон строго последовательный: 1С-прогоны не выполняются параллельно (наблюдение контура),
    # поэтому лестница идёт в этом цикле, а не через параллельный запуск.
    results = [run(bin_path, ib, PROGRAMS[kind], variant, work, args.timeout, encoding,
                   program_kind=kind,
                   # Файл программы пишется только там, где команда подставляет его аргументом:
                   # `/LoadConfigFromFiles`, `-TestOnly` и `/AllowExecuteScheduledJobs` файл
                   # программы не читают, и лишний файл в рабочем каталоге размывает границу.
                   write_script=kind != "missing" and needs_script(variant),
                   cfg=cfg, loadlist=loadlist)
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
    # Дисциплина токенов: шаг лестницы модификаторов обязан менять ровно ОДИН токен команды,
    # иначе нельзя сказать, каким именно изменением получен исход (например `-Format Hierarchical`
    # -> `-Format Plain`). Отчёт держит и позиции изменённых токенов, и список исключений.
    report["ladder_single_command_token"] = all(step["single_command_token"]
                                                for step in report["ladder_diffs"])
    report["ladder_token_positions"] = [{"from": step["from"], "to": step["to"],
                                         "tokens": step["command_tokens"]}
                                        for step in report["ladder_diffs"][1:]]
    multi = [step for step in report["ladder_diffs"][1:] if len(step["command_tokens"]) > 1]
    report["ladder_multi_token_steps"] = [
        {"from": step["from"], "to": step["to"], "tokens": step["command_tokens"],
         "reason": TOKEN_MULTI_REASON.get((step["from"], step["to"]), "")} for step in multi]
    report["ladder_multi_token_documented"] = all(entry["reason"]
                                                  for entry in report["ladder_multi_token_steps"])
    print("один токен команды на шаг:", report["ladder_single_command_token"],
          "| недокументированных шагов с двумя токенами:",
          sum(1 for entry in report["ladder_multi_token_steps"] if not entry["reason"]))
    report.update(report_mutating)
    if mutating:
        print("варианты, способные изменить состояние ИБ:", mutating)
    if predicted := [r for r in results if r["variant"] in PREDICTIONS]:
        # Предсказания записаны в `PREDICTIONS` до прогона. Сверка механическая: источник
        # (`verify_prediction_sources`) обязан читаться, а сбывшееся предсказание — иметь код:
        # у зависшего прогона кода нет, поэтому оно не считается ни сбывшимся, ни опровергнутым.
        sources = verify_prediction_sources(args.local, ROOT)
        outcomes = {}
        for result in predicted:
            record = PREDICTIONS[result["variant"]]
            code = result["code"]
            if code is None:
                status = "no_code"
            elif record["predicts"] == "code0":
                status = "held" if code == 0 else "broken"
            else:
                status = "held" if code != 0 else "broken"
            outcomes[result["variant"]] = {
                "predicts": record["predicts"], "kind": record["kind"],
                "quote": record["quote"], "outcome": list(outcome_key(result)),
                "code": code, "status": status,
                "source_ok": sources[result["variant"]]["file_found"]
                             and sources[result["variant"]]["needle_found"],
            }
        report["predictions"] = outcomes
        report["prediction_sources"] = sources
        report["predictions_held"] = sorted(name for name, value in outcomes.items()
                                            if value["status"] == "held")
        report["predictions_broken"] = sorted(name for name, value in outcomes.items()
                                             if value["status"] == "broken")
        report["predictions_unresolved"] = sorted(name for name, value in outcomes.items()
                                                 if value["status"] == "no_code")
        report["prediction_sources_ok"] = all(value["source_ok"] for value in outcomes.values())
        print("предсказания (записаны до прогона):")
        for name in sorted(outcomes):
            value = outcomes[name]
            print(f"   {name}: ждали {value['predicts']}, код {value['code']} -> {value['status']}"
                  f" | источник {value['source_ok']}")
        print("сбылось:", report["predictions_held"] or "нет",
              "| опровергнуто:", report["predictions_broken"] or "нет",
              "| без кода (зависание):", report["predictions_unresolved"] or "нет")
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
    if args.checkkeys or args.checkconfig:
        # Наблюдение группы проверки. У шага два разных факта: код процесса (в замере: 0 — «ошибок
        # не обнаружено», 101 — «ошибки найдены») и строки с полным именем объекта
        # (`object_lines`). Их сводит вместе `check_verdict`: код сам по себе не различает вердикт
        # проверки и отказ имени. Маркер программы эти прогоны не ставят: команда проверки
        # файл программы не читает, поэтому «прогон дошёл» меряется здесь кодом процесса и следом в
        # одном из трёх мест (`/Out`, консоль процесса, файл `-ReportFile`) — отдельным ключом, а не
        # молчаливым наследованием `executed_variants`, которое осталось бы пустым.
        observations = {r["variant"]: check_observation(r) for r in results}
        report["check_observation"] = observations
        report["check_verdicts"] = {v: o["verdict"] for v, o in sorted(observations.items())}
        # «Имя принято» здесь означает «платформа вынесла читаемый вердикт проверки» (код 0 или
        # код 101 со строками дефектов), а не «код равен нулю»: иначе 15 шагов `/CheckConfig` с
        # найденными дефектами оказались бы записаны как отказ имени.
        report["check_accepted"] = sorted(v for v, o in observations.items() if o["accepted"])
        report["check_rejected"] = sorted(v for v, o in observations.items()
                                          if o["verdict"] == "refused" and not o["timed_out"])
        report["check_defect_found"] = sorted(v for v, o in observations.items()
                                              if o["verdict"] == "defects")
        report["check_no_defects"] = sorted(v for v, o in observations.items()
                                            if o["verdict"] == "clean")
        report["check_no_verdict"] = sorted(v for v, o in observations.items()
                                            if o["verdict"] == "no_verdict")
        report["check_timed_out"] = sorted(v for v, o in observations.items() if o["timed_out"])
        report["check_report_files"] = sorted(v for v, o in observations.items()
                                              if o["report_exists"])
        report["check_object_line_count"] = {v: o["object_line_count"]
                                             for v, o in sorted(observations.items())}
        report["check_object_names"] = {v: o["object_names"]
                                        for v, o in sorted(observations.items())
                                        if o["object_line_count"]}
        traced = sorted(v for v, o in observations.items()
                        if o["out_lines"] or o["console_line_count"] or o["report_exists"])
        report["check_trace_variants"] = traced
        report["check_silent_variants"] = sorted(set(observations) - set(traced))
        report["check_progress"] = sorted(v for v, o in observations.items() if not o["timed_out"])
        report["execution_confirmed"] = bool(traced) and len(report["check_progress"]) == len(results)
        ladder_variants = [variant for variant, _kind, _encoding in ladder]
        # Зеркало лестниц: хвост одинаковый, различие — только в имени команды. Если зеркало не
        # держится, наблюдение одного шага нельзя сравнить с наблюдением парного шага.
        report["check_mirror_same_tail"] = all(
            variant_signature(variant)["tail"]
            == variant_signature(check_mirror_variant(variant))["tail"]
            for variant in ladder_variants)
        report["check_mirror_differs_by_command_only"] = all(
            signature_diff(variant_signature(variant),
                           variant_signature(check_mirror_variant(variant))) == ["names"]
            for variant in ladder_variants)
        unpredicted = check_unpredicted_steps(ladder)
        report["check_predicted_steps"] = check_predicted_steps(ladder)
        report["check_unpredicted_steps"] = unpredicted
        report["check_unpredicted_matches_list"] = (
            set(unpredicted) == (CHECK_OBSERVATION_ONLY & set(ladder_variants)))
        print("наблюдение группы проверки:")
        for variant in sorted(observations):
            value = observations[variant]
            print(f"   {variant}: код {value['code']} ({value['verdict']}), строк объекта "
                  f"{value['object_line_count']},"
                  f" /Out {value['out_lines']}, консоль {value['console_line_count']},"
                  f" отчёт {value['report_exists']} ({value['report_bytes']} б)")
            for name in value["object_names"][:6]:
                print("      объект:", name)
        print("имя принято (вердикт читается):", len(report["check_accepted"]), "из", len(results))
        print("дефекты найдены:", report["check_defect_found"])
        print("дефектов нет:", report["check_no_defects"])
        print("имя отвергнуто:", report["check_rejected"],
              "| вердикт не читается:", report["check_no_verdict"],
              "| зависло:", report["check_timed_out"])
        print("файл отчёта создан:", report["check_report_files"])
        print("след прогона:", report["check_trace_variants"] or "ни один шаг не оставил следа",
              "| молчат:", report["check_silent_variants"])
        print("зеркало лестниц: хвост совпадает:", report["check_mirror_same_tail"],
              "| различие только в имени команды:",
              report["check_mirror_differs_by_command_only"])
        print("шаги без предсказания:", len(report["check_unpredicted_steps"]),
              "| сверяется со списком:", report["check_unpredicted_matches_list"])
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
    if args.predefined or args.extensions or args.loadopts or args.update or args.modes:
        # Код отвечает за дисциплину: один токен команды на шаг, читаемый источник предсказания,
        # наличие `--allow-mutating`. Состав исходов (имя принято или отвергнуто, предсказание
        # сбылось или опровергнуто) живёт в ключах отчёта `predictions*`, а не в коде: и «имя
        # принято», и «имя отвергнуто» — находки.
        if not report["prediction_sources_ok"]:
            print("exec_probe: источник предсказания не читается: предсказание без источника "
                  "предсказанием не считается", file=sys.stderr)
        return 0 if (ladder_ok(report) and report["prediction_sources_ok"]) else 1
    if args.checkkeys or args.checkconfig:
        # Код отвечает за дисциплину: один токен команды на шаг, зеркало лестниц, читаемый источник
        # предсказания. Состав исходов («имя принято», «имя отвергнуто», «дефект найден», «отчёт
        # создан») живёт в ключах `check_*`: и принято, и отвергнуто — находки наблюдения, а не
        # ошибка прогона.
        if not report["prediction_sources_ok"]:
            print("exec_probe: источник предсказания не читается: предсказание без источника "
                  "предсказанием не считается", file=sys.stderr)
        return 0 if (ladder_ok(report) and report["prediction_sources_ok"]) else 1
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

# Лестницы модификаторов `/LoadConfigFromFiles` (Task 16). Все четыре начинаются с заведомо
# рабочего шага `load-ok` (гейт подтверждает код 0) и дальше меняют только хвост, поэтому исход
# каждого шага нельзя приписать ничему, кроме одного изменённого токена (`command_tokens` в
# `ladder_diffs`). Порядок подобран именно так: `-AllExtensions` без значения стоит после шага с
# лишним positional-аргументом, `-Format` — только после `-listFile`, потому что канон связывает
# `format` с частичной загрузкой (стр. 489).
#
# Каждая из этих лестниц способна изменить состояние ИБ (загрузить конфигурацию целиком или по
# списку файлов, создать расширение, сменить режим обновления предопределённых данных), поэтому
# она требует `--allow-mutating` и идёт на отдельной временной ИБ, а не на ИБ гейта.
PREDEFINED_LADDER = (("load-ok", "marker", "cp1251"),
                     # `=`-форма и форма с отдельным значением: иначе «значение принято» нельзя
                     # отличить от «значение проигнорировали».
                     ("load-predefined-equals-dontupdate", "marker", "cp1251"),
                     ("load-predefined-flag", "marker", "cp1251"),
                     ("load-predefined-auto", "marker", "cp1251"),
                     ("load-predefined-autoupdate", "marker", "cp1251"),
                     ("load-predefined-dontupdate", "marker", "cp1251"),
                     # Вымышленное значение: если итог совпадает с `DontAutoUpdate`, значение не
                     # проверялось вовсе.
                     ("load-predefined-bogus-value", "marker", "cp1251"))

EXTENSION_LADDER = (("load-ok", "marker", "cp1251"),
                    ("load-extension-flag", "marker", "cp1251"),
                    ("load-extension-bogus-name", "marker", "cp1251"),
                    ("load-extension-cfgdir", "marker", "cp1251"),
                    ("load-extension-baddir", "marker", "cp1251"),
                    ("load-allextensions-baddir", "marker", "cp1251"),
                    ("load-allextensions-flag", "marker", "cp1251"),
                    ("load-rebuild-extensions", "marker", "cp1251"),
                    ("load-check-can-apply", "marker", "cp1251"))

LOADOPTS_LADDER = (("load-ok", "marker", "cp1251"),
                   ("load-files-flag", "marker", "cp1251"),
                   ("load-files-onefile", "marker", "cp1251"),
                   ("load-listfile-onefile", "marker", "cp1251"),
                   ("load-listfile-ok", "marker", "cp1251"),
                   ("load-format-flag", "marker", "cp1251"),
                   ("load-format-hierarchical", "marker", "cp1251"),
                   ("load-format-plain", "marker", "cp1251"),
                   ("load-format-bogus", "marker", "cp1251"))

# Лестница режимов обновления (Task 16). Шаг за шагом меняется: аргумент (`args`), имя команды
# (`names`), модификатор (`tail`) и, наконец, режим запуска (`mode`). Канон форм — макет обновления
# корпуса (`docs/evidence/cli-canonical-usage.md`): `/LoadCfg "<cf>"`, `/UpdateCfg "<cf|cfu>"`,
# `/UpdateDBCfg -server` и CONFIG-форма того же макета в УХ.
UPDATE_LADDER = (("load-ok", "marker", "cp1251"),
                 ("load-noarg", "marker", "cp1251"),
                 ("update-cfg-noarg", "marker", "cp1251"),
                 ("update-dbcfg", "marker", "cp1251"),
                 ("update-dbcfg-server", "marker", "cp1251"),
                 ("config-update-dbcfg-server", "marker", "cp1251"))

# Лестница режимов запуска (Task 16). Единственная изменённая позиция — режим: `DESIGNER` ->
# `CONFIG` при неизменной команде `/LoadConfigFromFiles <каталог конфигурации>`, исход которой в
# `DESIGNER` подтверждён (код 0, `reports/gate-*.json`). Смысл шага: канонический макет
# обновления корпуса пишет CONFIG-форму (`CONFIG {0} {1} /UpdateDBCfg -server ...`), и без этого
# наблюдения неизвестно, принимает ли этот режим вообще команду загрузки из файлов — то есть является
# ли `CONFIG` рабочим режимом для нашей конфигурации или только для обновления. Без лестницы вариант
# `config-load-ok` не доставался ни одной названной лестницей и оставался наблюдением «на будущее».
# `config-load-ok` предсказания в `PREDICTIONS` не имеет и это записано, а не забыто: источника,
# который предсказывал бы исход пары `CONFIG` + `/LoadConfigFromFiles`, нет. Обход корпусов
# (`reports/corpora-cli-usage-16.json`): `LoadConfigFromFiles` — 4 вхождения, все в подписи опций
# БСП (DESIGNER-форма), а CONFIG-форма макета обновления пишет только `/UpdateCfg` и
# `/UpdateDBCfg`. Предсказывать тут было бы нечего, поэтому шаг идёт как наблюдение без
# предсказания; эталонный `load-ok` при этом предсказан (`kontur`: `load_code` = 0).
MODE_LADDER = (("load-ok", "marker", "cp1251"),
               ("config-load-ok", "marker", "cp1251"))

# Лестницы группы проверки (Task 24). Их две, и они полные зеркала: 22 имени шагов в том же порядке,
# различается только имя команды — `/CheckModules` у `--checkkeys`, `/CheckConfig` у `--checkconfig`.
# Зеркало нужно потому, что источники расходятся: корпусный канон проверки пишет `/CheckConfig` и
# семь корпусных флагов (стр. 2953-2969), а контур (`scripts/ib_loop.py`, шаг `check`) прогоняет
# `/CheckModules` пятью клиентскими модификаторами, и его исход уже замерен (`check_code` = 0 в
# `reports/gate-14.json`). Одноимённые шаги различаются только именем команды, поэтому «имя принято»
# или «имя отвергнуто» нельзя случайно приписать другой команде.
# Базовые шаги названы `check-modules-base` и `check-config-base` (не `check-config-command`): пара
# базовых шагов и есть сравнение «одна переменная — имя команды», остальные 21 шаг сравниваются так же.
# Порядок шагов: измеренный канон (`CHECK_TAIL_BASE`), затем семь корпусных флагов в порядке корпуса,
# затем флаг файла отчёта, затем по одному имени группы поверх него. Вымышленное значение опции стоит
# перед настоящим той же опции, а вымышленное значение отчётного типа — первым в своей группе: так
# видно, проверяет ли платформа значение вообще.
CHECK_LADDER = (("check-modules-base", "marker", "cp1251"),
                ("check-modules-configlog", "marker", "cp1251"),
                ("check-modules-references", "marker", "cp1251"),
                ("check-modules-distributive", "marker", "cp1251"),
                ("check-modules-unreferenced", "marker", "cp1251"),
                ("check-modules-handlers", "marker", "cp1251"),
                ("check-modules-emptyhandlers", "marker", "cp1251"),
                ("check-modules-extended", "marker", "cp1251"),
                ("check-modules-reportfile", "marker", "cp1251"),
                ("check-modules-warnings-as-errors", "marker", "cp1251"),
                ("check-modules-nocheck", "marker", "cp1251"),
                ("check-modules-nbegin", "marker", "cp1251"),
                ("check-modules-nend", "marker", "cp1251"),
                ("check-modules-module-bogus", "marker", "cp1251"),
                ("check-modules-module", "marker", "cp1251"),
                ("check-modules-reportformat-bogus", "marker", "cp1251"),
                ("check-modules-reportformat-mxl", "marker", "cp1251"),
                ("check-modules-reportformat-txt", "marker", "cp1251"),
                ("check-modules-reporttype-bogus", "marker", "cp1251"),
                ("check-modules-reporttype-names", "marker", "cp1251"),
                ("check-modules-reporttype-ids", "marker", "cp1251"),
                ("check-modules-reporttype-brief", "marker", "cp1251"))

# Зеркало `CHECK_LADDER`: те же 22 позиции, изменена только команда (`/CheckConfig`).
CHECKCMD_LADDER = (("check-config-base", "marker", "cp1251"),
                   ("check-config-configlog", "marker", "cp1251"),
                   ("check-config-references", "marker", "cp1251"),
                   ("check-config-distributive", "marker", "cp1251"),
                   ("check-config-unreferenced", "marker", "cp1251"),
                   ("check-config-handlers", "marker", "cp1251"),
                   ("check-config-emptyhandlers", "marker", "cp1251"),
                   ("check-config-extended", "marker", "cp1251"),
                   ("check-config-reportfile", "marker", "cp1251"),
                   ("check-config-warnings-as-errors", "marker", "cp1251"),
                   ("check-config-nocheck", "marker", "cp1251"),
                   ("check-config-nbegin", "marker", "cp1251"),
                   ("check-config-nend", "marker", "cp1251"),
                   ("check-config-module-bogus", "marker", "cp1251"),
                   ("check-config-module", "marker", "cp1251"),
                   ("check-config-reportformat-bogus", "marker", "cp1251"),
                   ("check-config-reportformat-mxl", "marker", "cp1251"),
                   ("check-config-reportformat-txt", "marker", "cp1251"),
                   ("check-config-reporttype-bogus", "marker", "cp1251"),
                   ("check-config-reporttype-names", "marker", "cp1251"),
                   ("check-config-reporttype-ids", "marker", "cp1251"),
                   ("check-config-reporttype-brief", "marker", "cp1251"))

# Шаги группы проверки, у которых предсказания нет, и почему. Предсказание обязано иметь читаемый
# источник; корпус БСП подписывает из этой группы только семь флагов (стр. 2953-2969) и команду
# `/CheckConfig` (стр. 2953). Остальные имена измерены замером 426 имён, но ни один корпус, ни один
# канон и ни один прогон контура не говорит, что делает `-WarningsAsErrors`, `-noCheck`, `-NBegin`,
# `-NEnd`, `-Module` и отчётные опции. Предсказывать их исход было бы нечем, поэтому они идут
# наблюдением без предсказания — и это записано здесь, а не забыто: `CHECK_OBSERVATION_ONLY`
# проверяется тестом, что непредсказанных шагов ровно столько и это ровно они.
CHECK_UNCITED_STEPS = ("reportfile", "warnings-as-errors", "nocheck", "nbegin", "nend",
                       "module", "module-bogus", "reportformat-bogus", "reportformat-mxl",
                       "reportformat-txt", "reporttype-bogus", "reporttype-names",
                       "reporttype-ids", "reporttype-brief")
CHECK_OBSERVATION_ONLY = {f"check-{name}-{step}" for name in ("modules", "config")
                          for step in CHECK_UNCITED_STEPS}

# Шаги, у которых предсказание есть: базовый шаг (исход замерен прогоном контура) и семь корпусных
# флагов. Всего 8 на лестницу, 16 на обе — ровно столько записей в `PREDICTIONS` добавляет эта
# итерация.
CHECK_PREDICTED_STEPS = {f"check-{name}-{step}" for name in ("modules", "config")
                         for step in ("base", "configlog", "references", "distributive",
                                      "unreferenced", "handlers", "emptyhandlers", "extended")}


def check_mirror_variant(variant: str) -> str:
    """Парное имя шага в зеркальной лестнице проверки: `check-modules-X` <-> `check-config-X`.

    Зеркало проверяется по самому замеру (`check_mirror_*` в отчёте): у одноимённых шагов одинаков
    хвост модификаторов и различается только имя команды, поэтому «имя принято» или «имя отвергнуто»
    нельзя приписать другой команде проверки. Замена работает в обе стороны: лестница прогоняется
    по одной из двух цепочек имён, а сравнивать надо с той, которая сейчас не прогоняется.
    """
    for left, right in (("check-modules-", "check-config-"), ("check-config-", "check-modules-")):
        if variant.startswith(left):
            return right + variant[len(left):]
    raise KeyError(f"{variant}: не шаг группы проверки, парного имени у него нет")


def check_observation_variants() -> tuple:
    """Все 44 шага группы проверки, обе лестницы целиком: покрытие лестниц сверяется тестом, а не
    на глаз (у варианта без шага нет ни наблюдения, ни сравнения с зеркалом)."""
    return tuple(variant for ladder in (CHECK_LADDER, CHECKCMD_LADDER)
                 for variant, _program, _encoding in ladder)


def check_predicted_steps(ladder: tuple) -> list:
    """Шаги лестницы проверки, у которых есть запись в `PREDICTIONS`: сверяются с источником именно
    они. Пустой список означал бы, что лестница прогоняется без единого предсказания."""
    return sorted(variant for variant, _program, _encoding in ladder if variant in PREDICTIONS)


def check_unpredicted_steps(ladder: tuple) -> list:
    """Шаги без предсказания: наблюдение ради наблюдения. Список обязан совпадать с
    `CHECK_OBSERVATION_ONLY` — тогда «не предсказали» не выглядит как «забыли предсказать»."""
    return sorted(variant for variant, _program, _encoding in ladder if variant not in PREDICTIONS)


# Шаги прежних лестниц, где меняется ровно ДВА токена, и почему это всё ещё одно изменение.
# Способ входа `-User=<имя>` + `-Pwd=<пароль>` — ОДИН измеренный способ авторизации: в таблице
# имён платформы он описан двумя ключами (`CmdLine/UserName` и `CmdLine/UserPassword`), поэтому
# смена способа (одна переменная наблюдения) физически не может быть одним токеном. Каждый такой
# шаг зафиксирован здесь; лестница модификаторов (Task 16) таких шагов не имеет.
TOKEN_MULTI_REASON = {
    ("load-currentuser", "load-credentials"):
        "способ входа меняется целиком: -User/-Pwd — один измеренный способ (два ключа таблицы имён)",
    ("runscript-authoff", "runscript-credentials"):
        "способ входа меняется целиком: -User/-Pwd — один измеренный способ (два ключа таблицы имён)",
    ("runscript-credentials", "runscript-currentuser"):
        "способ входа меняется целиком: -User/-Pwd — один измеренный способ (два ключа таблицы имён)",
}


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
