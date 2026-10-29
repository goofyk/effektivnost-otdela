# SDD ledger — plan: docs/superpowers/plans/2026-10-26-effektivnost-otdela.md

## Rulings сделано на старте

- Ruling: тесты контура на stdlib `unittest` (`python -m unittest discover -s tests`), не pytest — pytest в среде пользователя не установлен (проверено: `ModuleNotFoundError: No module named 'pytest'`), устанавливать пакет без запроса нельзя. Цена, если неверно: переписать тесты на pytest позже.
- Ruling: скрипты skill (`sdd-workspace`, `task-start`, `task-done`) — bash-обёртки, в PowerShell этого пользователя не запускаются (`CantActivateDocumentInPipeline`); журнал ведётся вручную в том же каталоге и формате. Цена: нет автоматической сверки коммитов, сверяю вручную по `git log` при каждом `task-done`.
- Ruling: сборка идёт в отдельном репозитории `effektivnost-otdela` на ветке `feat/config-effektivnost`, не в `main`; слияние в `main` — только в конце и локально (remote нет).
- Ruling: спецификация (раздел 5) не указывает источник данных отсутствий для регистра `ДоступностьСотрудников`. Добавляю документ `ОтсутствиеСотрудника` (5-й документ, Task 9) и регистр сведений `ОтсутствияСотрудников` (7-й регистр, Task 10); заполнение `ДоступностьСотрудников` делает обработка `РасчётЭффективности` (Task 16). Цена, если неверно: две дополнительные метаданные в наблюдении отчёта; польза — данные отсутствий вводятся по-человечески, а регистр доступности перестаёт быть пустым.

## Pre-flight: сверка интерфейсов между задачами

| Задачи | Что производит один / потребляет другой | Что найдено |
| --- | --- | --- |
| Task 8 → Task 10 | Task 8 хотел `ЗагрузкаСотрудника` с запросами к регистрам, которых ещё нет | Исправлено в плане: Task 8 оставляет `НормаЧасовМесяца`, `ЗагрузкаСотрудника` появляется в Task 10 |
| Task 9 → Task 10 | проводящие движения документов | План явно говорит: движения добавляются в Task 10, в Task 9 только `ПроверитьДанные` — согласовано |
| Task 4 → Task 11, Task 15 | имена констант `ЗагрузкаНижняяГраница/Верхняя/Критическая`, веса | Имена совпадают во всех задачах |
| Task 11 → Task 16 | `НачальныеНастройки.ЗагрузитьИзCSV`, `УправлениеЗагрузкой.*`, `КомпетентностнаяМатрица.*` | Сигнатуры совпадают |
| Task 12 → Task 13, Task 16 | возможность исполнить BSL в ИБ | Зависимость осознанная: при неподтверждённом исполнении Task 13 фиксирует `skipped` с причиной, Task 16 оставляет ручное заполнение |
| Task 10 → Task 15 | отчётный запрос по `ПланЗагрузки`/`ЗатратыВремени`/`ДоступностьСотрудников` | Имена регистров совпадают |
| Task 6 → Task 14 | ссылка `Сотрудники.Пользователь` на платформенный справочник пользователей | Риск отмечен в Task 6: проверка наблюдением |

## Ревю и поправки
- Task 0: Builder-check дизайн-документа независимым проверщиком — 6 существенных замечаний; поправки записаны в план (раздел «Поправки плана после builder-check», приоритет над текстом задач).
- Ruling: четыре подплана reviewer'a выполняются четырьмя фазами одного плана (один журнал, без пауз на согласование) — причина: окно 12 часов и требование готового отчёта к возвращению заказчика. Цена, если неверно: при провале фазы 1 дальнейшие фазы не начинаются, отчёт остановится на «каркас проверен».
- Ruling: наблюдение B1 (несуществующий каталог при /LoadConfigFromFiles) и B2 (выгрузка поверх существующего дампа после неудачной загрузки) переносятся в Task 1 — раньше, чем первая собственная конфигурация. Цена: +2 запуска платформы.
- Ruling: запрет формулировок «пригодна к работе» и «формы живые» без подтверждения исполнения BSL (Task 12) и без отрицательного примера на имени обработчика (Task 8 step 5).

## Итерация 1: журнал наблюдений и решения (итог)

- Наблюдение (зелёная итерация): гейт дал код 0 (`reports/gate-05.json`): `load 0` (3 с), `check 0`
  (2 с, 73 байта), `dump 0` (2 с), 25 свежих файлов выгрузки, `layout_source == layout_dump`
  (`files 24`), `expected_mismatch {}`, `rights.code 0`, `diagnostic_findings []`. Тесты контура:
  80 тестов `OK` (`python -m unittest discover -s tests`).
- Наблюдение (причина зависания загрузки найдена и устранена): блок `<object><name>Enum.ГрейдыСпециалистов</name>`
  в `Roles/СотрудникОтдела/Ext/Rights.xml`. Лестницы 4 и 5 (`probe/rights_bisect.py`): блоки прав на
  справочник/документ/регистры/отчёт/константу/конфигурацию загружаются по 2 с; один блок `Enum.` даже
  с единственным `Read` даёт `код нет, 30.1 с, 0 байт`. Канон: в 1672 файлах прав (103 686 блоков)
  вида `Enum.` нет ни одного (`docs/canonical-rights.json`). Доказательство в
  `docs/evidence/load-bisect.md`.
- Ruling: права ролей проверяются статически до цикла платформы (`scripts/rights.py`, шаг 1b гейта,
  канон `--canon docs/canonical-rights.json`). Причина: p1c права не читает вовсе, а платформа об
  отказе этого класса молчит. Цена, если неверно: если канон корпусов неполон, контур даст ложную
  находку; проверка канона — 6 корпусов, 1672 файла, границы выборки подписаны в замере.
- Наблюдение (дефект исправлен): неканонический узел `<v8:DecimalQualifiers><v8:Precision>2` платформа
  приняла молча и заменила на `NumberQualifiers` с `Digits 0/FractionDigits 0` — разрядность `Часы`
  и `Ставка` обнулилась. Канон: `NumberQualifiers` 6050, `DecimalQualifiers` 0, `Precision` 0
  (15 157 XML). Исправлено в 6 местах; после этого `AccumulationRegisters/ЗатратыВремени.xml` совпал
  с выгрузкой байт в байт. Доказательство: `docs/evidence/dump-canonicalization.md`,
  `probe/corpora_type_qualifiers.py`.
- Наблюдение (дефект исправлен): `ПриНовомОбъекте()` в модулях объекта справочника и документа —
  обработчик, который платформа никогда не вызывает (нет такого события у `CatalogObject`/
  `DocumentObject`; 0 встреч в 5601 каноническом `ObjectModule.bsl` и 0 в 15 055 канонических `.bsl`);
  `ПередЗаписью(Отказ, Замечание, Параметр)` — против `CatalogObject.BeforeWrite` 1/1 (платформа
  сообщила об этом кодом 101: «Переменная не определена (ГрейдыСпециалистов)»). Значения нового
  сотрудника перенесены в `ПриСозданииНаСервере` (канон: 12 478 встреч), обращение к перечислению —
  через `Перечисления.` (канон: 10 431 встреч).
- Наблюдение: платформа переписывает права роли (источник 8 блоков / 43 права → выгрузка 6 блоков /
  19 прав; у роли с `setForNewObjects=true` блоки сняты целиком) и добавляет в выгрузку
  `ConfigDumpInfo.xml` (есть во всех шести канонических корпусах). Контур различает эти два класса
  (`gate.PLATFORM_ADDED_FILES`, `file_diff.platform_added`, `rights.py` на источнике и на выгрузке).
- Ruling: формулировка «права роли настроены» не допускается, пока не получен неподвижный состав
  прав (`rights.check(источник) == rights.check(выгрузка)`). Следующий замер — переписать файл прав
  так, как его выкладывает платформа, и проверить совпадение. Цена, если неверно: ещё одна итерация
  цикла платформы.
- Ruling: пути корпусов существуют только в `local.paths.json` (ключи `corpora_*`) или в аргументах
  запуска; общий модуль `scripts/corpora.py` (`dumps`/`report`/`files_named`/`wanted_files`/
  `largest`/`relative`), обход ограничен `limit_per_root`, выборка упорядочена по относительному
  пути. Закрытие: семь замеров содержали абсолютные пути в файлах репозитория — вынесены; правило
  закреплено `tests/test_corpora.py`.
- Наблюдение (дефект данных p1c): `PLATFORM_NAME_PAIRS` рассинхронизирован — 731 пара из 1520 стоят
  в обратном порядке (первая находка — индекс 461 `('Низкая', 'Description')`), а оба читателя
  (`graph.py:50`, `metadata/model.py:396`) раскладывают список как `(en, ru)`.
- Наблюдение (слепая зона p1c с готовыми данными): объектные страницы событий в `EVENT_SIGNATURES`
  есть (42 из 135), но их читает только проверка форм; для модулей объекта проверок нет.
- Наблюдение (платформенная добавка права, gate-06): платформа добавила в выгрузку
  `DataAdministration` (`true`) в блок `Configuration.ЭффективностьОтдела`, которого в источнике
  не было (74 права → 75). Замер канона `docs/canonical-rights-configuration.json` (1360 блоков
  `Configuration.`): `DataAdministration` 15 раз, все 15 `true`; из 14 блоков с
  `Administration=true` 14 имеют `DataAdministration`, случаев «`Administration` без
  `DataAdministration`» — 0. Ruling: это право в блоке `Configuration.` писать явно.
- Наблюдение (зелёные итерации 2 и 3, gate-07/gate-08/gate-09): гейт даёт код 0 трижды подряд —
  `load 0` (3.0 с, 3 байта), `check 0` (2.0 с, 73 байта), `dump 0` (2.0 с, 3 байта); 25 свежих
  файлов выгрузки, `layout_source == layout_dump` (`files 24`), `expected_mismatch {}`,
  `rights_immobility.code 0` (15 блоков / 75 прав с обеих сторон, `dropped []`, `added []`),
  `same 15`, `reordered 2` (оба `Roles/*/Ext/Rights.xml`), `differ 7` (только платформенные
  добавки), `platform_added ["ConfigDumpInfo.xml"]`, `only_source []`, `only_dump []`.
- Ruling (снимает прежний запрет): формулировка «права роли настроены» допустима — неподвижный
  состав прав получен (`rights.immobile(источник, выгрузка)` код 0, gate-07/08/09). Гейт это
  закрепил как отказ: несовпадение состава прав — код 1, отсутствие выгрузки — код 2.
- Наблюдение (класс 6): платформа переставляет блоки `<object>` в файлах прав, не меняя их
  состава (длины совпадают побайтово: 4951/4951 и 2201/2201). Контур называет это отдельным
  классом `reordered` (`gate.file_diff`); «переписано» и «переставлено» — разные утверждения,
  перестановка дефектом не является. Граница закреплена тестом `tests/test_dump_compare.py`:
  перестановка плюс потерянная строка — уже `differ`.
