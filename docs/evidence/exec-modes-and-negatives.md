# Исполнительные формы командной строки 1С: что удалось измерить, а что нет

Измерения делались скриптом `scripts/exec_probe.py` (лестницы `SWEEP`, `CONTROLS`, `NEGATIVE_LADDER`,
`AUTH_LADDER`, `TEST_LADDER`, `MODE_LADDER` и одиночные контроли) на временной ИБ, никогда на ИБ
гейта и никогда одновременно с живой ИБ пользователя. Каждый шаг лестницы меняет ровно одну часть
командной строки, поэтому различие исходов приписывается именно этой части. Код возврата платформы
в этих прогоны отвечает только за дисциплину лестницы: исход живёт в `bytes` (размер `/Out`),
в дословном списке строк `/Out` и в признаке `timed_out`.

Запись «маркер BSL» означает: в скрипте, который мы просили платформу выполнить, была строка
`P1C-EXEC-MARKER`, и мы искали её в журнале `/Out` и в консоли процесса. Ни в одном прогоне маркер
не появился. «3 байта» в колонке байт — это пустой журнал из одного BOM: платформа создала файл, но
не написала в него ни строчки.

## 1. `/RunScript <файл>`: 12 написаний вызова — один и тот же исход

Измерено 12 вызовов `/RunScript <файл>`: 5 в `reports/exec-12-programs.json` (рабочий скрипт
с маркером в cp1251, битый скрипт, отсутствующий файл, скрипт в utf-8, скрипт только из ASCII)
и 7 в `reports/exec-12-sweep.json` (тот же скрипт в utf-8, utf-8 с BOM и cp1251, плюс написания
с `/authoff`, `-User=… -Pwd=…`, `-CurrentUser` и с внешней ИБ). Все 12: код 1,
2.0-2.1 с, `/Out` 3 байта (пустой), маркера нет. Контроль `RunScript` вообще без аргумента
(`runscript-noarg`) даёт ровно те же 1 / 2.0 с / 3 байта.

Отдельно `runscript_matches_load_noarg = false` и `runscript_matches_load_ok = false`: журнал
загружающей команды при ошибке содержит строку («Файл не обнаружен ''»), журнал `/RunScript` —
ни строки.

**Следствие для инструментов p1c.** Ни один способ исполнить BSL из командной строки не даёт
ни результата скрипта, ни объяснения отказа. Поэтому `p1c` не может ни запустить наш код в ИБ, ни
проверить запросы, которые исполняются только в ИБ (запрос схемы компоновки данных, запросы
обработок). Пустой журнал при коде 1 — это не «ошибки нет»: отсутствие строк должно считаться
отсутствием доказательства, а не успехом.

**Что с этим делать (часть плана оптимизации p1c).** Не строить в `p1c` инструмент «проверить
запрос запуском в ИБ». Проверку запросов делать статически (sdbl), а в отчётах прямо писать, что
исполнение BSL в командной строке данной платформы (8.3.27.1606) не подтверждено ни одной формой.

## 2. `/EXECUTE`: процесс не заканчивается

`/EXECUTE <файл>` и `/EXECUTE <файл> /authoff`: код 1, 40.3-40.4 с (это наш таймаут, не ответ
платформы), `/Out` 0 байт. Для сравнения: `/RunScript` с тем же скриптом заканчивается за 2.0 с.

**Следствие для инструментов p1c.** Форма, которая висит дольше таймаута, не может быть частью
автоматической лестницы: она не различает «команда не существует», «команда требует GUI» и
«команда ждёт пользователя».

## 3. Модификаторы доступа неотличимы от базовой загрузки

Лестница `AUTH_LADDER`: базовая `load-ok` и четыре модификатора (`/authoff`, `-AllUsers`,
`-CurrentUser`, `-User=… -Pwd=…`) — все код 0, 2.0-3.0 с, `/Out` 3 байта. Ключи отчёта:
`auth_same_as_baseline` = все пять вариантов, `auth_differs_from_baseline` = [], `auth_timed_out` = [].

**Следствие для инструментов p1c.** На файловой загрузке конфигурации модификаторы доступа
наблюдаемо не влияют ни на что: их нельзя ни «проверить», ни «исключить как лишние». В документации
`p1c` их надо описывать как параметры подключения к серверной ИБ, а не как параметры
`/LoadConfigFromFiles`.

## 4. Контроли загружающей команды: здесь платформа говорит

`load-ok`: 0 / 3.0 с / 3 байта. `load-noarg`: 1 / 40 байта / строка `Файл не обнаружен ''`.
`load-baddir`: 1 / 117 байт / строка `Файл не обнаружен '<несуществующий каталог>'`.
`controls_distinct = true`: три разных исхода на трёх шагах, меняющих одну часть команды.

**Следствие для инструментов p1c.** Дешёвый способ отличить «загрузка не выполнена» от «загрузка
выполнилась пустотой» — читать строки `/Out`, а не только код. Именно так устроен `empty_dump_detected`
в `scripts/gate.py`: код 0 без выгруженных файлов считается отказом.

## 5. Отрицательные контроли имён флагов: `-<несуществующее>` подвешивает процесс