- Наблюдение (дефект исправлен, класс 7): `<LanguageCode>RU</LanguageCode>` платформа приняла
  молча и сохранила как есть. Канон — строчный: `ru` 6/6 корпусов, `en` 2
  (`docs/canonical-languages.json`, `<v8:lang>`: `ru` во всех шести). После исправления на `ru`
  подтверждено gate-09 в обе стороны: источник 1253 байта и выгрузка 1251 байта содержат
  `<LanguageCode>ru</LanguageCode>` (2 байта — класс 1, завершающий перевод строки).
- Наблюдение (замер имён режимов платформы): имена лежат в таблицах имён `1cv8.exe`
  (1 805 720 байт) и `1cv8c.exe` (1 590 168 байт) в кодировании UTF-16LE — однобайтовый поиск их
  не находит. `probe/platform_flag_strings.py`: `RunScript` @1232250 (соседи `AgentMode`,
  `AllZones`, `CheckCanApplyConfigurationExtensions`), `EXECUTE` @1241314 (соседи
  `UsePrivilegedMode`, `LogUI`, `URL`, `IBConnectionString`, `IBName`), `CheckModules` @1239378
  (соседи `CheckConfig`, `DeleteCfg`, `RollbackCfg`, `GetConfigGenerationID`), `RunEnterprise`
  @1239698 (соседи `DumpCfg`, `LoadCfg`, `RestoreIB`), `ExplAuthDlg` @1229360 и `CommandParam`
  @1228488 (оба в группе ключей `CmdLine/...`), `authoff` @1234186 (сосед
  `CmdLine/ResetSavedAuth`). Те же имена — в `1cv8c.exe`. Оговорка: `EXECUTE` встречается и в
  заведомо не-CLI контекстах (`IDS_DBCOPIES_EXECUTE_ERROR`, `IDS_EXECUTE_ONLY_COPIES_…` в
  `backbas.dll`/`backbas*.res`, `COMMANDEXECUTE` в `7zc.dll`) — само по себе имя режима не
  подтверждает.
- Наблюдение (ошибка замера исправлена): `probe/platform_flag_strings.py` при пустом `--root`
  подменял корень каталогом `.` и давал 0 вхождений, сканируя рабочий каталог (`Path("") ==
  Path('.')` — пустой путь не признак «пути нет»). Скрипт теперь требует `--root` или ключ `bin`
  в `local.paths.json` и отказывает кодом 2.

## Task 12–14 (режимы исполнения BSL в командной строке) — ни один режим не подтверждён

- Наблюдение (контроли формы команд): `--controls` в итерации 2 — 4 шага без `ladder_diffs`
  (`reports/exec-12-controls.json`, дисциплина лестниц тогда ещё не введена), после её введения —
  5 шагов / 5 `ladder_diffs` (`reports/exec-13-controls.json`, `ladder_name CONTROLS`,
  `ladder_single_variable true`, `ladder_single_command_part true`; первый diff — сид
  `{"from": "", "to": "runscript", "changed_triple": [], "changed_command": []}`). Значения:
  `runscript` и `runscript-noarg` — код 1, 2.0 с, 3 байта (пустой `/Out`); `load-noarg` — код 1,
  2.0 с, 40 байт (`Файл не обнаружен ''`); `load-ok` — код 0, 2.0–3.0 с, 3 байта; `load-baddir` —
  код 1, 2.0 с, 117 байт (`Файл не обнаружен '…\no-such-directory'`). `controls_classes` — 3
  различных класса (`controls_distinct true`), `controls_classes_by_variant` даёт класс каждому
  шагу. Следствие: `/RunScript <файл>` неотличим от `/RunScript` без файла и неотличим от
  успешной загрузки (`runscript_matches_load_noarg false`, `runscript_matches_load_ok false`,
  `runscript-noarg_matches_load_noarg false`, `runscript-noarg_matches_load_ok false`) — платформа
  не сообщает, что прочитала файл программы; у `/LoadConfigFromFiles` аргумент проверяется
  (тексты об ошибках и классы исходов разные).
- Наблюдение (отрицательные контроли `NEGATIVE_CONTROLS = {"bogus-slash": "/ZzzNetakoyKomandyNet",
  "bogus-dash": "-ZzzNetakoyKomandyNet"}`, они вне `VARIANTS`): `--negative` в итерации 2 — 3 шага
  (`reports/exec-12-negative.json`), после введения дисциплины — 4 шага / 4 `ladder_diffs`
  (`reports/exec-13-negative.json`, `ladder_name NEGATIVE_LADDER`). `/ZzzNetakoyKomandyNet` — код 1,
  1.0–2.0 с, 70 байт (`Пользователь ИБ не идентифицирован`); `-ZzzNetakoyKomandyNet` — таймаут
  (60.3 с в `exec-12-negative` и 40.4 с в `exec-13-negative`), код 1, 0 байт. `negative_clean
  false` из-за зависания однотипного `bogus-dash`; `negative_classes` разделяет три класса,
  `negative_matches_runscript false`, `negative_matches_runscript_noarg false`. Различие закреплено:
  косая черта разбирается платформой и отвечает текстом, дефисная форма имени зависает.
- Наблюдение (лестница авторизации `AUTH_LADDER`, 5 шагов / 5 `ladder_diffs`,
  `reports/exec-13-auth.json`): `load-ok` (код 0, 3.0 с, 3 байта) → `load-authoff`, `load-allusers`
  (`-AllUsers`), `load-currentuser` (`-CurrentUser`), `load-credentials` (`-User=1CTest
  -Pwd=1CTest`) — все код 0, 2.0 с, 3 байта; `auth_same_as_baseline` — все 5 имён,
  `auth_differs_from_baseline []`, `auth_timed_out []`. Имена авторизации платформой приняты, на
  загрузку конфигурации не влияют и следа исполнения не дают.
- Наблюдение (лестница текстов программы `PROGRAM_LADDER`, 5 шагов при одном `/RunScript`,
  `reports/exec-12-programs.json`; отчёт итерации 2 — дисциплина лестниц в нём ещё не зафиксирована:
  `ladder_name None`, `ladder_diffs 0`): `broken`, `runtime`, `missing` (файл программы удалён
  `prepare_script` — это не текст, а его отсутствие), `ascii`, `empty` — все код 1, 2.0 с, 3 байта,
  `marker_exists false`, один и тот же класс исхода `[1, false, "пустой"]`. Длины текстов берущиеся
  из таблицы `PROGRAMS` (в отчётах поля `program_bytes` нет — `None`): `marker` 784 знака
  (784 байта в cp1251, 1331 в UTF-8), `broken` 101, `runtime` 90, `ascii` 372, `empty` 62,
  `missing` 0. «Команда не принята» и «файл программы не прочитан» наблюдаемо неразличимы; ни одна
  гипотеза причины отказа не подтверждается.
- Наблюдение (лестница кодирований и хвостов `SWEEP`, 9 шагов / 9 `ladder_diffs`,
  `reports/exec-13-sweep.json`; в итерации 2 тот же набор был 8-шаговым без `execute-authoff` —
  `reports/exec-12-sweep.json`): шаги идут так — `runscript` при трёх кодированиях одного и того же
  текста (`cp1251` 784 байта, `utf-8-sig` тот же текст с BOM, `utf-8` 1331 байт) → три одинаковых
  исхода (код 1, 2.0 с, 3 байта) → `execute` и `execute-authoff` (оба таймаут 40.3 с, код 1, 0
  байт) → четыре хвоста авторизации поверх `runscript` (`-authoff`, `-credentials`, `-currentuser`,
  `-external`) — все код 1, 2.0 с, 3 байта. Следствие: кодирование файла программы не причина
  отказа. Кодирование BSL-файла — отдельная проверяемая переменная (`ENCODINGS = {"utf-8": "utf8",
  "utf-8-sig": "utf8bom", "cp1251": "cp1251"}`), файл программы пишется с `newline="\n"`, метка
  `$marker$` подставляется скриптом.