`/ZzzNetakoyKomandyNet`: код 1, 2.0 с, 70 байт, строка `Пользователь ИБ не идентифицирован`.
`-ZzzNetakoyKomandyNet`: код 1, 40.4-60.3 с (наш таймаут), `/Out` 0 байт. Отсюда
`negative_clean = false`: «несуществующее имя с дефисом» неотлично от зависания, и по нему нельзя
проверять, что платформа знает данное имя.

**Следствие для инструментов p1c.** Отрицательный контроль пригоден только для имён с косой
чертой. Положительный контроль устроен иначе: имена из замера, которые лестницы реально
передают, дают код 0 (`-files`, `-RebuildConfigurationExtensions`,
`/CheckCanApplyConfigurationExtensions` в `reports/effect-16-*-full.json`), а вывод о
несуществующем имени делается по членству в замере
`p1c/src/p1c/data/test_cli_flags.json`, а не по коду возврата.

## 6. Тестовые формы запуска: восемь вариантов, ноль строк журнала

`/TESTCLIENT <файл>`, `/TESTCLIENT`, `/TESTMANAGER <файл>`, `/TESTMANAGER`, `-testFile <файл>`,
`-testOut <файл>`, `-TestOnly`, `/AllowExecuteScheduledJobs` — все: код 1, 30.3-30.4 с (таймаут),
`/Out` 0 байт. Ключи отчёта: `test_timed_out` перечисляет все восемь, `test_silent_variants` —
ещё и базовый `/RunScript`, `test_output_variants` = `enterprise-runscript`, `extproc-file`,
`extproc-noarg` (то есть журнал написан только там, где ругается сама платформа).

**Следствие для инструментов p1c.** В `p1c` нет и не может быть «прогона тестов 1С из
командной строки». Тесты платформы для нас — закрытая зона; проверять поведение кода можно только
статически или через внешние обработки (раздел 8).

## 7. `ENTERPRISE` без окон невозможна

`enterprise-plain` (программа `ENTERPRISE`, `/DisableStartupDialogs`, `/authoff`) и
`enterprise-runscript`: код 1, 1.0-2.0 с, `/Out` 107 байт, дословно
`Запрещено использование окон. Передан ключ DisableStartupDialogs.`

**Следствие для инструментов p1c.** Любая попытка читать данные через интерфейс
`1cv8c`/`ENTERPRISE` в автоматике обречена; это же объясняет, почему `p1c` не может читать то, что
видно только в форме (описание формы, права в интерфейсе).

## 8. Внешние обработки: порядок аргументов и mojibake

`/LoadExternalDataProcessorOrReportFromFiles <файл, не являющийся обработкой>`: код 1, 475 байт,
пять строк, среди них `Целевой каталог или файл: 앀诌Ɵ` (U+C540, U+8BCC, U+19F — искажённое имя
пути) и `Файл 'file://…' не является файлом обработки или отчета.`
Без аргумента: код 1, 200 байт, пять строк (последняя пустая); оба пути платформа вывела искажёнными
символами: `\ue540쁹ƹ` и `\ue540쁹ƹ` — private-use зона Unicode (U+E540), то есть платформа
печатает отсутствующий аргумент, а не наш путь.
Двухаргументный контроль `/DumpExternalDataProcessorOrReportToFiles <файл> <каталог>` (код 1,
410 байт) показывает, что платформа подписывает аргументы наперекос: в строке
`Входной бинарный файл:` оказывается второй аргумент, а в
`Каталог или корневой файл выгрузки:` — первый. Тот же порядок строк подтверждает
`Формат: Иерархический` без всякого `-Format` в команде.

**Следствие для инструментов p1c.** Круг «`.epf` → XML → `.epf`» (docs/evidence/epf-roundtrip.md)
замыкается только когда аргументы стоят в том порядке, который платформа реально читает; подпись
аргументов в выводе платформы нельзя использовать как доказательство того, что мы передали их
правильно. Пустые имена в журнале — не искажение нашего вызова: платформа печатает
отсутствующий аргумент искажёнными символами, и парсить такой журнал нельзя.

## 9. Режим программы (`DESIGNER` против `CONFIG`) наблюдаемо не влияет

Лестница `MODE_LADDER` меняет один токен в позиции 0: `DESIGNER` → `CONFIG`
(`ladder_token_positions`), остальные токены идентичны. Оба шага: код 0, 2.0 с, `/Out` 3 байта,
`ladder_single_command_token = true`.

**Следствие для инструментов p1c.** Выбор режима — не то, что можно проверить по выводу журнала `/Out`;
его надо фиксировать в самих вызовах (загрузка конфигурации работает и в `CONFIG`), а различие
режимов доказывать формой вызова, а не исходом.

## 10. Дословные таблицы прогонов

Таблицы собраны генератором `exec_tables.py` (одноразовый скрипт вне репозитория) из
тех же отчётов, из которых собран текст выше; в колонке `маркер BSL` стоит `нет`, если
строка `P1C-EXEC-MARKER` не появилась ни в `/Out`, ни в консоли, и `таймаут`, если процесс
был прерван нашим таймаутом. Дословные подписи аргументов живут в колонке «строки /Out»:
именно они, а не наши формулировки, доказывают, как платформа прочитала команду. Длинные
значения агрегатов помечены `…(обрезано)`.