- Наблюдение (лестница тестовых режимов `TEST_LADDER`, 13 шагов / 13 diff'ов): `runscript`
  (код 1, 2.0 с, 3 байта, пустой) → `enterprise-runscript` (код 1, 2.0 с, 107 байт: «Запрещено
  использование окон. Передан ключ DisableStartupDialogs.») → обратно `runscript` (проверка, что
  менялся только `mode`) → `/TESTCLIENT <файл>`, `-testFile`, `-testOut`, `/TESTMANAGER <файл>`
  (все — таймаут 30.3 с, код 1, 0 байт) → `/LoadExternalDataProcessorOrReportFromFiles
  <файл программы>` (код 1, 2.0 с, 475 байт: «Файл '…' не является файлом обработки или отчета.»
  плюс мусорное значение во второй позиции аргументов) → та же команда без аргументов (код 1,
  2.0 с, 200 байт: обе позиции мусорные) → `/AllowExecuteScheduledJobs`, `-TestOnly`,
  `/TESTCLIENT`, `/TESTMANAGER` (таймаут 30.3–30.4 с, код 1, 0 байт). Итоги: `test_classes` —
  12 классов, `test_timed_out` — 8 вариантов, `test_output_variants` — 3 (предприятие и две
  внешние обработки), `confirmed_modes []`, `execution_confirmed false`.
- Наблюдение (зависания отделены от отказов замером, а не догадкой): 30.3–30.4 с при коде 1 и
  0 байт — `/TESTCLIENT` (с файлом и без), `/TESTMANAGER` (с файлом и без), `-testFile`,
  `-testOut`, `-TestOnly`, `/AllowExecuteScheduledJobs`, `-ZzzNetakoyKomandyNet`; 40.3–40.4 с —
  `/EXECUTE` и `/EXECUTE /authoff` (оба 40.3 с); `-ZzzNetakoyKomandyNet` — 40.4 с в
  `exec-13-negative.json` и 60.3 с в `exec-12-negative.json`; код 1 за 1.0–2.0 с с непустым `/Out`
  — только `enterprise-runscript` (107 байт), `enterprise-plain` (`ENTERPRISE … /RunScript` без
  файла, `reports/exec-13-enterprise.json` — 1 шаг, 1.0 с, 107 байт, тот же текст про окна),
  `extproc-twoargs` (546 байт: обе позиции приняты, «Файл '…' не является файлом обработки или
  отчета.» — `reports/exec-14-extproc-twoargs.json`), `extproc-file` (475 байт), `extproc-noarg`
  (200 байт), `dumpproc-args` (`/DumpExternalDataProcessorOrReportToFiles` с занятыми позициями,
  410 байт, «Формат: Иерархический» — `reports/exec-14-dumpproc-args.json`). Быстрый непустой код 0
  в этих лестницах не получен ни разу: `load-ok` (код 0) даёт пустой `/Out` в 3 байта. Быстрый
  непустой вывод ≠ исполнение программы.
- Ruling: форма команды живёт в таблицах `scripts/exec_probe.py` (`VARIANT_COMMAND`, `VARIANT_TAIL`,
  `NO_COMMAND_VARIANTS`, `CONTROLS`, `NEGATIVE_CONTROLS`), аргументы размечены метками
  `cfg`/`script`/`baddir`, поэтому соседний шаг лестницы меняет ровно один знак
  (`ladder_step_diffs`, `ladder_single_variable`, `ladder_single_command_part`). Код возврата
  лестницы отвечает только за дисциплину (`ladder_ok`), исходы живут в ключах отчёта
  (`test_classes`, `execution_confirmed`, `confirmed_modes`, `negative_clean`); класс исхода
  `outcome_key = (код, таймаут, "пустой"/"непустой")` с порогом больше 3 байт. Цена, если неверно:
  без этого «команда принята» и «команда зависла» неотличимы, а лестница молча меняет по два знака.
- Итог Task 12–14 (слепое пятно инструментов): `executed_variants []` во всех отчётах
  `reports/exec-12-*.json`, `reports/exec-13-*.json`, `reports/exec-14-*.json` — **ни один режим
  исполнения BSL в командной строке не подтверждён**. Следствие для p1c: `p1c.test.*`
  (`gen`/`check`/`compile`/`run`/`report`) и `p1c.debug.*` не имеют подтверждённого исполнителя в
  ИБ командной строки, хотя 426 имён из `p1c/src/p1c/data/test_cli_flags.json` и имена из таблиц
  `1cv8.exe`/`1cv8c.exe`/`mngui.dll` (`RunScript` @1232250, `EXECUTE` @1241314, `CheckModules`
  @1239378) выглядят как готовый режим. Живость конфигурации (формы, отчёт, обработка) проверяется
  статикой (`p1c.check.bsl`, `p1c.check.forms`) и человеком в GUI, не инструментом.
- Наблюдение (ITS не подтверждает): страница `v838doc/…/adm/TI000000493` — «Доступ к данному
  материалу ограничен»; открытые зеркала «Приложений 7» имён `RUNSCRIPT`/`/EXECUTE`/
  `/LOADCONFIGFROMFILES` не содержат; вход по креденшам ITS не получен (200 с `PHPSESSID` без
  подтверждения входа, 500 на запросе личных данных, либо страница входа 21 582 байта, байтово
  идентичная анонимной, с `div id="emptyUsernameOrPasswordMessage"`).
- Открытое наблюдение (не проверялось): `bogus-slash` даёт «Пользователь ИБ не идентифицирован», а
  `enterprise-plain` — «Запрещено использование окон. Передан ключ DisableStartupDialogs.». Есть ли
  в ИБ зарегистрированные пользователи, видно только из прогона без `/DisableStartupDialogs`
  (риск GUI), — не делалось: живая ИБ пользователя не трогается.

## Итерация 4 (Task 14–15: канон содержимого и цикл внешней обработки .epf ↔ XML)

- Наблюдение (цикл замкнут: `probe/epf_roundtrip.py`, 6 шагов / 5 `plan_diffs`,
  `plan_single_command_part true`, `roundtrip_closed true`, `reports/epf-15-roundtrip.json`):
  `dump-dir-epf` — код 0, 1.9 с, 551 байт `/Out`, 4 файла выгрузки (`ГПН_КонсольЗаданий.xml` 1960,
  `Forms/Форма.xml` 1526, `Forms/Форма/Ext/Form.xml` 30513, `Forms/Форма/Ext/Form/Module.bsl`
  22414); в `/Out`: «Выгрузка внешней обработки или отчета в XML.», «Входной бинарный файл: …»,
  «Каталог или корневой файл выгрузки: …», «Формат: Иерархический».
- Наблюдение (позиции аргументов проверяются платформой): `dump-epf-epf` — код 1, 691 байт
  («Ошибка при выполнении файловой операции '…'. Объект существует и это не каталог»);
  `dump-epf-dir` — код 1, 616 байт («'…' является путем к директории, в то время как ожидается путь
  к файлу.»). Аргумент 1 — каталог или корневой файл выгрузки, аргумент 2 — входной бинарный файл;
  обратный порядок даёт код 1 с текстом. `/LoadExternalDataProcessorOrReportFromFiles` без
  аргументов печатает мусорные значения в обе позиции: аргумента ровно два, их наличие платформа
  не проверяет (тот же класс, что у `RunScript`).
- Наблюдение (обратная половина цикла): `load-epf-dir`, `load-root-dir`, `load-root-target` — код 0
  (1.3–1.4 с), `.epf` 12 132 / 12 035 / 12 035 байта при исходном `.epf` 12 262 байта: платформа
  пересобирает архив, совпадения по байтам не ожидается. Цикл замкнут по составу файлов, не по хешу.
- Наблюдение (входной `.epf` — из шаблонов платформы, не из корпусов): `…\Roaming\1C\1cv8\tmplts\1c\…`
  (`ГПН_КонсольЗаданий.epf` 12 262; `КонсольЗапросов` 112 155, `УниверсальныйОбменДаннымиXML`
  162 434 и др.); во всех шести корпусах `.epf/.erf/.cfe/.dt` и каталога `ExternalDataProcessors`
  нет ни одного.
- Слепое пятно инструментов: у p1c нет цикла `.epf` ↔ XML и нет чтения `ExternalDataProcessors`;
  единственный путь в ИБ и обратно — `p1c.load` (`/LoadConfigFromFiles` + `/DumpConfigToFiles`) по
  всей конфигурации. Отдельная обработка или отчёт как объект (один `.epf`) инструментом не
  обрабатывается.
- Уточнение (пояснение к счётчикам ниже, не правка истории): числа канона в этом и следующем блоках —
  замеры итерации 4 (47 209 модулей четырёх корпусов, 19 154 формных модулей). Действующие счётчики того
  же канона по шести корпусам — `reports/corpora-query-canon-16.json` (50 261 прочитанный модуль,
  48 файлов крупнее 2 MiB пропущено), свёрстка — `docs/evidence/canonical-queries.md`; счётчики нашей
  конфигурации против них — `reports/self-canonical-17.json`; счётчики конструктора
  `Новый СообщениеПользователю` — `reports/corpora-msg-ctor-18.json`. Раздел «Уточнение к счётчикам
  канона» ниже перечисляет действующие числа.
- Наблюдение (канон запросов, замер 47 209 модулей ERP/UH/SSL/LSO): `СУММА(` 14 956,
  `МАКСИМУМ(` 6 153, `СУММ(` 0, `МАКС(` 12; `СтрСконать` 0 против `СтрСоединить` 3 531;
  `Новый Соответствие` 18 783 с `.Получить(` 23 390 и `.Существует(` 225; `ЧДЦ=` 2 207
  (`ЧДЦ=2` 839, `ЧДЦ=2; ЧГ=0` 37), `ЧГ=0` 10 418; `ДФ=dd.MM.yyyy` 948 (внутри `Формат(…` 851);
  `Новый Массив` 46 515 плюс 5 141 пустых и `Новый Массив("…")` 0 → массив только через
  `.Добавить` (17 602); `ПОМЕСТИТЬ вт` 1 343, `ЛЕВОЕ СОЕДИНЕНИЕ вт… КАК` 1 033, `УНИЧТОЖИТЬ вт`
  111; `.Обороты(` 772 (с `&` 182); `ЕСТЬNULL(… Неопределено` 110; разделитель `";"` 2 030 против
  `,` 10 236.
- Наблюдение (канон `.Обороты`, 5 образцов ERP): `РегистрНакопления.<Имя>.Обороты(&НачПериод,
  &КонПериод, , <отбор>) КАК <Alias>` + `СУММА(<Alias>.<Ресурс>) КАК <Имя>` + явное
  `СГРУППИРОВАТЬ ПО`; текст запроса — единой строкой с переводом через `|`; подзапросов в `FROM`
  нет (только `ПОМЕСТИТЬ вт…` / `УНИЧТОЖИТЬ вт…`).
- Наблюдение (канон CSV-выгрузки из формы, образец `ERP/Catalogs/Новости/Forms/
  ФормаЭкспортаОбъектаВXML/Ext/Form/Module.bsl`): `&НаКлиенте` +
  `Новый ДиалогВыбораФайла(РежимДиалогаВыбораФайла.Сохранение)` +
  `Новый ОписаниеОповещения("ПослеВыбораФайла", ЭтотОбъект, ДопПараметры)` + форма с проверкой
  `ТипЗнч(…) = Тип("Массив")` + `Новый ЗаписьТекста(ИмяФайла, "UTF-8", Символы.ПС, Ложь,
  Символы.ПС)` + `ПоказатьОповещениеПользователя` + `#Если НЕ ВебКлиент Тогда`; предупреждение
  поля формы — `Новый СообщениеПользователю` + `.Поле`/`.УстановитьДанные(ЭтотОбъект)`/
  `.Сообщить()`. Замер 19 154 формных модулей: `Сохранение` 115, `ОписаниеОповещения` 90 363,
  `ЗаписьТекста` 571, `СообщениеПользователю` 25 573, `ПоказатьОповещениеПользователя` 1 612,
  `Объект.<Имя>(` 4 670.

## Итерация 5 (обработка выгрузки + предопределённые данные) — принята платформой, гейт код 0

- Наблюдение (зелёная итерация): гейт (`scripts/gate.py`) завершился кодом 0; отчёт
  `reports/gate-11.json`: `load_code 0` (5.1 с, 3 байта), `check_code 0` (2.0 с, 73 байта,
  «Синтаксических ошибок не обнаружено!»), шаг `dump` — код 0 (2.0 с, 3 байта), `step_problems []`,
  `ib_ready_before true`; 32 файла в выгрузке и 32 свежих; `layout_source == layout_dump` (files 31,
  `data_processor 1`, `predefined_data 1`, `object_module 6`, `bsl_module 8`, `form_descriptor 2`,
  `form_data 2`, `form_module 2`, `language 1`, `role 2`, `role_rights 2`, `subsystem 1`,
  `report_template 1`, `report_template_data 1`); `metadata.expected_mismatch {}` и
  `metadata.layout_mismatch {}`; `rights_immobility.code 0` (17 блоков / 79 прав с обеих
  сторон, `dropped []`, `added []`); `diff_files` — `same 21`, `reordered 2`, `differ 8`,
  `only_source []`, `only_dump []`, `platform_added ["ConfigDumpInfo.xml"]`;
  `diagnostics_by_step = {"load": [], "check": ["Синтаксических ошибок не обнаружено!"],
  "dump": []}`, `diagnostic_findings []`, `reason ""`.
- Наблюдение (побайтовое совпадение с выгрузкой платформы — 21 файл): среди них новые
  `Catalogs/Сотрудники/Ext/Predefined.xml`, `DataProcessors/ВыгрузкаЗатратCSV.xml`, оба его модуля
  (`Ext/ManagerModule.bsl`, `Ext/ObjectModule.bsl`), `Forms/ФормаВыгрузки/Ext/Form.xml` и
  `Forms/ФормаВыгрузки/Ext/Form/Module.bsl` — раскладка обработки, форма и предопределённые данные
  написаны так, как их пишет платформа.
- Наблюдение (класс счётчика `predefined_data`): предопределённые данные не описаны ни одним
  дескриптором метаданных (`PredefinedDataName` 0 из 337 образцов корпусов) и `p1c.load` их не
  читает вовсе, поэтому в `scripts/layout.py` они — независимый класс
  (`rglob("*/Ext/Predefined.xml")`), а не производный от метаданных. Канон подтверждён замером
  `probe/corpora_predefined_samples.py` → `docs/evidence/corpora-predefined-samples.md`: при
  наличии `Ext/Predefined.xml` — `PredefinedDataUpdate` = `Auto` 286 / `DontAutoUpdate` 41 /
  `AutoUpdate` 10; корень `xsi:type="CatalogPredefinedItems"`, запись `<Item id="uuid">` с
  `Name`/`Code`/`Description`/`IsFolder`, вложенность через `<ChildItems>`, `<Parent>` нет (0 во
  всех шести корпусах), `Enums/**/Ext/Predefined.xml` нет ни в одном корпусе. Ruling:
  предопределённые данные делаются только там, где их пишет платформа (справочник `Сотрудники`),
  не перечислению.
- Наблюдение (дефект исправлен до замера): `<v8:lang>ru</v8:lang` (без закрывающей `>`) в атрибуте
  `КонецПериода` новой формы — XML не парсится, платформа отвергла бы его на загрузке. В том же
  файле 15 корректных `<v8:lang>ru</v8:lang>`, поэтому правка через `edit` требует контекста
  следующего элемента (`<v8:content>…`). После исправления: 23 XML парсятся без ошибок, в 8 BSL
  сбалансированы `#Область`/`Процедура`/`Функция`.
- Наблюдение (канон прав обработки): `Edit` в блоках `DataProcessor.*` не встречается ни в одном
  файле прав ERP/UH/SSL (перебрано все файлы), порядок прав — `Use` затем `View` (тот же порядок,
  что у `Report` в нашей выгрузке и в ERP `ПолныеПрава`). Обеим ролям выдано ровно `Use` + `View`;
  после этого состав прав неподвижен (17 блоков / 79 прав).
- Наблюдение (канон раскладки обработки, сверка с `ИИ Чат 1С/Project/DataProcessors/
  ГПН_ИИ_НастройкиАдминистратора.xml`): `Properties` ровно `Name, Synonym, Comment,
  UseStandardCommands, DefaultForm, AuxiliaryForm, IncludeHelpInContents, ExtendedPresentation,
  Explanation`; `InternalInfo` — два `xr:GeneratedType` (`DataProcessorObject.…` и
  `DataProcessorManager.…`, каждый с `TypeId`/`ValueId`); `ChildObjects><Form>Имя</Form>`; файлы
  `Ext/ManagerModule.bsl` (только комментарий — 6/6 в корпусе), `Ext/ObjectModule.bsl`,
  `Forms/Форма.xml`, `Forms/Форма/Ext/Form.xml`, `Forms/Форма/Ext/Form/Module.bsl`. Ruling: модуль
  менеджера с кодом — неканоничен, логика — в модуле объекта.
- Наблюдение (канон узлов формы, замер 10 305 файлов `ERP/Forms/*/Ext/Form.xml`): `Autofill>false`
  6 830, `CommandBarButton` 7 431, `LabelDecoration` 4 716, `<Height>` 4 395, `AlwaysHorizontal`
  1 798, `MultiLine>true` 1 020, `VerticalStretch>true` 659, `FormAttributeDescription` 0 (у
  атрибутов нашей формы `xsi:type` нет), `<Action>` каноничен (16 встреч в корпусе `ai_chat`,
  `CommandHandler` 0). Кнопки — в `AutoCommandBar`: `<Autofill>false</Autofill>` +
  `Type>CommandBarButton` + `CommandName>Form.Command.<Имя>` + `ExtendedTooltip`; Id — единая
  нумерация кнопок `AutoCommandBar` и `ChildItems`, `Attributes` и `Commands` нумеруются отдельно
  (с 1); декорации без ссылок на стиль (`Styles` в конфигурации нет). Многострочный текст —
  `InputField` + `AutoMaxWidth>false` + `Height>10` + `AutoMaxHeight>false` +
  `HorizontalStretch`/`VerticalStretch` + `MultiLine>true` при атрибуте `xs:string` с
  `StringQualifiers>Length 0 / AllowedLength Variable`. Типы дат — `xs:dateTime` с
  `<v8:DateQualifiers><v8:DateFractions>` (`xs:dateTime` 2 394, `DateTime` 2 012, `Date` 352,
  `Time` 12).
- Наблюдение (класс 8: порядок `ChildObjects`): `Configuration.xml/ChildObjects` приведён к порядку
  платформы из дампа (замер gate-10, подтверждён корпусом `ai_chat`, 109 объектов): `Language,
  Subsystem, Role×2, CommonModule, Constant, Catalog, Document, Enum, Report, DataProcessor,
  InformationRegister, AccumulationRegister`; обработка добавлена в `<Content>` подсистемы.
- Наблюдение (канон модулей уровня конфигурации, замер шести корпусов): `Ext/SessionModule.bsl`,
  `Ext/ManagedApplicationModule.bsl`, `Ext/OrdinaryApplicationModule.bsl`,
  `Ext/ExternalConnectionModule.bsl` плюс необязательные `Ext/ClientApplicationInterface.xml`,
  `Ext/CommandInterface.xml`, `Ext/HomePageWorkArea.xml`, `Ext/MainSectionCommandInterface.xml`,
  `Splash`/`Logo`/`MainSectionPicture` (картинка в `<Имя>\Picture.*`), `ParentConfigurations.bin`,
  `StandaloneConfigurationContent.bin`; `Ext/CommandModule.bsl` и `Ext/ConfigurationModule.bsl` —
  0 во всех шести корпусах. Связь файла с метаданными — только через `ConfigDumpInfo.xml`
  (`Configuration.<Имя>.SessionModule` и т. п.). Минимально виденный набор `Ext/`:
  `ClientApplicationInterface.xml` (842), `HomePageWorkArea.xml` (786), `SessionModule.bsl` (4 554).
- Наблюдение (что инструменты видят на этой сборке): независимый счётчик контура даёт 22 класса
  (`layout_source == layout_dump`), `tool_counts_source == tool_counts_dump` = 10 классов
  {`accumulation_register 1`, `catalog 1`, `common_module 1`, `constant 1`, `data_processor 1`,
  `document 1`, `enum 1`, `form_data 2`, `information_register 1`, `report 1`},
  `tool_blind_kinds` — 12 классов: `bsl_module, files, form_descriptor, form_module, language,
  object_module, predefined_data, report_template, report_template_data, role, role_rights,
  subsystem` (10 + 12 = 22). Все слепые классы теперь покрыты независимым счётчиком контура
  (`scripts/layout.py`), но не p1c; `metadata.declared` — 12 классов метаданных (роль учитывается
  как 2 объекта).
- Ревю: тесты контура 157 `OK` (`python -m unittest discover -s tests`); в
  `tests/test_layout_counts.py` добавлены `Catalogs/Сотрудники/Ext/Predefined.xml` в `SAMPLE` и
  тест `test_predefined_data_is_a_class_of_its_own`. `scripts/normalize_text.py` изменил 6 файлов
  (все новые: UTF-8 с BOM, CRLF, табы), 25 уже были каноничны.
- Открытая граница той итерации (итерации 5; актуальная граница — в разделе «Открытая граница
  (актуально на конец итерации 8)» ниже): ни один класс исполнения (Task 12–14) не подтверждён — живость форм,
  отчёта и обработки проверяется статикой (`p1c.check.bsl`, `p1c.check.forms`) и GUI; следующий
  замер исполнения возможен только в изолированной ИБ, живую ИБ пользователя трогать нельзя.

## Итерация 6 (Task 15: канон запросов по шести корпусам, SKD отчёта, самомер нашей конфигурации)

- Ревю: корпусный канон меряют репозиторные `probe/corpora_query_canon.py`,
  `probe/corpora_cli_usage.py`, `probe/forms_kind_events.py`; одноразовые счётчики ВТ/SKD — вне
  репозитория (`…\Temp\opencode\vt3_groupby.py`, `vt_vocab.py`, `vt_skd_statements.py`,
  `vt_corpora2.py`, `vt_lex2.py`, `itogi_decompose.py`, `self_query_measure.py`), артефакт каждого —
  в `reports/`. Репозиторная лестница повторного обхода корпусов отвергнута: обход дороже самой меры.
- Наблюдение (канон BSL, `reports/corpora-query-canon-16.json`; 50 261 модуль шести корпусов,
  48 файлов крупнее 2 MiB пропущено, `corpora_cf` не обходится): `.Добавить(` 688 873,
  `Новый Массив` 109 195, `Формат(` 121 041, `ВЫБОР` 76 270, `ЕСТЬNULL(` 62 365,
  `.Получить(` 50 955, `СУММА(` 38 924, `МАКСИМУМ(` 12 818, `МИНИМУМ(` 4 187, `ЧГ=0` 19 641,
  `ЧДЦ=` 5 913 (из них `ЧДЦ=2` 2 729), `СтрСоединить` 13 999, `ДФ=dd.MM.yyyy` 2 549,
  `.Обороты(` 2 053, `.Существует(` 1 387. Нули и почти-нули: `СУММ(` 0, `СтрСконать` 0,
  `ВЫБОР ПЕРВОЕ` 0, `ВЫБОРКА` 7, `МАКС(` 28.
- Наблюдение (выведенные счётчики той же меры): `?(` 131 355 против `ВЫБОР … КОГДА` 74 753
  (перенос строки не важен) → тернарная функция канонична; `Новый Массив(` 11 787 при
  `.Добавить(` 688 873 → массив только через `.Добавить`; `ДФ=…` внутри `Формат(` 2 451 из 2 549;
  `ЕСТЬNULL(… Неопределено)` 227.
- Наблюдение (формы запросов в SKD-шаблонах корпусов, `reports/vt_skd_statements.json`; 2 471
  запрос, 6 424 оператора): текстов с одним оператором 1 071, с несколькими 1 400, с `СГРУППИРОВАТЬ
  ПО` 606; формы `есть_параметры` 2 076, `поместить` 1 400, `поместить_и_сгруппировать` 516,
  `уничтожить` 29, `подзапрос_в_из` 6 → подзапрос в `FROM` корпусом не подтверждён; последний
  оператор текста: `ВЫБРАТЬ` 2 454, `УНИЧТОЖИТЬ` 17; суффиксов ВТ 149.
- Наблюдение (написание `СГРУППИРОВАТЬ ПО`, `reports/vt3_groupby.json`): канонической формы
  19 923 = 18 444 в BSL + 1 479 в SKD-запросах; dotted-написание `.<имя>.СГРУППИРОВАТЬ ПО` — 2
  встречи, обе внутри комментария
  (`CommonModules/РаспознаваниеДокументовЗамерыВремениСлужебный/Ext/Module.bsl:46`), `dotted_raw` 0;
  написания `СГРУППИРОВАНО ПО` — 2 встречи (в ERP) против 19 923 канонических. Различных суффиксов
  ВТ 779 (9 623 вхождения), файлов крупнее 2 MiB пропущено 763.
- Наблюдение (словарь ВТ-токенов, `reports/vt_vocab.json`): `dot_mode` — ровно 12 токенов
  (`границы, данныеграфика, движенияссубконто, задачипоисполнителю, обороты, оборотыдткт, остатки,
  остаткииобороты, срезпервых, срезпоследних, субконто, фактическийпериоддействия`); в BSL 1 722
  различных имени / 26 325 вхождений, в SKD-запросах 143 имени / 1 334 вхождения. Токена
  `актуальныйпериоддействия` в замере нет — он убран из нашего SKD.
- Наблюдение (разбор `.Итоги` и `.Движения`, `reports/itogi_decompose.json`): `.Итоги` 1 678 встреч
  — 657 как отдельное слово, 1 021 как начало более длинного имени, 4 как суффикс имени источника;
  `.Движения` 2 562 — 1 056 / 1 506 / 31; вызовов `.Движения(` 0. Самоконтроль счётчика: 8 проверок
  `OK`. Лексика grammar p1c (`reports/vt_lex2.json::attr_map`, 182 записи): по одной встрече у
  `GROUPEDBY`, `GROUP_BY`, `TOTALS`, `SLICEFIRST_VT`, `SLICELAST_VT`, `OVERALL`, `DOT_MODE`;
  `MOVEMENTS` 0 и `VIRTUAL_TABLE_SUFFIX` 0.
- Ревю: SKD отчёта переписан на канон (`СГРУППИРОВАТЬ ПО` + `ПОМЕСТИТЬ вт…` +
  `ЛЕВОЕ СОЕДИНЕНИЕ вт…` + `УНИЧТОЖИТЬ вт…`); `Template.xml` записан 07:40:05, следующий зелёный
  гейт — `reports/gate-13.json` (шаг `load` начат 07:41:32).
- Наблюдение (самомер нашей конфигурации против тех же счётчиков, `reports/self-canonical-17.json`):
  8 модулей / 28 092 байта, формных модулей 2; `?(` 3, `ДФ=…` внутри `Формат(` 2,
  `ЕСТЬNULL(… Неопределено)` 0, `Новый Массив(` 0; написаний `СГРУППИРОВАТЬ ПО` в BSL: dotted 10,
  каноническая форма 3 (`DataProcessors/ВыгрузкаЗатратCSV/Ext/ObjectModule.bsl:82`, `:97`,
  `InformationRegisters/ПланЗагрузки/Ext/ManagerModule.bsl:39`); в SKD-тексте dotted 0, каноническая
  форма 2. Из 10 dotted-встреч 9 — текст самого мерящего скрипта; настоящая ВТ-строка одна:
  `РегистрНакопления.ЗатратыВремени.Обороты` (`DataProcessors/ВыгрузкаЗатратCSV/Ext/ObjectModule.bsl:80`).
- Документ: `docs/evidence/canonical-queries.md`; таблицы пишет генератор
  `probe/render_query_tables.py`, контроль `python probe/render_query_tables.py --check` даёт
  `fragments: 28, checked lines: 680`, `unused fragments: none`, `all checked lines present verbatim`.
- Слепое пятно: валидность запроса SKD на платформе не проверяема — headless-исполнения BSL в ИБ нет
  (закрыто в итерации 3), прогона отчёта в GUI не делалось.

## Итерация 7 (Task 16: лестницы модификаторов платформы и круг `.epf` ↔ XML)

- Ревю: ожидания пишутся до прогона и живут в ключе `expectations` артефакта; честные счётчики
  сбывшихся ожиданий по шести лестницам (по 7 ожиданий в каждой): PREDEFINED 4, EXTENSION 4,
  LOADOPTS 4 (плюс одно опровергнуто), UPDATE 4, MODE 3 (4 непроверяемы), REPEAT 4 (3 непроверяемы).
  Часть ожиданий про `config_uuid` в режиме `--fresh-ib` непроверяема — в артефакте у них пустой
  `evidence` и пояснение в `note`.
- Опровергнуто ровно одно ожидание: `partial-second-identifier-is-ib-uuid-before-step`
  (`reports/effect-16-loadopts-full.json`: в сообщении о частичной загрузке названы идентификаторы
  `6b1e3a24-…` и `cbb4c193-…`, а `config_uuid` ИБ до шага — `9a51d3ae-…`).
- Наблюдение (единственный след успешной загрузки в `ConfigDumpInfo.xml`): при каждой загрузке
  переписываются 29 значений `configVersion`, а файлы, байты и идентификатор конфигурации
  неизменны (лестница `repeat`: три одинаковых шага) → `configVersion` не является хешем содержимого,
  вывод «изменений нет» на нём основываться не может.
- Наблюдение (модификаторы загрузки, артефакты `reports/effect-16-{predefined,extensions,loadopts,update,modes,repeat}-full.json`,
  прогнаны 01:43–01:48): `load-files-onefile` — код 1, 337 байт («Файл - Configuration.xml: ошибка
  частичной загрузки — идентификатор … отличается»); `-listFile` с валидным списком — код 1, 337
  байт, с битым списком — 90 байт; `-Format` (флаг без значения, `hierarchical`, `plain`,
  придуманное имя) — код 1 и те же 337 байт; `extension-bogus-name` — 140 байт («Загрузка не должна
  менять принадлежность основного объекта конфигурации»); `allextensions` — 4 463 байта / 24 строки
  (12 уникальных «Файл объекта не существует - …Configuration.xml»); `load-noarg` — 40 байт
  («Файл не обнаружен ””»); `update-cfg-noarg` — 75 байт («Файл не содержит доступных обновлений»);
  `config-update-dbcfg-server` — код 0, 3 байта.
- Наблюдение (общие для шести прогонов): `source_uuid 6b1e3a24-…`, ИБ одна (`…\probe_ib`),
  `timeout 90`, `restore_same_to_source 21`, `restore_differ_to_source 8`,
  `restore_matches_base false`.
- Наблюдение (круг `.epf` ↔ XML замкнут по составу файлов, `reports/epf-16-roundtrip.json`, 08:57):
  `plan` 6 шагов / 5 `plan_diffs`, каждый меняет ровно одну часть команды
  (`plan_single_command_part true`); `dump_confirmed`, `load_confirmed`, `roundtrip_closed` — true;
  выгрузка: `Module.bsl` 22 414, `Ext/Form.xml` 30 513, `Forms/Форма.xml` 1 526, корневой
  `ГПН_КонсольЗаданий.xml` 1 960 (кандидат корня один); загрузка даёт `.epf` 12 132 / 12 035 /
  12 035 байта при исходном `.epf` 12 262 (sha1 произведённого `da32d9fb4e9a09b6`).
- Дефект первой версии замера (`reports/epf-15-roundtrip.json`, запись оставлена как запись о дефекте):
  снимок каталога брался не на той позиции, из-за чего sha1 произведённого `.epf` был `None`.
  В `epf-16` позиции зафиксированы: `dump_at [0, 1, 2]`, `root_at [4, 5]`,
  `dump_before_first_root true`.
- Документ: `docs/evidence/modifier-effects.md` (раздел 9 — таблица ожиданий по семи прогонам,
  включая `loadopts-shared`), `docs/evidence/epf-roundtrip.md` (раздел 4 — дефект `epf-15`).
- Слепое пятно: у p1c нет цикла `.epf` ↔ XML и нет чтения `ExternalDataProcessors`; отдельная
  обработка или отчёт как объект одним инструментом не обрабатывается.

## Итерация 8 (Task 17–19: матрица покрытия конфигурации инструментами p1c)

- Ревю: матрица строится на прогонах самих CLI по нашей конфигурации и её выгрузке, только
  read-only подкоманды (mutating-подкоманды `cf set` и `cf normalize` в матрицу не включены).
  `probe/tool_coverage.py` → `reports/toolcov_runs.json` (12:11) плюс 15 отдельных артефактов
  `reports/toolcov_*.json` (у прогона без отчёта артефакта нет) и `reports/toolcov_summary.txt`;
  артефакт гейта читается явным `GATE_ARTIFACT` = `gate-14.json`.
- Наблюдение (две независимые меры по 22 классам раскладки): по пути файла инструменты видят 5
  классов (`bsl_module, files, form_data, form_module, object_module`), по имени объекта — ещё 10
  (`accumulation_register, catalog, common_module, constant, data_processor, document, enum,
  form_descriptor, information_register, report`); без инструмента остаются 7 классов (`language,
  predefined_data, report_template, report_template_data, role, role_rights, subsystem`);
  `gate_tool_blind_kinds` — 12.
- Наблюдение (сверка читателя с независимым гейтом): `reader_vs_gate` равны для `load-model-cfg` и
  `load-model-dump`, `diff_reader_vs_gate {}`.
- Наблюдение (падения и неправильные порядки аргументов): `cf-info-cfg-dir` — код 1, Traceback,
  отчёта нет (у `cf info` и `cf cat` нет `--format` и `--out`); `load-object-wrong-order` — код 2,
  «Корень выгрузки не найден: catalog.Сотрудники»; `forms-form-wrong-order` — код 2, «Корень выгрузки
  не найден: ФормаЭлемента».
- Наблюдение (`p1c.check.bsl` по cfg — 15 находок): 11 `IDS_STX_VAR_NOTDECLARED` (шум канона неявных
  реквизитов), 1 `IDS_STX_CTOR_NOTFOUND`, 3 `IDS_STX_METHODNOTFOUND`; разбор арности конструктора —
  по замеру `reports/p1c-ctor-data-23.json`.
- Наблюдение (`p1c.check.sdbl`): по cfg (`check`) — `queries 3`, `field_ok 20`,
  `skip_field_fields_unknown 3`, `skip_vt_no_help_fields 1`, `sources 7`; по SKD-шаблону отчёта
  (`query` по тексту запроса из `Template.xml`) — `queries 1`, `field_ok 13`, `sources 5`.
- Наблюдение (ловушка меры): имена `Form`/`Module`/`Template` — не имена объектов (`GENERIC_STEMS`);
  5 классов измеряются только путём (`PATH_ONLY_KINDS`); хит имени вплотную к разделителю пути —
  отражённый путь (`name_hits_path_only_echo`); содержимое отчётов переносит только генератор,
  `SKIP_REPORT_KEYS = (context_effective, context_signature, schema)`.
- Ревю: имена флагов берутся только из замера `p1c/src/p1c/data/test_cli_flags.json` (426 имён в
  `files[].names`); словарь подкоманд и флагов CLI — из текстов `--help`
  (`probe/cli_vocabulary.py` → `reports/cli-vocabulary-22.json`, 8 инструментов, все `help_exit 0`).
- Документ: `docs/evidence/tool-coverage.md` (12 разделов, 901 строка).

## Контроли корпуса и данных p1c (вне окон 1С-замеров)

- Наблюдение (директива `&Сервер`, `reports/corpora-server-annotation-18.json`; 50 309 BSL-файлов
  шести корпусов): строк, где `&Сервер` стоит отдельно, — 0; всего встреч `&Сервер` с продолжением
  строки — 8, и все 8 — имена параметров запроса: `&СерверПодписи` в
  `CommonModules/СервисКриптографииDSSСлужебный/Ext/Module.bsl` (ERP `:2892`, `:2893`; SSL `:2922`,
  `:2923`; UH `:2844`, `:2845`) и `&СерверДокументооборота` в
  `CommonModules/ДокументооборотСКонтролирующимиОрганами/Forms/КонтейнерКлиентскихМетодов/Ext/Form/Module.bsl`
  (ERP `:24974`, UH `:20828`). Отдельной директивы `&Сервер` в корпусах нет.
- Ревю: standalone-`&Сервер` в `InformationRegisters/ПланЗагрузки/Ext/ManagerModule.bsl` — дефект
  нашей конфигурации; директива убрана (файл записан 12:02:17), `scripts/normalize_text.py` —
  «изменено 0, уже как в платформе 31», следующий гейт `reports/gate-14.json` (12:09:38) — код 0.
  Что платформа делала с директивой, не измерено.
- Наблюдение (регистр написаний аннотаций, `reports/corpora-token-skip-20.json`): `&НаСервере`
  317 861 встреча, с границей слова `&НаСервере\b` 300 926, слова словаря вида
  `&НаСервере[\p{L}\p{N}_]+` 16 935; различных написаний 3 (`&НаСервереБезКонтекста` 16 920,
  `&НаСервереБезконтекста` 10, `&НаСерверебезКонтекста` 5); проверка
  `na_token_equals_vocab_exact_name false` → регистрозависимость написаний реальна.
- Наблюдение (цена лимита обхода, `reports/corpora-bsl-sizes-21.json`): 50 309 файлов /
  2 690 063 711 байт; крупнее лимита 1 MiB — 214 файлов / 401 742 608 байт (эти файлы в счётчики
  канона не входят).
- Наблюдение (конструктор `СообщениеПользователю`, `reports/corpora-msg-ctor-18.json`):
  `Новый СообщениеПользователю` 26 426 встреч в 3 820 файлов; в исходниках p1c имя встречается в
  `p1c/src/p1c/data/platform_arities.py` (2) и `p1c/src/p1c/data/test_api.json` (1), в таблицах
  конструкторов его нет.
- Наблюдение (страницы событий форм, `reports/forms-events-kind-19.json`): `pages_total 135`,
  страниц «form extension» 29, базовый набор событий 26 имён (`ClientApplicationForm`),
  сопоставлений вида страницы 14, placements флага `--kind` 5.
- Наблюдение (данные конструкторов p1c, `reports/p1c-ctor-data-23.json`): `TYPE_CONSTRUCTORS` — 22
  записи, имена которых похожи на события и методы (`AfterWrite`, `BeforeWrite`, `ПриЧтенииНаСервере`,
  `Прочитать`, `ВыборЗначения`), членство `Массив` / `СообщениеПользователю` / `ТекстовыйДокумент` —
  false, ссылок на имя таблицы 2 (объявление `platform_arities.py:22189` и генератор
  `p1c/scripts/extract_help_arities.py:252`), в пакете p1c — 0. `TYPE_SIGNATURES` — 1 885 записей,
  ключей-конструкторов среди них 0; модели типов 1 913, типов без арностей конструктора 1 869;
  `СообщениеПользователю` — вид `collection`, арности пустые, свойств 0, метод один
  (`установитьданные`); в таблицах модели (`SCALARS` 12, `COLLECTIONS` 12, `EXTRA_TYPES` 27) его нет.
  Арность конструктора модель берёт только из вручную написанных таблиц.
- Ревю: счётчики корпусов не смешивать — 50 261 (обход канона, лимит 2 MiB) и 50 309
  (обходы ripgrep: `corpora-server-annotation-18`, `corpora-token-skip-20`,
  `corpora-bsl-sizes-21`, `corpora-msg-ctor-18`) — два разных измерения одного множества.

## Гейты gate-12 … gate-14 (ещё три зелёных прогона)

- Наблюдение (четыре артефакта идентичны по содержанию): если из отчётов убрать `started` и
  `seconds` шагов, нормализованный JSON `gate-11` … `gate-14` побайтово одинаков (5 451 знак).
  Значит гейт различает раскладку, метаданные и права, но не различает правку текста SKD и правку
  модуля: содержательно он подтверждает «конфигурация загружается и та же», а не «текст изменён».
- Наблюдение (gate-14): `load_code 0` (14.2 с, 3 байта), `check_code 0` (2.0 с, 73 байта,
  «Синтаксических ошибок не обнаружено!»), шаг `dump` — код 0 (2.0 с, 3 байта), `timed_out false` у
  трёх шагов, `step_problems []`, `reason ""`, `ib_ready_before true`, `create_code None`;
  `dump_files 32` и `dump_fresh_files 32`; `layout_source == layout_dump` (31 файл, 22 класса);
  `tool_counts_source == tool_counts_dump` (10 классов), `tool_blind_kinds` 12;
  `metadata.declared` 12 классов, `expected_mismatch {}`, `hard_problems []`,
  `layout_mismatch {}`, `layout_compare {}`; `rights` код 0 (17 блоков / 79 прав),
  `rights_immobility` код 0 (`dropped []`, `added []`, 17 блоков / 79 прав с обеих сторон);
  `diff_files`: `platform_added ["ConfigDumpInfo.xml"]`, `differ` 8 файлов, `reordered` оба
  `Roles/*/Ext/Rights.xml`, `only_source []`, `only_dump []`.
- Наблюдение (хронология прогонов по метке времени шага `load`): gate-11 — 27.10 18:07 (5.1 с),
  gate-12 — 22:23 (2.1 с), gate-13 — 28.10 07:41 (17.3 с, сразу после записи SKD в 07:40),
  gate-14 — 12:09 (14.2 с, сразу после записи `ManagerModule.bsl` в 12:02). Правки, относящейся к
  gate-12, в журнале нет: это повторный прогон того же содержимого, артефакт оставлен как контроль
  воспроизводимости.

## Дефект контура: `.gitignore` проглатывал каталоги `Reports` конфигурации

- Дефект: правило `reports/` без якоря матчовало любой каталог с именем `Reports`, в том числе
  `cfg/ЭффективностьОтдела/Reports/**`. Проверка: на диске 31 файл `cfg`, в git 28;
  `git check-ignore -v` указал `.gitignore:3:reports/`. Не попадали в git три файла отчёта:
  `Reports/ОтчётЗагрузки.xml` (2 701 байт),
  `Reports/ОтчётЗагрузки/Templates/ОсновнаяСхемаКомпоновкиДанных.xml` (1 363 байта),
  `Reports/ОтчётЗагрузки/Templates/ОсновнаяСхемаКомпоновкиДанных/Ext/Template.xml` (6 809 байтов).
- Ревю: правило заменено на `/reports/`; после этого `git status` показывает
  `?? cfg/ЭффективностьОтдела/Reports/` и ` M .gitignore`. Артефакты замеров по-прежнему вне git.
- Ревю: этот дефект касался только версионности; гейт и матрица мерили файлы на диске, поэтому их
  числа не изменились.

## Уточнение к счётчикам канона (что чем заменено)

- Действующие счётчики канона BSL/SKD по шести корпусам: `reports/corpora-query-canon-16.json`
  (50 261 модуль, 48 файлов крупнее 2 MiB пропущено), свёрстка —
  `docs/evidence/canonical-queries.md`; та же мера по нашей конфигурации —
  `reports/self-canonical-17.json`.
- Действующие счётчики ВТ-написаний: `reports/vt3_groupby.json` (формы `СГРУППИРОВАТЬ ПО`),
  `reports/vt_vocab.json` (словарь токенов `dot_mode`), `reports/vt_skd_statements.json` (формы
  текстов запросов), `reports/itogi_decompose.json` (разбор `.Итоги` и `.Движения`),
  `reports/vt_corpora2.json` и `reports/vt_lex2.json` (лексика корпусов и грамматики p1c).
- Счётчики конструктора `Новый СообщениеПользователю`: `reports/corpora-msg-ctor-18.json` (корпуса)
  и `reports/p1c-ctor-data-23.json` (данные p1c).
- Числа итераций 4–5 (47 209 модулей четырёх корпусов, 19 154 формных модулей) остаются записями о
  тех прогонах; они не пересчитаны.

## Ревю итераций 6–8

- Доказано: конфигурация загружается и остаётся той же после правки SKD и правки модуля
  (gate-13, gate-14); канон запросов и написаний ВТ измерен по шести корпусам и применён к нашей
  конфигурации; покрытие инструментов p1c измерено прогонами самих CLI и сверено с независимым
  гейтом; модификаторы платформы измерены лестницами с ожиданиями, записанными до прогонов;
  круг `.epf` ↔ XML замкнут по составу файлов.
- Тесты контура: `python -m unittest discover -s tests` — `Ran 261 tests … OK`. Код возврата 1 из-за
  предупреждений `scripts/exec_probe.py` в stderr о mutating-лестницах; это ожидаемо и не является
  провалом тестов.
- Что не закрыто: три итоговых документа (`docs/итог-боевой-проверки.md`, `docs/слепые-пятна.md`,
  `docs/план-оптимизации-p1c.md`) ещё не записаны; ничего из Task 12–19 не закоммичено.

## Открытая граница (актуально на конец итерации 8)

- Исполнение BSL в ИБ по-прежнему не подтверждено: `/RunScript` даёт код 1 при 3 байтах вывода,
  `/TESTCLIENT`, `/TESTMANAGER`, `-testFile`, `-testOut`, `-TestOnly`, `/AllowScheduledJobs` —
  таймаут 30.3–30.4 с при 0 байтах, `/EXECUTE` — код 1 при 40.3–40.4 с и 0 байтах; входов `RunScript`
  в шести корпусах 0. Неиспробованные кандидаты headless-проверки модулей: `/CheckConfig`,
  `/CheckModules`, `-ExtendedModulesCheck`, `-WarningsAsErrors`, `-Module`, `-NBegin`, `-NEnd`,
  `-ReportFile`, `-ReportFormat`, `-ReportType`, `-EmptyHandlers`, `-UnreferenceProcedures`,
  `-HandlersExistence`. (Список записи на конец итерации 8: эти кандидаты опробованы замером 25,
  см. раздел «Итерация 9» ниже.)
- Валидность SKD-запроса отчёта на платформе не измерена (только статика `p1c.check.sdbl`); что
  платформа делает с директивой `&Сервер` — не измерено.
- Модификаторы доступа неотличимы от базовой загрузки (`auth_differs_from_baseline []`);
  влияние `PredefinedDataUpdate` на строки предопределённых данных наблюдаемо неотличимо от его
  отсутствия.
- Регистронезависимость `-listFile` против `-listfile` не измерена.

## Итерация 8 (окончание): итоговые документы, контроль текстов, свёртка путей

- Итоговые документы записаны и закоммичены (`bb7db14`): `docs/итог-боевой-проверки.md` (241 строка,
  19093 байта), `docs/слепые-пятна.md` (286 строк, 22241 байт), `docs/план-оптимизации-p1c.md`
  (126 строк, 25345 байта). Числа — из подсчёта строк и байтов самих файлов на момент коммита
  (переводов строки 240, 285 и 125).
- Контроль текстов трёх итоговых документов: два rg-прохода — CJK
  (`\p{Han}|\p{Katakana}|\p{Hiragana}|\p{Hangul}`) и склейка латиницы с кириллицей
  (`[A-Za-z]{4,}[а-яё]{2,}|[а-яё]{2,}[A-Za-z]{4,}`) — обе без находок (rg exit 1). Расширенный шаблон
  `[A-Za-z]{3,}[а-яё]|[а-яё][A-Za-z]{3,}` находит только настоящее имя обработки `ВыгрузкаЗатратCSV`.
- Исправленные дефекты формулировок (пять правок скриптами вне репозитория `<tmp>\fix_plan.py`,
  `<tmp>\fix_plan2.py`): в плане убраны CJK-вкрапления (два иероглифа U+53CD и U+6620 заменены
  словом «отражает») и склейки латиницы с кириллицей: слова «меряла», «попытка», «округление»,
  «тип-коллекция» и глагол «переписывать» были записаны с латинскими вставками; в §13 слепых пятен
  артефактам (`reports/corpora-bsl-sizes-21.json`: 50 309 файлов, 2 690 063 711 байт, 214 файлов выше
  лимита, 401 742 608 байт в них; `reports/corpora-token-skip-20.json`: `limit_max_module_bytes`
  1 048 576, `files_over_limit` 214, `na_any_over_limit` 25 710, `na_token_over_limit` 24 065;
  `reports/corpora-query-canon-16.json`: `limits.max_file_bytes` 2 097 152, 48 пропущено); §12
  переименован в «Код возврата и внешний контур: пять случаев» и исправлен по настоящему артефакту
  `reports/exec-13-auth.json` (пять вариантов `load-ok`, `currentuser`, `credentials`, `authoff`,
  `allusers`; все код 0, класс вывода «пустой», `auth_same_as_baseline` 5,
  `auth_differs_from_baseline []`, `auth_timed_out []`); артефакта `reports/exec-12-auth.json` не
  существует — ссылка на него убрана.
- Свёртка абсолютных путей: в `docs/evidence/exec-modes-and-negatives.md` было 46 абсолютных путей, в
  `docs/evidence/task1-observations.md` — 1; скриптом вне репозитория `<tmp>\collapse_paths.py`
  машинные префиксы свёрнуты в `<tmp>` и `<repo>`, в начало добавлено «Пояснение о путях» (строка 10),
  файл нормализован до CRLF (361 CRLF, lone_lf 0). Байты, коды возврата и секунды в таблицах не
  менялись. Полный обход `docs/**/*.md` (20 файлов) скриптом `<tmp>\doc_scan_all.py`: `abs=0` и `cjk=0`
  у каждого файла; в двух документах `docs/evidence/*` и плане правка коснулась только текста,
  фрагменты `<!--TABLE-->`/`<!--OUT-->` не затронуты.
- Искажённые глифы платформы в строках `/Out` записаны escape-последовательностями и пояснены в
  разделе 8 и в пояснении о путях: U+C540, U+8BCC, U+19F (прогон `extproc-file`) и U+E540, U+C079,
  U+1B9 (прогон `extproc-noarg`); в `reports/exec-13-test.json` те же символы стоят литерными, а один
  из них (U+E540) невидим при печати. Сознательное исключение этих строк из CJK-контроля больше не
  нужно: контроль чист, искомое содержание сохранено. В `docs/superpowers/specs/*design.md` исправлена
  склейка `UTF-8 c BOM` (латинская `c` заменена на кириллическую `с`).
- Проверки после всех правок текстов: `python -m unittest discover -s tests` — `Ran 261 tests … OK`
  (код возврата 0; предупреждения `scripts/exec_probe.py` о mutating-лестницах в stderr остаются);
  `python probe/render_query_tables.py --check` — `fragments: 28 checked lines: 680`,
  `unused fragments: none`, `all checked lines present verbatim in the evidence documents`.
- Итог задачи на этой точке: конфигурация загружается и чинится (гейт gate-14: `load_code 0` за
  14.2 с, `check_code 0` за 2.0 с, «Синтаксических ошибок не обнаружено!»), права названы настроенными
  (`rights_immobility.code 0`, 17 блоков / 79 прав в обе стороны), слепые пятна p1c описаны числами
  матрицы (`kinds_seen_by_path` 5, `kinds_seen_by_name_only` 10, `kinds_seen_by_no_tool` 7), план
  оптимизации инструментов разбит на блоки A–G. Граница меры (нет подтверждённого headless-исполнения
  BSL; модификаторы доступа и `PredefinedDataUpdate` наблюдаемо неотличимы от их отсутствия)
  зафиксирована в разделе «Открытая граница» выше и в `docs/слепые-пятна.md`.

## Итерация 9 (замер 25: имена группы проверки headless — `/CheckModules` и `/CheckConfig`)

- Мера: накопительная лестница из 22 шагов под `/CheckModules` (`CHECK_LADDER`) и её полное зеркало
  под `/CheckConfig` (`CHECKCMD_LADDER`, база — тот же канон `check-config-base`): шаг `base` =
  `CHECK_TAIL_BASE` (пять флагов доступа из `ib_loop.CHECK_KEYS`), шаги 2–8 наращивают цепь
  `-ConfigLogIntegrity -IncorrectReferences -DistributiveModules -UnreferenceProcedures
  -HandlersExistence -EmptyHandlers -ExtendedModulesCheck` (порядок — канон корпуса БСП
  `DataProcessors/ПроверкаБСППередСборкой/Forms/Форма/Ext/Form/Module.bsl`), шаг 9 добавляет
  `-ReportFile=<tmp>\p1c_effektivnost\exec_check_report`, шаги 10–22 = тот же 14-токенный префикс
  плюс ровно одно новое имя. Имена взяты только из замера `p1c/src/p1c/data/test_cli_flags.json`
  (426 имён в `files[].names`) и окна соседства `reports/flags-24-checkgroups.json`; значения
  `-ReportFormat` (`mxl`, `txt`) и `-ReportType` (`Brief`, `ByObjectNames`, `ByObjectIDs`) — из того
  же окна, третий вариант каждого значения и значения `-NBegin`, `-NEnd`, `-Module` — заведомо
  вымышленные (`ZzzNetakogoZnacheniyaNet`).
- Прогоны: 132 прогона лестниц — 44 на чистой ИБ `<tmp>\p1c_effektivnost\probe_ib`, 44 на битой
  func-ИБ, 44 на битой form-ИБ (по одному прогону за раз, `rc 0` у всех шести артефактов), плюс
  6 шагов `ib_loop` сборки трёх битых ИБ; 353.4 с времени платформы, 0 таймаутов,
  `check_rejected []`, `check_silent_variants []`. Лестница только читает ИБ — `--allow-mutating`
  не понадобился, ИБ гейта gate-14 не тронута, модифицирующие прогоны шли только на `probe_ib`
  и на отдельных `broken_ib_*`.
- Находки чистой ИБ (раздел 10): `/CheckModules` — 22 шага, код `[0]`, 73 байта
  `Синтаксических ошибок не обнаружено!`, один и тот же `/Out` (хеш `0ca69e`) на всех шагах,
  0 строк объекта, 2.0–7.3 с; `/CheckConfig` — коды `[0, 101]`, 43 байта `Ошибок не обнаружено`
  (7 шагов, хеш `1400ce`, 0 строк объекта) против 340 байт и кода 101 (15 шагов, хеш `d92f21`,
  2 строки `ВидОбъекта.ИмяОбъекта`), 2.0–14.2 с. Единственный токен, меняющий вердикт, —
  `-ExtendedModulesCheck`; `-ReportFile` запрошен 28 раз (14 шагов из 22 на каждой лестнице) —
  `check_report_files []`.
- Битые ИБ (`scripts/mutate.py`: `unknown_function_call`, `form_missing_handler`,
  `subsystem_bad_content`; рецепт — `<tmp>\make_broken_cfg.py` (31 файл копии `cfg`) затем
  `python scripts/ib_loop.py --ib <tmp>\p1c_effektivnost\broken_ib_<вид> --cfg <копия>
  --steps create,load`): первые две — `create` код 0 (195 байт) и `load` код 0 (3 байта),
  `steps done: 4` вместе с лестницами; третья — `load` код 1, 177 байт, две строки
  `Неизвестный объект метаданных - Catalog.ТакогоНет` (`broken_loop_subsystem.json`,
  `platform_errors [1]`), лестница на ней не прогоняется: дефект ссылки виден уже из шага загрузки.
- Оракул измерен (раздел 11): `/CheckConfig` с `-ExtendedModulesCheck` на func-ИБ — код 101,
  501 байт, хеш `e6482f`, 3 строки объекта, третья — дословно `Документ.ФактРаботы.МодульОбъекта
  Возможно ошибочный метод: "ПроверитьЧасыДокумента"` (именно про введённый вызов). На form-ИБ
  границу находки держит `-HandlersExistence`: код 101, 195 байт, хеш `246bb9`, одна строка
  `Справочник.Сотрудники.Форма.ФормаЭлемента.Форма Отсутствует обработчик:  Форма
  "ПриСозданииНаСервере"` (два пробела после двоеточия — дословно), `-EmptyHandlers` поверх него
  даёт побайтово тот же `/Out`; 15 шагов с `-ExtendedModulesCheck` — код 101, 532 байта, хеш
  `debd25`. На той же битой ИБ тот же флаг под `/CheckModules` — код 0, 73 байта, 0 строк объекта:
  `/CheckModules` читает синтаксис, а не содержание; `check_defect_found` 17 шагов (form-ИБ) и 15
  (func-ИБ) против `check_no_defects` 22 у `/CheckModules`.
- Дисциплина предсказаний: по 8 предсказаний на лестницу (16 на замер) записаны в `PREDICTIONS` до
  прогонов по чистой ИБ и не переписывались; на битых ИБ они работают как оракул —
  `predictions_held` 8/8/7/7/5, `predictions_broken` = ["check-config-extended"] на func-ИБ и
  ["check-config-handlers", "check-config-emptyhandlers", "check-config-extended"] на form-ИБ;
  `predictions_unresolved []` и `prediction_sources_ok true` во всех шести артефактах.
- Артефакты (в `.gitignore`; числа и дословные строки — только из них): `reports/check-25-clean.json`,
  `check-25-clean-checkconfig.json`, `check-25-broken-func.json`,
  `check-25-broken-func-checkconfig.json`, `check-25-broken-form.json`,
  `check-25-broken-form-checkconfig.json` (по 22 шага). Таблицы раздела 12 сгенерированы
  `<tmp>\gen_check_tables.py` и вставлены `<tmp>\splice_check_tables.py` (анкор проверен на
  единственность, CRLF сохранены); сравнение чистый↔битый — `<tmp>\dump_broken_cmp.py` и
  `<tmp>\dump_broken_cmp2.py` (в нём же `argv` каждого шага, хеши `/Out` и предсказания).
- Код контура: `scripts/exec_probe.py` (2041 строка, 171 654 байта) — `--checkkeys`,
  `--checkconfig`, `CHECK_LADDER`/`CHECKCMD_LADDER`, `CHECK_OPTION_NAMES` (2 имени команд +
  7 корпусных флагов + 8 нецитированных имён), `check_verdict` (вердикты `clean`, `defects`,
  `no_verdict`, `refused`), `check_observation`; `tests/test_exec_probe.py` (1544 строки,
  105 559 байтов) — `TestCheckLadder` (21 тест). Проверки: `python -m unittest discover -s tests`
  → `Ran 282 tests … OK` (код 0), `python probe/render_query_tables.py --check` →
  `fragments: 28 checked lines: 680`, `unused fragments: none`.
- Документы: `docs/evidence/exec-modes-and-negatives.md` (901 строка, 108 381 байт) — раздел 10
  (находки чистой ИБ), раздел 11 (ожидания, записанные до прогонов → результат), раздел 12
  (шесть таблиц артефактов), два новых пункта финального списка; `docs/план-оптимизации-p1c.md`
  (126 строк) — новая строка E9 и переписанная строка C10 (направление закрыто измерением,
  встраивание вывода осталось задачей); `docs/итог-боевой-проверки.md` (247 строк) — список
  неиспробованных кандидатов заменён измеренным; `docs/слепые-пятна.md` (293 строки) — пункт §15
  про headless-проверку переписан на измеренное, к оценке границы добавлена лестница группы
  проверки (17 имён, 132 прогона).
- Контроль текстов после правок: rg-проходы CJK (`--pcre2`, находок нет) и склейки латиницы с
  кириллицей (`[A-Za-z]{4,}[а-яё]{2,}|[а-яё]{2,}[A-Za-z]{4,}` — у четырёх изменённых документов 0),
  обход `<tmp>\doc_scan_all.py` по 20 файлам `docs/**/*.md`: `abs=0`, `cjk=0` у всех; исправлены
  три опечатки раздела 10 («разбор строк», «машинно читается», «восьми нецитированных имён») и
  одна ошибка счёта предсказаний в разделе 11 (16 на лестницу → по 8 на лестницу). Строки
  `scripts/exec_probe.py` и `tests/test_exec_probe.py` — 115 и 104 символа максимум, BOM нет,
  перевод строк LF.
- Открытая граница после итерации 9 (заменила список неиспробованных кандидатов границы итерации
  8): исполнить BSL по-прежнему нельзя; модификаторы доступа и влияние `PredefinedDataUpdate`
  неотличимы; регистронезависимость `-listFile` против `-listfile` не измерена; из имён группы
  проверки наблюдаемого различия не дают `-IncorrectReferences`, `-ConfigLogIntegrity`,
  `-DistributiveModules`, `-UnreferenceProcedures` и `-EmptyHandlers` (поодиночке — 43 байта
  `Ошибок не обнаружено` и на чистой, и на обеих битых ИБ), регистронезависимость их написаний не
  измерена, содержимое отчёта `-ReportFile` не получено ни разу (84 запроса), а дефект ссылки
  метаданных headless-командой проверки не измеряется — ИБ с ним не загружается (код 1).
- Закоммичено в `aebe547` (`6 files changed, 1837 insertions(+), 21 deletions(-)`):
  `scripts/exec_probe.py`, `tests/test_exec_probe.py` и четыре документа. Этот журнал — отдельный
  коммит.


## Итерация 9 (замер 26: регистр написаний имён команд и флагов)

- Кого замерили: 11 регистровых двойников уже измеренных шагов — `/checkmodules` и
  `/CHECKMODULES` (близнец `/CheckModules`), `/checkconfig` и `/CHECKCONFIG` (близнец
  `/CheckConfig`), `-handlersexistence` и `-HANDLERSEXISTENCE` (близнец `-HandlersExistence`),
  `-extendedmodulescheck` и `-EXTENDEDMODULESCHECK` (близнец `-ExtendedModulesCheck`),
  `/loadconfigfromfiles` (близнец `/LoadConfigFromFiles`), `-listfile` (близнец `-listFile`) и
  `-format` (близнец `-Format`). Двойник — шаблонный шаг: копия близнеца, у которой ровно один
  токен изменён по регистру; сверено внешне (`case_spelling_register_only true`, `argv`
  отличается ровно одним токеном), самого написания двойника в таблице 426 имён
  `p1c/src/p1c/data/test_cli_flags.json` нет (`case_in_measured false`, совпадение по `lower()`
  ровно одно — с именем близнеца).
- Дисциплина замера: регистровые двойники НЕ входят в `check_observation_variants()` (её счётчик
  44 варианта закреплён тестом) и живут в отдельных полях отчёта `case_*`; близнец и двойник не
  соседствуют в лестнице — повтор эталонного близнеца служит «сбросом» состояния
  (`case_twin_adjacency_problems []`); сравнение «измеренный → регистровый» идёт внутри одного
  прогона (`outcome_key` плюс байты `/Out` и число строк `ВидОбъекта.ИмяОбъекта`). Род предсказаний
  «близнец предсказывает двойника» для этих шагов ОТКЛОНЁН: все 11 шагов идут наблюдением, причина
  каждого записана в `CASE_OBSERVATION_REASONS` (11 записей, каждая обязана называть измеренного
  близнеца); `case_prediction_free true`, непредсказанные шаги перечислены списком
  (`case_unpredicted_matches_list true`).
- Прогоны (строго по одному): `--casecheck` — 25 шагов на преднамеренно битой form-ИБ
  (`scripts/mutate.py form_missing_handler`: из модуля формы
  `Catalogs/Сотрудники/Forms/ФормаЭлемента` удалена процедура `ПриСозданииНаСервере`),
  `--caseload` — 12 шагов на ИБ
  `<tmp>\p1c_effektivnost\probe_ib` с `--allow-mutating` и `--cfg`; код возврата контура в обоих
  прогонах 0 (в артефактах поля `exit_code` нет — это наше наблюдение в терминале).
- Находка: регистр написания платформа не различает. `case_differs_from_twin = []`,
  `case_same_as_twin` содержит все 11 имён — код, длина `/Out` и строки объекта побайтово совпали.
  На битой ИБ: `/CheckModules` в трёх написаниях — код 0, 73 байта, 0 строк объекта; `/CheckConfig`
  в трёх написаниях — код 0, 43 байта; `-HandlersExistence` и его два написания — код 101, 195 байт,
  1 строка объекта; `-ExtendedModulesCheck` и его два написания — код 101, 532 байта, 3 строки
  объекта. На загруженной ИБ: `/LoadConfigFromFiles` и `/loadconfigfromfiles`, `-listFile` и
  `-listfile` с файлом-списком, `-Format` и `-format` — везде код 0 и 3 байта.
- Исправленное прочтение прошлых замеров загрузки (найдено при сверке, а не при планировании):
  код 1 и 337 байт у `-listFile <файл-список>` и `-Format` в четырёх LOADOPTS-артефактах
  (`reports/effect-16-loadopts-{fresh,fresh2,fresh3,full}.json`) — отказ частичной загрузки из-за
  несовпадения идентификаторов конфигурации на восстанавливаемой ИБ (§5 и §10
  `docs/evidence/modifier-effects.md`), а не «пустая ИБ»; на ИБ, куда та же конфигурация уже
  загружена (`reports/effect-16-loadopts-shared.json`, `reports/flags-26-caseload.json`), те же
  шаги дают код 0 и 3 байта. Единственный «говорящий» шаг caseload-лестницы —
  `load-listfile-onefile` (`-listFile Configuration.xml`, голое имя файла раскладки; в рабочей
  директории прогона такого файла нет, в каталоге конфигурации он есть): код 1, 90 байт,
  `Ошибка чтения файла-списка загружаемых файлов` — по сообщению нельзя сказать, что именно
  платформа сочла нечитаемым. Утверждение «`-listFile` с валидным списком даёт код 1» из прошлых
  документов исправлено во всех четырёх документах.
- Артефакты (в `.gitignore`; числа и дословные строки — только из них):
  `reports/flags-26-casecheck.json`, `reports/flags-26-caseload.json`. Таблицы раздела 13
  сгенерированы `<tmp>\case_tables.py` и вставлены `<tmp>\insert_case_tables.py` (якорь проверен
  на единственность, CRLF сохранены); внешняя сверка дисциплины — `<tmp>\case_discipline_check.py`
  (337 flag-like имён из 426; `adjacency []`, `reason_count 11`, `reasons_without_twin []`,
  `case_mutating` — ровно 3 двойника загрузки).
- Код контура: `scripts/exec_probe.py` (2380 строк) — `VARIANT_COMMAND`/`VARIANT_TAIL` для 11
  двойников, `CASE_VARIANTS`/`CASE_TWIN`/`case_variants()`/`case_twin_of()`, флаги `--casecheck`
  (25 шагов) и `--caseload` (12 шагов, в `MUTATING_LADDERS`), `CASE_OBSERVATION_REASONS`, хелперы
  `case_ladder_variants`/`case_twin_adjacency`/`case_twin_signature_diff`, блок отчёта `case_*`;
  `tests/test_exec_probe.py` (1856 строк) — `TestCaseLadders` (15 тестов) и правки четырёх
  существующих классов. Проверки: `python -m unittest discover -s tests` → `Ran 297 tests … OK`
  (код 0), `python probe/render_query_tables.py --check` → `fragments: 28 checked lines: 680`,
  `unused fragments: none`.
- Документы: `docs/evidence/exec-modes-and-negatives.md` (1171 строка) — раздел 12 (находки
  замера 26, в том числе три буллета «почему у двойников нет предсказаний» и абзац про исправленное
  прочтение LOADOPTS-кодов), новый раздел 13 с двумя дословными таблицами case-прогонов, пункт 9
  финального списка; `docs/итог-боевой-проверки.md` (255 строк) §6 — 11 двойников добавлены в
  измеренное, в незакрытое перенесён регистр **значений** модификаторов; `docs/слепые-пятна.md`
  (306 строк) §12 и §15 — написано измеренное, недомеренным оставлен регистр значений и регистр
  BSL-аннотаций, к оценке границы добавлены 11 двойников; `docs/план-оптимизации-p1c.md` (126
  строк) — F6 переписан (в `p1c` держать одно измеренное написание, регистронезависимость тестом не
  покрывать), к C10 и E9 добавлены ссылки на разделы 10–11 и таблицы раздела 13 и на
  `reports/flags-26-*.json`.
- Контроль текстов после правок: скан `<tmp>\doc_scan.py` по четырём изменённым документам — у
  `docs/итог-боевой-проверки.md`, `docs/слепые-пятна.md` и `docs/план-оптимизации-p1c.md` находков
  нет; у `docs/evidence/exec-modes-and-negatives.md` 19 находок, все пред-существующие (цитаты `/Out`,
  в которых платформа печатает путь к файлу; имена вида `ВыгрузкаЗатратCSV` в таблицах; свёрнутые
  `<tmp>` в колонке команд прошлых прогонов). Строки `scripts/exec_probe.py` и `tests/test_exec_probe.py` — не длиннее 115
  символов, абсолютных путей в скриптах, probe, тестах и документах нет (сверено после правок).
- Открытая граница после замера 26: регистр **значений** модификаторов (`-Format PLAIN` против
  `-Format Plain`, значения `-ReportFormat`/`-ReportType`) не измерен; регистр BSL-аннотаций
  (`&НаСервереБезКонтекста` против 10 и 5 встреч других написаний) к argv отношения не имеет и не
  измерен; всё остальное из открытой границы итерации 9 без изменений.
- Закоммичено в `ba7f562` (6 файлов): `scripts/exec_probe.py`, `tests/test_exec_probe.py` и четыре
  документа. Этот журнал — отдельный коммит.