### exec-12-programs.json — формы запуска: /RunScript с разными написаниями скрипта
- `executed_variants` = []

| вариант | хвост командной строки после `<программа> DESIGNER /F <иб> /Out <файл>` | код | сек | байт в /Out | строки /Out (дословный список) | маркер BSL |
|---|---|---|---|---|---|---|
| runscript | `/DisableStartupDialogs /RunScript C:\Users\goof0\AppData\Local\Temp\opencode\p1c_effektivnost\exec_runscript_broken_cp1251.txt` | 1 | 2.0 | 3 | [] | нет |
| runscript | `/DisableStartupDialogs /RunScript C:\Users\goof0\AppData\Local\Temp\opencode\p1c_effektivnost\exec_runscript_runtime_cp1251.txt` | 1 | 2.0 | 3 | [] | нет |
| runscript | `/DisableStartupDialogs /RunScript C:\Users\goof0\AppData\Local\Temp\opencode\p1c_effektivnost\exec_runscript_missing_cp1251.txt` | 1 | 2.0 | 3 | [] | нет |
| runscript | `/DisableStartupDialogs /RunScript C:\Users\goof0\AppData\Local\Temp\opencode\p1c_effektivnost\exec_runscript_ascii_utf8.txt` | 1 | 2.0 | 3 | [] | нет |
| runscript | `/DisableStartupDialogs /RunScript C:\Users\goof0\AppData\Local\Temp\opencode\p1c_effektivnost\exec_runscript_empty_cp1251.txt` | 1 | 2.0 | 3 | [] | нет |

### exec-12-sweep.json — обход форм исполнения (RunScript, EXECUTE, варианты доступа)
- `executed_variants` = []

| вариант | хвост командной строки после `<программа> DESIGNER /F <иб> /Out <файл>` | код | сек | байт в /Out | строки /Out (дословный список) | маркер BSL |
|---|---|---|---|---|---|---|
| runscript | `/DisableStartupDialogs /RunScript C:\Users\goof0\AppData\Local\Temp\opencode\p1c_effektivnost\exec_runscript_marker_cp1251.txt` | 1 | 2.0 | 3 | [] | нет |
| runscript | `/DisableStartupDialogs /RunScript C:\Users\goof0\AppData\Local\Temp\opencode\p1c_effektivnost\exec_runscript_marker_utf8bom.txt` | 1 | 2.0 | 3 | [] | нет |
| runscript | `/DisableStartupDialogs /RunScript C:\Users\goof0\AppData\Local\Temp\opencode\p1c_effektivnost\exec_runscript_marker_utf8.txt` | 1 | 2.0 | 3 | [] | нет |
| execute | `/DisableStartupDialogs /EXECUTE C:\Users\goof0\AppData\Local\Temp\opencode\p1c_effektivnost\exec_execute_marker_utf8.txt` | 1 | 40.4 | 0 | [] | таймаут |
| runscript-authoff | `/DisableStartupDialogs /RunScript C:\Users\goof0\AppData\Local\Temp\opencode\p1c_effektivnost\exec_runscript-authoff_marker_utf8.txt /authoff` | 1 | 2.0 | 3 | [] | нет |
| runscript-credentials | `/DisableStartupDialogs /RunScript C:\Users\goof0\AppData\Local\Temp\opencode\p1c_effektivnost\exec_runscript-credentials_marker_utf8.txt -User=1CTest -PUser=1CTest` | 1 | 2.0 | 3 | [] | нет |
| runscript-currentuser | `/DisableStartupDialogs /RunScript C:\Users\goof0\AppData\Local\Temp\opencode\p1c_effektivnost\exec_runscript-currentuser_marker_utf8.txt -CurrentUser` | 1 | 2.0 | 3 | [] | нет |
| runscript-external | `/DisableStartupDialogs /RunScript C:\Users\goof0\AppData\Local\Temp\opencode\p1c_effektivnost\exec_runscript-external_marker_utf8.txt -ExternalConnection` | 1 | 2.0 | 3 | [] | нет |

### exec-12-controls.json — контроли: загружающая команда без аргумента и с битым аргументом
- `controls_classes` = [[0, false, "пустой"], [1, false, "непустой"], [1, false, "пустой"]]
- `controls_distinct` = true
- `executed_variants` = []

| вариант | хвост командной строки после `<программа> DESIGNER /F <иб> /Out <файл>` | код | сек | байт в /Out | строки /Out (дословный список) | маркер BSL |
|---|---|---|---|---|---|---|
| load-ok | `/DisableStartupDialogs /LoadConfigFromFiles C:\Users\goof0\Documents\REA\Platform1C\effektivnost-otdela\cfg\ЭффективностьОтдела` | 0 | 3.0 | 3 | [] | нет |
| load-noarg | `/DisableStartupDialogs /LoadConfigFromFiles` | 1 | 2.0 | 40 | ["Файл не обнаружен ''"] | нет |
| load-baddir | `/DisableStartupDialogs /LoadConfigFromFiles C:\Users\goof0\AppData\Local\Temp\opencode\p1c_effektivnost\no-such-directory` | 1 | 2.0 | 117 | ["Файл не обнаружен 'C:\\Users\\goof0\\AppData\\Local\\Temp\\opencode\\p1c_effektivnost\\no-such-directory'"] | нет |
| runscript-noarg | `/DisableStartupDialogs /RunScript` | 1 | 2.1 | 3 | [] | нет |

### exec-12-negative.json — отрицательные контроли: несуществующие имена флагов
- `executed_variants` = []
- `negative_classes` = {"runscript": [1, false, "пустой"], "bogus-slash": [1, false, "непустой"], "bogus-dash": [1, true, "пустой"]}
- `negative_clean` = false
- `negative_matches_runscript` = false

| вариант | хвост командной строки после `<программа> DESIGNER /F <иб> /Out <файл>` | код | сек | байт в /Out | строки /Out (дословный список) | маркер BSL |
|---|---|---|---|---|---|---|
| runscript | `/DisableStartupDialogs /RunScript C:\Users\goof0\AppData\Local\Temp\opencode\p1c_effektivnost\exec_runscript_marker_cp1251.txt` | 1 | 2.1 | 3 | [] | нет |
| bogus-slash | `/DisableStartupDialogs /ZzzNetakoyKomandyNet` | 1 | 1.0 | 70 | ["Пользователь ИБ не идентифицирован"] | нет |
| bogus-dash | `/DisableStartupDialogs -ZzzNetakoyKomandyNet` | 1 | 60.3 | 0 | [] | таймаут |

### exec-13-auth.json — контроль: модификаторы доступа к /LoadConfigFromFiles
- `auth_classes` = {"load-ok": [0, false, "пустой"], "load-authoff": [0, false, "пустой"], "load-allusers": [0, false, "пустой"], "load-currentuser": [0, false, "пустой"], "load-credentials": [0, false, "пустой"]}
- `auth_differs_from_baseline` = []
- `auth_same_as_baseline` = ["load-ok", "load-authoff", "load-allusers", "load-currentuser", "load-credentials"]
- `auth_timed_out` = []
- `executed_variants` = []
- `ladder_diffs` = [{"from": "", "to": "load-ok", "changed_triple": [], "changed_command": [], "single_variable": true, "single_command_part": true}, {"from": "load-ok", "to": "load-authoff", "changed_triple": ["variant"], "changed_command": ["tail"], "single_variable": true, "single_command_part": true}, {"from": "load-authoff", "to": "load-allusers", "changed_triple": ["variant"], "changed_command": ["tail"], "single_variable": true, "single_command_part": true}, {"from": "load-allusers", "to": "load-currentuser", "changed_triple": ["variant"], "changed_command": ["tail"], "single_variable": true, "single_comm …(обрезано)
- `ladder_name` = "AUTH_LADDER"
- `ladder_single_command_part` = true
- `ladder_single_variable` = true

| вариант | хвост командной строки после `<программа> DESIGNER /F <иб> /Out <файл>` | код | сек | байт в /Out | строки /Out (дословный список) | маркер BSL |
|---|---|---|---|---|---|---|
| load-ok | `/DisableStartupDialogs /LoadConfigFromFiles C:\Users\goof0\Documents\REA\Platform1C\effektivnost-otdela\cfg\ЭффективностьОтдела` | 0 | 3.0 | 3 | [] | нет |
| load-authoff | `/DisableStartupDialogs /LoadConfigFromFiles C:\Users\goof0\Documents\REA\Platform1C\effektivnost-otdela\cfg\ЭффективностьОтдела /authoff` | 0 | 2.0 | 3 | [] | нет |
| load-allusers | `/DisableStartupDialogs /LoadConfigFromFiles C:\Users\goof0\Documents\REA\Platform1C\effektivnost-otdela\cfg\ЭффективностьОтдела -AllUsers` | 0 | 2.0 | 3 | [] | нет |
| load-currentuser | `/DisableStartupDialogs /LoadConfigFromFiles C:\Users\goof0\Documents\REA\Platform1C\effektivnost-otdela\cfg\ЭффективностьОтдела -CurrentUser` | 0 | 2.0 | 3 | [] | нет |
| load-credentials | `/DisableStartupDialogs /LoadConfigFromFiles C:\Users\goof0\Documents\REA\Platform1C\effektivnost-otdela\cfg\ЭффективностьОтдела -User=1CTest -Pwd=1CTest` | 0 | 2.0 | 3 | [] | нет |

### exec-13-sweep.json — обход форм исполнения, второй заход
- `executed_variants` = []
- `ladder_diffs` = [{"from": "", "to": "runscript", "changed_triple": [], "changed_command": [], "single_variable": true, "single_command_part": true}, {"from": "runscript", "to": "runscript", "changed_triple": ["encoding"], "changed_command": [], "single_variable": true, "single_command_part": true}, {"from": "runscript", "to": "runscript", "changed_triple": ["encoding"], "changed_command": [], "single_variable": true, "single_command_part": true}, {"from": "runscript", "to": "execute", "changed_triple": ["variant"], "changed_command": ["names"], "single_variable": true, "single_command_part": true}, {"from": " …(обрезано)
- `ladder_name` = "SWEEP"
- `ladder_single_command_part` = true
- `ladder_single_variable` = true

| вариант | хвост командной строки после `<программа> DESIGNER /F <иб> /Out <файл>` | код | сек | байт в /Out | строки /Out (дословный список) | маркер BSL |
|---|---|---|---|---|---|---|
| runscript | `/DisableStartupDialogs /RunScript C:\Users\goof0\AppData\Local\Temp\opencode\p1c_effektivnost\exec_runscript_marker_cp1251.txt` | 1 | 2.0 | 3 | [] | нет |
| runscript | `/DisableStartupDialogs /RunScript C:\Users\goof0\AppData\Local\Temp\opencode\p1c_effektivnost\exec_runscript_marker_utf8bom.txt` | 1 | 2.0 | 3 | [] | нет |
| runscript | `/DisableStartupDialogs /RunScript C:\Users\goof0\AppData\Local\Temp\opencode\p1c_effektivnost\exec_runscript_marker_utf8.txt` | 1 | 2.0 | 3 | [] | нет |
| execute | `/DisableStartupDialogs /EXECUTE C:\Users\goof0\AppData\Local\Temp\opencode\p1c_effektivnost\exec_execute_marker_utf8.txt` | 1 | 40.3 | 0 | [] | таймаут |
| execute-authoff | `/DisableStartupDialogs /EXECUTE C:\Users\goof0\AppData\Local\Temp\opencode\p1c_effektivnost\exec_execute-authoff_marker_utf8.txt /authoff` | 1 | 40.3 | 0 | [] | таймаут |
| runscript-authoff | `/DisableStartupDialogs /RunScript C:\Users\goof0\AppData\Local\Temp\opencode\p1c_effektivnost\exec_runscript-authoff_marker_utf8.txt /authoff` | 1 | 2.0 | 3 | [] | нет |
| runscript-credentials | `/DisableStartupDialogs /RunScript C:\Users\goof0\AppData\Local\Temp\opencode\p1c_effektivnost\exec_runscript-credentials_marker_utf8.txt -User=1CTest -Pwd=1CTest` | 1 | 2.0 | 3 | [] | нет |
| runscript-currentuser | `/DisableStartupDialogs /RunScript C:\Users\goof0\AppData\Local\Temp\opencode\p1c_effektivnost\exec_runscript-currentuser_marker_utf8.txt -CurrentUser` | 1 | 2.0 | 3 | [] | нет |
| runscript-external | `/DisableStartupDialogs /RunScript C:\Users\goof0\AppData\Local\Temp\opencode\p1c_effektivnost\exec_runscript-external_marker_utf8.txt -ExternalConnection` | 1 | 2.0 | 3 | [] | нет |

### exec-13-controls.json — контроли лестницы: load-ok / load-noarg / load-baddir
- `controls_classes` = [[0, false, "пустой"], [1, false, "непустой"], [1, false, "пустой"]]
- `controls_classes_by_variant` = {"runscript": [1, false, "пустой"], "runscript-noarg": [1, false, "пустой"], "load-noarg": [1, false, "непустой"], "load-ok": [0, false, "пустой"], "load-baddir": [1, false, "непустой"]}
- `controls_distinct` = true
- `executed_variants` = []
- `ladder_diffs` = [{"from": "", "to": "runscript", "changed_triple": [], "changed_command": [], "single_variable": true, "single_command_part": true}, {"from": "runscript", "to": "runscript-noarg", "changed_triple": ["variant"], "changed_command": ["args"], "single_variable": true, "single_command_part": true}, {"from": "runscript-noarg", "to": "load-noarg", "changed_triple": ["variant"], "changed_command": ["names"], "single_variable": true, "single_command_part": true}, {"from": "load-noarg", "to": "load-ok", "changed_triple": ["variant"], "changed_command": ["args"], "single_variable": true, "single_command_ …(обрезано)
- `ladder_name` = "CONTROLS"
- `ladder_single_command_part` = true
- `ladder_single_variable` = true
- `runscript_matches_load_noarg` = false
- `runscript_matches_load_ok` = false

| вариант | хвост командной строки после `<программа> DESIGNER /F <иб> /Out <файл>` | код | сек | байт в /Out | строки /Out (дословный список) | маркер BSL |
|---|---|---|---|---|---|---|
| runscript | `/DisableStartupDialogs /RunScript C:\Users\goof0\AppData\Local\Temp\opencode\p1c_effektivnost\exec_runscript_marker_cp1251.txt` | 1 | 2.0 | 3 | [] | нет |
| runscript-noarg | `/DisableStartupDialogs /RunScript` | 1 | 2.0 | 3 | [] | нет |
| load-noarg | `/DisableStartupDialogs /LoadConfigFromFiles` | 1 | 2.0 | 40 | ["Файл не обнаружен ''"] | нет |
| load-ok | `/DisableStartupDialogs /LoadConfigFromFiles C:\Users\goof0\Documents\REA\Platform1C\effektivnost-otdela\cfg\ЭффективностьОтдела` | 0 | 2.0 | 3 | [] | нет |
| load-baddir | `/DisableStartupDialogs /LoadConfigFromFiles C:\Users\goof0\AppData\Local\Temp\opencode\p1c_effektivnost\no-such-directory` | 1 | 2.0 | 117 | ["Файл не обнаружен 'C:\\Users\\goof0\\AppData\\Local\\Temp\\opencode\\p1c_effektivnost\\no-such-directory'"] | нет |

### exec-13-negative.json — отрицательные контроли, второй заход
- `executed_variants` = []
- `ladder_diffs` = [{"from": "", "to": "runscript", "changed_triple": [], "changed_command": [], "single_variable": true, "single_command_part": true}, {"from": "runscript", "to": "runscript-noarg", "changed_triple": ["variant"], "changed_command": ["args"], "single_variable": true, "single_command_part": true}, {"from": "runscript-noarg", "to": "bogus-slash", "changed_triple": ["variant"], "changed_command": ["names"], "single_variable": true, "single_command_part": true}, {"from": "bogus-slash", "to": "bogus-dash", "changed_triple": ["variant"], "changed_command": ["names"], "single_variable": true, "single_co …(обрезано)
- `ladder_name` = "NEGATIVE_LADDER"
- `ladder_single_command_part` = true
- `ladder_single_variable` = true
- `negative_classes` = {"runscript": [1, false, "пустой"], "runscript-noarg": [1, false, "пустой"], "bogus-slash": [1, false, "непустой"], "bogus-dash": [1, true, "пустой"]}
- `negative_clean` = false
- `negative_matches_runscript` = false
- `negative_matches_runscript_noarg` = false

| вариант | хвост командной строки после `<программа> DESIGNER /F <иб> /Out <файл>` | код | сек | байт в /Out | строки /Out (дословный список) | маркер BSL |
|---|---|---|---|---|---|---|
| runscript | `/DisableStartupDialogs /RunScript C:\Users\goof0\AppData\Local\Temp\opencode\p1c_effektivnost\exec_runscript_marker_cp1251.txt` | 1 | 2.0 | 3 | [] | нет |
| runscript-noarg | `/DisableStartupDialogs /RunScript` | 1 | 2.0 | 3 | [] | нет |
| bogus-slash | `/DisableStartupDialogs /ZzzNetakoyKomandyNet` | 1 | 2.0 | 70 | ["Пользователь ИБ не идентифицирован"] | нет |
| bogus-dash | `/DisableStartupDialogs -ZzzNetakoyKomandyNet` | 1 | 40.4 | 0 | [] | таймаут |

### exec-13-test.json — формы тестового запуска и внешней обработки
- `executed_variants` = []
- `ladder_diffs` = [{"from": "", "to": "runscript", "changed_triple": [], "changed_command": [], "single_variable": true, "single_command_part": true}, {"from": "runscript", "to": "enterprise-runscript", "changed_triple": ["variant"], "changed_command": ["mode"], "single_variable": true, "single_command_part": true}, {"from": "enterprise-runscript", "to": "runscript", "changed_triple": ["variant"], "changed_command": ["mode"], "single_variable": true, "single_command_part": true}, {"from": "runscript", "to": "testclient-file", "changed_triple": ["variant"], "changed_command": ["names"], "single_variable": true,  …(обрезано)
- `ladder_name` = "TEST_LADDER"
- `ladder_single_command_part` = true
- `ladder_single_variable` = true
- `test_classes` = {"runscript": [1, false, "пустой"], "enterprise-runscript": [1, false, "непустой"], "testclient-file": [1, true, "пустой"], "testfile-flag": [1, true, "пустой"], "testout-flag": [1, true, "пустой"], "testmanager-file": [1, true, "пустой"], "extproc-file": [1, false, "непустой"], "extproc-noarg": [1, false, "непустой"], "jobs-allow": [1, true, "пустой"], "testonly-flag": [1, true, "пустой"], "testclient-plain": [1, true, "пустой"], "testmanager-plain": [1, true, "пустой"]}
- `test_output_variants` = ["enterprise-runscript", "extproc-file", "extproc-noarg"]
- `test_silent_variants` = ["runscript", "runscript", "testclient-file", "testfile-flag", "testout-flag", "testmanager-file", "jobs-allow", "testonly-flag", "testclient-plain", "testmanager-plain"]
- `test_timed_out` = ["testclient-file", "testfile-flag", "testout-flag", "testmanager-file", "jobs-allow", "testonly-flag", "testclient-plain", "testmanager-plain"]

| вариант | хвост командной строки после `<программа> DESIGNER /F <иб> /Out <файл>` | код | сек | байт в /Out | строки /Out (дословный список) | маркер BSL |
|---|---|---|---|---|---|---|
| runscript | `/DisableStartupDialogs /RunScript C:\Users\goof0\AppData\Local\Temp\opencode\p1c_effektivnost\exec_runscript_marker_cp1251.txt` | 1 | 2.0 | 3 | [] | нет |
| enterprise-runscript | `/DisableStartupDialogs /RunScript C:\Users\goof0\AppData\Local\Temp\opencode\p1c_effektivnost\exec_enterprise-runscript_marker_cp1251.txt` | 1 | 2.0 | 107 | ["Запрещено использование окон. Передан ключ DisableStartupDialogs."] | нет |
| runscript | `/DisableStartupDialogs /RunScript C:\Users\goof0\AppData\Local\Temp\opencode\p1c_effektivnost\exec_runscript_marker_cp1251.txt` | 1 | 2.0 | 3 | [] | нет |
| testclient-file | `/DisableStartupDialogs /TESTCLIENT C:\Users\goof0\AppData\Local\Temp\opencode\p1c_effektivnost\exec_testclient-file_marker_cp1251.txt` | 1 | 30.3 | 0 | [] | таймаут |
| testfile-flag | `/DisableStartupDialogs -testFile C:\Users\goof0\AppData\Local\Temp\opencode\p1c_effektivnost\exec_testfile-flag_marker_cp1251.txt` | 1 | 30.3 | 0 | [] | таймаут |
| testout-flag | `/DisableStartupDialogs -testOut C:\Users\goof0\AppData\Local\Temp\opencode\p1c_effektivnost\exec_testout-flag_marker_cp1251.txt` | 1 | 30.3 | 0 | [] | таймаут |
| testmanager-file | `/DisableStartupDialogs /TESTMANAGER C:\Users\goof0\AppData\Local\Temp\opencode\p1c_effektivnost\exec_testmanager-file_marker_cp1251.txt` | 1 | 30.3 | 0 | [] | таймаут |
| extproc-file | `/DisableStartupDialogs /LoadExternalDataProcessorOrReportFromFiles C:\Users\goof0\AppData\Local\Temp\opencode\p1c_effektivnost\exec_extproc-file_marker_cp1251.txt` | 1 | 2.0 | 475 | ["Загрузка внешней обработки или отчета из XML.", "Корневой файл выгрузки: C:\\Users\\goof0\\AppData\\Local\\Temp\\opencode\\p1c_effektivnost\\exec_extproc-file_marker_cp1251.txt", "Целевой каталог или файл: 앀诌Ɵ", "", "Файл 'file://C:\\Users\\goof0\\AppData\\Local\\Temp\\opencode\\p1c_effektivnost\\exec_extproc-file_marker_cp1251.txt' не является файлом обработки или отчета."] | нет |
| extproc-noarg | `/DisableStartupDialogs /LoadExternalDataProcessorOrReportFromFiles` | 1 | 2.0 | 200 | ["Загрузка внешней обработки или отчета из XML.", "Корневой файл выгрузки: 쁹ƹ", "Целевой каталог или файл: 쁹ƹ", "", ""] | нет |
| jobs-allow | `/DisableStartupDialogs /AllowExecuteScheduledJobs` | 1 | 30.3 | 0 | [] | таймаут |
| testonly-flag | `/DisableStartupDialogs -TestOnly` | 1 | 30.3 | 0 | [] | таймаут |
| testclient-plain | `/DisableStartupDialogs /TESTCLIENT` | 1 | 30.3 | 0 | [] | таймаут |
| testmanager-plain | `/DisableStartupDialogs /TESTMANAGER` | 1 | 30.4 | 0 | [] | таймаут |

### exec-13-enterprise.json — программа ENTERPRISE без команд исполнения
- `executed_variants` = []
- `ladder_diffs` = [{"from": "", "to": "enterprise-plain", "changed_triple": [], "changed_command": [], "single_variable": true, "single_command_part": true}]
- `ladder_name` = "single"
- `ladder_single_command_part` = true
- `ladder_single_variable` = true

| вариант | хвост командной строки после `<программа> DESIGNER /F <иб> /Out <файл>` | код | сек | байт в /Out | строки /Out (дословный список) | маркер BSL |
|---|---|---|---|---|---|---|
| enterprise-plain | `/DisableStartupDialogs /authoff` | 1 | 1.0 | 107 | ["Запрещено использование окон. Передан ключ DisableStartupDialogs."] | нет |

### exec-14-dumpproc-args.json — /DumpExternalDataProcessorOrReportToFiles с двумя путями: подписи аргументов наперекос
- `executed_variants` = []
- `ladder_diffs` = [{"from": "", "to": "dumpproc-args", "changed_triple": [], "changed_command": [], "single_variable": true, "single_command_part": true}]
- `ladder_name` = "single"
- `ladder_single_command_part` = true
- `ladder_single_variable` = true

| вариант | хвост командной строки после `<программа> DESIGNER /F <иб> /Out <файл>` | код | сек | байт в /Out | строки /Out (дословный список) | маркер BSL |
|---|---|---|---|---|---|---|
| dumpproc-args | `/DisableStartupDialogs /DumpExternalDataProcessorOrReportToFiles C:\Users\goof0\AppData\Local\Temp\opencode\p1c_effektivnost\exec_dumpproc-args_marker_utf8.txt C:\Users\goof0\AppData\Local\Temp\opencode\p1c_effektivnost\no-such-directory` | 1 | 2.0 | 410 | ["Выгрузка внешней обработки или отчета в XML.", "Входной бинарный файл: C:\\Users\\goof0\\AppData\\Local\\Temp\\opencode\\p1c_effektivnost\\no-such-directory", "Каталог или корневой файл выгрузки: C:\\Users\\goof0\\AppData\\Local\\Temp\\opencode\\p1c_effektivnost\\exec_dumpproc-args_marker_utf8.txt", "Формат: Иерархический", ""] | нет |

### exec-14-extproc-twoargs.json — /LoadExternalDataProcessorOrReportFromFiles с двумя путями
- `executed_variants` = []
- `ladder_diffs` = [{"from": "", "to": "extproc-twoargs", "changed_triple": [], "changed_command": [], "single_variable": true, "single_command_part": true}]
- `ladder_name` = "single"
- `ladder_single_command_part` = true
- `ladder_single_variable` = true

| вариант | хвост командной строки после `<программа> DESIGNER /F <иб> /Out <файл>` | код | сек | байт в /Out | строки /Out (дословный список) | маркер BSL |
|---|---|---|---|---|---|---|
| extproc-twoargs | `/DisableStartupDialogs /LoadExternalDataProcessorOrReportFromFiles C:\Users\goof0\AppData\Local\Temp\opencode\p1c_effektivnost\exec_extproc-twoargs_marker_utf8.txt C:\Users\goof0\AppData\Local\Temp\opencode\p1c_effektivnost\no-such-directory` | 1 | 2.0 | 546 | ["Загрузка внешней обработки или отчета из XML.", "Корневой файл выгрузки: C:\\Users\\goof0\\AppData\\Local\\Temp\\opencode\\p1c_effektivnost\\exec_extproc-twoargs_marker_utf8.txt", "Целевой каталог или файл: C:\\Users\\goof0\\AppData\\Local\\Temp\\opencode\\p1c_effektivnost\\no-such-directory", "", "Файл 'file://C:\\Users\\goof0\\AppData\\Local\\Temp\\opencode\\p1c_effektivnost\\exec_extproc-twoargs_marker_utf8.txt' не является файлом обработки или отчета."] | нет |

### exec-16-modes.json — лестница MODE_LADDER: режим запуска программы
- `executed_variants` = []
- `ladder_diffs` = [{"from": "", "to": "load-ok", "changed_triple": [], "changed_command": [], "command_tokens": [], "single_variable": true, "single_command_part": true, "single_command_token": true}, {"from": "load-ok", "to": "config-load-ok", "changed_triple": ["variant"], "changed_command": ["mode"], "command_tokens": [{"part": "mode", "position": 0, "from": "DESIGNER", "to": "CONFIG"}], "single_variable": true, "single_command_part": true, "single_command_token": true}]
- `ladder_multi_token_documented` = true
- `ladder_multi_token_steps` = []
- `ladder_mutating_variants` = ["config-load-ok"]
- `ladder_name` = "MODE_LADDER"
- `ladder_single_command_part` = true
- `ladder_single_command_token` = true
- `ladder_single_variable` = true
- `ladder_token_positions` = [{"from": "load-ok", "to": "config-load-ok", "tokens": [{"part": "mode", "position": 0, "from": "DESIGNER", "to": "CONFIG"}]}]

| вариант | хвост командной строки после `<программа> DESIGNER /F <иб> /Out <файл>` | код | сек | байт в /Out | строки /Out (дословный список) | маркер BSL |
|---|---|---|---|---|---|---|
| load-ok | `/DisableStartupDialogs /LoadConfigFromFiles C:\Users\goof0\Documents\REA\Platform1C\effektivnost-otdela\cfg\ЭффективностьОтдела` | 0 | 2.0 | 3 | [] | нет |
| config-load-ok | `/DisableStartupDialogs /LoadConfigFromFiles C:\Users\goof0\Documents\REA\Platform1C\effektivnost-otdela\cfg\ЭффективностьОтдела` | 0 | 2.0 | 3 | [] | нет |

## Что с этим делать (сводный список плана оптимизации p1c)

1. В `src/p1c/test/run.py` — не выбрасывать stdout процесса и собирать argv без битой склейки;
   сегодня вывод тестов теряется, и «тихий» прогон неотличим от зависшего.
2. В `cli/runner.py:286,298` — не перезаписывать `--root` молча; порядок токенов в argv
   контролировать отдельным проверочным шагом (мы измеряем `single_command_token`, `p1c` — нет).
3. Во всех семи CLI `p1c` безусловный `return 0`: добавить различение «прогон не выполнялся»
   (пустой журнал / таймаут) и «прогон выполнился и ничего не нашёл».
4. Считать строки `/Out` честно (`out_lines_total` / `out_lines_unique`), а не по обрезке
   первых восьми: именно так мы доказали, что `/RunScript` и `/EXECUTE` не пишут ни строчки.
5. Контролировать сам факт загрузки (наш `empty_dump_detected`), а не код 0.
6. Не пытаться исполнять BSL и запросы в ИБ из командной строки: зафиксировать в документации
   `p1c`, что `/RunScript`, `/EXECUTE`, `/TESTCLIENT`, `/TESTMANAGER`, `-testFile`, `-testOut`,
   `-TestOnly`, `/AllowExecuteScheduledJobs` и `ENTERPRISE` без окон измеренно недоступны.
