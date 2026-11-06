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
- Наблюдение (канон CSV-выгрузки из формы, образец `ERP/Catalogs/Новости/Forms/`
  `ФормаЭкспортаОбъектаВXML/Ext/Form/Module.bsl`): `&НаКлиенте` +
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
  (25 шагов) и `--caseload` (12 шагов, в `MUTATING_LADDERS`), `CASE_OBSERVATION_REASONS`,
  вспомогательные функции
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

## Итерация 10 (блок B плана: каталог вместо книги `.cf`, порядок позиционных аргументов, коды возврата 0/1/2)

- Тесты до правки закоммичены в `p1c` как `5165b80` (7 файлов тестов, 471 вставка): код 2 на каталоге
  вместо книги `.cf`, код 2 на переставленных позиционных аргументах и код 1 на пустом корпусе для
  каждой команды структурного слоя. Причина падения подтверждена прогоном каждого файла отдельно:
  падают ровно новые проверки, старые якоря сообщений и содержимое отчётов остаются зелёными.
- Правка кода закоммичена в `p1c` как `dd7110c` (10 файлов: восемь CLI-обвязок, `writers.py` из
  `src/p1c/core`, `README.md` и один файл тестов; 316 вставок, 61 удаление). Два помощника собраны в
  одном месте: `read_code` (код 1, если источник прочитан, но в нём нет записей) и `arg_order_error`
  (код 2 с каноническим порядком «имя, затем корень» в тексте ошибки).
- Мера кода 1 берётся из источника, а не из вывода: модель метаданных по шести ключам (без
  `collections`, потому что пустой корпус даёт `collections: 1`, и без счётчика пропущенных файлов);
  статистика графа по модулям; число измеренных модулей для `metrics root|top` и строки прочитанного
  файла для `metrics module`; файлы обоих каталогов и записи книги при сравнении; число записей книги
  для `cf`. Счётчик исходников добавлен в `diff/cli.py` локально, чтобы не править `diff/diff.py` и
  не добавлять ключей в содержимое отчёта: текстовый формат сравнения сверяется в тесте по
  фиксированным строкам.
- Структурные исключения записаны текстом в `README.md` и в docstring каждого слоя:
  `check.forms events` и `check.sdbl fields` — справочная таблица платформы (коды 0 и 2);
  `check.forms check` и `check.sdbl check` задают код 1 порогом находок, поэтому пустая выгрузка без
  находок даёт 0; у `load object`, `graph calls|callers`, `cf cat|set|keywords|normalize` код 1
  недоступен, потому что пустое уже сообщено ошибкой контекста либо таблица платформы не пуста.
  Аргументы автоматически не переставляются: неразобранный аргумент сообщается кодом 2.
- `p1c.cf`: каталог на месте книги отвергается до открытия (код 2, текст «Книга .cf ожидается файлом,
  а передан каталог: …») вместо аварийного текста в 1479 байт; `main` возвращает код подкоманды;
  подкоманды `info`, `list` и `cat` приняли `--format json|sarif|text` и `--out` и пишут отчёт
  `p1c.result/v1`, а текстовый вывод остаётся значением по умолчанию; `sarif` для этих подкоманд —
  ошибка кода 2, потому что это формат диагностик. Имена флагов не выдуманы: `--format` и `--out` уже
  есть у шести других слоёв `p1c` и у `p1c.cli.runner`.
- Прогон после правок: `python scripts/run_tests.py` → тестов 73, неудачно 0;
  `python tests/core/test_wording.py` → запрещённых формулировок нет (357 файлов).
- Документы: в плане строка B1 уточнена (ожидаемый код 1 → 2: каталог на месте книги — ошибка
  аргумента, а не пустой источник), после строки B8 добавлен абзац статуса блока B (B1–B3 закрыты,
  B4–B8 открыты); в `docs/evidence/tool-coverage.md` после пункта 12 добавлен абзац «Статус к
  итерации 10» (пункты 7 и 8 закрыты, пункт 6 закрыт частично). Строки матрицы 18 прогонов, раздел 8
  и раздел 10 не переписаны: они описывают измеренный прогон до правки.
- Контроль фрагментов после правок документов: `python probe/render_query_tables.py --check` →
  28 фрагментов, 680 закреплённых строк, неиспользованных фрагментов нет; все закреплённые строки
  присутствуют в документах дословно.
- Контроль текстов: скан `<tmp>\doc_scan.py` по трём изменённым документам (план — 133 строки,
  `docs/evidence/tool-coverage.md` — 912 строк, `README.md` в `p1c` — 1374 строки): новых склеек,
  иероглифов и абсолютных путей нет. Зафиксировано отдельно: в `README.md` на строках 235 и 237
  встречается заимствованное название проверочного случая (две встречи, этой правкой не добавлены),
  а 18 срабатываний по шаблону абсолютного пути дают обращения к сетевым адресам и схемам ресурсов
  отчётов, которые были в документе и до этой правки; ни то ни другое не относится к этой правке
  и оставлено без изменения.
- Контроль комментариев и текстовых констант правленых файлов `p1c`: `<tmp>\py_text_scan.py` по 16
  файлам (восемь CLI, `writers.py`, семь файлов тестов и тест формулировок) — иероглифов 0, абсолютных
  путей 0 (единственная находка — адрес схемы отчёта SARIF в `writers.py`), семь находок склейки, и
  все семь — буква `n` у последовательности перевода строки перед кириллическим `КонецПроцедуры`
  внутри образцов BSL; проверка по строкам файлов подтвердила, что настоящих склеек нет. Скрипт
  `<tmp>\glue_dump.py` печатает строку целиком, чтобы такие находки различать.
- Сообщения коммитов: в `p1c` — кириллицей через `git commit -F` (файл сообщения UTF-8 без признака
  порядка байтов, 2473 байта); в `effektivnost-otdela` — транслитерацией латиницей (993 байта, все
  знаки `ASCII`). Новых абсолютных путей в `scripts`, `probe`, тестах и документах нет; длина строк
  `scripts/exec_probe.py` не менялась.
- Закоммичено в `1a3bb9f` (2 файла): `docs/план-оптимизации-p1c.md`, `docs/evidence/tool-coverage.md`.
- Открытое на следующую итерацию (блок A): читатель `Roles/*/Ext/Rights.xml` и `Ext/Predefined.xml` в
  `load/reader.py` с парными образцами в `examples/designer_dump` и `examples/edt_project`; имена
  видов сверять по `scripts/layout.py` (`role`, `role_rights`, `predefined_data`). Не решено, придётся
  ли расширять `scripts/counts.py::counts_from_model` и `probe/tool_coverage.py`, чтобы закрытие
  A1 и A2 отразилось в `tool_blind_kinds` (12 → 0) и `kinds_seen_by_no_tool` (7 → 0), и мерить ли
  предопределенные данные по файлам (так считает гейт) или по записям. Сначала нужно измерить
  фактическое содержимое `examples/designer_dump/Enums`: в списке образцов виден один файл, но прогон
  `check.sdbl fields enum.ВидПодчинения` даёт код 2.
- Фоновый обход `corpora_case_exact.py` (относится к замеру 25, не к этой итерации) прерван
  перезапуском сервера, артефакт не получен; перезапускать только по необходимости.

## Итерация 11 (блок A: читатель прав ролей и предопределённых данных в `p1c`)

- Форма записей выбрана до кода и закреплена тестом: два верхних ключа модели `roles` и
  `predefined_data`; роли не добавляются ни в `objects`, ни в `COLLECTIONS_MAP` (иначе падают
  проверки `objects == 4` и числа коллекций образца). Роль: `name`, `path` (`Roles/<Имя>/Ext/Rights.xml`),
  `flags` (все верхние дети корня, кроме блоков объектов), `objects` — блоки в порядке файла с
  `rights` дословными строками. Предопределённые данные: ключ `"<вид>.<имя>"` (та же форма, что у
  `objects`), `items` — плоский список `<Item>` с `parent`, `uuid` из атрибута `id`, `code` дословно
  (ведущие нули), `description`, `is_folder`.
- Дескриптор `Roles/<Имя>.xml` не читается; запасного чтения через `Roles/<Имя>/Rights.xml` (без
  `Ext/`) не добавлено; `detect_layout` не менялся.
- RED `0172da1` — 18 красных проверок в `tests/load/test_rights_predefined.py`; GREEN `b1554bf` —
  `parse_rights_xml`, `parse_predefined_xml`, `_read_predefined_items`, вставки в
  `load_configuration_model`, две формы записей в docstring модуля, `roles` и `predefined_data` в
  `MODEL_KEYS` меры кода 1, два абзаца README.
- Проверки `p1c`: `python tests/load/test_rights_predefined.py` — все проверки зелёные;
  `python scripts/run_tests.py` → тестов 74, неудачно 0; `python tests/core/test_wording.py` →
  запрещённых формулировок нет (364 файла); `<tmp>\py_text_scan.py` по `reader.py` и `load/cli.py` —
  0 находок, по файлу теста — 1 находка по шаблону абсолютного пути (пространство имён XML в
  образце файла прав, это данные, не путь); `<tmp>\doc_scan.py` по `README.md` — 20 находок, и все
  20 были в документе до этой правки (две — заимствованное название проверочного случая, остальные —
  обращения к схемам ресурсов отчётов).
- Мера A1 на нашей cfg подтверждена читателем: 2 роли (`АдминистраторСистемы` — 9 блоков и 57 прав,
  `СотрудникОтдела` — 8 блоков и 22 права) = 17 блоков и 79 прав; те же числа стоят в гейте
  `gate-14.json` → `rights_immobility` (`source_blocks 17`, `dump_blocks 17`, `source_rights 79`,
  `dump_rights 79`). В этом корпусе все 79 значений прав — `true`; различие «право false против
  отсутствия права» закреплено образцами `p1c`, а не нашим корпусом.
- Мера A2 подтверждена: одна запись `catalog.Сотрудники` (`Catalogs/Сотрудники/Ext/Predefined.xml`),
  6 строк, из них 2 группы и 3 со `parent`, коды `000000001`…`000000006` с ведущими нулями,
  представления прочитаны; cfg и выгрузка дают одинаковый набор.
- Контур аудита (TDD): RED — новый тест `test_counts_include_role_rights_and_predefined_data`
  падает как `KeyError: 'role_rights'`; GREEN — в `scripts/counts.py::counts_from_model` добавлены
  пары `roles → role_rights` и `predefined_data → predefined_data`, имя `role` (дескриптор) не
  выдаётся и закреплено проверкой `assertNotIn("role", got)`; docstring функции перечисляет, что
  лежит вне `collections`. Прогон: `python -m unittest tests.test_contour.CountsTest` → Ran 6, OK;
  `python -m unittest discover -s tests` → Ran 298, OK (код возврата 0; в stderr остаются ожидаемые
  сообщения `exec_probe: лестница … Нужен --allow-mutating`, они не провал тестов).
- Повтор матрицы покрытия: `python probe/tool_coverage.py` (18 прогонов, платформу не запускает) →
  `kinds 22 by path 7 by name only 12 no tool 3`; `role_rights` и `predefined_data` закрыты путём
  инструментом `load`, класс `role` закрыт именем. Слепые: `language`, `report_template`,
  `report_template_data`.
- Открытый вопрос этой правки: прежняя транскрипция чисел §2 и §3 `docs/evidence/tool-coverage.md`
  (18 прогонов) не согласуется с нынешним артефактом сильнее, чем это объясняется правками читателя.
  Проверено, что `git diff 6780e04 HEAD -- probe/tool_coverage.py` пуст, а `scripts/layout.py` не
  менялся с 27.10; колонка «файлов cfg» печатается суммой хитов по классам макета (строка 518),
  где псевдокласс `files` считает каждый файл ещё раз сверх своего класса.

### Замер «до правок»: повтор матрицы против `p1c` до правок блока B и A

Существующая транскрипция (§2: `load-model-dump` 4 файла / 11 имён, `metrics-top-dump` 7,
`bsl-check-cfg` 3, `load-forms-dump` 4, `load-object-catalog` 2) сверяется с прогоном того же файла
замера против `p1c` на коммите `746b66b` (последний перед правками блока B и A). Изолированный
прогон: `<tmp>\opencode\cov_before\` — копия `probe/tool_coverage.py`, копии `scripts/layout.py` и
`scripts/counts.py`, `reports/gate-14.json`, свой `local.paths.json` с тем же `cfg` и `dump`, но с
`p1c` на временном дереве коммита `746b66b`. Платформа не запускается, изменяющих подкоманд
нет.

PREDICTED (записаны до прогона, не переписываются):
1. Колонки «файлов cfg» и «имён cfg» у `load-model-dump` и `load-model-cfg` останутся 16 и 18:
   мера — сумма хитов по классам, её не меняет читатель; значит прежние 4 и 11 из этой меры не
   воспроизводятся.
2. `reader_kind_counts` прежнего читателя не содержит `role_rights` и `predefined_data` (ключей
   модели нет), `diff_reader_vs_gate` для обоих прогонов модели даёт ровно
   `{"predefined_data": [0, 1], "role_rights": [0, 2]}`.
3. `kinds_seen_by_no_tool` прежнего замера содержит `role`, `role_rights`, `predefined_data` —
   их становится 5 (плюс `language`, `report_template`, `report_template_data` без `subsystem`) либо
   6 (если `subsystem` тоже не именован). Именованным `subsystem` будет только если отчёт `load`
   содержит ключ `context_effective` с корневым путём, где имя папки `cfg` совпадает с именем
   подсистемы: предсказано, что так и будет (5), потому что `context_effective` был в отчётах и до
   правок (`git grep context_effective 746b66b`).
4. Прежние коды возврата: `cf-info-cfg-dir` — код 1 без JSON-отчёта (флагов `--format`/`--out` у
   `cf` до блока B нет), `load-object-wrong-order` и `forms-form-wrong-order` — код 2 с текстом
   «Корень выгрузки не найден: …» (прежняя формулировка до `arg_order_error`).

Фактический исход прогона «до правок» (артефакт `<tmp>\opencode\cov_before\reports\`; предсказания
выше не переписываются):

1. Не подтвердилось. Колонки «файлов cfg» и «имён cfg» таблицы §2 — множества **различных** путей и
   **различных** имён внутри прогона (`probe/tool_coverage.py:411-414`), а не суммы хитов по классам;
   суммы печатает только консоль замера (`:518-519`). Прежние 4 файла и 11 имён у `load-model-cfg` и
   `load-model-dump` воспроизвелись ровно (у прогона по cfg дополнительно 1 эхо-имя). Причина ошибки
   предсказания: консольные суммы (16 и 18) были приняты за источник чисел таблицы; этим же закрыт
   «открытый вопрос этой правки».
2. Не подтвердилось по направлению сравнения. У прежнего читателя `reader_vs_gate` для обоих прогонов
   модели даёт `equal_to_gate_tool_counts_source: true` и пустый `diff_reader_vs_gate`, потому что
   `gate-14.json` посчитан этим же читателем до правок (`gate_tool_counts_source` — 10 классов).
   Предсказанный `{"predefined_data": [0, 1], "role_rights": [0, 2]}` описывает нынешний читатель
   против прежнего гейта, а не прежний читатель против прежнего гейта.
3. Не подтвердилось по составу: `kinds_seen_by_no_tool` прежнего замера — 7 классов (`language`,
   `predefined_data`, `report_template`, `report_template_data`, `role`, `role_rights`, `subsystem`),
   а не 5 и не 6. Ошибка предсказания: я отнёс `subsystem` к названным классам, хотя матрица считает
   название класса только по собственному имени, а встречи имени конфигурации в отчётах прежнего замера
   — только как часть пути (`tools_name_echo_only`: `bsl`, `cf`, `diff`, `load`); эхо слепоту не снимает.
   `kinds_seen_by_path` 5 и `kinds_seen_by_name_only` 10 воспроизвелись.
4. Подтвердилось: `cf-info-cfg-dir` — код 1, traceback, JSON-отчёта нет; `load-object-wrong-order` и
   `forms-form-wrong-order` — код 2 с текстом «Корень выгрузки не найден: …».

Не предсказано заранее (с причиной):

- `reader_kind_counts` прежнего читателя — 10 классов в каждом из двух модельных прогонов (по 11
  ключей, потому что `form_data` даёт 2). Причина: классы модели поштучно в предсказаниях не стояли.
- Прежний `reader_kind_counts` посчитан копией `scripts/counts.py` уже после GREEN-правки (106 строк
  против 97 в HEAD). Для прежнего дерева `p1c` числа это не изменило: обе новые пары стоят под
  `if model.get("roles")` и `if model.get("predefined_data")`, а прежняя модель этих ключей не имеет.
  Сверка копии с HEAD — различие только в docstring и в этих четырёх строках; `scripts/layout.py`,
  `scripts/paths.py` и `probe/tool_coverage.py` в копии совпадают с HEAD построчно.
- `subsystem` в прежнем замере имеет эхо в четырёх инструментах (`bsl`, `cf`, `diff`, `load`), в
  нынешнем — в трёх: после правки A1 имя конфигурации названо собственным именем в блоке прав
  `Subsystem.ЭффективностьОтдела`, и эхо у `load` пропало. Причина: блок прав — новое место, где имя
  подсистемы стоит не внутри пути.
- Прежний артефакт содержит 17 JSON-отчётов из 18 прогонов (у `cf-info-cfg-dir` отчёта нет) — то же
  число, что и в нынешнем замере. Построчно сверять колонки §2 по всем 18 прогонам я не собирался.

### Пересъёмка документов матрицы (итерация 11)

- `docs/evidence/tool-coverage.md` переснят вручную по нынешнему артефакту: §2 (по 7 файлов и 14 имён
  у обоих модельных прогонов, эхо 0 у `load-model-cfg`, код 2 у `cf-info-cfg-dir`), §3
  (`predefined_data` — 1 путь, `role_rights` — 2 пути, `role` — 1 имя, `subsystem` — 1 имя и 3 эхо),
  §4 (`subsystem` закрыт именем через блок прав), §5 (фрагмент `reader_vs_gate` с двумя различиями и
  разбор отставания `gate-14.json`), §6 (строки `model.predefined_data 1` и `model.roles 2` в обоих
  блоках плюс описание формы записей ролей и предопределённых данных), §7 (тексты ошибок двух
  wrong-order прогонов и `p1c/src/p1c/core/writers.py:298-306`), §8 (раздел переименован: код 2 и
  `Книга .cf ожидается файлом, а передан каталог: <cfg>`, прежний traceback сохранён как запись прогона
  до правки), §10 (пункты 1, 2, 5 и 6), §11 (статусы «к итерации 10» и «к итерации 11» с таблицей
  до/после), §12 (12 классов из 22, три несопоставимые меры одной матрицы, отметка о том, что матрица
  переснята, а гейт не пересоздавался).
- Строки таблиц переносятся из `reports/query-tables.md` вручную: маркеров фрагментов в документах нет,
  `--fix` у генератора нет. Контроль: `python probe/render_query_tables.py --check` → 28 фрагментов,
  677 проверенных строк, «all checked lines present verbatim» (код 0).
- Скан текстов `<tmp>\opencode\doc_scan.py` по `docs/evidence/tool-coverage.md` — 1007 строк, 0 находок.
- Тесты контура после правок: `python -m unittest tests.test_contour.CountsTest` → Ran 6, OK;
  `python -m unittest discover -s tests` → Ran 298, OK, код возврата 0.
- План: в `docs/план-оптимизации-p1c.md` добавлен статус блока A к итерации 11 (A1 и A2 закрыты,
  `kinds_seen_by_no_tool` 7 → 3, `tool_blind_kinds` 12 → 10 по счётчику живого читателя, артефакт
  гейта не пересоздавался).
- Отложенная работа: `gate-15` — пересчёт `tool_counts_source` и `tool_blind_kinds` живым читателем
  (полный обход корпусов, только вне окон 1С-замеров); A3–A6 — подсистемы, языки, макеты компоновки
  данных и модули уровня конфигурации; чтение дескрипторов `Roles/<Имя>.xml` (класс `role` по пути
  файла по-прежнему не закрыт).

## Итерация 12 (гейт `gate-15`: пересчёт `tool_blind_kinds` живым читателем)

Поправка к предыдущей записи: `gate-15` обхода корпусов не требует. `scripts/gate.py:366-371` считает
`tool_counts_source` читателем `p1c.load` (через `scripts/counts.py:object_counts`) и
`tool_blind_kinds = layout_source − tool_counts_source` по одному исходнику `cfg`; корпуса в этом
расчёта нет. Цена — один цикл платформы (шаги `load`, `check`, `dump`).

Исходные данные до прогона (замерены, не вывод): `cfg` — 31 файл, свежайший файл 2026-10-28 15:02,
то есть с прогона `gate-14` (шаги `load` 14.2 с, `check` 2.0 с, `dump` 2.0 с) исходник не менялся;
`ib_ready_before` прежнего прогона — `true`; выгрузка — 32 файла.

PREDICTED (записаны до прогона, после прогона не переписываются):

1. Код возврата 0, артефакт `reports/gate-15.json`, `reason` пустой, `step_problems` и
   `diagnostic_findings` пустые.
2. Шагов ровно три (`load`, `check`, `dump`), `create` отсутствует (ИБ существует), `create_code`
   остаётся `null`; коды всех трёх шагов 0.
3. `metadata.layout` (он же `layout_source`) — побайтово те же 22 класса и те же числа, что в
   `gate-14.json` (в частности `role 2`, `role_rights 2`, `predefined_data 1`, `files 31`);
   `expected_mismatch` пуст, `hard_problems` пуст.
4. `rights` — код 0, счётчики `rights_files 2`, `object_blocks 17`, `rights 79`;
   `rights_immobility` — код 0, `dropped []`, `added []`, 17/17 блоков и 79/79 прав.
5. `tool_counts_source` — 12 ключей вместо 10: прежние 10 ключей с прежними значениями (включая
   `form_data 2`) плюс `predefined_data 1` и `role_rights 2`. Причина: `scripts/counts.py` выдаёт эти
   две пары из ключей модели `roles` и `predefined_data`, а имя `role` не выдаёт.
6. `tool_blind_kinds` — 10 классов вместо 12: `bsl_module`, `files`, `form_descriptor`,
   `form_module`, `language`, `object_module`, `report_template`, `report_template_data`, `role`,
   `subsystem`. Причина: из прежних 12 вычитаются `predefined_data` и `role_rights`, которые теперь
   названы читателем.
7. `tool_counts_dump` — тоже 12 ключей с `predefined_data 1` и `role_rights 2`: в выгрузке те же два
   `Roles/*/Ext/Rights.xml` и один `Catalogs/Сотрудники/Ext/Predefined.xml`.
8. `dump_files 32`, `dump_fresh_files 32`; `diff_files` по составу как в `gate-14.json` (исходник не
   менялся): `Catalogs/Сотрудники/Ext/Predefined.xml` в `same`, оба `Roles/*/Ext/Rights.xml` в
   `reordered`.
9. Нормализованный JSON `gate-15.json` против `gate-14.json` различается ровно четырьмя местами:
   `steps` (начало и длительность), `tool_counts_source`, `tool_counts_dump`, `tool_blind_kinds`.
   Побайтового равенства, как у `gate-11` … `gate-14`, не будет: отчёт стал длиннее на эти два ключа.
10. После этого `probe/tool_coverage.py:56 GATE_ARTIFACT` указывает на устаревший артефакт, и
    предсказание про матрицу: при `GATE_ARTIFACT = "gate-15.json"` `reader_vs_gate` для обоих
    модельных прогонов даст `equal_to_gate_tool_counts_source: true` и пустой
    `diff_reader_vs_gate`, а `gate_tool_blind_kinds` станет 10; остальные числа матрицы
    (7 / 12 / 3 из 22) не изменятся, потому что матрица считается прогонами инструментов, а не
    гейтом.
### Итерация 12: фактический исход

Команда (один 1С-прогон, 2026-10-29 21:20): `python scripts/gate.py --cfg
"cfg/ЭффективностьОтдела" --out reports/gate-15.json --canon docs/canonical-rights.json
--timeout 240` — код возврата 0, артефакт `reports/gate-15.json` (8180 байт, mtime 21:20:14).
Все 10 предсказаний подтверждены.

1. Подтверждено: код 0, `reason ""`, `step_problems []`, `diagnostic_findings []`.
2. Подтверждено: три шага `load` / `check` / `dump` (код 0 у каждого), `create_code null`,
   `ib_ready_before true`.
3. Подтверждено: блоки `metadata`, `layout_source`, `layout_dump`, `layout_compare` побайтово равны
   `gate-14.json` (22 класса, `role 2`, `role_rights 2`, `predefined_data 1`, `files 31`);
   `expected_mismatch {}`, `hard_problems {}`.
4. Подтверждено: `rights.code 0` (`rights_files 2`, `object_blocks 17`, `rights 79`);
   `rights_immobility` — код 0, `dropped []`, `added []`, 17/17 блоков и 79/79 прав.
5. Подтверждено: `tool_counts_source` — 12 ключей: прежние 10 с прежними значениями (включая
   `form_data 2`) плюс `predefined_data 1` и `role_rights 2`; имени `role` в счётчике нет.
6. Подтверждено: `tool_blind_kinds` — 10 классов: `bsl_module`, `files`, `form_descriptor`,
   `form_module`, `language`, `object_module`, `report_template`, `report_template_data`, `role`,
   `subsystem`.
7. Подтверждено: `tool_counts_dump` — 12 ключей, равный `tool_counts_source` по составу.
8. Подтверждено: `dump_files 32`, `dump_fresh_files 32`, `diff_files` побайтово равен прежнему
   (`same` 21 файла, `differ` 8, `reordered` 2, `platform_added` 1 — `ConfigDumpInfo.xml`,
   `only_source []`, `only_dump []`).
9. Подтверждено: отличающихся ключа ровно четыре — `steps`, `tool_counts_source`,
   `tool_counts_dump`, `tool_blind_kinds`; побайтового равенства с `gate-14.json` нет
   (8180 байт против 8125).
10. Подтверждено: после смены `GATE_ARTIFACT` на `gate-15.json` повтор матрицы (18 прогонов восьми
    инструментов, платформа 1С не запускалась, код 0) даёт `gate_tool_counts_source` 12 и
    `gate_tool_blind_kinds` 10, а `reader_vs_gate` у обоих модельных прогонов —
    `equal_to_gate_tool_counts_source: true` с пустым `diff_reader_vs_gate`. Числа матрицы не
    изменились: 22 класса = 7 по пути файла + 12 только по имени + 3 ничем (`language`,
    `report_template`, `report_template_data`); `reader_kind_counts` — 12 классов в обоих модельных
    прогонов.

Непредсказанное (записано как наблюдение, не как подтверждение):

- Длительность шага `load` 6.0 с против 14.2 с в `gate-14.json` при тех же 3 байтах stdout;
  `check` и `dump` — те же 2.0 с и 2.0 с (73 байта и 3 байта). Причина различия длительности не
  измерена.
- Перенаправление консоли PowerShell в файл даёт UTF-16LE: текст консоли при декодировании как UTF-8
  даёт mojibake, поэтому читать надо артефакт JSON (`reports/gate-15.json`), а не файл консоли; код
  возврата при этом читается по переменной `$LASTEXITCODE`.

Проверка гейта и замер матрицы:

- Артефакт читался скриптом-сверкой (`<tmp>\opencode\gate15_report.py`, `<tmp>\opencode\gate15_keys.py`),
  который сравнил `gate-15.json` с `gate-14.json` по всем ключам отчёта. Побайтово равны 23 ключа:
  `cfg_name`, `check_code`, `create_code`, `diagnostic_findings`, `diagnostics`,
  `diagnostics_by_step`, `diff_files`, `dump_configuration_name`, `dump_files`, `dump_fresh_files`,
  `expected_file`, `ib_ready_before`, `layout_compare`, `layout_dump`, `layout_source`, `load_code`,
  `metadata`, `reason`, `rights`, `rights_immobility`, `source_configuration_name`, `step_problems`,
  `tool_counts_error`. Отличаются ровно 4: `steps`, `tool_counts_source`, `tool_counts_dump`,
  `tool_blind_kinds`.
- `probe/tool_coverage.py:56` — изменена только константа `GATE_ARTIFACT` (плюс комментарий о том,
  что `gate-14.json` остаётся прежним артефактом того же гейта); артефакт замера теперь
  `reports/toolcov_runs.json` с `gate_artifact gate-15.json`.
- `python probe/render_query_tables.py` (без флагов) переснял `reports/query-tables.md`: 28
  фрагментов, 732 строки. Изменились ровно 5 строк фрагмента `OUT coverage-reconcile` — ярлык
  артефакта, `gate_tool_counts_source` (10 → 12 классов), `gate_tool_blind_kinds` (12 → 10) и обе
  строки `reader_vs_gate` (`false` с 2 различиями → `true` с пустым различием). Прежняя копия —
  `<tmp>\opencode\query_tables_before.md`.

Правки документов (строки матрицы переносились вручную: маркеров фрагментов в документах нет, а
`--fix` у генератора нет):

- `docs/evidence/tool-coverage.md`: строка 16 (артефакты замера — `gate-15.json` и пояснение, что
  `gate-14.json` это тот же гейт по тому же исходнику, посчитанный читателем до правок A1/A2); блок
  §5 (7 строк заменены дословно, по содержанию среди них отличаются 5); проза §5 (сверка читателя с
  гейтом сошлась, прежняя сверка против `gate-14.json` сохранена как запись прогона, слепых классов
  по гейту 10, числа прав — те же, что в `gate-14.json`, и названа причина); пункт 5 §10 (12 классов
  у читателя и те же 12 в счётчике гейта); §11 (строка таблицы `reader_vs_gate`, абзац про отставание
  артефакта заменён записью прогона `gate-15.json` с длительностями шагов и с исправлением прежней
  причины — обхода корпусов гейт не делает, эти величины считаются по одному исходнику `cfg` через
  `scripts/counts.py`; добавлен «Статус к итерации 12»); §12 (артефакты, соответствующие матрице:
  `reports/gate-15.json`, прежний `gate-14.json` не перезаписывался). Строка 777 с историческим
  прогоном `&Сервер` (`reports/gate-14.json даёт код 0`) не менялась: это запись того прогона.
- `docs/слепые-пятна.md`: статус перенумерован на итерацию 12; запись про `tool_blind_kinds` = 12
  дополнена фактом `gate-15.json` = 10; абзац §1 про независимые числа гейта переписан (12 в
  `gate-14.json`, 10 в `gate-15.json`, полная слепота 7 классов до правок и 3 после).
- `docs/итог-боевой-проверки.md`: статус к итерации 12 (сверка читателя с гейтом разошлась против
  `gate-14.json` и сошлась против `gate-15.json`); добавлен блок чисел `gate-15.json` и запись о
  четырёх отличающихся ключах и о том, что побайтового равенства `gate-11` … `gate-14` с `gate-15`
  нет; ссылка на `layout_source` расширена до `gate-15.json`; в разделе про покрытия числа 12 и 7
  сохранены как запись прогона до правок и добавлены 10 из `gate-15.json` с 7 / 12 / 3 после правок;
  абзац про права дополнен тем, что после правки A1 читатель называет `role_rights` и те же 17 блоков
  и 79 прав, а контроль неподвижности по-прежнему исполняет `scripts/rights.py`.
- `docs/план-оптимизации-p1c.md`: «Статус блока A к итерации 11» заменён на «Статус блока A к
  итерации 12» с фактом `tool_blind_kinds` 12 → 10 по артефакту `gate-15.json` (вместо «осталось бы
  10»); в таблице блока G колонка «сейчас» обновлена (10 / 3 / 7 / 12 с прежними числами в скобках);
  в строках A5 и F3 прежние числа помечены как запись замеренного прогона.

Что не тронуто сознательно: `scripts/exec_probe.py` (запись `check-modules-base` с
`source: "reports/gate-14.json"`) и `tests/test_exec_probe.py:947` — `gate-14.json` остаётся
источником прежнего утверждения о коде 0; менять его в этой итерации означало бы переписать прежнее
доказательство.

Что не делалось: обходов корпусов не было; модифицирующих вариантов к гейт-ИБ
(`<tmp>\p1c_effektivnost\ib`) не применялось — только шаги гейта `load` / `check` / `dump`,
`--allow-mutating` не использовался; `cfg` (31 файл) не менялся.

Отложенная работа (по состоянию на конец итерации 12): A3–A6 (`subsystems`, `languages`,
`session_parameters`, `templates`, модули уровня конфигурации) и чтение дескрипторов `Roles/<Имя>.xml`
— класс `role` в `gate-15.json` остаётся среди 10 слепых классов: матрица закрывает его только именем
сущности, пути файла `Roles/<Имя>.xml` никто не называет.

## Итерация 13 (блок A3–A5: читатель добирает языки, подсистемы, дескрипторы и содержимое макетов)

### Решение исполнителя до начала работы (Ruling)

- **Что берётся.** А3 в части `Languages` и `Subsystems` (в `cfg` папка называется `Subsystems`,
  а в строке плана — `SubSystems`; расхождение имён фиксируется как факт: таксон `layout.py` —
  `"Subsystems": "subsystem"`, и именно его обязан называть манифест); А4 в части дескриптора макета
  (`Reports/ОтчётЗагрузки/Templates/ОсновнаяСхемаКомпоновкиДанных.xml`, свойство `TemplateType`) и
  содержимого схемы компоновки данных (`…/Ext/Template.xml`); дескрипторы `Roles/<Имя>.xml` и
  дескрипторы форм `Forms/<Имя>.xml`; А5 — класс каждого реально прочитанного файла.
- **Что откладывается и почему.** `CommonPictures`, `SettingsStorages`, `SessionParameters` — таких
  папок в `cfg` (31 файл) нет, поэтому читать нечего и проверять не на чем; A6 (модули уровня
  конфигурации); дескрипторы `Commands/<Имя>.xml` — в `cfg` каталога `Commands` нет, поэтому классы
  `command_descriptor` и `command_module` у layout-счётчика равны нулю и в сверке классов не
  участвуют.
  Отдельно фиксируется, что `layout.py` не знает таких папок вовсе: их таксонов в `KIND_FOLDERS` нет.
- **Форма учёта А5.** Манифест прочитанных файлов вида
  `{"path": <путь posix относительно base>, "kind": <таксон из scripts/layout.py>}`. Запись
  создаётся в точке фактического открытия файла, класс присваивает тот парсер, который файл открыл.
  Это отклонение от формулировки А5 («поле `kind` у записей модели»): у дескрипторов роли, языка,
  подсистемы, формы и макета, а также у файлов содержимого (`Ext/Rights.xml`, `Ext/Predefined.xml`,
  `Ext/Form.xml`, `Ext/Template.xml`, модули `.bsl`) своей записи модели нет, поэтому поле `kind`
  внутри записей модели эти классы не покрывает.
- **Новые ключи модели `p1c`:** `languages`, `subsystems`, `role_descriptors`, `form_descriptors`,
  `templates`, `template_data` и манифест прочитанных файлов; у записей форм и команд появляется
  `exports`. Значения берутся дословно из замеренных файлов корпуса: у языка `Name`, `Synonym`,
  `LanguageCode`; у подсистемы `Name`, `Synonym`, `Content` (9 ссылок вида `Catalog.Сотрудники` …
  `CommonModule.РасчётПоказателей`); у дескрипторов `Name`, `Synonym`, `Comment`, а у формы ещё
  `FormType` и `UsePurposes`, у макета — `TemplateType`.
- **Манифестный `counts_from_model`.** Классы берутся из пар `path`/`kind` манифеста;
  `files` — длина манифеста; `bsl_module` — записи манифеста с путём на `.bsl`, то есть
  `object_module 6` и `form_module 2` дают `bsl_module 8` (пересечение намеренное: это разные
  наблюдения об одном множестве файлов); record-производные `form_data` и `command_module` убираются;
  `skipped_module_files` остаётся record-производным, потому что это диагноз читателя, а не
  содержимое источника.
- **Ожидаемые числа.** Манифест по `cfg` даёт ровно те же 22 имени класса, что и `layout_source`
  `gate-15.json`: 9 дескрипторов коллекций плюс `role`, `subsystem`, `language`, `form_descriptor`,
  `form_data`, `form_module`, `report_template`, `report_template_data`, `role_rights`,
  `predefined_data`, `object_module`, плюс `files` и `bsl_module`. Ожидается `tool_blind_kinds` 10 → 0
  и `kinds_seen_by_path` 7 → 22.
- **Разрешение расхождения по числу файлов.** Читатель не открывает `Configuration.xml` /
  `Configuration.mdo` и не должен открывать: иначе паритет `m1 == m2` ломается, потому что у EDT есть
  `src/Configuration/Configuration.mdo`, а у выгрузки — `Configuration.xml`. Поэтому манифест по `cfg`
  даёт 30 записей против `files 31` у layout. `tool_blind_kinds` считается по именам классов и от этого
  не меняется. Тест паритетности формулируется как равенство множеств имён классов, плюс отдельная
  проверка: единственное различие по числам — класс `files`, а недостающий файл ровно один и это
  `Configuration.xml`; в остальных классах незакрытых файлов быть не должно. Разница записывается как
  факт, а не как ошибка.
- **Открытые решения, которые решаются по ходу (записывать в Ruling по факту):** обязательность
  реального открытия `Forms/*/Ext/Form/Module.bsl` — сейчас в `module_jobs` только менеджерные,
  объектные, рекордные модули и общие модули; либо туда добавляются модули форм (и тогда у записей
  форм появляются `exports`), либо класс `form_module` называется только по открытым файлам манифеста.
  Правка четырёх тестов паритетности `m1 == m2` (`p1c/tests/load/test_reader.py:82`,
  `tests/load/test_sources.py:44`, `tests/load/test_rights_predefined.py:149`,
  `tests/metadata/test_loader.py:85`) не нужна, если манифестные пути нормализуются тем же `base`
  (у EDT `reader.py:701-703` снимает `src/`) и корневые дескрипторы не читаются.
- **Код гейта от читателя не зависит:** `check_metadata` (`gate.py:64-105`) сверяет `layout_counts`
  с `docs/expected-metadata.json`; `tool_counts_source`, `tool_counts_dump` и `tool_blind_kinds`
  (`gate.py:363-371`, оба в `except RuntimeError`) на код возврата не влияют.
  `tool_blind_kinds = sorted(set(layout_source) - set(tool_counts_source))`.
- **Правки существующих тестов — сознательные.** В контуре: `tests/test_contour.py` — класс
  `CountsTest` (`:77-160`), в том числе проверка `assertNotIn("role", got)` (`:127`) и докстринг
  `:115-116` («объявлять дескриптор прочитанным нельзя») — переписываются под манифест с сохранением
  смысла каждого теста. В `probe/tool_coverage.py` меняется только `GATE_ARTIFACT` (`:58`) на
  `gate-16.json`. `PATH_ONLY_KINDS` (`:108`) и `OTHER_NAMED_KINDS` (`:99-100`) не меняются.
  Единственный импорт `scripts/counts.py` в контуре — `tests/test_contour.py:23`.
- **Прежние числа сохраняются только как запись прежнего замера** (`gate-14.json`, `gate-15.json`,
  прежняя матрица 5/10/7): `scripts/exec_probe.py` (`source: "reports/gate-14.json"`) и
  `tests/test_exec_probe.py:947` не меняются; `docs/expected-metadata.json` (`iteration: 5`,
  22 класса, `files 31`, `bsl_module 8`, `object_module 6`) — эталон, без отдельного решения не трогать.

Попутно в этом журнале поправлены две формулировки прежних записей: путь образца формы записан двумя
код-испанами (имя больше не склеивается латиницей с кириллицей через перенос строки) и иностранное
слово в записи про дескриптор роли заменено на «запасного чтения». Смысл обеих записей не
изменён.

### Журнал итерации 13: Task 21 и Task 22 (код `p1c`, контур пока не тронут)

- **Task 21 — фикстурный корпус (`p1c` commit `a10f68f`).** Копия `cfg/ЭффективностьОтдела` перенесена в
  `p1c/examples/managed_app` — 31 файл, байт-в-байт; копия сделана скриптом, замеры sha256 и размеров
  сняты с боевого корпуса до копирования. Красный тест `p1c/tests/load/test_fixture_corpus.py` (31 отказа
  «нет файла фикстуры») после копирования зелёный: фикстура проверяется целиком — «нет ни недостающих,
  ни лишних файлов», `Configuration.xml` в корпусе есть, каталога `src/` нет.
- **Числа независимого счётчика по копии равны числам боевого корпуса по всем 22 классам:** `files 31`,
  `bsl_module 8`, `object_module 6`, `form_descriptor 2`, `form_data 2`, `form_module 2`, `role 2`,
  `role_rights 2`, `predefined_data 1`, `language 1`, `subsystem 1`, `report_template 1`,
  `report_template_data 1` и по 1 у девяти дескрипторов коллекций (восемь видов коллекций плюс
  `common_module`).
- **Task 22 — манифест прочитанных файлов (`p1c` commit `408a6ec`).** RED: `python tests/load/test_read_manifest.py`
  даёт 27 отказов, и причина ровно отсутствующий ключ `read_files` в модели читателя (ни одна пара
  «путь/класс» не названа, ключ `skipped_files` при этом на месте). GREEN: 27 проверок зелёные, полный
  прогон `python scripts/run_tests.py` — тестов 76, неудачно 0.
- **Что реализовано.** `_opened(path, kind)` внутри `load_configuration_model` вызывается в точке
  фактического чтения: дескриптор коллекции перед `parse_object_xml`, `Ext/Predefined.xml`,
  `Roles/Имя/Ext/Rights.xml`, дескриптор общего модуля, `CommonAttributes/*.xml`, и модуль в `Ext/` —
  только после того как скан подтвердил чтение. Один файл называется один раз (`opened_paths`), поэтому
  манифест отвечает на вопрос «какие файлы прочитаны», а не «сколько раз их читали».
- **Класс модуля `.bsl` = таксон раскладки, а не ярлык парсера** (`KIND_EXT_MODULE = "object_module"` для
  `.bsl` непосредственно в `Ext/`): независимый счётчик считает `object_module` как все модули в `Ext/`,
  включая `CommonModules/РасчётПоказателей/Ext/Module.bsl` (отсюда `object_module 6`). Сверка манифеста с
  layout-счётчиком плечо-в-плечо возможна только при общем таксоне; внутренние имена парсеров для сверки
  не используются.
- **`scan_one` сообщает признак `read`** (файл прочитан): отсутствующий и нечитаемый модуль дают одинаковый
  пустой список экспортов, и без этого признака манифест назвал бы прочитанным файл, которого нет на диске.
  Нечитаемый модуль по-прежнему попадает только в `skipped_files` и в манифесте не появляется (проверено
  тестом на временной фикстуре).
- **Замер манифеста после Task 22:** `examples/designer_dump` — 13 записей, `examples/edt_project` — 13 тех же
  записей (без `src/`), `examples/managed_app` — 18 записей: девять дескрипторов коллекций (восемь видов
  плюс `common_module`), `object_module 6`, `role_rights 2`, `predefined_data 1`; модулей формы и дескрипторов
  ролей, языков, подсистем, форм и макетов в манифесте ещё нет.
- **Отсрочки зафиксированы сознательно:** класс содержимого формы (`form_data`), дескрипторы
  `Forms/<Имя>.xml`, дескрипторы и содержимое `Templates`, языки, подсистемы и дескрипторы ролей — Task 23–24;
  корневые `Configuration.xml` / `Configuration.mdo` читатель не открывает и не должен (иначе паритет
  `m1 == m2` ломается); модуль команды в манифесте отсутствует.
- **Правки четырёх тестов паритета модели не понадобились** — ожидание из Ruling подтверждено прогоном:
  манифестные пути нормализуются тем же `base` (`src/` у EDT снимается), `tests/load/test_scan.py` зелёный.
- **Поправка плана (ошибка замера, не кода).** В Task 23 Step 1 были указаны имена ролей
  `Roles/СотрудникОтдела.xml` и `Roles/ПолныеПрава.xml`; в боевом корпусе и в фикстуре `examples/managed_app`
  второй роли нет — реально `Roles/СотрудникОтдела.xml` и `Roles/АдминистраторСистемы.xml` (по 1242 и
  1262 байта). Имя `ПолныеПрава` взято из другой фикстуры `examples/designer_dump`. План исправлен,
  значения тестов берутся из фикстуры.

### Журнал итерации 13: Task 23 и Task 24 (код `p1c`, контур пока не тронут)

- **Task 23 — языки, подсистемы и дескрипторы ролей (`p1c` commit `a220ef7`, два файла).** RED:
  `python tests/load/test_languages_subsystems_roles.py` — 16 отказов по отсутствующим ключам `languages`,
  `subsystems`, `role_descriptors` и по манифестным парам. Две проверки из них отказали по ошибке самого
  теста: ссылка подсистемы сравнивалась полным именем `Catalog.Сотрудники` вместо короткого `Сотрудники`,
  который даёт файл `Subsystems/ЭффективностьОтдела.xml`, и вместо множества ключей сравнивался список
  с дублирующимися строками. Обе исправлены в тесте до реализации — код при этом не менялся. GREEN:
  тест зелёный, полный прогон `python scripts/run_tests.py` — тестов 77, неудачно 0; правки четырёх
  тестов паритета модели не потребовались.
- **Значения дескрипторов переносятся дословно:** язык — `name` `Русский`, `synonym` `Русский`,
  `language_code` `ru`, `path`; подсистема — 9 ссылок `content` в порядке файла; дескриптор роли — `name`,
  `synonym`, `comment`, `path`. Прав в записи роли нет: они лежат в `Ext/Rights.xml` и читаются отдельно,
  поэтому классы `role` и `role_rights` остаются двумя разными наблюдениями об одном объекте. Свойства
  читают две вспомогательные функции: `_descriptor_properties` (находит `Properties` внутри корневого элемента — у
  дескрипторов коллекций обёртка над ними различается) и `_property_text` (текст элемента либо текст
  `v8:content` внутри `v8:item`). Обходы `Languages`, `Subsystems` и `Roles` сделаны отдельным циклом
  после цикла коллекций и перед чтением `Ext/Rights.xml`.
- **Правка `cli.py` (`MODEL_KEYS`) из списка файлов Task 23 перенесена в Task 25**, где для неё есть тест
  на вывод `load model`. Менять ключи отчёта без проверки вывода — оставить непроверенное изменение,
  что противоречит порядку «сначала падающий тест».
- **Task 24 — дескрипторы и содержимое форм и макетов (`p1c` commit `dcf0112`, три файла).** RED:
  `python tests/load/test_forms_templates.py` — 26 отказов из 35 проверок, все по отсутствующим ключам
  `form_descriptors`, `templates`, `template_data` и по парам `form_descriptor`, `form_data`,
  `form_module`, `report_template`, `report_template_data`. Первая версия теста падала на `KeyError`
  и снимала `Traceback`, который скрывал остаток проверок; обращения к полям записей формы в тесте
  сделаны через `get(...) or []`, чтобы падающий тест показывал все проверки сразу. GREEN: 35 проверок
  зелёные; полный прогон — тестов 78, неудачно 0 (в их числе `tests/core/test_wording.py` и
  `tests/core/test_layers.py`).
- **Закрыто решение из Ruling про модули форм:** выбран вариант с `module_jobs` — путь
  `Forms/<Имя>/Ext/Form/Module.bsl` добавляется в задания сканирования, и у записей форм (объектных
  и общих) появляется ключ `exports` из этого модуля; он проверяется тестом. Вариант «называть
  `form_module` только по факту открытия» отвергнут: он не даёт честно объявить класс модуля формы
  и не даёт записям формы их экспорты, на которые опираются проверки форм
  (`p1c/src/p1c/check/forms/checks.py` читает текст модуля формы сам, через `module_text`). Проверено,
  что новый ключ не ломает `p1c/tests/diff/test_diff.py:83-84`: `exports` записей форм вложен в изменения
  формы, а `SECTIONS` сравнения версий новых ключей модели не содержит.
- **`module_jobs` стал тройками `(ключ, путь, класс)`** во всех шести местах, где задания создаются.
  В фазе слияния класс больше нельзя подставлять единым `KIND_EXT_MODULE = "object_module"`: модуль
  формы лежит не в `Ext/` объекта и раскладкой считается отдельным классом. Ключ задания модуля формы —
  `("форма", относительный путь модуля)`; он не пересекается с `(obj_name, "manager")` и различает две
  формы одного объекта.
- **Содержимое общих форм (`CommonForms/<Имя>/Ext/Form.xml`) названо `form_data`,** и её модуль
  сканируется как `form_module`: независимый счётчик раскладки относит общие формы к тем же классам,
  что и формы объектов, поэтому манифест обязан называть их одинаково.
- **Дословность значений форм и макетов:** `form_type` = `Managed`, `use_purposes` =
  `PlatformApplication` и `MobilePlatformApplication` (назначения использования, как в выгрузке),
  `template_type` = `DataCompositionSchema`, тип набора данных макета — из атрибута `xsi:type`
  (функция `_xsi_type` ищет атрибут по локальному имени, потому что префикс пространства имён в файлах
  разный). Корень содержимого макета — `DataCompositionSchema` без обёртки `MetaDataObject`: имя и тип
  макета лежат в дескрипторе, поэтому в записи содержимого остаются только источники данных, наборы
  данных с полями, текст запроса и вычисляемые поля. Текст запроса в модели нормализован разбором XML
  до переводов строки `\n` и читается в тесте как «начинается с `ВЫБРАТЬ` и кончается
  `УПОРЯДОЧИТЬ ПО`».
- **Правка `p1c/tests/load/test_read_manifest.py`:** докстринг переписан (не открываются только
  дескриптор команды, отсутствующий модуль и нечитаемый модуль), проверка «модуль формы ещё не назван»
  заменена позитивной проверкой класса `form_module`, и добавлена проверка, что манифест фикстурного
  корпуса называет каждый его файл, кроме `Configuration.xml`.
- **Замер манифеста после Task 23 и Task 24.** `examples/managed_app` — 30 записей из 31 файла корпуса:
  20 имён класса, из них девять дескрипторов коллекций (восемь видов плюс `common_module`), `role 2`,
  `role_rights 2`, `predefined_data 1`, `language 1`, `subsystem 1`, `form_descriptor 2`, `form_data 2`,
  `form_module 2`, `report_template 1`, `report_template_data 1`, `object_module 6`; модулей `.bsl` — 8,
  `skipped_files` пуст. `examples/designer_dump` и `examples/edt_project` — по 15 записей (было 13):
  добавились `form_data 1` и `form_module 1`, `object_module 5`, модулей `.bsl` — 6. Модуль команды
  `Catalogs/Номенклатура/Commands/Печать/Ext/CommandModule.bsl` в этих фикстурах по-прежнему не
  сканируется, поэтому его нет ни в манифесте, ни в `skipped_files`.
- **Сверка с раскладкой (пока как наблюдение, не как тест контура):** манифест корпуса даёт 20 имён
  класса, `scripts/layout.py` по тому же корпусу — 22; недостающих имён нет вообще, расхождение только
  по числу файлов (30 против 31, ровно `Configuration.xml`), как и записано в Ruling.

### Журнал итерации 13: Task 25 (код `p1c`, контур пока не тронут)

- **Что закрыто:** счётчик записей источника `_measure` в `p1c/src/p1c/load/cli.py` опирается на
  `MODEL_KEYS`, и в него вошли шесть ключей-записей: языки, подсистемы, дескрипторы ролей, дескрипторы
  форм, дескрипторы макетов и содержимое макетов. Корпус, где прочитан только дескриптор языка,
  подсистемы или роли, больше не считается пустым: код 0 вместо 1. Состав payload команды `model` и
  таблица команд не изменены.
- **Замер до правки (причина RED):** корпус `Configuration.xml` плюс один дескриптор давал код 1 —
  по прежним ключам записей ноль; после правки тот же корпус даёт код 0. Отказали 5 проверок из 35:
  три выходных кода корпусов с одним дескриптором и две проверки `MODEL_KEYS` (содержит новые ключи,
  каждый новый ключ даёт ровно одну запись). Проверено вызовом `_measure` по прежним восьми ключам.
- **Что оказалось зелёным ещё до правки:** разделы (1)–(2) нового теста. Команда `model` печатает
  прочитанную модель целиком, поэтому пути манифеста и записи шести новых ключей уже были в выводе
  в обоих форматах (замер: JSON 66572 символа, текстовый вывод 1451 строка). Задача проверяет вывод,
  а не меняет его.
- **Отступление от формулировки плана «пустой каталог → 1»:** по замеру пустой каталог и каталог без
  признаков раскладки дают код 2 («Не удалось определить раскладку…») — раскладка не опознана, и это
  ошибка аргумента, а не пустой источник. Код 1 получает распознанный, но пустой корпус:
  `Configuration.xml` без остальных файлов. Оба случая записаны и в тесте, и в плане.
- **Отступление: кейс «прочитано только содержимое макета» из теста убран** как неоднозначное
  свидетельство. Такой корпус заодно даёт запись объекта `Report.ОтчётЗагрузки` (объект создаётся по
  `Configuration.xml`), поэтому его код 0 неотличим от случая, когда новый ключ в счётчик не входит.
  Проверка кода 0 сделана на трёх корпусах: с дескриптором языка, дескриптором подсистемы и
  дескриптором роли.
- **Манифест `read_files` и `skipped_files` в счётчик не входят** — решение из Interfaces задачи:
  они описывают работу читателя, а не содержимое корпуса. Проверено тестом: модель, где заполнены
  только эти два ключа, даёт 0 записей источника.
- **Прогон:** `p1c/tests/load/test_model_report_paths.py` — 35 проверок, все зелёные; полный прогон
  `python scripts/run_tests.py` — тестов 79, неудачно 0; `python scripts/run_tests.py --smoke` — тестов 93,
  неудачно 0. Четыре теста, сравнивающих модели целиком, остались зелёными: значения новых ключей
  равны в фикстурах выгрузки и проекта EDT, сравнение версий и счётчик серверных статистик новых
  ключей не содержат.
- **Коммит кода и теста в `p1c`:** `900ae8d`.
- **Два наблюдения, которые в этой итерации не исправляются (записаны, чтобы не потерять):**
  1. Обход форм и макетов идёт по каталогам (`Forms/<Имя>/` и `Templates/<Имя>/`), поэтому одиночный
     дескриптор `Forms/<Имя>.xml` без каталога формы не открывается и не попадает ни в манифест, ни
     в `skipped_files`. Замер: корпус `Configuration.xml` плюс единственный дескриптор формы даёт код 0
     за счёт записей объекта, манифест пуст.
  2. Нечитаемый `Roles/<Имя>/Ext/Rights.xml` даёт непройденное исключение разбора XML
     (`p1c/src/p1c/load/reader.py:610`, вызов в обходе ролей `:1071`) вместо записи в `skipped_files`,
     и обход прерывается: код команды не возвращается. Ожидается другое: нечитаемый файл обязан быть
     записью диагноза, как нечитаемый модуль.

### Журнал итерации 13: Task 26 (счётчик контура перестроен на манифест)

- **Что закрыто:** `scripts/counts.py::counts_from_model` считает классы по парам `path`/`kind`
  манифеста `read_files` — по фактам открытия файла парсером. `files` стал длиной манифеста,
  `bsl_module` — числом манифестных записей с путём на `.bsl`, `skipped_module_files` остался
  record-производным (записи диагноза `skipped_files`, манифестной пары у них нет). Счёт по ключам
  модели удалён полностью.
- **Замер до правки (причина RED):** `python -m unittest tests.test_contour.CountsTest -v` —
  отказали 4 теста из 8, и все четыре — assertions о классах, импорт целый:
  `test_counts_come_from_manifest_pairs` вернул `{}` (прежний счётчик манифест не читает);
  `test_model_keys_without_manifest_pairs_count_as_nothing` вернул из ключей модели
  `catalog 2, command_module 1, common_attribute 1, common_form 1, common_module 2, form_data 2,
  predefined_data 1, role_rights 1` там, где ожидание `{}`; корпусный счётчик назвал 12 имён против
  ожидаемых 22; сверка имён с `layout_counts` — те же 12 против 22.
- **Что было зелёным ещё до правки:** `test_compare_detects_mismatch`,
  `test_skipped_module_files_stay_record_derived` (записи диагноза счётчик считал и раньше) и оба
  теста отказа читателя (`test_object_counts_refuses_without_reader_path`,
  `test_object_counts_wraps_reader_refusal_as_runtime_error`).
- **Классы, которые исчезли из счётчика:** `common_form`, а также record-производные `form_data`
  (по числу форм в записях объектов) и `command_module` (по числу команд). Теперь `form_data`
  появляется только как манифестная пара, созданная парсером содержимого формы; `command_descriptor`
  и `command_module` в нашем корпусе равны нулю и в сверке не участвуют (каталога `Commands` нет).
  Прежний запрет «объявлять дескриптор роли прочитанным нельзя» стал проверкой `role` только как
  манифестной пары: при открытии лишь `Roles/<Имя>/Ext/Rights.xml` имени `role` в счёте нет.
- **Step 5, сверка без платформы:** режима `--offline` у `probe/tool_coverage.py` нет (проверено по
  `main` `434-533`), поэтому сверка сделана прямыми вызовами `layout_files`, `layout_counts`,
  `counts_from_model` и `reader_kind_counts` скриптом во временном каталоге — обход 31 файла
  исходника и 32 файла выгрузки, вне окна 1С-замеров. Итог: `layout_files` — 22 класса и
  `layout_counts_match` без расхождений; `layout_counts` и `counts_from_model` называют одни и те
  же 22 имени; `tool_blind_kinds` по прежней формуле (`set(layout_source) − set(tool_counts_source)`,
  `scripts/gate.py:370-371`) становится пустым; единственное числовое различие — `files` `[31, 30]`,
  незакрытым остаётся ровно `Configuration.xml`; `kinds_seen_by_path` по манифесту — 22, невидных
  классов нет. По выгрузке тот же результат: манифест 30 записей, `skipped_files` пуст, слепых
  классов нет.
- **Прогон тестов:** `python -m unittest discover -s tests` — тестов 300, отказов 0, ошибок 0.
  Четыре корпусные проверки `CountsTest` прогнаны, а не пропущены (в выводе 3 строки со словом
  `skipped`, и все три — имена тестов, которые проверяют пропуск нечитаемых файлов; признака
  пропуска `skipped (` в прогоне нет).
- **Что не тронуто:** артефакты прежних прогонов `reports/gate-14.json` и `reports/gate-15.json`
  (`tool_counts_source` в них — запись прежнего замера: 10 и 12 классов, `tool_blind_kinds` — 12 и
  10), `scripts/exec_probe.py` с `source: "reports/gate-14.json"`, `tests/test_exec_probe.py:947`,
  `docs/expected-metadata.json`, а также `PATH_ONLY_KINDS` (`probe/tool_coverage.py:108`) и
  `OTHER_NAMED_KINDS` (`:99-100`) — они описывают меру матрицы, а не способ счёта.
- **Коммиты:** код и тесты контура — `f1833b1` (`scripts/counts.py`, `tests/test_contour.py`);
  правка плана с отмеченными замерами — `cb2cc97`.

### Итерация 13, Task 27: PREDICTIONS (записаны до прогона, после прогона не переписываются)

Исходные данные до прогона (замерены, не вывод): `cfg/ЭффективностьОтдела` — 31 файл, свежайший
2026-10-28 15:02:17, то есть с прогона `gate-15` исходник не менялся; гейт-ИБ существует (11
файлов, свежайшая запись 2026-10-29 21:21 — след прогона `gate-15`), поэтому шаг `create` не
понадобится; каталог выгрузки тоже существует (32 файла, та же запись прогона) — формулировка плана
«каталог выгрузки отсутствует, его создаёт шаг `dump`» по замеру неверна: его создал прежний прогон,
шаг `dump` перезаписывает файлы, а различение старых файлов делает именно проверка свежести
(`dump_fresh_files` против `dump_files`). Замер манифеста читателя на исходнике и на нынешней
выгрузке: по 30 записей, `skipped_files` пуст, 22 класса, слепых классов нет. Отчёт команды
`p1c.load model` по исходнику и по выгрузке содержит 30 различных путей и 16 различных имён
(среди имён есть `ЭффективностьОтдела` — его читатель называет как подсистему, а не как эхо
аргумента).

1. Код возврата 0, артефакт `reports/gate-16.json`, `reason` пустой, `step_problems` и
   `diagnostic_findings` пустые.
2. Шагов ровно три (`load`, `check`, `dump`), `create` отсутствует, `create_code` остаётся `null`,
   коды всех трёх шагов 0; длительности `load` ≈ 6 с, `check` ≈ 2 с, `dump` ≈ 2 с (замер
   `gate-15.json`: 6.0 с, 2.0 с, 2.0 с).
3. `metadata.layout` (он же `layout_source`) — те же 22 класса и те же числа, что в
   `gate-15.json`: `files 31`, `bsl_module 8`, `object_module 6`, `form_descriptor 2`, `form_data 2`,
   `form_module 2`, `role 2`, `role_rights 2`, `predefined_data 1`, `language 1`, `subsystem 1`,
   `report_template 1`, `report_template_data 1`, `common_module 1` и по 1 у `accumulation_register`,
   `catalog`, `constant`, `data_processor`, `document`, `enum`, `information_register`, `report`;
   `expected_mismatch` пуст, `hard_problems` пуст.
4. `rights` — код 0, `rights_files 2`, `object_blocks 17`, `rights 79`; `rights_immobility` — код 0,
   `dropped []`, `added []`, 17 блоков из 17 и 79 прав из 79.
5. `tool_counts_source` — 22 ключа вместо 12, с числами замеренного манифеста исходника: `files 30`,
   `bsl_module 8`, `object_module 6`, `form_module 2`, `form_descriptor 2`, `form_data 2`, `role 2`,
   `role_rights 2`, `predefined_data 1`, `language 1`, `subsystem 1`, `report_template 1`,
   `report_template_data 1`, `common_module 1` и по 1 у восьми дескрипторов коллекций. Причина:
   `counts.counts_from_model` (через `counts.object_counts`) считает пары манифеста, а не ключи
   модели.
6. `tool_blind_kinds` — пустой список вместо 10 классов (`bsl_module`, `files`, `form_descriptor`,
   `form_module`, `language`, `object_module`, `report_template`, `report_template_data`, `role`,
   `subsystem`). Причина: читатель назвал все 22 класса, формула вычитания не изменилась.
7. `tool_counts_dump` — те же 22 ключа и те же числа, что в `tool_counts_source` (в выгрузке тот же
   состав файлов: 32 файла на диске, 30 прочитанных, `Configuration.xml` не читается ни одним
   парсером записей).
8. `dump_files 32`, `dump_fresh_files 32` (шаг `dump` перезаписывает все файлы выгрузки);
   `diff_files` по составу как в `gate-15.json`: `Catalogs/Сотрудники/Ext/Predefined.xml` в `same`,
   оба `Roles/*/Ext/Rights.xml` в `reordered`.
9. Нормализованный JSON `gate-16.json` против `gate-15.json` различается ровно четырьмя местами:
   `steps` (начало и длительности), `tool_counts_source`, `tool_counts_dump`, `tool_blind_kinds`.
   Побайтового равенства не будет: `tool_counts_source` стал 22 ключа вместо 12.
10. Матрица после `GATE_ARTIFACT = "reports/gate-16.json"`: 18 прогонов восьми инструментов
    (`bsl`, `cf`, `diff`, `forms`, `graph`, `load`, `metrics`, `sdbl`), платформа 1С не запускается,
    коды прогонов те же, что в прежнем замере: 2 у `load-object-wrong-order`, `forms-form-wrong-order`
    и `cf-info-cfg-dir`, 1 у `bsl-check-cfg` (15 находок), 0 у остальных 14.
11. Строки §2 у `load-model-cfg` и `load-model-dump`: файлов cfg в JSON-отчёте 30 вместо 7, имён cfg
    16 вместо 14, имён только как часть пути 0, хитов только в консоли 0. Суммы хитов по классам
    (третья величина, `probe/tool_coverage.py:518-521`) — 68 путей и 21 имя у каждого из двух
    модельных прогонов.
12. Категории матрицы: закрытые хотя бы по пути файла — 22 класса из 22 (было 7); закрытые только
    именем сущности — 0 (было 12); не закрытые ни по пути, ни по имени — 0 (было 3: `language`,
    `report_template`, `report_template_data`). `reader_kind_counts` обоих модельных прогонов — 22
    класса с `files 30`; `reader_vs_gate` — совпадение с `gate-16.json`, `diff_reader_vs_gate` пуст;
    `gate_tool_blind_kinds` пуст.
13. `python probe/render_query_tables.py --check` до правок документов обязан отказать на строках
    матрицы (покрытии классов и двух строках моделей), и стать зелёным после правок §2, §5 и §11 в
    `docs/evidence/tool-coverage.md`.
14. Что заранее не предсказано: пути и имена остальных 16 прогонов матрицы. Причина измерима:
    читатель `p1c.load`, которым пользуются `load forms`, `check.bsl`, `metrics` и `diff`, изменён в
    задачах 22–24, и чем именно изменятся их отчёты — можно узнать только повтором матрицы. Всё
    непредсказанное записывается отдельным списком с причиной после прогона.

### Журнал итерации 13: Task 27 (единственный 1С-прогон `gate-16`, пересъёмка матрицы, правка документов)

- **Что закрыто:** единственная 1С-операция итерации (`gate-16`), пересъёмка матрицы покрытия на манифест
  прочитанных файлов, сверка артефакта с пунктами 1–14 выше, правка четырёх документов и проверка
  номерных ссылок. Хэши этой задачи: код замера `c88ce8f`, документы `86d63e1`, отмеченные шаги 1–8
  плана `0a2aed4`, этот журнал — следующий коммит, финальный коммит плана (шаги 9–10) — после него.

**Единственный прогон платформы.**

- Команда: `python scripts/gate.py --cfg "cfg/ЭффективностьОтдела" --out reports/gate-16.json --canon
  docs/canonical-rights.json --timeout 240` (`bin`, `ib`, `dump`, `p1c` подставлены из
  `local.paths.json`); без `--allow-mutating`, один раз, повторов «для устойчивости» не было; гейт-ИБ
  открыт только на чтение.
- Итог: код 0, артефакт `reports/gate-16.json` — 8438 байт и 27 ключей верхнего уровня; набор ключей
  идентичен `reports/gate-15.json` (8180 байт) и `reports/gate-14.json` (8125 байт).
- Шаги по замеренным `started` и `seconds`: `load` начался 07:45:11, 8.0 с, `bytes 3`; `check` 07:45:19,
  2.0 с, `bytes 73`; `dump` 07:45:21, 2.0 с, `bytes 3` (закончился 07:45:23). У всех трёх код 0,
  `timed_out false`, `reason ""`.
- `create`-шага нет: `create_code null`, `ib_ready_before true`; `step_problems []`,
  `diagnostic_findings []`, `reason ""`, `tool_counts_error ""`.

**Сверка с `PREDICTIONS` (пункты 1–14; сам список выше не переписан).**

1. Подтверждено: код 0, `reason ""`, `step_problems []`, `diagnostic_findings []`.
2. Частично: `check` 2.0 с и `dump` 2.0 с, три шага, `create` отсутствует и `create_code null` — как
   предсказано; `load` 8.0 с вместо ≈6 с. Это единственное числовое отклонение прогона (причина —
   отдельным списком ниже, пункт 1).
3. Подтверждено: `metadata.layout` и `layout_source` — 22 класса, `files 31` и те же числа, что у
   `gate-15.json`: `bsl_module 8`, `object_module 6`, `form_descriptor 2`, `form_data 2`, `form_module 2`,
   `role 2`, `role_rights 2`, и по 1 у `predefined_data`, `language`, `subsystem`, `report_template`,
   `report_template_data`, `common_module`, `accumulation_register`, `catalog`, `constant`,
   `data_processor`, `document`, `enum`, `information_register`, `report`; `layout_compare {}`;
   `layout_dump` — 22 класса с `files 31`; `metadata.expected_mismatch {}`, `metadata.hard_problems []`,
   `metadata.problems []`, `metadata.reason ""`.
4. Подтверждено: `rights` код 0, `rights_files 2`, `object_blocks 17`, `rights 79`, `problems []`;
   `rights_immobility` код 0, `dropped []`, `added []`, 17 блоков из 17 и 79 прав из 79.
5. Подтверждено: `tool_counts_source` — 22 ключа с `files 30` и числами манифеста исходника:
   `bsl_module 8`, `object_module 6`, `form_module 2`, `form_descriptor 2`, `form_data 2`, `role 2`,
   `role_rights 2`, по 1 у `predefined_data`, `language`, `subsystem`, `report_template`,
   `report_template_data`, `common_module` и восьми дескрипторов коллекций.
6. Подтверждено: `tool_blind_kinds` пуст (у `gate-15.json` — 10 классов, у `gate-14.json` — 12).
7. Подтверждено: `tool_counts_dump` — те же 22 ключа и `files 30` (в выгрузке 32 файла на диске,
   прочитаны 30; `Configuration.xml` не открывает ни один парсер записей).
8. Подтверждено: `dump_files 32`, `dump_fresh_files 32`; `diff_files` равен составу `gate-14.json` и
   `gate-15.json`: `same 21` (в том числе `Catalogs/Сотрудники/Ext/Predefined.xml`), `reordered 2` (оба
   `Roles/*/Ext/Rights.xml`), `differ 8`, `only_source 0`, `only_dump 0`, `platform_added 1`
   (`ConfigDumpInfo.xml`).
9. Подтверждено: различие с `gate-15.json` ровно в четырёх ключах — `steps`, `tool_counts_source`,
   `tool_counts_dump`, `tool_blind_kinds`; побайтового равенства не ожидаем и его нет.
10. Подтверждено: матрица — 18 прогонов восьми инструментов (`bsl`, `cf`, `diff`, `forms`, `graph`,
    `load`, `metrics`, `sdbl`), платформа внутри матрицы не запускалась; коды те же, что в прежнем
    замере: 2 у `load-object-wrong-order`, `forms-form-wrong-order` и `cf-info-cfg-dir` (у последнего
    JSON-отчёта нет, `stderr: Книга .cf ожидается файлом, а передан каталог: <cfg>` — одинаково в прежнем
    и нынешнем замере), 1 у `bsl-check-cfg` (15 находок, `stats.files 8`), 0 у остальных 14.
11. Подтверждено: у `load-model-cfg` и `load-model-dump` — 30 различных путей и 16 различных имён
    (было 7 и 14), новых имён два: `Русский` и `ОсновнаяСхемаКомпоновкиДанных`; суммы хитов по классам
    — 68 путей и 21 имя у каждого из двух прогонов; имён только как часть пути 0, хитов только в консоли 0.
12. Подтверждено: категории матрицы 22 / 0 / 0 (было 7 / 12 / 3); `reader_kind_counts` обоих модельных
    прогонов — 22 класса с `files 30`; `reader_vs_gate` (верхнеуровневый ключ `reports/toolcov_runs.json`)
    — `equal_to_gate_tool_counts_source true` и пустой `diff_reader_vs_gate` как против `gate-16.json`,
    так и против прежнего снимка матрицы (`gate_artifact gate-15.json`).
13. Подтверждено, но шире предсказанного: до правок документов `--check` отказал (код 1) не на трёх
    строках матрицы, а на 41 вхождении фрагментов в шести регионах (`coverage-kinds` 16,
    `coverage-content-load` 14, `coverage-reconcile` 7, `coverage-content-checks` 1, `coverage-runs` 2,
    метка `self-dotted` 1). После правок §2, §5 и §11 — код 0, `fragments: 28 checked lines: 692`,
    `unused fragments: none`.
14. Ответ на предсказание: пути и имена 16 из 18 прогонов не изменились (сверка прогон за прогоном с
    прежним снимком матрицы); изменились только `load-model-cfg` и `load-model-dump` — пути 16 → 68,
    имена 18 → 21.

**Что оказалось непредсказанным (причины измерены, кроме названной не измеренной).**

1. `load` 8.0 с вместо ≈6 с. Причина не измерена: в артефакте нет разбивки шага `load`, `bytes 3` у него
   такое же, как у `gate-15.json`, и `scripts/ib_loop.py` в этой итерации не правился. Отклонение
   зафиксировано как отклонение; `PREDICTIONS` не переписаны.
2. Ключи `diagnostics` (одна строка «Синтаксических ошибок не обнаружено!») и `diagnostics_by_step`
   (`check` — 1 строка, `load` и `dump` пустые) равны прежним артефактам, хотя в списке предсказаний их
   не было.
3. Очередь модулей читателя выросла 18 → 20: добавлены два слота модулей форм (правка `dcf0112`). Замер
   `probe/reader_module_queue.py` → `reports/reader-module-queue.txt`: 20 записей — 7 «менеджер
   значений», 3 «менеджер значений (регистр)», 2 «модуль набора записей (регистр)», 5 «модуль объекта»,
   1 модуль общего модуля, 2 модуля форм; файлов на диске 8, отсутствующих слотов 12; манифест 30
   записей, `skipped_files 0`; объектов 8, форм объектов 2, общих модулей 1, общих форм 0. Из-за этой
   строки изменился `stderr` в 11 из 18 прогонов матрицы (у `diff-model-cfg-dump` — дважды), но пути и
   имена не изменились ни у одного из них, кроме двух модельных прогонов.
4. Правка генератора `probe/render_query_tables.py` вне списка файлов задачи: добавлены `MANIFEST_KEYS`
   и `manifest_class_counts()`, чтобы таблица покрытия классов строилась парами манифеста, а не ключами
   модели (иначе `--check` не прошёл бы по новой таблице), и исправлена метка `:350` — смешанное
   написание (кириллическая `д` в начале латинского слова) заменено на `dotted-написание виртуальной
   таблицы`, как в остальных строках документа; та же строка `docs/evidence/canonical-queries.md:229`
   исправлена по этому же замеру.
5. Цитаты таблиц и `OUT`-блоков перенесены скриптом сверки (сначала просмотр расхождений, затем
   применение): изменено 5 регионов из 8 (`coverage-runs` 2 строки, `coverage-kinds` 16,
   `coverage-reconcile` 7, `coverage-content-load` 14, `coverage-content-checks` 1). Вариант вставки по
   маркерам не применялся: маркеров таблиц и блоков ни в одном из 15 документов `docs/evidence/` нет
   (проверено). `docs/слепые-пятна.md` (390 строк) и `docs/итог-боевой-проверки.md` (323 строки)
   правлены вручную, потому что проверка фрагментов покрывает только четыре документа `docs/evidence/`.
   `docs/evidence/tool-coverage.md` — 1025 строк в `f6330c7` и 1148 после правок.
6. Номерные ссылки на `probe/tool_coverage.py` переведены на рабочее дерево: файл сдвинулся
   (537 строк в `f6330c7`, 538 в рабочем дереве; `GATE_ARTIFACT` со строки 58 на 59), поэтому
   обновлены ссылки `PATH_EDGE` 286,
   `name_occurrences` 289-304, `PATH_ONLY_KINDS` 109, `OTHER_NAMED_KINDS` 100, `names_counted` (`:92`),
   `GENERIC_STEMS` 105, `entity_name` 174-187, колонок консоли 334 / 336-337 / 338-342, `tables` 407,
   `:414-416`, `:518`, `:521-524` и `skd_query_text()` 213-219; ссылки на исходники `p1c` сверены по HEAD
   `900ae8d` (`cli.py:151-160`, `rglob("*.bsl")` 157, `cmd_check` `:213`, `stats["files"] += 1` `:237`,
   `cmd_query` `:261`, `load/cli.py:124-131` и `:114`, `check/forms/cli.py:195-202` и `:180`). Проверка
   83 ссылок шести документов: 17 ссылок не разрешились из-за сокращённых имён файлов (`reader.py`,
   `checks.py`, `semantic.py`, `platform_arities.py`, `sdbl.py`, `test_scan.py`) — все 17 сверены вручную
   по полным путям (`src/p1c/load/reader.py`, `src/p1c/check/forms/checks.py`,
   `src/p1c/check/bsl/semantic.py`, `src/p1c/data/platform_arities.py`, `src/p1c/sdbl/sdbl.py`,
   `tests/load/test_scan.py`, 11 различных мест) и ведут на строки, которые говорят то же, что и ссылка;
   битых ссылок не осталось.
7. В HEAD `probe/tool_coverage.py:58` стоял `gate-15.json`, а не `gate-14.json` — шаг 5 задачи 26 об этом
   не говорил. Переход сделан на `gate-16.json` (`:59`); прежние артефакты остались записью прежних
   замеров (12 классов и 10 слепых у `gate-15.json`, 10 и 12 у `gate-14.json`), их числа в документах
   не переписаны.
8. Наблюдение: `reader_vs_gate` против `gate-14.json` даёт два расхождения — `predefined_data [1, 0]` и
   `role_rights [2, 0]`. Причина: `gate-14.json` посчитан читателем до правок A1–A2, где этих записей не
   было; матрица сверяется с `gate-16.json`, поэтому в матрице расхождение не проявляется. Это
   наблюдение, а не правка.
9. Шаги 2 и 6 плана оказались неверны по замеру и исправлены коммитом `0a2aed4` с явной пометкой:
   каталог выгрузки существует (32 файла, след прогона `gate-15`), а в шаге 6 были выдуманы
   `Subsystems/ConfigGenerationSettingsStorageMap.xml`, `Reports/ОтчётЗагрузки/Templates/ОтчётПоЗатратам.xml`
   и `…/Schema.dcsset`. Замер: каталога `SettingsStorages` в `cfg/ЭффективностьОтдела` нет (12 папок и
   `Configuration.xml`, 31 файл), макет отчёта — `ОсновнаяСхемаКомпоновкиДанных`.
10. Отложено и не закрыто в этой итерации: `CommonPictures`, `SettingsStorages`, `SessionParameters`
    (таких папок в `cfg/ЭффективностьОтдела` нет), строка A6 (модули уровня конфигурации), дескрипторы
    `Commands/<Имя>.xml`. Два наблюдения задачи 25 не исправлены: одиночный дескриптор `Forms/<Имя>.xml`
    или `Templates/<Имя>.xml` без каталога не открывается (манифест пуст), и нечитаемый
    `Roles/<Имя>/Ext/Rights.xml` даёт непройденный `xml.etree.ElementTree.ParseError` в `parse_rights_xml`
    (`src/p1c/load/reader.py:610`, вызов `:1071`) вместо записи в `skipped_files`.

**Что не изменено и чем проверено.**

- Не тронуты `scripts/exec_probe.py`, `tests/test_exec_probe.py:947`, `docs/expected-metadata.json`,
  `PATH_ONLY_KINDS` (`probe/tool_coverage.py:109`) и `OTHER_NAMED_KINDS` (`:100`); прежние числа
  (`gate-14.json` 10 и 12, `gate-15.json` 12 и 10, прежняя матрица 7 / 12 / 3 и 5 / 10 / 7) остались в
  документах как запись прежних замеров.
- Тесты после всех правок: контур — `python -m unittest discover -s tests` → Ran 300 tests, OK, код 0;
  `p1c` — `python scripts/run_tests.py` → тестов 79, неудачно 0, код 0, рабочее дерево `p1c` чистое;
  `python probe/render_query_tables.py --check` → код 0 (`fragments: 28 checked lines: 692`).
- Скан текстов (семь файлов `docs/` вместе с этим журналом и три файла `probe/`) сверен построчно с
  состоянием до правок задачи 27 (коммит `f6330c7`): было 53 флага, стало 54. Новые — 3 в строках
  этого журнала, где приведены цитаты имён корпуса `ВыгрузкаЗатратCSV` и
  `СервисКриптографииDSSСлужебный`, в которых латиница стоит вплотную к кириллице, и 1 в файле плана
  (то же первое имя). Оба имени уже стоят в закоммиченных документах, новых имён не придумано. Сняты
  3 прежних флага: в метке `dotted-написание виртуальной таблицы` кириллическая `д` заменена на
  латинскую — `docs/evidence/canonical-queries.md:229` и генератор
  `probe/render_query_tables.py:350`; в прежней строке 809 этого файла заимствованное английское
  название вспомогательной функции заменено на `вспомогательные функции` (правка вне задачи 27, чтобы
  в репозитории не осталось ни одного флага по списку англицызмов; в этом журнале то слово не
  приводится). Прочие флаги совпадают с прежним замером: 24 в `docs/evidence/tool-coverage.md`, 6 в
  `docs/evidence/canonical-queries.md` (4 — имя обработки, 2 — встроенное имя функции 1С, начинающееся
  кириллицей и продолжающееся латиницей; `:29` и `:59`, то же имя в `docs/evidence/sdbl-controls.md`),
  по 1 в `docs/итог-боевой-проверки.md` и `docs/план-оптимизации-p1c.md`, 1 в
  `probe/tool_coverage.py:293` (в докстринге приведён вид пути из отчёта), 3 в
  `probe/render_query_tables.py:203` и `:204` (экранированные переводы строки, не путь), 0 в
  `docs/слепые-пятна.md` и `probe/reader_module_queue.py`. CJK нигде не встречается; отметки по
  абсолютным путям — только названные цитаты в докстрингах `probe/`; записываемых абсолютных путей в
  файлах `probe/` и `docs/` нет. Из прежних 15 флагов `progress.md` (все до заголовка этого журнала)
  снят названный выше флаг в прежней строке 809, остальные 14 не тронуты.
### Журнал итерации 14: Task 28 (домикнинг плана под замеры `gate-16.json`)

- Задача вне плана итерации 13 и вне правок кода: строки `docs/план-оптимизации-p1c.md`, оставшиеся от
  прежних замеров, сверены с артефактом `gate-16.json` и reader-замерами 30.10.2026. Изменён один файл —
  19 новых строк вместо 16 прежних, файл вырос с 169 до 172 строк. Код `p1c` и `probe/` в этой задаче не
  тронут, 1С-прогонов не было; основанием послужили закоммиченные артефакты `reports/` и разобранные
  места `docs/evidence/`.
- Что правлено и на каком основании.
  1. Строка A4 и абзац статуса блока A: пути класса шаблона — `Reports/ОтчётЗагрузки/Templates/
     ОсновнаяСхемаКомпоновкиДанных.xml` и `…/ОсновнаяСхемаКомпоновкиДанных/Ext/Template.xml`. Прежние
     имена `ОтчётПоЗатратам.xml` и `Schema.dcsset` были выдуманы (пункт 9 журнала Task 27) и теперь
     названы явно как выдуманные. Замер файла макета: 5445 символов, корень
     `DataCompositionSchema`, ровно один блок `<query>` длиной 1097 символов (скрипт
     `<tmp>\opencode\t28_measure_template.py` → `<tmp>\opencode\t28_measure_template.json`).
     Отступление по этому замеру: тот же скрипт по тегам `dataset`/`field`/`dataSource` без учёта
     пространств имён нашёл 0 наборов данных и 0 полей — эти нули в план не записаны; в план попали
     1 набор данных из 6 полей и 1 вычисляемое поле `КоэффициентЗагрузки` из разбора читателем модели
     (`docs/evidence/tool-coverage.md` §10 п. 1 и §11 п. 4, `model.template_data`). Имя вычисляемого
     поля в план добавлено вместо прежней безымянной формулировки «1 вычисляемое поле».
  2. Строка A4 продолжена замером разбора текста макета: `check.sdbl query` на этих 1097 символах даёт
     `queries 1` и `field_ok 13` из 13 ссылок при 0 находок (`reports/skd2_new-exact.json` → `stats`,
     строка `new-exact` в `docs/evidence/sdbl-controls.md` §6), и это не тот же обход, что `check`:
     обход `check` берёт файлы по `rglob("*.bsl")` (`p1c/src/p1c/check/sdbl/cli.py:151-160`, `:157`),
     а `query` читает текст из позиционного аргумента (`:347`), поэтому макет в обход `check` не входит.
  3. Строка метрики блока A дополнена указанием прогона, которым метрика закрыта (`gate-16.json`).
  4. Строка C1: прежняя формулировка «11 `IDS_STX_VAR_NOTDECLARED` и 3 `IDS_STX_METHODNOTFOUND` — шум
     канона» неверна по составу находок. Разбор `reports/toolcov_bsl-check-cfg.json` (15 находок):
     11 × `IDS_STX_VAR_NOTDECLARED` (8 неявных реквизитов `Ставка`, `ДатаПриёма`, `Сотрудник`, `Часы`,
     `НачалоПериода` и 3 на неявное свойство `Движения.`), 1 × `IDS_STX_CTOR_NOTFOUND` и
     3 × `IDS_STX_METHODNOTFOUND`. Последние четыре — не шум канона, а пробел данных `p1c`, и в строке C1
     они теперь отнесены к C2. Разбор тех же 15 находок уже записан в `docs/evidence/tool-coverage.md` §9.
  5. Строка C6: к прежней формулировке «возвращает пустые `kind` и `owner`» добавлено, что в том же
     отчёте `form.kind` (`catalog`) и `form.object` (`Сотрудники`) заполнены, а пустуют только поля трёх
     событий. Сверено с артефактом `reports/toolcov_forms-form-element.json` (ключ `form` с полями
     `attributes, commands, events, exports, items, kind, module, name, object, path`; ключа `owner` у
     формы нет) и с пересъёмкой матрицы под `gate-16.json`. Отдельно проверено, что `form.kind` и
     `form.object` были заполнены уже на дереве `f6330c7` (`git show` прежнего
     `docs/evidence/tool-coverage.md` — строки 480 и 618 того файла): правка итерации 13 к этому
     отношения не имеет, и в плане это не подано как новое достижение.
  6. Строка F3 закрыта: манифест `model.read_files` отдаёт класс каждого открытого файла, и по замеру
     `kinds_seen_by_name_only` стал 0 при `kinds_seen_by_path` 22.
  7. Таблица блока G переснята целиком: `tool_blind_kinds` 0 (`gate-16.json`; было 12 в `gate-14.json`,
     10 в `gate-15.json`), `kinds_seen_by_no_tool` 0 (было 7, затем 3), `kinds_seen_by_path` 22 (было 5,
     затем 7), `kinds_seen_by_name_only` 0 (было 10, затем 12); находки `check.bsl` — 15, из них 11 шум и
     4 пробел данных; `types_without_ctor` / `types_without_properties` 1869 / 1885; `check.forms form`
     (поля событий `kind`, `owner`) — пусто; коды CLI — 0 безусловных (18 прогонов матрицы: код 0 у 14,
     код 1 у `bsl-check-cfg`, код 2 у `cf-info-cfg-dir`, `load-object-wrong-order`,
     `forms-form-wrong-order`); SKD-строка — `check`: 3 запроса, `sources 7`, `field_ok 20` из 23 ссылок,
     `skip_vt_no_help_fields 1`, `skip_field_fields_unknown 3` (`reports/toolcov_sdbl-check-cfg.json`) и
     `query` на тексте макета: 1 запрос, `field_ok 13` из 13.
     Проверка кодов: `reports/toolcov_runs.json` → 18 записей `runs`, распределение кодов
     `{0: 14, 1: 1, 2: 3}` (скрипт `<tmp>\opencode\t28_run_codes.py`). Отдельно снято сомнение по
     строке 720 `docs/evidence/tool-coverage.md`, где `cf-info-cfg-dir` показан кодом 1: это трассировка
     прежнего прогона до правки обвязки (`:716-729`), а не прогон матрицы, и в распределение кодов она не
     входит. Восемь оставшихся в `p1c` `return 0` (`cf/cli.py:158, 164, 204, 217, 232`;
     `check/forms/cli.py:183`; `check/sdbl/cli.py:313`; `load/cli.py:108`) перечитаны: каждый стоит под
     комментарием о структурной недоступности кода 1, потому что отсутствующий источник уже сообщён
     ошибкой контекста с кодом 2; в план это записано именно так, а не как «ни одного `return 0`».
- Прежние числа нигде не переписаны: 12 и 10 в `gate-14.json`, 10 в `gate-15.json`, прежние 7 / 3 по
  матрице и 5 / 10 по именам сохранены в плане как запись прежних замеров («было …»).
- `PREDICTIONS` этой задачи не писались: задача — сверка текста с уже существующими артефактами, нового
  прогона нет. Непредсказанных шагов два: правка строки C1 (состав находок оказался иным, чем в формулировке)
  и правка строки «коды CLI» (пришлось перечитать восемь `return 0` в `p1c`, чтобы не писать в плане
  неверного «ни одного»).
- Скан текстов (`<tmp>\opencode\t28_scan_plan.py` на обёртке `<tmp>\opencode\scan_texts.py`, сверка
  построчно с базой `dc96979`): флагов было 1, стало 1; новых флагов нет; 19 изменённых строк — чистые по
  всем четырём отметкам (склейка латиницы с кириллицей, CJK, абсолютные пути, англицызмы). Единственный
  флаг плана — прежний, на строке 101: в пути `DataProcessors/ВыгрузкаЗатратCSV/Ext/ObjectModule.bsl`
  латиница стоит вплотную к кириллице внутри замеренного имени файла; имя придумано не было, и строка в
  этой задаче не менялась.
- Коммит правки плана — отдельно от этого журнала: `b2daca5`.

### Журнал итерации 14: Task 29 (командные модули читаются как `command_module`, экспорты команды прикрепляются)

- План итерации 14 написан тремя файлами в `docs/superpowers/plans/` (14a — задачи 29–33,
  14b — 34–38, 14c — 39–42); все три прошли скан `<tmp>\opencode\scan_texts.py` без флагов.
  Способ исполнения — inline (выбор пользователя). Ruling: лиджер — установленный
  `effektivnost-otdela/.superpowers/sdd/effektivnost-otdela/progress.md` (не generic-воркспейс
  `executing-plans`), нумерация продолжается с Task 29; репозиторий `p1c` — на ветке `main`
  (так же, как в итерациях 1–13), контур `effektivnost-otdela` — на `feat/config-effektivnost`.
- Замер до правки (`<tmp>\opencode\t29_owner.py`, `t29_pulsar_layout.txt`): файла
  `Commands/<Имя>.xml` нет ни в одном из 7 корпусов и 3 фикстур (0 дескрипторов); декларации
  команд лежат inline в `<ChildObjects><Command>` XML владельца (пульсар: 457 файлов, 2432
  декларации, у 26 из 44 владельцев), а командный модуль — `Commands/<Имя>/Ext/CommandModule.bsl`
  (пульсар: 44 объектных + 47 у CommonCommands). Формулировку роадмапа про `Commands/<Имя>.xml`
  правит Task 33.
- RED: `tests/load/test_commands.py` (новый) падал на 3 проверках — нет пары `command_module`,
  нет поля `exports`; пины `tests/load/test_read_manifest.py:93-97` перевёрнуты из негативных
  в позитивные. GREEN: читатель добавляет командный модуль в `module_jobs` с ключом
  `("команда", rel(module))` и классом `KIND_COMMAND_MODULE = "command_module"`, в фазе 3
  прикрепляет `exports` к записи команды.
- Полный прогон `p1c`: `python scripts/run_tests.py` — тестов 80, неудачно 0 (было 79, +1 новый).
- Офлайн-замер пульсара (`<tmp>\opencode\t29_pulsar_measure.py`): `command_module` 44 (ровно
  объектных командных модуля), `common_command_module` 0 (до Task 30), CommonCommands `.bsl`
  в манифесте 0.
- Коммит `p1c`: `45933b7` (reader.py, test_read_manifest.py, test_commands.py).

### Журнал итерации 14: Task 30 (дескрипторы и содержимое общих коллекций)

- RED: `tests/load/test_common_collections.py` (новый, синтетическая фикстура через `tempfile` —
  `Configuration.xml` + `CommonCommands/К1[.xml,/Ext/CommandModule.bsl]`, `CommandGroups/Г1.xml`,
  `CommonPictures/П1[.xml,/Ext/Picture.xml,/Ext/Picture/Picture.png]`,
  `CommonTemplates/Т1[.xml,/Ext/Template.xml]`, `CommonForms/Ф1[.xml,/Ext/Form.xml,/Ext/Form/Module.bsl,/Ext/Help.xml]`).
  Падал на 16 проверках: не было классов дескрипторов, классов содержимого и ключей модели.
- GREEN: читатель читает дескрипторы `CommonCommands/CommandGroups/CommonPictures/CommonTemplates`
  и дескрипторы общих форм с классами раскладки `common_command`, `command_group`, `common_picture`,
  `common_template`, `common_form`; содержимое — `common_command_module`, `common_picture_data`,
  `common_picture_content`, `common_template_data`, `help` (справка общих форм). Ключи модели —
  `common_commands`, `command_groups`, `common_pictures`, `common_templates`, `common_form_descriptors`
  (общий помощник `_descriptor` + пять парсеров). Модуль общей команды — в `module_jobs` с ключом
  `("общая команда", имя)` и классом `common_command_module`; экспорты прикрепляются в фазе 3.
- Ruling: дескриптор общих форм идёт в отдельный ключ `common_form_descriptors` (параллель
  `form_descriptors`), а не в `common_forms` (который остаётся списком записей содержимого форм) —
  так класс `common_form` (дескриптор) не смешивается с `form_data`/`form_module` (содержимое).
- Полный прогон `p1c`: `python scripts/run_tests.py` — тестов 81, неудачно 0 (+1 новый).
- Офлайн-замер пульсара (`<tmp>\opencode\t30_pulsar_measure.py`): `common_command 47`,
  `command_group 7`, `common_picture 403`, `common_template 13`, `common_form 65`,
  `common_command_module 47`, `common_picture_data 403`, `common_picture_content 403`,
  `common_template_data 16`, `help 82` — все совпали; `read_files` вырос 2979 → 4465.
- Коммит `p1c`: `8d6004b` (reader.py, test_common_collections.py).

### Журнал итерации 14: Task 31 (одиночные макеты и коллекции вне COLLECTIONS_MAP)

- RED: `tests/load/test_single_templates_storages.py` (новый) падал на 10 проверках — не было
  одиночного макета `report_template`, дескрипторов `settings_storage`/`filter_criteria` и
  содержимого хранилища.
- GREEN: одиночный дескриптор `Templates/<Имя>.xml` без каталога читается как `report_template`;
  `SettingsStorages/<Имя>.xml` → `settings_storage` (+ содержимое: `Ext/ManagerModule.bsl` →
  `object_module`, формы → `form_descriptor`/`form_data`/`form_module`, справка → `help`);
  `FilterCriteria/<Имя>.xml` → `filter_criteria` (+ тип через `_parse_type`). Ключи модели —
  `settings_storages`, `filter_criteria`; формы хранилища идут в `form_descriptors`/`common_forms`.
- Офлайн-замер (`<tmp>\opencode\t31_measure.py`): пульсар — `settings_storage 1`,
  `filter_criteria 1`, `form_descriptor 455` (= 442 объектов + 13 форм хранилища),
  `help 98` (= 82 общих форм + 16 хранилища); ssl — 3 одиночных макета названы `report_template`.

### Журнал итерации 14: Task 32 (ограждающий разбор XML — диагноз вместо падения)

- RED (проверен честно через `git stash`): на читателе до правки битый `Roles/Р/Ext/Rights.xml`
  давал необработанный `ParseError` в `parse_rights_xml:614`; тест это ловит.
- GREEN: обёртка `_read(path, kind, fn, *args)` (внутри `load_configuration_model`) — при
  `ET.ParseError` пишет `model["xml_diagnostics"]` записью `{"path","kind","error"}` и возвращает
  None, а манифест (`_opened`) создаётся только при успехе. Все точки `ET.parse` (было 11, после
  Task 29–31 стало 18) обёрнуты; поведение `skipped_files` и `load/scan.py` не менялось.
- Полный прогон `p1c`: `python scripts/run_tests.py` — тестов 83, неудачно 0 (+2 новых: 82 → 83).
- Ruling: правки reader.py задач 31 и 32 переплетены (Task 32 оборачивает точки разбора, которые
  добавил Task 31), поэтому они закоммичены одним коммитом `76680e1` (reader.py + два теста), а
  не двумя. Цена — слегка грубее `git bisect`; для репозитория без удалённой копии это приемлемо.

### Журнал итерации 14: Task 33 (паритет манифеста и раскладки, фикстура, evidence)

- Фикстура `p1c/examples/reader_gaps` (27 файлов) собрана генератором `<tmp>\opencode\gen_reader_gaps.py`
  и закоммичена в `p1c` (`5f0b7ea`): каталог с модулями и командой, общие коллекции, хранилище настроек,
  критерий отбора, одиночный макет, язык/подсистема/роль. Единственный непрочитанный файл —
  `Configuration.xml` (замер: `disk - manifest == {"Configuration.xml"}`).
- RED: `tests/test_manifest_gaps.py` (контур, новый) — до фикстуры и измерителя падал бы на отсутствии
  фикстуры; после фикстуры три теста зелёные (покрытие путей, `gaps() == {}`, новые классы по 1).
- Измеритель `scripts/manifest_gaps.py` закреплён (`GAP_KINDS` переименованы к фактическим классам
  манифеста: `common_command`, `command_group`, `common_picture`, `common_template`, `common_form`,
  `form_data` и т.д.) и закоммичен вместе с тестом (`5a8b15e`).
- Замер паритета на фикстуре: расхождения только (1) `object_module` 6 против 4 — layout.py считает
  командные модули в `Ext/*.bsl` (`scripts/layout.py:113`), известный квирк независимой линейки, его
  не менять; (2) классы содержимого (`common_command_module`, `common_picture_data`,
  `common_picture_content`, `common_template_data`, `help`) — их layout.py не считает, они только в
  манифесте; (3) `files` 27 против 26 — ровно `Configuration.xml`. Дескрипторы совпадают.
- Документы: `docs/план-оптимизации-p1c.md` — исправлена формулировка про `Commands/<Имя>.xml`
  (такого файла нет) и добавлен «Статус блока A к итерации 14»; `docs/evidence/tool-coverage.md` —
  статус итерации 14. Коммит `7274fd9`. Скан текстов: флаги только на прежних строках (цитаты имён
  корпуса), новые абзацы чистые.

### Журнал итерации 14: Task 34–38 (блок C: канонические неявные члены и арности конструкторов)

- Task 34 (канал владельца модуля): `module_owner(path)` в `metadata/module_paths.py` (карта
  папка→префикс объектного типа), `check_options_for` кладёт `opts["owner"]` для объектных модулей,
  `resolve_varref` (`semantic.py:598`) сверяется со свойствами владельца до глобальных имён. RED→GREEN:
  `tests/check_bsl/test_module_owner.py`. Коммит `5b88173`.
- Task 35 (`Движения`): тип `Движения` с `dynamic_members` в `builtin_type_model`; в канале владельца
  для `ДокументОбъект.*` ссылка `движения` возвращает `RType("Движения")`. RED→GREEN:
  `tests/check_bsl/test_dvizheniya.py`. Коммит `f162742`.
- Task 36 (`СообщениеПользователю`): запись в `EXTRA_TYPES` — `ctor (0,)`, свойства `Текст`/`Поле`,
  метод `Сообщить` (метод `УстановитьДанные` приходит из `TYPE_SIGNATURES`). RED→GREEN:
  `tests/check_bsl/test_soobshchenie.py`. Коммит `585933a`.
- Task 37 (мёртвый `TYPE_CONSTRUCTORS`): удалён из `data/platform_arities.py` и из генератора
  `scripts/extract_help_arities.py` (страницы типов без точки пропускаются с комментарием). Замер:
  `grep TYPE_CONSTRUCTORS` по `p1c` пуст, `hasattr(platform_arities, 'TYPE_CONSTRUCTORS') == False`.
  Коммит `49e12f4`.
- Task 38 (замер и evidence): `check.bsl` по `examples/managed_app` — 15 → 2 (было 11 scope + 1 ctor +
  3 method; осталось 2 неявных реквизита в модуле формы, канал владельца для форм не введён —
  отдельный зазор, вне плана). `builtin_type_model()`: 1914 типов, с `ctor_arities` 45 (44→45,
  +`СообщениеПользователю`), `dynamic_members` 6 (5→6, +`Движения`); `types_without_ctor` 1869,
  `types_without_properties` 1891. PREDICTIONS записаны до прогона в плане 14b (15 → меньше), факт
  совпал (15 → 2). `docs/evidence/tool-coverage.md` дополнен статусом блока C.
- Полный прогон `p1c`: `python scripts/run_tests.py` — тестов 86, неудачно 0 (84 → 86: +2 новых
  check_bsl-теста; TYPE_CONSTRUCTORS-задача тестов не добавляла).

### Журнал итерации 14: Task 39–42 (блок B: B4/B5/B6 и закрытие итерации)

- Task 39 (B4): `cli/runner.py:298` — `args.root` больше не затирается позиционным (`args.root or
  args.rest[0]`); `cmd_run` перехватывает `ValueError` от `detect_layout` и отдаёт `W.error` (код 2)
  по образцу `load/cli.py`. RED→GREEN: `tests/cli/test_runner_root.py`. Коммит `f90ae8f`.
- Task 40 (B5): `test/run.py` переведён на argparse (голый/неизвестный флаг — код 2, а не
  `IndexError`; `SystemExit` от argparse возвращается значением). Кейсы добавлены в
  `tests/test_run/test_run.py`. Коммит `2f296b5`.
- Task 41 (B6): `check/sdbl/cli.py` `cmd_fields` различает `--no-model` (свой текст) и отсутствие
  корня (прежний текст); успех — код 0 (`:313`). Кейс в `tests/check_sdbl/test_cli.py`. Коммит `4f22fa5`.
- Task 42 (закрытие итерации): роадмап `docs/план-оптимизации-p1c.md` — B4/B5/B6 и C1/C2/C4 отмечены
  «закрыто (итерация 14)», якоря B6 исправлены на `check/sdbl/cli.py:293`/`:313`, добавлены статусы
  блоков B и C, метрика G (`находки check.bsl` 15 → 2). Полный прогон `p1c` — тестов 87, неудачно 0
  (86 → 87: +`test_runner_root.py`).

## Final review (итерация 14, свежий ревьюер `general`)

Ревьюер прочитал планы, лиджер и все изменённые файлы; оба набора тестов зелёные (p1c 87/87,
контур 303/303). Critical — нет. По эффекту переоценено мной:

- `Final: fixed` #1 (канал владельца применялся и к модулю менеджера — ложные негативы):
  `check_options_for` гейтит `owner` по имени файла (`ObjectModule.bsl`/`RecordSetModule.bsl`).
  `tests/check_bsl/test_module_owner.py` RED→GREEN, suite 87/87. Коммит `c2cf830`.
- `Final: fixed` #2 (декларации команд из `<ChildObjects><Command>` не читались): помощник
  `_command_declarations` + слияние в блоке команд; docstring `parse_object_xml` исправлен.
  `tests/load/test_commands.py` RED→GREEN, suite 87/87. Коммит `00cad6c`.
- `Final: minor (deferred)` #3: `p1c.test.run` захватывает stdout/stderr подпроцесса, но не
  сохраняет в результат — для этого нужен новый ключ контракта `p1c.testresult/v1` (вне итерации);
  `capture_output=True` как минимум не даёт выводу платформы портить JSON.
- `Final: minor (deferred)` #4: канал владельца проверяется до коллекций/глобальных имён, а план
  (14b Task 34) описывал вставку после `global_enums` — фактический порядок ближе к теневому
  перекрытию имён 1С; оставлено как есть.
- `Final: minor (deferred)` #5: расхождение `--root` и позиционного корня не сообщается — уже
  зафиксировано рулингом Task 39 «`--root` побеждает молча».
- `Final: minor (deferred)` #6: текст `--no-model` у `fields` отличается от формулировки плана
  («поля недоступны без модели» vs «Поля берутся из модели метаданных…») — тест и код согласованы.
- `Final: Ruling` (Declined to judge): префикс-проверка `Движения` (`owner_type.name.lower().
  startswith("документобъект.")`) верна — `resolve_type` возвращает `.name` исходного регистра и
  корректно исключает `ДокументМенеджер`; принятие любого поля после `Движения.<Регистр>` через
  `dynamic_members` — замысел плана; `command_descriptor` в `GAP_KINDS` всегда 0 — соответствует
  замеру (файла `Commands/<Имя>.xml` нет).

## Пакет 8 (вне плана итерации 15): канал владельца на абсолютном пути

- Дефект: `module_owner` искал папку-якорь вида метаданных первым слева. Путь модуля приходит
  абсолютным в `p1c-run`, LSP и MCP (`cli/runner.py:199` передаёт `str(path)`), а в домашнем
  пути есть папка `Documents` — владелец становился `ДокументОбъект.<сегмент после чужого
  Documents>` (`ДокументОбъект.REA`, `ДокументОбъект.Пульсар`), тип не резолвился, канал
  владельца молчал. Для раскладки формы тот же класс ошибки закрыт замером 59; `module_owner`
  остался в прежнем виде.
- RED до правки: `tests/metadata/test_module_paths.py`, новый раздел (7) — 11 проверок, падение
  `AssertionError: владелец по абсолютному пути -> ДокументОбъект.Рабочие`. Второй RED после
  первой версии правки: относительные пути давали `None` (цикл не доходил до первого сегмента).
  GREEN после `range(len(parts) - 1, -1, -1)` и правила «за якорем стоит имя метаданных, а
  затем сегмент раскладки».
- Замер 62 (контур `cfg/ЭффективностьОтдела`, 8 модулей): `p1c-run` — 11 находок -> 2; пропало
  9 ложных `IDS_STX_VAR_NOTDECLARED` (`Сотрудники:11,17`; `ФактРаботы:6,12,18,19,21,24,25`),
  появилось 0; имена подтверждены метаданными контура (`Сотрудник`, `Часы`, `Ставка`,
  `ДатаПриёма`). `check.bsl.cli` (путь относительный) — 2 -> 2.
- Замер 60 (фикстуры, четыре условия: два разбора x две формы корня): `examples/designer_dump`
  — 5 находок, коды `IDS_STX_PROC_NOTDEFINED` и `IDS_STX_PROPERTYNOTFOUND`, правила `names` и
  `scope`, во всех четырёх условиях; `examples/managed_app` — 2 находки
  `IDS_STX_VAR_NOTDECLARED` (`НачалоПериода`, 6:28 и 20:49): база метрики G не изменилась.
  Прежние ожидания теста «с `antlr4` — 6, без него — 5`» и число KNOWN_BSL_FALLBACK_GAP
  пересняты: расхождение было следствием дефекта канала владельца, а не разбора.
- Замер 61 (корпус `corpora_pulsar`, гейт `check.bsl.cli`): CONTROL (HEAD `12b1713`) и FIXED
  (`823728a`) — по 32 547 находок, строки form 26 177 / common 4 010 / object 2 356 /
  command 4, `stats.files` 1 195, расхождений по кодам нет. Предсказания
  `iter15_m61_predictions.md` записаны до прогонов; отклонений от них нет; время прогонов
  77.1 с и 26.9 с — тепловой кэш чтений ОС.
- Побочный результат: базовая линия замера 55 (`p1c 3aa061f`) больше не база сравнения —
  33 047 -> 32 547, form 26 102 -> 26 177, common 4 452 -> 4 010, object 2 488 -> 2 356,
  command 5 -> 4. Task 49 сверяется с артефактами `m61_*`.
- Заодно закрыты пять проваленных проверок тестов (было 94 файла / 5 падений): блокирующий
  пакет в `tests/bsl/test_fallback.py` ставился в PYTHONPATH как сам пакет, а не как его
  каталог-контейнер, поэтому зависимость не перекрывалась и запасной путь никогда не
  проверялся на машине с установленной зависимостью. Ожидания `tests/cli/test_runner.py`
  пересняты замером 60.
- Гейты: `scripts/run_tests.py` — 94 файла / 0 падений; `--smoke` — 108 / 0;
  `tests/core/test_wording.py` — 444 файла, 0 попаданий; `tests/core/test_layers.py` — 16 слоёв;
  контур `python -m unittest discover -s tests` — 303/303. Коммит `p1c 823728a`.
- Открытым оставлено: та же форма риска у `module_kind_of` и `common_module_name` (сначала
  мерить, не чинить вслепую); пункты 5.3 про подавления прежних инвентарей имён,
  `runtime_codes.json` и 9 имён перечислений без перевода; первый запуск CI на машине
  партнёра. Номера замеров 60, 61 и 62 заняты этим пакетом, следующий свободный — 63.
- Артефакты замеров: `iter15_m61_predictions.md`, `m61_runner.py`, `m61_control_pulsar.json`,
  `m61_fixed_pulsar.json`, `m61_compare.py` и `m61_compare.log`, `m62_contour.py` и
  `m62_contour.log`, `m60_fixtures.py` и `m60_fixtures.log`, `m60_rootform.py` и
  `m60_rootform.log`. Контрольное рабочее дерево `wt_owner_control` удалено после замера.

### Журнал итерации 15: Task 45 (канал имён формы в `resolve_varref`, гейт G 2 → 0)

- Код (`p1c 0bdd76f`): `FORM_COMPOSITION` — фиксированный список шести имён §7.2 (`Элементы`,
  `ЭтаФорма`, `ВладелецФормы`, `Команды`, `ТекущиеДанные`, `Модифицированность`), свёрнутый
  `norm()`, в `src/p1c/metadata/model.py`; в `resolve_varref` после блока канала владельца и до
  `if low in self.ctx.collections:` ветка `options["form"]`: имя из `form.attrs` или из
  `FORM_COMPOSITION` считается объявленным и даёт `RType(None)`. Тип ни одного реквизита не строгий
  (строгий `Объект` — Task 47, канал методов типа формы — Task 48).
- Предсказания: `<tmp>\opencode\iter15_task45_predictions.md` (21 пункт, записан до прогонов, после
  прогона не переписан).
- RED честно: `<p1c>/tests/check_bsl/test_form_context.py` до правки — три падения (`IDS_STX_VAR_NOTDECLARED`
  на реквизитах три раза, на именах композиции шесть раз, `Модифицированность` объявленной); после
  правки 18 проверок / 0 падений. В тесте отдельно закреплено, что без `options["form"]` те же тексты
  дают находки (канал включает, а не подавляет всё), что локальная переменная цикла с именем
  `Элементы` сильнее канала (её тип `Число` даёт `IDS_STX_METHODNOTFOUND`), что канал не действует в
  объектном модуле, и что реквизит с именем коллекции (`Справочники`) разрешается как реквизит.
- Замер 63 (база и предвычисление, оба до кода, read-only): `m63_task45_base.py` и
  `m63_task45_base.summary.log` — база корпуса есть артефакт замера 61 `m61_fixed_pulsar.json`
  (32 547 находок, формная строка 26 177 в 442 файлах, `IDS_STX_VAR_NOTDECLARED` в формах 21 508),
  гейт фикстуры `m63_task45_gate.json` — 2 находки `НачалоПериода`;
  `m63_task45_precount.py` и `m63_task45_precount.summary.log` — предвычисление по индексу
  раскладок: канал закроет 20 980 находок, 69 файлов освободятся полностью, 360 сохранят находки,
  файлов с находками 760 → 691; коллизии имён раскладки с глобальными каналами — с коллекциями 0,
  с общими модулями 0, с глобальными функциями 92, с перечислениями 4, со свойствами глобального
  контекста 93.
- Гейт G закрыт артефактом `<tmp>\opencode\iter15_task45_gate.json`: `summary.count` 0 (база 2, обе
  `НачалоПериода` — `DataProcessors/ВыгрузкаЗатратCSV/Forms/ФормаВыгрузки/Ext/Form/Module.bsl` 6:28 и
  20:49), `stats.files` 8, выход CLI 0. Тот же прогон по `cfg/ЭффективностьОтдела`
  (`iter15_task45_contour.json`) — тоже 0; деревья фикстуры и контура байтово одинаковы (`diff -rq`
  пуст), поэтому вторая цифра независимым подтверждением не считается.
- Замер 64 (корпус после Task 45; `iter15_task45_pulsar.py` → `iter15_task45_pulsar.json` и
  `iter15_task45_pulsar.summary.log`; прогон `check.bsl.cli` по `corpora_pulsar` через python-обёртку,
  `stats.files` 1 195, в stderr «форм 520, модулей к сканированию 1 670», 27.6 с,
  returncode 1 — находки есть): итог 32 547 → 11 567, закрыто 20 980, и все
  закрытые — `IDS_STX_VAR_NOTDECLARED` в модулях формы; новых находок 0; файлов с находками 760 → 691
  (освободились полностью 69 — совпало с предвычислением замера 63), у 360 находок стало меньше, ни в
  одном файле находок не стало больше. Формная строка 26 177 → 5 197 (файлов 442 → 373); в ней
  изменился только `IDS_STX_VAR_NOTDECLARED` 21 508 → 528, остальные десять кодов равны базе
  (`IDS_STX_METHODNOTFOUND` 1 863, `IDS_STX_CTOR_NOTFOUND` 1 303, `IDS_STX_PROC_NOTDEFINED` 916,
  `IDS_STX_PROPERTYNOTFOUND` 258, `IDS_STX_TYPE_NOTDEFINED` 231, `IDS_STX_PARAMS_TOOMANY` 75,
  `BSL_CTX_NOT_AVAILABLE` 8, `BSL_CTX_CLIENT_ONLY` 7, `IDS_STX_PROC_DEFINED` 6,
  `IDS_STX_PARAMS_NOTENOUGH` 2). Строки не-форм равны базе: `common` 4 010 / 143 файла, `object`
  2 356 / 172, `command` 4 / 3. `by_rule`: `scope` 23 005 → 2 025, остальные правила равны;
  `by_grounding`: `official_code` 26 263 → 5 283, `own_code` 6 284 без изменений.
- Остаток формной строки подтверждён по артефакту: `IDS_STX_VAR_NOTDECLARED` 528 находок / 32 имени
  (верх остатка — `УсловноеОформление` 312, `КлючТекущегоВарианта` 50, `ТекущийЭлемент` 41,
  `ТолькоПросмотр` 23, `ВариантМодифицирован` 16, `ОписаниеОповещенияОЗакрытии` 15, `ИмяФормы` 14,
  `ПараметрыПриложения` 11), `IDS_STX_PROC_NOTDEFINED` 916 находок / 17 имён — равны базе; имён,
  появившихся в остатке, нет. Верх закрытых имён: `Элементы` 9 807, `Список` 247, `Отчет` 215,
  `ТаблДок` 198, `ЭтаФорма` 172, `ТЗОшибки` 118, `ПорядковыйНомерПерехода` 116, `ДеревоСодержания` 115,
  `КэшЗначений` 105, `НаборКонстант` 104 — то есть закрывают и имена композиции, и реквизиты раскладки.
- Отклонение от предсказания (единственное, арифметическое): итог корпуса предсказан 21 567,
  измерено 11 567; 32 547 − 20 980 = 11 567, то есть в предсказании закрытые находки прибавлены к
  базе вместо вычитания. Закрытые находки (20 980), формная строка (5 197 и 373 файла), остаток
  (528 / 32 и 916 / 17), исчезнувшие файлы (69) и итоговое число файлов (691) предсказаны точно.
  Предсказание «`IDS_STX_PROPERTYNOTFOUND` 258 и `IDS_STX_METHODNOTFOUND` 1 863 могут только
  уменьшиться» подтвердилось как «не изменились»: ни одна из 93 коллизий с именами глобального контекста
  не даёт находок этих кодов, потому что они возникают на обращении к члену, тип базы которого
  остаётся `None` (строгий тип даст Task 47), а не на самом имени.
- Оговорка к сводке замера 64 (артефакт не переписывался): строка лога «имена, пропавшие из остатка»
  печатает разность имён базы и имён остатка, то есть список закрытых имён, а не ожидаемый пустой
  список; содержательные проверки те же и корректны — остаток 528 / 32 равен базе, «имена, появившиеся
  в остатке» пуст.
- Прогоны: `python tests/check_bsl/test_form_context.py` — 18 / 0; `python scripts/run_tests.py` —
  95 файлов / 0 падений (было 94); `python scripts/run_tests.py core` — 11 / 0 (`test_layers.py`
  16 слоёв, `test_wording.py` без попаданий); контур `python -m unittest discover -s tests` — 303/303.
  План ожидал 89 файлов (88 после Task 44 плюс один новый); факт 95 — между Task 44 и Task 45 в `p1c`
  легли тесты промежуточных пакетов (имена кодов платформы, писатель индекса, матрица прогонов,
  LSP и CLI), лиджер-записей у них нет, их дописывает Task 50 (п. 3 плана: записи
  `Task 43` и `Task 44`–`Task 49`).
- Скан текстов: чистые `src/p1c/check/bsl/semantic.py`, `tests/check_bsl/test_form_context.py` и файл
  сообщения коммита; в `src/p1c/metadata/model.py` флаги GLUE только на прежних строках с латиницей в
  именах платформы, где латиница написана слитно с кириллицей, новых нет. В тесте тела модулей
  собираются помощником `module_text()`: escape-последовательности табуляции и перевода строки прямо в
  литералах склеивались с кириллицей и давали флаги GLUE.
- Открыто по итогам Task 45 и уходит в Task 50: (1) имена остатка — неявные члены модуля формы за
  пределами фиксированных шести (§7.2 и §2 «Нецели»), кандидаты на расширение списка —
  `УсловноеОформление`, `КлючТекущегоВарианта`, `ТекущийЭлемент`, `ТолькоПросмотр`, `ИмяФормы`,
  `ПараметрыПриложения`; записывать в §10 дизайн-дока. (2) В `src/p1c/data/platform_global_context.py`
  есть `КонецПериода`, но нет `НачалоПериода` — кандидат в `docs/evidence/p1c-data-defects.md`: в
  фикстуре находка закрыта каналом формы, а не глобальным контекстом, поэтому в замере дефект не
  проявился. (3) 93 имени раскладки, совпадающих со свойствами глобального контекста, теперь
  разрешаются как реквизиты — сверить с §10 (сузение подавления инвентаря имён).
- Номера замеров 63 и 64 заняты этой задачей (55–58 резервировал план итерации 15, 59–62 заняты
  ранее). Артефакты: `iter15_task45_predictions.md`, `iter15_task45_gate.json`,
  `iter15_task45_contour.json`, `iter15_task45_pulsar.py`, `iter15_task45_pulsar.json`,
  `iter15_task45_pulsar.log`, `iter15_task45_pulsar.err`, `iter15_task45_pulsar.summary.log`,
  `m63_task45_base.py` и `m63_task45_base.summary.log`, `m63_task45_precount.py` и
  `m63_task45_precount.summary.log`, `m63_task45_gate.json`, `iter15_task45_commit.txt` — все в
  `<tmp>\opencode\`. Следующий свободный номер замера — 65.

### Журнал итерации 15: Task 46 (стандартные свойства объектных типов в читателе)

- Код (`p1c a76a31f`; три файла: `src/p1c/load/reader.py` +37/−6, новый
  `tests/load/test_standard_attributes.py` +114, `tests/lsp/test_lsp.py` — две строки ожидания подсказки
  наведения): тип `STANDARD_ATTRIBUTES` расширен до `dict[str, dict[str, str | None]]`, вторым блоком
  добавлены стандартные свойства объектных типов — в `catalog`: `Ссылка`, `Родитель`, `Владелец`,
  `ДополнительныеСвойства`; в `document`: `Ссылка`; в `business_process`: `Ссылка`, `Стартован`,
  `Завершен`; в `task`: `Ссылка`, `Выполнена`, `Исполнитель`, `РольИсполнителя`, `БизнесПроцесс`,
  `Завершен` — все с типом значения `None`. В `_STD_METHODS` секций `catalog`/`object` и `document`/`object`
  добавлены `ПроверитьЗаполнение` (0..0, возврат `Булево`) и `УстановитьПометкуУдаления` (1..1, без
  возврата) с пустым `availability`; арности взяты из таблиц платформы (`platform_arities.py`), новых
  таблиц арностей не заводили. Имена видов `task` и `business_process` в `catalog` и `document` не
  перенесены. Свою таблицу свойств в `loader.py` не заводили (п. 4 плана): конструктор `_sig`
  (`loader.py:52-60`) `availability` не заполняет, а заполненный он дал бы `BSL_CTX_NOT_AVAILABLE` там,
  где его сейчас нет (замер 51: методов с `availability` у типов фикстуры 0). Таблицы платформы дают
  семействам объектных типов методы, но не дают их свойств — замер 49f: у `СправочникОбъект.<Имя>` 26
  методов и 0 свойств; пробник `m56_probe_model.log` подтверждает, что семейных типов в реестре типов
  корпусной модели нет вовсе и «типов с такими свойствами: 0». Записи применяются по-прежнему в
  `reader.py:1175-1178` — свойства ставятся перед атрибутами выгрузки в дескрипторе метаданных, а
  `build_type_model` разносит их на объектный и ссылочный тип: тестом зафиксировано, что `Ссылка` есть и
  у `СправочникСсылка.Сотрудники`; менеджерских типов правка не касается — у `СправочникМенеджер.Сотрудники`
  свойств 0 (тот же пробник). Ожидание подсказки наведения в `tests/lsp/test_lsp.py` переснято 6 → 10
  реквизитов: подсказка считает атрибуты дескриптора в том же списке, где реквизиты выгрузки.
- Предсказания: `<tmp>\opencode\iter15_m56_predictions.md` (25 пунктов, записаны до прогонов, после прогона
  не переписаны). Замер 56 зарезервирован планом итерации 15 (§7.5.16, Task 46).
- RED честно: новый тест на дереве HEAD (`git archive HEAD src tests examples` распакован в
  `<tmp>\opencode\m65c_red`, тест скопирован в него) падает ровно на трёх проверках — свойства объектных
  типов фикстуры (`получено ()`), `Ссылка` у ссылочного типа (`получено False`), арности методов и пустой
  `availability` (`получено ((), ())`); шесть остальных проверок до правки проходят. Артефакт
  `m65c_red.log` («неудачно: 3») — совпадает с предсказанием 23.
- Замер 56 (читает корпус `<corpora_pulsar>` только, `m56_task46_ownerkinds.py` →
  `m56_task46_ownerkinds.log`: модель корпуса через `load_configuration_model` и `build_type_model`, индекс
  форм Task 44, тексты модулей через `strip_preprocessor` с трёхзначной политикой `#Если` и `tokenize` из
  `p1c.bsl.parser`, сборка модели 8.9 с): записей форм 520 (предсказание 1 подтверждено), с объявленным
  раскладкой реквизитом `Объект` 131, и у всех 131 `obj_type` резолвится, «записей без ключа в индексе: 0»
  (предсказания 2 и 3 подтверждены). Обращения вида `Объект.<имя>` меряются в двух вариантах: А — только
  сам реквизит, Б — вместе с цепочками вида `ЭтаФорма.Объект.<имя>`. **Отклонение от предсказаний 5–7 —
  основа разбивки:** предсказано 1 954 обращения (база §6 дизайн-дока, повтор замера 4), измерено в
  варианте А 1 932 (разрешено 1 574, нерезолвлено 322, без резолвящегося типа 36), в варианте Б 2 055
  (1 624 / 334 / 97). Вариант Б даёт ровно предсказанные 334 нерезолвленных, вариант А — 322;
  предсказанного деления «1 933 / 21» нет: в формах без объявленного `Объект` измерено 36 обращений (А) и
  97 (Б). Файлов модулей прочитано 502, без файла модуля 18 (список в разделе H лога), модулей, где лексер
  текст не разобрал, — 1: `Documents/ГПН_ИнтегрированныеПланы/Forms/ФормаБюджет/Ext/Form/Module.bsl`
  («Недопустимый символ '#' (строка 1)»), форм с хотя бы одним обращением 70.
- Нерезолвленные имена (вариант Б): 11 имён, сумма 334 — `Ссылка` 286 (`СправочникОбъект` 223,
  `ДокументОбъект` 50, `ЗадачаОбъект` 9, `БизнесПроцессОбъект` 4), `Родитель` 14 (только справочник),
  `Стартован` 6 и `Завершен` 5 (только бизнес-процесс), `Выполнена` 5, `БизнесПроцесс` 4, `Исполнитель` 4,
  `Владелец` 4, `РольИсполнителя` 2 (только задача), плюс два имени вне §6: `Область` 3 (база `Строка`) и
  `Пустая` 1 (база `СправочникОбъект`) — **отклонение от предсказания 9** («имён вне списка не появится»).
  Оба — следствие правила разбивки варианта Б (любой идентификатор `Объект`, за которым стоит точка, а
  цепочка приписывается объектному типу владельца формы): корпусные строки
  `ТабличныйДокумент.Область("R1C" + к).Текст`
  (`Reports/ГПН_СравнениеВерсийСтруктурРезультатовСодержанияПроекта/Forms/ФормаОтчета/Ext/Form/Module.bsl:773,776,779`)
  и `ТекущиеДанные.Объект.Пустая()` (`Catalogs/Файлы/Forms/ФормаЭлемента/Ext/Form/Module.bsl:694`) — то
  есть обращение не к реквизиту формы, а к типу `Строка` и к методу `Пустая()`. Предсказанное
  распределение §6 (предсказание 8: `Ссылка` 287, `БизнесПроцесс` 6, `Ключ` 3, `Стартован` 3,
  `Завершен` 1, `ДополнительныеСвойства` 1, `Предопределенный` 2, `ПроверитьЗаполнение` 1,
  `УстановитьПометкуУдаления` 1) разошлось с измеренным на 1–5 обращений по каждому из этих имён: в
  варианте Б часть обращений уже разрешается (`Предопределенный` 2 из 2) либо не попадает в нерезолвленные
  (`Ключ` — 3 обращения, 0 нерезолвленных; `ДополнительныеСвойства`, `ПроверитьЗаполнение` и
  `УстановитьПометкуУдаления` — по одному обращению, 0 нерезолвленных). Имена §6 без нерезолвленных
  обращений: `Ключ`, `Предопределенный`, `ДополнительныеСвойства`, `ПроверитьЗаполнение`,
  `УстановитьПометкуУдаления` — **отклонение от предсказаний 16 и 17**: `Предопределенный` читатель
  объявляет уже сейчас, а у четырёх остальных у объектных типов корпуса нет носителя с нерезолвленным
  обращением.
- Предсказания 11–15 подтверждены: `Выполнена`, `Исполнитель` и `РольИсполнителя` только у вида владельца
  `task` (сумма 11 = измеренные 5 + 4 + 2), `Родитель` и `Владелец` только у форм владельцев вида
  `catalog`, `БизнесПроцесс` и `Стартован` только у `task` и `business_process`. **Отклонение от
  предсказания 13** (`Завершен` только у `business_process`): измерено именно так (5 обращений, все на
  `БизнесПроцессОбъект`), но п. 4 плана требует `БизнесПроцесс` и `Завершен` и в `task`, а проверка таблиц
  платформы даёт только семейно-независимую пару `("Completed", "Завершен")` (`platform_name_pairs.py:3985`;
  рядом `("Executed", "Выполнена")` :4980 и `("Started", "Стартован")` :8878) — `Завершен` в `task` записан
  по плану, подтверждение по Синтакс-Помощнику открыто и уходит в Task 50. Пары `РольИсполнителя` в
  `p1c/data` нет вовсе — записано как пробел данных. Разбивка по видам владельцев (вариант Б, все /
  нерезолвленные) даёт тождество предсказания 10 (сумма всех 2 055, нерезолвленных 334): `catalog` 939/231,
  `data_processor` 534/11, `document` 407/50, `business_process` 92/32, `settings_storage` 34/0,
  `(общая форма)` 19/3, `task` 18/7, `information_register` 12/0. Ключи читателя выбраны по разделу E лога:
  `СправочникОбъект` → `Ссылка`, `Родитель`, `Владелец` (плюс `ДополнительныеСвойства`), `ДокументОбъект` →
  `Ссылка`, `ЗадачаОбъект` → `Ссылка`, `Выполнена`, `БизнесПроцесс`, `Исполнитель`, `РольИсполнителя`
  (плюс `Завершен` по плану), `БизнесПроцессОбъект` → `Ссылка`, `Стартован`, `Завершен`.
- Проверка до правки (`m56_crosscheck_findings.py` → `m56_crosscheck_findings.log`, по артефакту Task 45
  `iter15_task45_pulsar.json`: 11 567 находок, 691 файл, `stats.files` 1 195): находок с именем члена из
  14 имён §6 — 517; по кодам `IDS_STX_METHODNOTFOUND` 398 (`Ссылка` 316, `ДополнительныеСвойства` 23,
  `Родитель` 22, `Исполнитель` 13, `Ключ` 9, `Владелец` 5, `Выполнена` 5, `РольИсполнителя` 3,
  `БизнесПроцесс` 1, `Завершен` 1) и `IDS_STX_VAR_NOTDECLARED` 119 (`ДополнительныеСвойства` 111,
  `Выполнена` 4, `Исполнитель` 2, `РольИсполнителя` 2). По типу базы: `ВыборкаИзРезультатаЗапроса` 239,
  `ДополнительныеСвойства` 111, `СправочникОбъект` 64, `СтрокаТаблицыЗначений` 43, `Неопределено` 35,
  `РегистрСведенийНаборЗаписей` 11, `Выполнена` 4, `Массив` 3, `ДокументОбъект` 3. Это и есть масштаб
  правки: на типизованных метаданных объектных базах (`СправочникОбъект.<Имя>`, `ДокументОбъект.<Имя>`)
  стоят только 67 находок — их Task 46 и закрывает; 239 находок на выборке из результата запроса и 43 на
  строке таблицы значений правка читателя не касается; `Ссылка` как член ссылочного типа базы — 0 находок;
  имён §6 без единой находки в артефакте — `Стартован`, `Предопределенный`, `ПроверитьЗаполнение`,
  `УстановитьПометкуУдаления`.
- Прогоны после правки: `python tests/load/test_standard_attributes.py` — 9 проверок / 0 падений;
  `python scripts/run_tests.py` — 96 файлов / 0 падений; `python scripts/run_tests.py core` — 11 / 0
  (`test_wording.py` без попаданий, `test_layers.py` 16 слоёв); контурный `python -m unittest discover -s
  tests` (запущен в каталоге контура) — 303/303 OK. План ожидал 90 файлов — расхождение объяснено в записи
  Task 45 (промежуточные пакеты без лиджер-записей дописывает Task 50). Первая попытка дать контурный
  прогон из `<p1c>` дала «NO TESTS RAN»: обёртка `run_tests.py` сама обходит `tests/`, а `unittest
  discover` нужно запускать в каталоге контура.
- Гейт фикстуры (замер 65, раздел А; `iter15_task46_gate.json`): `summary.count` 0, `stats` `{"files": 8}`,
  выход CLI 0, 1.1 с — предсказание 21 подтверждено (база Task 45 тоже 0).
- Замер 65 (корпус после Task 46; `iter15_task46_pulsar.py` → `iter15_task46_pulsar.json`,
  `iter15_task46_pulsar.summary.log`, `iter15_task46_pulsar.err`; прогон `check.bsl.cli` по
  `corpora_pulsar`, `stats.files` 1 195, stderr «форм 520, модулей к сканированию 1 670», 148.5 с,
  returncode 1 — находки есть): итог 11 567 → 11 427, закрыто 140, открытых 0; файлов с находками 691 →
  690; строки по видам модулей: `form` 5 197 → 5 165 (файлов 373 → 373), `common` 4 010 → 3 979
  (143 → 143), `object` 2 356 → 2 279 (172 → 171), `command` 4 / 3 без изменений. В формной строке
  изменился только `IDS_STX_METHODNOTFOUND` 1 863 → 1 831 (−32); остальные десять кодов равны базе
  (`IDS_STX_CTOR_NOTFOUND` 1 303, `IDS_STX_PROC_NOTDEFINED` 916, `IDS_STX_VAR_NOTDECLARED` 528,
  `IDS_STX_PROPERTYNOTFOUND` 258, `IDS_STX_TYPE_NOTDEFINED` 231, `IDS_STX_PARAMS_TOOMANY` 75,
  `BSL_CTX_NOT_AVAILABLE` 8, `BSL_CTX_CLIENT_ONLY` 7, `IDS_STX_PROC_DEFINED` 6, `IDS_STX_PARAMS_NOTENOUGH`
  2). `by_rule`: `names` 9 337 → 9 270, `scope` 2 025 → 1 952, `declarations` 10, `execution_context` 19,
  `parameters` 176 без изменений; `by_grounding`: `official_code` 5 283 → 5 210, `own_code` 6 284 → 6 217.
  Остатки формной строки равны базе: `IDS_STX_VAR_NOTDECLARED` 528 находок / 32 имени (пропавших имён 0,
  появившихся 0), `IDS_STX_PROC_NOTDEFINED` 916 / 17. Файл с находками, у которого находок стало 0, один —
  `Catalogs/ТомаХраненияФайлов/Ext/ObjectModule.bsl` (объектный модуль, было 2); у 39 файлов находок стало
  меньше, у 0 стало больше. Верх закрытых по файлам:
  `Catalogs/ДополнительныеОтчетыИОбработки/Ext/ObjectModule.bsl` 13, `Catalogs/Валюты/Ext/ObjectModule.bsl`
  8, `Tasks/ЗадачаИсполнителя/Ext/ObjectModule.bsl` 8, `Catalogs/ВариантыОтчетов/Ext/ObjectModule.bsl` 7,
  `CommonModules/ВариантыОтчетов/Ext/Module.bsl` 7,
  `SettingsStorages/ХранилищеВариантовОтчетов/Forms/СохранениеВариантаОтчета/Ext/Form/Module.bsl` 7.
- Отклонение от предсказаний 19–20 и от п. 5 плана («Task 46 сам по себе не закрывает и не создаёт
  находок … строки `METHODNOTFOUND` формной строки обязаны остаться 1 863; сдвиг разобрать»): закрыто 140,
  формная `IDS_STX_METHODNOTFOUND` стала 1 831. Предпосылка предсказания 20 подтверждена: тип базы `Объект`
  в модуле формы остаётся `RType(None)`, и ни одна закрытая находка не стоит на формном реквизите — остаток
  `IDS_STX_VAR_NOTDECLARED` 528 / 32 равен базе. Закрываются обращения, где тип базы известен из других
  каналов: правка добавила свойства и методы самим типам `СправочникОбъект.<Имя>`, `ДокументОбъект.<Имя>`,
  `ЗадачаОбъект.<Имя>` и `БизнесПроцессОбъект.<Имя>`, а к ним в корпусе обращаются уже типизованно.
  Ожидаемое «0 закрытых» ошибочно, потому что предсказание учитывало только канал формы, а разбивка замера
  64 (Task 45) не трогала строки `common` и `object`.
- Оговорка к сводке замера 65 (артефакт не переписывался): строка лога «вне правила пункта 22 (ожидаемо
  0): 73» печатает находки с голым именем — помощник замера 65 не отличает «базы нет» от «база не
  опознана», и они попадают в колонку базы как собственное имя. Содержательная проверка та же и корректна:
  построчный разбор (замер 65b) даёт, что вне правила не закрыто ничего.
- Замер 65b (построчный разбор всех 140 закрытых, `m65b_closed.py` → `m65b_closed.log`; сравнивает
  артефакты Task 45 и Task 46): закрытых 140, открытых 0; по паре (вид модуля, код) — `object`
  `IDS_STX_VAR_NOTDECLARED` 73, `form` `IDS_STX_METHODNOTFOUND` 32, `common` `IDS_STX_METHODNOTFOUND` 31,
  `object` `IDS_STX_METHODNOTFOUND` 4; по паре (код, имя) — `VAR_NOTDECLARED` `ДополнительныеСвойства` 65,
  `METHODNOTFOUND` `Ссылка` 45, `Родитель` 11, `ДополнительныеСвойства` 9, `VAR_NOTDECLARED` `Выполнена` 4,
  `METHODNOTFOUND` `Владелец` 2, `VAR_NOTDECLARED` `Исполнитель` 2 и `РольИсполнителя` 2. Все 73
  `VAR_NOTDECLARED` — голые имена в модулях объекта (разбивка `{'object': 73}`): владелец модуля теперь
  объявляет `ДополнительныеСвойства`, `Выполнена`, `Исполнитель` и `РольИсполнителя` (заземление
  `official_code`, правило `scope`). Все 67 `METHODNOTFOUND` стоят на типизованных базах
  `СправочникОбъект.<имя>` (64) и `ДокументОбъект.<имя>` (3) — ровно те 67, которые обещает перекрёстная
  проверка до правки. Закрытых имён вне набора, добавленного этой правкой, — 0, то есть правило пункта 22
  выполнен: правка читателя не закрыла ничего постороннего.
- Скан текстов (`iter15_task46_scan.log`): `src/p1c/load/reader.py` и файл сообщения коммита — `[ok]`; в
  `tests/lsp/test_lsp.py` 19 флагов и до правки, и после, новых нет (все прежние: escape-последовательность
  перевода строки, приклеенная к кириллице в литералах тел модулей, и литералы uri в проверках LSP); в новом
  тесте два флага склейки — та же домовая запись печати итога, где перевод строки написан `\n` перед
  кириллическим словом «неудачно»; она есть в восьми существующих тестовых файлах, поэтому тест ради
  сканера не выворачивался.
- Открыто по итогам Task 46 и уходит в Task 50: (1) `РольИсполнителя` в `p1c/data` нет
  (`platform_name_pairs.py` пары не даёт), а `Завершен` в `task` записан по плану, а не по измеренному
  носителю — сверить с Синтакс-Помощником и записать в `docs/evidence/p1c-data-defects.md`; (2) типы
  значений добавленных свойств — `None` по измеренному правилу (тип члена не замерен, поставленный тип дал
  бы находки на цепочках вида `Объект.Ссылка.<член>`), их заводит Task 47; (3) типы записей регистров в
  Task 46 не разбирались, а перекрёстная проверка даёт там 11 открытых находок `ДополнительныеСвойства` на
  `РегистрСведенийНаборЗаписей` — отдельный предмет; (4) `availability` у новых методов оставлен пустым
  сознательно (замер 51) — решение зафиксировать в дизайн-доке.
- Номера замеров 56 (резерв плана итерации 15 для Task 46), 65 и 65b заняты этой задачей (55 занят
  Task 44, 59–64 заняты ранее). Артефакты: `iter15_m56_predictions.md`, `m56_task46_ownerkinds.py` и
  `m56_task46_ownerkinds.log`, `m56_probe_model.py` и `m56_probe_model.log`, `m56_crosscheck_findings.py` и
  `m56_crosscheck_findings.log`, `iter15_task46_gate.json`, `iter15_task46_pulsar.py`,
  `iter15_task46_pulsar.json`, `iter15_task46_pulsar.log`, `iter15_task46_pulsar.err`,
  `iter15_task46_pulsar.summary.log`, `m65b_closed.py` и `m65b_closed.log`, `m65c_red.log` (распакованное
  дерево HEAD `m65c_red` остаётся), `m65c_runtests.log`, `m65c_core.log`, `iter15_task46_scan.log`,
  `iter15_task46_commit.txt` — все в `<tmp>\opencode\`. Следующий свободный номер замера — 66.

### Журнал итерации 15: Task 47 (шаги 1–2: замер 57 и отбор типов для строгого `Объект`)

- Что исполнено этой записью: шаги 1 и 2 плана Task 47 — офлайн-симуляция строгого `Объект` (замер **57**
  с подзамерами **57b, 57c, 57d, 57e, 57f, 57g, 57h**) и решение по остатку. Код в `p1c` не изменялся:
  `build_form_index` (`src/p1c/metadata/loader.py:217-255`) по-прежнему заполняет `obj_type` у любого
  резолвящегося `<Type>` без отбора, ветка канала формы в `resolve_varref`
  (`src/p1c/check/bsl/semantic.py:618-626`) по-прежнему возвращает `RType(None)`. Шаги 3 (RED-тесты), 4
  (правка), 5 (прогоны) и 6 (коммит) не исполнены; цена правки на прогонах — замер **66**, он не исполнен.
  Рабочее дерево `p1c` чистое, HEAD `a76a31f` (Task 46).
- Предсказания: `iter15_m57_predictions.md` (18 пунктов), `iter15_m57f_predictions.md` (10 пунктов и
  преамбула), `iter15_m57g_predictions.md` (5 пунктов) — записаны до прогонов, после прогонов не переписаны.
  **Отклонение процесса:** замеры 57b, 57c, 57d и 57e исполнены без отдельного файла предсказаний — то же
  нарушение, что отмечено дефектом F16 и записано в §7.5.16 для 49b, 49c, 49d и 50; ожидание 57h записано до
  прогона в докстринге `m57h_oblast_lines.py` (строки 10–15), по образцу замера 17. Их вывод принимается как
  метод измерения, а не как подтверждённое ожидание.
- Метод: модель читателя корпуса `<corpora_pulsar>` (сборка 16.3 с) поверх правки Task 46, индекс форм
  Task 44; тексты 502 модулей через `strip_preprocessor` (политика three-valued — консервативный союз ветвей
  `#Если`, как у проверщика) и `tokenize` из `p1c.bsl.parser`. `check_module_text` ни в одном замере этого
  блока не запускался, корпус только читался, по одному ключу за проход.
- Число, ради которого затевался замер: остаток обращений `Объект.<имя>` при строгом типе реквизита — **0**
  (вариант А: 1 932 обращения, разрешено 1 896, без резолвящегося типа 36) у всех 44 измеренных
  типов-владельцев. Оценка плана «≈47 из 334» не подтверждена: 334 и 322 — промахи до Task 46, их закрыла
  правка Task 46 у тех же типов.
- Второе звено цепочек — то, чего план не предсказал (пункт 9 предсказаний 57 «цепочки молчат» не
  подтверждён): из 305 цепочек `Объект.<имя>.<член>` 76 молчат (тип первого звена `None`), 229 проверяются и
  дают **139 промахов** `IDS_STX_PROPERTYNOTFOUND` (57e §Б). Из них 137 на типах `ТабличнаяЧасть.*`, 1 на
  `ЗадачаСсылка.ЗадачаИсполнителя` и 1 на `ПеречислениеСсылка.ВидыТранспортаСообщенийОбмена` (57f §В) —
  предсказание «все 139 на табличных частях» не подтверждено. Причина — неполнота `TABULAR_METHODS`
  (`loader.py:45`, 6 имён: `Вставить`, `Добавить`, `Количество`, `Найти`, `Очистить`, `Удалить`) при том, что
  корпус обращается к значениям табличных частями `НайтиСтроки`, `Выгрузить`, `Загрузить`, `Сортировать`,
  `НайтиПоИдентификатору`, `Индекс`, `Сдвинуть`. Это неполнота модели `p1c`, а не ошибки корпуса: раздел В
  57f печатает штатные вызовы 1С (`Объект.Назначение.Загрузить(НазначениеРодителя.Выгрузить());`,
  `Объект.Состав.НайтиСтроки(ПараметрыОтбора)`). Исправление таблицами вне Task 47: уходит в Task 50
  (`docs/evidence/p1c-data-defects.md`) и зафиксировано в §10 дизайн-дока.
- **Решение шага 2 (обязательная запись; никаких «включим и посмотрим на корпусе»).** `obj_type`
  заполняется, если семейство полного типа из `<Type>` входит в пять измеренных семейств
  (`СправочникОбъект`, `ДокументОбъект`, `ОбработкаОбъект`, `ЗадачаОбъект`, `БизнесПроцессОбъект`) **и**
  полный тип не входит в 13 типов с ненулевым остатком второго звена: `СправочникОбъект.ГруппыВнешнихПользователей`,
  `СправочникОбъект.ГруппыДоступа`, `СправочникОбъект.ГруппыПользователей`,
  `СправочникОбъект.ДополнительныеОтчетыИОбработки`, `СправочникОбъект.Календари`,
  `СправочникОбъект.СценарииОбменовДанными`, `СправочникОбъект.ШаблоныСообщений`,
  `ДокументОбъект.ГПН_СтруктураРезультатовWBS`, `ОбработкаОбъект.ОписаниеОбработчиковОбновления`,
  `ОбработкаОбъект.ПомощникИнтерактивногоОбменаДанными`, `ОбработкаОбъект.СопоставлениеОбъектовИнформационныхБаз`,
  `ОбработкаОбъект.ЗагрузкаКурсовВалют`, `БизнесПроцессОбъект.Задание`. Сумма их остатков — ровно 139
  (56 + 26 + 5 + 7 + 5 + 5 + 4 + 7 + 1 + 11 + 3 + 6 + 3), то есть гейт снимает весь измеренный остаток
  второго звена. Whitelist из 31 измеренного полного имени отвергнут: фикстурные типы шага 3
  `СправочникОбъект.Сотрудники` и `ОбработкаОбъект.ВыгрузкаЗатратCSV` в реестре корпуса отсутствуют (57f §Д)
  и по корпусной мерке остались бы без типа, что противоречит шагу 3. Типы вне пяти семейств (`Строка` в 9
  формах, `ДокументСсылка.ГПН_ИнтегрированныеПланы`, `ПланВидовХарактеристикОбъект.ОбъектыАдресацииЗадач`)
  остаются с `obj_type is None`: их остаток не измерен ни на одном звене (§12 п.3). Цена по индексу корпуса:
  `obj_type` заполняется у 101 формы из 131 и остаётся `None` у 30 (причины невключения: 389 записей без
  объявленного `Объект`, 19 форм deny-типов, 9 + 1 + 1 форм вне семейств); обращений варианта А с типом
  1 043, без типа 853 (57f §Б, 57g §А/§В). Арностных находок 0 и ни одного метода с заполненным
  `availability` у 76 типов-владельцев (57d §А/§Б) — потолок `BSL_CTX_NOT_AVAILABLE` 8/7 гейта Task 49 этим
  каналом не двигается. 29 включаемых типов без измеренных обращений безопасны на этом корпусе тривиально: у
  них нет ни одного обращения варианта А, а значит и цепочек нет (57f §Е, 57g §В: 60 включаемых типов =
  31 измеренный + 29 без обращений).
- Дефекты этого блока замеров (номера продолжаются после F17): **F18** — раздел В замера 57f печатает промахи
  по именам второго звена только по выборке 60 строк корпуса: сумма его чисел 44 вместо 139, и две строки с
  именем `Пустая` лежат за пределами напечатанного списка; распределение имён в документы переносится как
  состав имён, а не как доли 139. **F19** — первый прогон 57h дал в разделе В «реквизит `Объект` не объявлен»
  для всех трёх раскладок: помощник искал имя реквизита в дочернем теге `<Name>`, а эта выгрузка пишет его
  атрибутом тега (`<Attribute name="Объект" id="1">`) — та же форма ошибки, что у F10 и F14; раздел В
  перегенерирован, разделы А, Б и Г оба прогона дают одно и то же (`m57h_oblast_lines.first.log` сохранён).
  **F20** — строка «всего обращений: 3223» в 57d §Б базы в логе не имеет и не сопоставима ни с 1 896
  (вариант А), ни с 2 055 (вариант Б); выводы 57d держатся на нулевых счётчиках и на 1 896. **F21** — 57c §Д
  искал подстроку `Объект.Область` / `Объект.Пустая`, не требуя точки перед именем, и дал 2 ложные строки из 7
  (`CommonModules/ВерсионированиеОбъектов/Ext/Module.bsl:1388` и `:1390`, реальная база `СсылкаНаОбъект`).
  Отдельно о базе, а не о дефекте: 57 §Г насчитывает 309 цепочек, потому что считает их по всем 520 записям
  индекса и до фильтра «модуль без обращений», а 57e — 305 только по формам с резолвящимся `obj_type` и
  читаемым модулем; 4 различающиеся цепочки не печатает ни один артефакт.
- Исправление прежней записи (Task 46): она объясняла три нерезолвленных `Объект.Область` строками
  `ТабличныйДокумент.Область("R1C" + к).Текст` из `Reports/ГПН_СравнениеВерсийСтруктурРезультатовСодержанияПроекта/Forms/ФормаОтчета/Ext/Form/Module.bsl:773,776,779`.
  57h §Г и 57c §Г показывают: в этих строках имени `Объект` нет вовсе, вхождений `.Объект.Область` в файле 0.
  Подлинные строки — `CommonForms/СравнениеТабличныхДокументов/Ext/Form/Module.bsl:793, 799, 805`
  (`ТабДокПриемник.Объект.Область(…)`), и у раскладки этой формы `<Type>` реквизита `Объект` = `xs:string`
  (тип `Строка`) — поэтому форма гейтом не включается и промах по имени `Область` на строгом канале не
  возникает. Второе обращение `Пустая`
  (`DataProcessors/РаботаСФайлами/Forms/ПрисоединенныйФайл/Ext/Form/Module.bsl:637`) замеры 57 и 57b не
  видели: у этой раскладки реквизит `Объект` не объявлен, а они считают только формы с резолвящимся
  `obj_type` (база 57h шире — все 502 модуля).
- Что обязан сделать шаг 4: в `build_form_index` не заполнять `obj_type` вне пяти семейств и для 13
  невключаемых имён (решение — по семействам плюс список невключаемых, не whitelist); в `resolve_varref` при
  `low == norm("Объект")` и незаполненном `obj_type` возвращать `RType(form.obj_type)`, иначе `RType(None)`
  как сейчас. Порядок каналов не меняется (Task 45 уже ставит канал формы раньше `ctx.global_functions`).
  Шаг 3 (RED) и шаг 5 (тесты, контур 303/303, гейт фикстуры `summary.count 0`, корпусной прогон
  `iter15_task47_pulsar.json` — замер 66) не исполнены; предсказания 57 (пункты 11–16) и 57f (пункты 9–10)
  относятся именно к этим прогонам и пока не подтверждены.
- Документы: в дизайн-доке `docs/superpowers/specs/2026-10-31-iteraciya-15-formnyj-kontekst-design.md`
  написан новый §7.5.17 (замеры 57–57h поштучно: скрипт, предсказания, лог, «подтверждено / не подтверждено»
  с базой подсчёта, отклонение метода 309 против 305, дефекты F18–F21, «что решено» и «следствие для плана») и
  переписан абзац нумерации замеров в конце §7.5.16: 55 исполнен (Task 44), 56 исполнен (Task 46), 57 и
  57b–57h исполнены этой записью, 58 зарезервирован за Task 49, 59–65 и 65b заняты ранее, 66 закреплён за
  корпусным прогоном Task 47 и не исполнен, следующий свободный — 67. Исправлен пункт 4 «Итога этих замеров
  для плана» §7.5.16: он ссылался на «замер остатка (замер 55)», тогда как 55 — пересъёмка базовой линии
  Task 44, а остаток меряет замер 57. Строки 142–144 §4.1 сверены с §7.5.17: строке 143 добавлены цитаты
  57b §Д и 57g §Б, строка 144 дополнена двумя оставшимися типами промахов и оговоркой F18. В §10 расширена
  строка о `TABULAR_METHODS`: было «отсутствие `Итог` / `НайтиСтроки`», стало — семь измеренных имён с
  явной пометкой, что `Итог` в Task 47 заново не измерялось, и ценой пробела 139 промахов. В плане Task 47
  добавлен пункт «Решение шага 2» с измеренным решением и ценой.
- Скан текстов трёх изменённых документов (`t47_scan_docs.py` на обёртке
  `<tmp>\opencode\scan_texts.py`, четыре отметки: склейка латиницы с кириллицей, CJK, абсолютные пути,
  англицызмы; сверка мультимножеством по содержимому строк с базой HEAD): дизайн-док — 2 022 строки в базе
  и 2 412 сейчас, флагов 0 и 0; план — 188 и 189 строки, флагов 0 и 0; этот лиджер — 2 247 и 2 371 строки,
  флагов 13 и 13, новых и снятых нет (прежние 13 — цитаты имён платформы и корпуса до заголовка Task 47).
  Первый проход скана нашёл в новом §7.5.17 одно запрещённое домовой отметкой англицызмов английское слово
  (название помощника разбора цепочек в абзаце о замере 57e, написанное заодно без пробела после точки с
  запятой) — заменено на русское «помощник» до итогового прохода. В обёртку
  добавлены два узких исключения VERBATIM для подлинных смешанных имён метаданных корпуса,
  `ГПН_СтруктураРезультатовWBS` и `ХарактеристикиWBS`: каталог `Documents/ГПН_СтруктураРезультатовWBS`
  сверен обходом `rglob` по `<corpora_pulsar>`, имя `ХарактеристикиWBS` сверено чтением
  `Documents/ГПН_СтруктураРезультатовWBS/Forms/ФормаДокумента/Ext/Form.xml`; исключение вырезает только эти
  два токена и не ослабляет проверку остального текста. Ни CJK, ни абсолютных путей в трёх документах нет.
- Номера замеров: **57** и подзамеры **57b, 57c, 57d, 57e, 57f, 57g, 57h** заняты этой записью (55 занят
  Task 44, 56 — Task 46, 58 зарезервирован за Task 49, 59–64, 65 и 65b заняты ранее). **66** закреплён за
  корпусным прогоном Task 47 после правки кода и не исполнен. Артефакты (все в `<tmp>\opencode\`):
  `iter15_m57_predictions.md`, `m57_task47_strict.py`, `m57_task47_strict.log`, `m57b_probe_types.py`,
  `m57b_probe_types.log`, `m57c_prior_artifacts.py`, `m57c_prior_artifacts.log`, `m57d_arity_probe.py`,
  `m57d_arity_probe.log`, `m57e_chain_residual.py`, `m57e_chain_residual.log`, `iter15_m57f_predictions.md`,
  `m57f_gate_types.py`, `m57f_gate_types.log`, `m57f_gate_types.stdout.log`, `m57f_gate_types.err`,
  `iter15_m57g_predictions.md`, `m57g_gate_forms.py`, `m57g_gate_forms.log`, `m57g_gate_forms.err`,
  `m57h_oblast_lines.py`, `m57h_oblast_lines.first.log`, `m57h_oblast_lines.log`, `m57h_run.log`.
  Следующий свободный номер замера — **67**.

### Журнал итерации 15: Task 47 (шаги 3–6: RED-тесты, правка кода, прогоны, замеры 66 и 66b, коммит `p1c 688f9b7`)

- **Что исполнено этой записью.** Шаги 3 (RED-тесты), 4 (правка), 5 (прогоны) и 6 (коммит) плана
  Task 47; шаги 1–2 той же задачи записаны предыдущей записью. Код в `p1c` закоммичен — `688f9b7`
  (база `a76a31f`), 4 файла, +241/−9: `src/p1c/metadata/loader.py` (комментарий гейта 47–67,
  `FORM_OBJ_TYPE_FAMILIES` 68–70 — пять семейств, `FORM_OBJ_TYPE_DENY` 73–81 — 13 полных типов,
  помощник `form_obj_type_ok` 84–94, условие в `build_form_index` 296–298, при этом `attrs` реквизита
  пишется до проверки гейта — `loader.py:295`), `src/p1c/check/bsl/semantic.py` (канал формы в
  `resolve_varref` (`semantic.py:600`): комментарий 618–629 и
  `return RType(form.obj_type if low == norm("Объект") else None)` — 631) и два теста, написанных
  **до** правки: раздел (8) `tests/metadata/test_form_index.py` (строки 201–273, 60 проверок) и
  раздел (9) `tests/check_bsl/test_form_context.py` (строки 134–183, 33 проверки). Имя `Объект`
  остаётся объявленным в `attrs` при любом типе: без этого модуль формы вернулся бы к
  `IDS_STX_VAR_NOTDECLARED`, и предсказание 57 п.14 было бы нарушено. Пуша нет (разрешения на пуш не
  выдавалось), дерево `p1c` после коммита чистое.
- **RED до правки** (тесты добавлены в рабочее дерево раньше правки `build_form_index` и
  `resolve_varref`): `iter15_task47_red_form_index.log` — 44 `[ok]`, 16 `[FAIL]`, «ПРОВАЛЕН: 16» из 60
  (14 падений — отсутствие констант гейта, помощника и самих решений гейта, которых на том дереве нет
  вовсе, и 2 падения — `obj_type` записей формы невключаемого типа и строчного `<Type>`);
  `iter15_task47_red_form_context.log` — 3 падения из 33 (отсутствующий член строгого типа, он же
  вызовом, и второе звено цепочки). **Отклонение от предсказания 57 п.17:** там ожидалось одно падение
  в `test_form_context.py` и «только проверка `obj_type is None`» в `test_form_index.py`; измерено 3 и
  16. Лог RED сохранён как есть и после прогона не переписывается: в его лейблах остались числа
  подписей до их исправления (F24).
- **GREEN после правки (шаг 5):** `iter15_task47_green2_form_index.log` — 60 `[ok]`;
  `iter15_task47_green2_form_context.log` — 33 `[ok]`; `iter15_task47_run_tests2.log` — «тестов: 96,
  неудачно: 0» (план ожидал 90 файлов, §12 п.4 требует больше 87 — выполнено); `iter15_task47_core2.log`
  — 11/0; `iter15_task47_contour2.log` — «Ran 303 tests in 33.667s / OK»; гейт фикстуры
  `iter15_task47_gate.json` — returncode 0, `stats {"files": 8}`, `summary.count 0` (первый проход —
  `iter15_task47_gate_first.json`). Предсказание 57 п.16 (96/0, core 11/0, контур 303/303) подтверждено
  ровно этими числами; 57 п.11 (гейт фикстуры 0 при `{"files": 8}`) и 57f п.9 (фикстурные типы
  `СправочникОбъект.Сотрудники` и `ОбработкаОбъект.ВыгрузкаЗатратCSV` попадают в гейт по семействам)
  подтверждены прогоном фикстуры на дереве с гейтом.
- **Замер 66 — корпусный прогон после правки.** Скрипт `iter15_task47_pulsar.py` (обёртка
  `subprocess.run(..., timeout=1500)`, stdout/stderr бинарно в `.log` / `.err`), предсказания
  `iter15_m66_predictions.md` (19 пунктов разделов А–Д плюс раздел Е рисков и раздел Ж, записаны до
  прогона и после не переписаны), артефакты `iter15_task47_pulsar.json`, `iter15_task47_pulsar.log`,
  `iter15_task47_pulsar.err` и сводка `iter15_task47_pulsar.summary.log`. **База** — `iter15_task46_pulsar.json`
  (замер 65, запись Task 46): тот же корпус `<corpora_pulsar>` (сборка 16.3 с), те же опции, дерево `p1c`
  до правки Task 47, 11 427 находок; корпус только читался, один ключ за проход, прогонов на изменение
  корпуса нет. Прогон исполнен дважды: первый — на дереве до трёх правок текста шага 4 (артефакты
  сохранены как `iter15_task47_pulsar_first.json`, `.log`, `.err`, `.summary.log`), второй — на
  закоммиченном дереве `688f9b7` (канонические имена); `diff` двух сводок показывает только две строки
  длительностей (гейт фикстуры 1,3 → 2,2 с, корпус 104,0 → 95,6 с), все счётчики совпадают. Итог:
  **11 427 → 11 426** — закрыто 2 и открыта 1; файлов с находками 690 → 690; `stats {"files": 1 195}`;
  формная строка 5 165 → 5 164 (файлов 373), `IDS_STX_METHODNOTFOUND` 1 831 → 1 829,
  `IDS_STX_PROPERTYNOTFOUND` 258 → 259, девять прочих кодов формной строки равны базе (в том числе
  `BSL_CTX_NOT_AVAILABLE` 8, `BSL_CTX_CLIENT_ONLY` 7 и `IDS_STX_PROC_DEFINED` 6 — потолок гейта Task 49
  не двинулся); `by_rule names` 9 270 → 9 269, `by_grounding own_code` 6 217 → 6 216, `official_code`
  5 210 равен; остатки по именам 528/32 и 916/17 равны базе. Отклонений от предсказаний 66 — семь
  пунктов (3, 6, 7, 8, 9, 10 и 11), и все семь про один сдвиг в одном файле; разбор построчно — §7.5.18
  дизайн-дока. Кратко: закрытые — `IDS_STX_METHODNOTFOUND` `Неопределено.КодЯзыка`
  (`Catalogs/Валюты/Forms/ФормаЭлемента/Ext/Form/Module.bsl:179:18`) и `Неопределено.ПараметрыПрописи`
  (`182:17`);
  открытая — `IDS_STX_PROPERTYNOTFOUND` `СтрокаТабличнойЧасти.Представления.ПараметрыПрописи`
  (`182:17`). Одна процедура, строка 178 `НайденнаяСтрока = Объект.Представления.Добавить();`: до правки
  тип базы `None`, переменная оставалась `Неопределено`, и оба обращения давали `METHODNOTFOUND`; после
  правки тип строки табличной части разрешается и записывается в переменную присваиванием
  (`semantic.py:413-418`), поэтому 179 закрылась, а 182 стала находкой.
- **Риск раздела Е предсказаний, измеренный отдельно.** Мест вида `А = Объект;` в модулях формы — 4 в 4
  файлах (`Catalogs/ВнешниеПользователи`, `Catalogs/Календари`, `Catalogs/ПроизводственныеКалендари`,
  `Catalogs/ПрофилиГруппДоступа`, все `Forms/ФормаЭлемента/Ext/Form/Module.bsl`), изменений находок в
  них 0 (раздел И сводки). Реализовался другой пункт Е — звенья глубже `Объект.<имя>.<член>`
  (`Объект.<ТЧ>.Добавить().<колонка>`), которые офлайн-мерой 57e не измерялись.
- **Цена гейта после правки (раздел З сводки, измерена прямо по `build_form_index` на закоммиченном
  дереве, не симуляцией):** 520 записей индекса, 131 с объявленным `Объект`, `obj_type` заполнен у 101
  (предсказано 101), у 30 остаётся `None` — 0 форм без `<Type>`, 19 форм на 13 невключаемых типах и
  9 + 1 + 1 форм на трёх семействах вне измеренных; 389 форм без объявленного `Объект`; заполненные
  семейства — `ОбработкаОбъект` 65, `СправочникОбъект` 30, `ЗадачаОбъект` 4, `ДокументОбъект` 2;
  константы — 5 семейств и 13 невключаемых типов. Каждое число совпало с 57g §А/§В: гейт в коде стоит
  ровно в тех границах, в которых он был измерен до правки.
- **Замер 66b — построчная причина единственной открытой находки.** Скрипт `m66b_rowtype.py`,
  предсказания `iter15_m66b_predictions.md` (раздел А «прочитано до прогона, не замер» и 6 пунктов),
  логи `m66b_rowtype.log` (итоговый), `m66b_rowtype.first.log` (первый прогон, сохранён),
  `m66b_rowtype.stdout.log` (совпадает с итоговым побайтно) и пустой `m66b_rowtype.err.log` (0 b).
  Подтверждены пункты 1, 2, 4, 5 и 6; **пункт 3 не подтверждён числом:** предсказано ровно 2 объявления
  табличной части `Представления`, измерено 5 владельцев (`Валюты`, `ВариантыОтчетов`,
  `МакетыПечатныхФорм`, `ПредопределенныеВариантыОтчетов`, `ПредопределенныеВариантыОтчетовРасширений`).
  Числа и вывод — §7.5.18 дизайн-дока.
- **Судьба предсказаний 57 (пункты 11–16) и 57f (пункты 9–10) на этих прогонах:** подтверждены п.11,
  п.14, п.16 и 57f п.9; не подтверждены п.12 (итог корпуса и равенство формной строки базе), п.15
  (`PROPERTYNOTFOUND` не выше базы 258 — измерено 259), п.13 по форме (открытая находка стоит в модуле
  формы, но её база — локальная переменная с типом `СтрокаТабличнойЧасти.Представления`, а тип владельца
  `СправочникОбъект.Валюты` гейтом включён, хотя предсказание требовало невключаемого типа) и 57f п.10
  (формная строка не меняется). Решение шага 2 ни одно из этих отклонений не меняет: остаток первого
  звена остаётся нулевым (новых промахов первого звена в прогоне нет, `METHODNOTFOUND` снизился), а
  остаток второго звена по-прежнему стоит на невключаемых типах.
- **Дефекты этого блока (номера продолжаются после F21), подробный разбор — §7.5.18 дизайн-дока:**
  **F22** — тип табличной части в читателе ключуется только именем табличной части (`loader.py:171-183`),
  а `register_type` перекрывает реестр целой записью (`model.py:141-142`): 5 владельцев имени
  `Представления` делят один тип `СтрокаТабличнойЧасти.Представления`, колонки `Валюты` (`КодЯзыка`,
  `ПараметрыПрописи`) в нём потеряны, и это стоит 1 случайно закрытой и 1 открытой находки; исправление
  отложено в §10 и в очередь Task 50. **F23** — первый прогон 66b дал 0 колонок во всех пяти блоках,
  потому что помощник искал имя колонки в теге `<InternalInfo>`, а выгрузка пишет его как
  `<Attribute uuid="…"><Properties><Name>`; раздел Б перегенерирован, первый лог сохранён. **F24** — три
  подписи в текстах этой правки называли числа замера, которых нет ни в одном артефакте («5 / 25 / 3»
  вместо измеренных 4 / 26 / 1 в двух лейблах проверок раздела (8), «21 обращение» вместо 36 и 97 в
  подписи раздела (9), «57g раздел В» вместо разделов А и Б в комментарии гейта); исправлены до коммита и
  сверены с `m57e_chain_residual.log`, `m56_task46_ownerkinds.log`, `m57_task47_strict.log` и
  `m57g_gate_forms.log`. **F25** — прежняя запись (шаги 1–2) назвала обёртку скана
  `iter15_task47_scan_docs.py`; на диске она `t47_scan_docs.py`, и имя в той записи исправлено этой
  правкой (лог `iter15_task47_scan_docs.log` назван верно, артефакты не переименовывались). **F26** —
  тело сообщения коммита `688f9b7` перечислило отклонения только от пунктов 3, 8, 9, 10 и 11, хотя
  отклонились также пункты 6 и 7 (`by_rule` и `by_grounding`); сообщение коммита не переписывается,
  неполнота перечисления исправлена здесь и в §7.5.18. **F27** — текст этой же записи (абзац про
  скан) цитировал строку докстринга `type_model_to_json` с адресом ресурса, и из-за этого скан
  трёх документов дал новый флаг ABS-PATH: 13 отметок стало 14. Цитата убрана обёрткой
  `t47_ledger_fix_flag.py` до коммита документов, набор флагов вернулся к базе.
- **Скан текстов.** `iter15_task47_scan_p1c.log` (обёртка `t47_scan_p1c.py` на `<tmp>\opencode\scan_texts.py`,
  четыре отметки: склейка латиницы с кириллицей, CJK, абсолютные пути, англицызмы) по четырём
  изменённым файлам `p1c`: одна отметка ABS-PATH — `src/p1c/metadata/loader.py:317` (строка
  докстринга `type_model_to_json`, в которой написан адрес ресурса реестра; та же отметка есть
  и в HEAD), три отметки сняты домовым
  VERBATIM-списком подлинных смешанных имён метаданных корпуса (`ГПН_СтруктураРезультатовWBS`,
  `ВыгрузкаЗатратCSV`, `ХарактеристикиWBS`). База — те же файлы из HEAD (`t47_head_loader.py`,
  `t47_head_semantic.py`, `t47_head_test_form_index.py`, `t47_head_test_form_context.py`) и лог
  `iter15_task47_scan_p1c_head.log`: та же отметка на строке 265, то есть **новых отметок 0** — она
  существовала до Task 47 и не относится к этой правке. CJK и склеек нет; сообщение коммита
  `iter15_task47_commit.txt` — 58 строк, 0 символов вне ASCII (проверено отдельным проходом).
- **Коммит.** `688f9b7`, subject `check.bsl: strogij tip rekvizita Obekt iz Type raskladki (tolko po
  nulovomu ostatku zamera 57)`, тело — транслитерация ASCII, `Co-Authored-By: Claude Code
  <noreply@anthropic.com>`; в теле уже разобраны закрытые и открытая находка, цена гейта после правки,
  отказ от whitelist и нереализованный риск присваивания. Ничего не запушено.
- **Документы этой записи** (коммитятся в `effektivnost-otdela` этим же коммитом, база `ed1d6c6`): в
  дизайн-доке написан §7.5.18 (замеры 66 и 66b поштучно: скрипт, предсказания, артефакты, база,
  «подтверждено», семь отклонений с причиной, цена гейта после правки, дефекты F22–F27, «следствие для
  плана» и абзац нумерации замеров, перенесённый из §7.5.17 в конец §7.5.18); в §7.5.17 исправлена
  последняя ссылка (прежде — «проверка цены после правки … не исполнена»), в §4.1 добавлены две строки
  журнала решений (цена включения строгого `Объект` на прогонах и отложенный дефект ключа типов
  табличных частей), в §10 добавлен абзац о ключе типов табличных частей рядом с `TABULAR_METHODS`, в
  §11 дополнен риск строгого `Объект` измеренным шумом правки; в плане Task 47 флажки шагов остаются
  незакрытыми (домовая конвенция плана). Абзац нумерации дополнен номером 65c (он занят записью
  Task 46, прежде в нём не упоминался), и тот же абзац перевёрстан: после прошлой правки в нём
  оставались строки по 150–185 символов. Итог скана трёх документов после этих правок
  (`t47_scan_docs.py`, лог `iter15_task47_scan_docs.log`): дизайн-док 2 412 → 2 613 строк
  (флагов 0 → 0, новых 0), план 189 → 189 (0 → 0, новых 0), лиджер 2 371 → 2 538 (флагов
  13 → 13). До правки текста лиджер давал 14 флагов: новый флаг ABS-PATH дал именно текст этой
  записи, где я процитировал строку докстринга `type_model_to_json` с адресом ресурса, а домовая
  отметка путей реагирует на последовательность из латинской буквы, двоеточия и слэша — она
  возникает внутри этого адреса (сам дефект записан в абзаце дефектов выше, F27). Цитата убрана
  обёрткой `t47_ledger_fix_flag.py`, новый флаг снят, прежние 13 отметок остались на своих
  строках; лог скана до правок этого шага сохранён как `iter15_task47_scan_docs.steps12.log`.
- **Номера замеров:** **66** (корпусный прогон после правки) и **66b** (разбор его открытой находки)
  заняты этой записью; 55 занят Task 44, 56 — Task 46, 57 и 57b–57h — записью про шаги 1–2, 58
  зарезервирован за Task 49 (не исполнен), 59–64, 65, 65b и 65c заняты ранее. Следующий свободный номер
  замера — **67**. Артефакты этой записи (все в `<tmp>\opencode\`): `iter15_m66_predictions.md`,
  `iter15_task47_pulsar.py`, `iter15_task47_pulsar.json`, `iter15_task47_pulsar.log`,
  `iter15_task47_pulsar.err`, `iter15_task47_pulsar.summary.log`, `iter15_task47_gate.json`,
  `iter15_task47_pulsar_first.json`, `iter15_task47_pulsar_first.log`, `iter15_task47_pulsar_first.err`,
  `iter15_task47_pulsar_first.summary.log`, `iter15_task47_gate_first.json`,
  `iter15_task47_gate.log`, `iter15_task47_pulsar.stdout.log`, `iter15_task47_pulsar.stdout2.log`,
  `iter15_task47_pulsar.stderr2.log`, `iter15_m66b_predictions.md`,
  `m66b_rowtype.py`, `m66b_rowtype.log`, `m66b_rowtype.first.log`, `m66b_rowtype.stdout.log`,
  `m66b_rowtype.err.log`, `iter15_task47_red_form_index.log`, `iter15_task47_red_form_context.log`,
  `iter15_task47_green_form_index.log`, `iter15_task47_green_form_context.log`,
  `iter15_task47_green2_form_index.log`, `iter15_task47_green2_form_context.log`,
  `iter15_task47_run_tests.log`, `iter15_task47_run_tests2.log`, `iter15_task47_core2.log`,
  `iter15_task47_contour.log`, `iter15_task47_contour2.log`, `t47_scan_p1c.py`,
  `iter15_task47_scan_p1c.log`, `iter15_task47_scan_p1c_head.log`, `t47_head_loader.py`,
  `t47_head_semantic.py`, `t47_head_test_form_index.py`, `t47_head_test_form_context.py`,
  `iter15_task47_commit.txt`, `t47_docs_edit.py`, `t47_ledger_record.py`, `t47_ledger_fix_flag.py`,
  `t47_ledger_fix_counts.py`, `t47_scan_docs.py`,
  `iter15_task47_scan_docs.log`, `iter15_task47_scan_docs.steps12.log` (сохранённый лог скана трёх
  документов до правок этого шага) и `iter15_task47_docs_commit.txt`. Первые прогоны тестов и
  контура (`_green_`, `run_tests.log`, `contour.log`, `gate.log`) оставлены как есть; повторные
  прогоны с суффиксом `2` относятся к итоговому дереву.

### Журнал итерации 15: Task 48 (объединение 81 имени методов типа формы в кеш `TypeModel.form_methods` и VarRef-ветка `check_call`, замеры 67 и 68, коммит `p1c db6b424`)

- **Что исполнено этой записью.** Шаги 1–6 плана Task 48 (`docs/superpowers/plans/2026-10-31-iteraciya-15-formnyj-kontekst.md`) целиком: цена канала измерена **до** правки (шаг 1), причина правки (шаг 2), кеш `TypeModel.form_methods` (шаг 3), VarRef-ветка `check_call` (шаг 4), прогоны шага 5 (тесты, `run_tests.py`, контур, гейт фикстуры, корпусный прогон — замер 68), скан текстов и коммит (шаг 6). Код в `p1c` закоммичен — `db6b424` (база `688f9b7`), 3 файла, +217/−4: `src/p1c/metadata/model.py` (поле `form_methods` 141, `FORM_METHOD_TYPES` 360, помощник `form_methods_union` 363–411, `ctx.form_methods = form_methods_union(ctx)` 610, `CONTEXT_GROUPS` 749–753), `src/p1c/check/bsl/semantic.py` (`check_call` 690, VarRef-ветка 697, блок `ctx.global_functions` 716–721, ветка канала 722–738, `IDS_STX_PROC_NOTDEFINED` 739–740, `_check_availability` 878–895) и `tests/check_bsl/test_form_context.py` (раздел (10) — 32 проверки, написан до правки; всего в файле 65 проверок). Пуша нет: разрешения на пуш в этом разговоре не выдавалось; рабочее дерево `p1c` после коммита чистое.
- **Причина (шаг 2 плана).** Таблицы `TYPE_SIGNATURES` дают методы трёх формных типов по отдельности (`data/platform_arities.py`), а `<Variant>` в 520 записей `Ext/Form.xml` корпуса не встречается ни в одной раскладке (перепроверено разведкой `t48_variant_probe.py`: 0 вхождений элемента `<Variant>`, `<Variant `, `<Variant/>` и `<VariantList` во всех 520 записях; подстрока `Variant` в 127 файлах на 162 вхождения, и это другие токены (`v8:variant`, `v8:StandardPeriodVariant`, `VariantAppearance`)), поэтому модуль формы нельзя отнести ни к одному формному типу. Голые вызовы `Закрыть`, `РеквизитФормыВЗначение`, `ЗначениеВРеквизитФормы`, `ОповеститьОВыборе`, `ИзменитьРеквизиты`, `Открыта` и другие — после веток области видимости и `ctx.global_functions` — падали в `IDS_STX_PROC_NOTDEFINED`: в формной строке базовой линии 916 находок по 17 именам (артефакт `iter15_task47_pulsar.json`, дерево `688f9b7`).
- **Замер 67 — цена включения измерена до правки (шаг 1; §12 п.3 разрешает включать канал только по измеренному нулевому остатку).** Офлайн-симуляция того же конвейера CLI на модели выгрузки корпуса: скрипт `m67_union_channel.py` (440 строк), предсказания `iter15_m67_predictions.md` (11 пунктов, записаны до прогона и после не переписаны), артефакты `iter15_m67_base.json` (11 426 находок) и `iter15_m67_channel.json` (10 526), лог `m67_union_channel.log` (170 строк). Верность симуляции доказана: прогон без обёртки повторил артефакт Task 47 поштучно (закрыто 0, открыто 0, `stats` с `files` 1 195, та же подпись контекста `726583f1…29726`). С включённым каналом: 11 426 → 10 526, закрыто 900 по 12 именам и только по коду `IDS_STX_PROC_NOTDEFINED`, открыто 0; формная строка 5 164 → 4 264 в 373 → 293 файлах; остаток 16 находок по 5 именам; пять кодов §8 и четыре формных потолка не сдвинулись; файлов с находками 690 → 610; 8 имён-коллизий остались за `ctx.global_functions` вместе с его арностью. Объединение: 27 + 57 + 15 = 99 методов трёх типов, 81 различное имя, разногласие арностей у 2 имён. Разбор — §7.5.19 дизайн-дока.
- **RED до правки.** Раздел (10) на дереве до правки: 43 [ok] и 22 [fail] из 65 проверок файла (`iter15_task48_test_red.log`); все 22 падения — из раздела (10). Разложение падений: 3 проверки кеша (поля нет, 0 ключей вместо 81), 3 `Закрыть`, 4 `ПередЗакрытием`, 4 `ОповеститьОВыборе`, 6 проверок доступности по контексту процедуры, 2 проверки объединения для имени `ПроверитьЗаполнение`. В том же разделе 10 проверок прошли и до правки — они ждут ровно того, что делал прежний код: 4 проверки приоритета `ctx.global_functions`, 2 гейта по виду модуля, 2 про свою процедуру модуля формы, 2 про членские вызовы на своих таблицах.
- **GREEN после правки (шаг 5).** 65 [ok] / 0 падений (`iter15_task48_test_green.log` и повторный прогон на итоговом дереве `iter15_task48_green2_form_context.log`, по 8 872 b); `scripts/run_tests.py` — «тестов: 96, неудачно: 0» (`iter15_task48_runtests.log`); контур — «Ran 303 tests in 12.194s / OK» (`iter15_task48_contour.log`); гейт фикстуры `examples/managed_app` — returncode 0, `stats` с `files` 8, `summary` со счётом 0 (`iter15_task48_gate.json`).
- **Замер 68 — корпусный прогон после правки (шаг 5).** Скрипт `iter15_task48_pulsar.py` (14 517 b; обёртка `subprocess.run` с `timeout` 1500, stdout и stderr пишутся бинарно; корпус `<corpora_pulsar>` только на чтение, один ключ за проход, прогонов на изменение корпуса нет), предсказания `iter15_m68_predictions.md` (26 пунктов, записаны до прогона и после не переписаны), артефакты `iter15_task48_pulsar.json` (10 526 находок), `iter15_task48_pulsar.err` (117 b), `iter15_task48_gate.json` и сводка `iter15_task48_pulsar.summary.log`. База подсчёта №1 — `iter15_task47_pulsar.json` (замер 66: тот же корпус, те же опции CLI, один ключ, дерево до правки, 11 426 находок); база подсчёта №2 — артефакты замера 67. Итог: 11 426 → 10 526; закрыто 900 ровно по коду `IDS_STX_PROC_NOTDEFINED` и по тем же 12 именам (сумма 900); открыто 0 по всем кодам. Формная строка 5 164 → 4 264 в 373 → 293 файлах, `IDS_STX_PROC_NOTDEFINED` 916 → 16, десять прочих кодов формной строки равны базе; по корпусу `IDS_STX_PROC_NOTDEFINED` 992 → 92, пять кодов гейта §8 (12, 7, 10, 165, 11) и три крупных кода (5 533, 664, 960) без сдвигов; файлов с находками 690 → 610 (исчезло 80, стало меньше 205, стало больше 0). Сверка с офлайн-симуляцией: та же сумма, те же строки «вид модуля → находок/файлов», максимальная разность по каждому коду 0, одинаковые наборы закрытых имён. Разбор — §7.5.19.
- **Судьба предсказаний.** Замер 67 — подтверждены 11 пунктов из 11. Замер 68 — подтверждены 26 из 26: пункт 23 (заранее объявленное расхождение шага 5 плана) подтверждён измерением обеих причин, условный пункт 24 (случай, когда открылась бы хотя бы одна находка `BSL_CTX_NOT_AVAILABLE` или `IDS_STX_PARAMS_TOOMANY` в формной строке) не сработал — открытых находок нет вовсе. Непредсказанных сдвигов нет.
- **Отклонения от плана Task 48 (шаг 5), обе причины измерены до правки.** (1) План ждёт остаток формного `IDS_STX_PROC_NOTDEFINED` «22 вхождения» по списку из восьми имён, а сумма самого этого списка — 24; измерено 16 находок по 5 именам (`Активизировать` 8, `Открыть` 4, `УстановитьТекущийВариант` 2, `РазблокироватьДанныеФормыДляРедактирования` 1, `УстановитьТекущиеПользовательскиеНастройки` 1), и ни одного из этих имён в объединении 81 нет. `ОбновитьОтображениеДанных` (1) и `ОткрытьСправкуФормы` (1) входят в объединение и закрываются каналом; имени `ОбновитьИнтерфейс` в формной строке этого кода в базе нет вовсе — его обращения разрешает `ctx.global_functions`, поэтому 6 плановых вхождений в остатке быть не могло (замер 67 §В, замер 68 §Д). (2) `scripts/run_tests.py` даёт 96 файлов вместо ожидавшихся по плану 90 — расхождение объяснено записями Task 46 и Task 47, §12 п.4 требует больше 87. Флажки шагов плана не закрывались: план в этой задаче не правился.
- **Дефекты этого блока (номера продолжаются после F27), подробный разбор — §7.5.19 дизайн-дока:**
  - **F28** — раздел В скрипта замера 67 упал **до** обоих прогонов CLI: обращение к ключу `res`, которого у сырого артефакта прогона нет (`KeyError`). Логи того прогона сохранены как `m67_union_channel.attempt1.log` и `m67_union_channel.attempt1.stdout.log` (по 7 461 b); сверка логов двух прогонов даёт только две строки длительностей, все счётчики совпадают.
  - **F29** — раздел В скрипта замера 68 упал **уже после** обоих прогонов CLI: свод закрытых и открытых индексировался кортежем находки (файл, код, строка, колонка, текст), а печать JSON таких ключей не принимает. Исправлен только разбор по кодам; оба прогона CLI повторены теми же командами, артефакты первого прогона сохранены как есть с суффиксом `attempt1`.
  - **F30** — 6 флагов GLUE в новом разделе теста (`iter15_task48_scan_p1c.log`: `test_form_context.py:211, 280-283`): перевод строки прижимался к кириллическому слову в литерале помощника `cdir`. Снято тем же приёмом, что в `module_text` (перевод строки пишется отдельно от следующего слова), повторный скан — 0 флагов.
  - **F31** — обёртка сравнения флагов скана рабочего дерева с копией из HEAD: сначала `IndexError`, затем ложное «все флаги новые» (сравнение по одним только номерам строк, а правка сдвинула номера). Сравнение сделано по мультимножествам пар (паттерн, текст): 22 → 22, новых 0.
  - **F32** — сообщение коммита `p1c` было подготовлено с кириллическими словами (домовое правило — только ASCII-транслитерация); исправлено **до** коммита, проверка дала пустой список не-ASCII (`iter15_task48_commit.txt`, 93 строки, 7 320 b).
  - **F33** — два счёта в прежних текстах: список имён остатка в шаге 5 плана назван числом 22 при сумме списка 24, и запись Task 47 не перечислила в списке артефактов `t47_docs_commit_msg.py` (7 521 b) и копии документов до правок `t47_base_*.md` (277 293 / 64 148 / 296 614 b).
  - **F34** — адреса строк §5.4 и разделов 7.5 дизайн-дока сняты с дерева до Tasks 44–47 и после Task 48 расходятся с кодом (например `semantic.py:699-707` вместо 697 и 716–738). Пересъёмка одним проходом по всему документу отложена в §10; текущие адреса перечислены там же.
  - **F35** — помощник разведки `t48_probe_keys.py` упал на первой попытке: `most_common()` вызывался у простого словаря (`AttributeError`). Исправлено до получения вывода; артефакты прогонов не переписывались.
  - **F36** — в сообщении коммита `p1c` раздел (10) теста назван «из 33 проверок»: измерено 32 проверки раздела (10) и 65 проверок всего в файле (33 — число проверок разделов (0)–(9)). Ни одно число замеров от этого не меняется.
  - **F37** — длина лога замера 67 записана «171 строка» (§7.5.19 и эта запись), при измеренных
    170 переводах строки: `m67_union_channel.log` и `m67_union_channel.stdout.log` побайтово равны
    (по 16 477 b), `splitlines()` по каждому даёт 170. Число взято как оценка по размеру файла, а
    не измерено; исправлено **до** коммита документов. attempt1-логи — по 7 461 b и по 58 строк,
    что с текстом соглашалось и не правится.
  - **F38** — комментарии кода Task 48 (`semantic.py` 724–725 и `model.py` 356–357) утверждали, что
    `<Variant>` в раскладке «бывает только у 6 форм из 520», со ссылкой на §5.4, где сказано
    обратное («в 520 разобранных файлах `<Variant>` нет»). Числа не давал ни один замер; разведка
    `t48_variant_probe.py` измерила 0 вхождений элемента `<Variant>` в 520 `Ext/Form.xml` (подстрока
    `Variant` — 162 вхождения в 127 файлах: `v8:variant`, `v8:StandardPeriodVariant`,
    `<VariantAppearance>`). Дизайн-док прав; комментарии приведены к измеренному отдельным коммитом
    `p1c bf0ea78` (parent `db6b424`, 2 файла, +6/−4, только текст комментариев). После правки:
    `tests/check_bsl/test_form_context.py` — 0 падений (65 проверок), скан трёх файлов и сверка с
    копиями из HEAD `db6b424` по мультимножествам пар (паттерн, текст) — 22 → 22, новых 0.
  - **F39** — пункт о скане трёх документов (`t48_ledger_scan_bullet.py`) записал длины
    лиджера «2 538 → 2 456», смешав две базы подсчёта: 2 538 — все строки копии из HEAD
    (`splitlines()`), 2 456 — непустые строки рабочего дерева, и ни одна из них не названа;
    тысячи в том же пункте напечатаны без разделяющего пробела («2613 → 2809»), тогда как
    прежняя запись Task 47 пишет «2 412 → 2 613» (строки 2507–2508 лиджера). Исправлено
    до коммита документов: `t48_ledger_fix_len.py` (пересчёт по файлам на диске и копиям
    HEAD) и `t48_ledger_final.py` (перезапись пункта целиком), база названа явно и
    приводятся обе — с пустыми строками и без них.
  - **F40** — разница байтов рабочего дерева лиджера с копией HEAD записана в том же пункте
    как «26 853 b»: значение было верно в момент вставки пункта, но после правки F39 тот же
    файл отличается от той же копии на большую величину. Все три разницы пересняты
    `t48_ledger_final.py` после правок текста (для лиджера — итерациями до совпадения,
    потому что в эту разницу входит и длина пункта, и размер перечня артефактов: после    того как `t48_ledger_final.py` перезаполнил перечень, цифра разошлась — это поймал    его assert, и величина переснята `t48_ledger_diff_fix.py` внутри существующих    строк лиджера; расхождение в запись не перенесено.
- **Скан текстов (изменённый код `p1c`).** `python -I` со `scan_texts.py` по трём файлам: `model.py` — 22 флагов GLUE в рабочем дереве и те же 22 в копии из HEAD (`iter15_task48_scan_p1c2.log`, `iter15_task48_scan_p1c.log`, `iter15_task48_scan_p1c_head.log`), новых 0; `semantic.py` и `test_form_context.py` — 0 флагов (после снятия F30). После правки комментариев (F38) скан повторён по тем же трём файлам и снова сверен с копиями из HEAD по тем же мультимножествам: `model.py` 22 → 22, новых 0; `semantic.py` и `test_form_context.py` 0 → 0 (`iter15_task48_scan_p1c_fix.log`, `iter15_task48_scan_p1c_fix_head.log`).
- **Коммит кода.** В `p1c`: `db6b424` (parent `688f9b7`), 3 файла, +217/−4. Subject — `check.bsl: kanal metodov tipa formy (obedinenie 81 imeni v kesh TypeModel, dostupnost po kontekstu procedury)`; сообщение — ASCII-транслитерацией из файла `iter15_task48_commit.txt` через `git commit -F`, с атрибуцией `Co-Authored-By: Claude Code <noreply@anthropic.com>`. Пуша нет. Второй коммит — `bf0ea78` (parent `db6b424`), 2 файла, +6/−4, subject — `commentarii: v 520 raskladkah elementa Variant net (defekt F38)`, сообщение — ASCII-транслитерацией из файла `iter15_task48_comment_fix.txt` через `git commit -F`, та же атрибуция; рабочее дерево `p1c` после него чистое, пуша нет.
- **Документы этой записи.** Правки дизайн-дока `docs/superpowers/specs/2026-10-31-iteraciya-15-formnyj-kontekst-design.md`: §7.5.19 (замеры 67 и 68), абзац нумерации замеров перенесён из конца §7.5.18 в конец §7.5.19 и дополнен номерами 67 и 68, две новые строки журнала решений §4.1 (позиция ветки канала и измеренная цена включения; кеш 81 имени на встроенной модели и по русским именам типов), указывающий абзац в конце §5.4, исправленный первый риск §11 (16 находок по 5 именам вместо «22 вхождения 6 имён»), абзац в §10 об отложенной пересъёмке адресов строк (F34) — с исправленным числом строк файла `data/platform_arities.py` (22 188 вместо 22 189) и со словом «проверены» вместо «пересняты» (адресов в этом файле не переснимали, они сверены), предложение в §5.4 о перепроверке `<Variant>` разведкой (F38) и исправленная длина лога замера 67 в §7.5.19 (170 вместо 171, F37). План не правился.
- **Скан текстов трёх документов и их сверка с HEAD (шаг 12).** `python -I` со `scan_texts.py` по дизайн-доку, плану и лиджеру: 0 флагов в дизайн-доке, 0 в плане, 13 в лиджере (GLUE 11, ANG 2); вынесений `[verbatim-exception]` 49 — это дословные имена метаданных из списка сканера, флагами не считаются; записей `[ok]` 2 (`iter15_task48_scan_docs.log`, 5 322 b). Те же три документа просканированы копиями из HEAD `018a746` и сверены мультимножествами пар (паттерн, текст), а не номерами строк: счёты те же — 0, 0 и 13 (GLUE 11, ANG 2), новых флагов 0, исчезло 0 (`iter15_task48_scan_docs_head.log`, 4 570 b). Длины документов — все строки `splitlines()`, пустые включены: дизайн-док 2 613 → 2 809, план 189 (не правился), лиджер 2 538 → 2 591 до этого пункта и 2 592 после него; в лиджере той же базы без пустых строк — 2 418 → 2 469 и 2 470. Разницы байтов рабочего дерева с копиями HEAD (30 909 b, 189 b, 31 009 b) объясняются только переводами строки: в файлах на диске CR+LF, в копии HEAD — одиночные LF. Пункт и его правки — дефекты F39 и F40 этой записи.
- **Номера замеров.** **67** — офлайн-симуляция цены канала 81 имени до правки кода, **68** — корпусный прогон после правки: оба **исполнены** артефактами этой записи и §7.5.19. Номер **58** зарезервирован за Task 49 и не исполнен; следующий свободный номер — **69**. Разведка без номера и без файла предсказаний (её вывод замером не считается): `t48_red_baseline.py`, `t48_union_probe.py`, `t48_union_probe2.py`, `t48_union_probe3.py`, `t48_probe_keys.py` (последний обосновывает русские имена типов в §4.1) и `t48_variant_probe.py` (перепроверка утверждения §5.4, обосновывает F38).
- **Артефакты этой записи** (все в `<tmp>\opencode`, если не сказано иное). Замер 67: `m67_union_channel.py` (26 410 b), `m67_union_channel.log` (16 477 b), `m67_union_channel.stdout.log` (16 477 b), `m67_union_channel.attempt1.log` и `m67_union_channel.attempt1.stdout.log` (по 7 461 b), `iter15_m67_predictions.md` (18 389 b), `iter15_m67_base.json` (7 009 248 b), `iter15_m67_channel.json` (6 400 729 b). Замер 68: `iter15_task48_pulsar.py` (14 517 b), `iter15_m68_predictions.md` (11 471 b), `iter15_task48_pulsar.json` (6 400 757 b), `iter15_task48_pulsar.log` (0 b), `iter15_task48_pulsar.err` (117 b), `iter15_task48_pulsar.stdout.log` (7 075 b), `iter15_task48_pulsar.summary.log` (7 004 b), `iter15_task48_gate.json` (3 486 b), `iter15_task48_gate.log` (0 b) и артефакты первого прогона с суффиксом `attempt1` (`iter15_task48_pulsar.attempt1.json` 6 400 757 b, `.attempt1.log` 0 b, `.attempt1.err` 117 b, `.attempt1.stdout.log` 2 406 b, `iter15_task48_gate.attempt1.json` 3 486 b, `iter15_task48_gate.attempt1.log` 0 b). Тесты и прогоны шага 5: `iter15_task48_test_red.log` (10 196 b), `iter15_task48_test_green.log` (8 872 b), `iter15_task48_green2_form_context.log` (8 872 b), `iter15_task48_runtests.log` (3 711 b), `iter15_task48_contour.log` (4 801 b). Скан кода и коммит: `iter15_task48_scan_p1c.log` (1 014 b), `iter15_task48_scan_p1c_head.log` (1 419 b), `iter15_task48_scan_p1c2.log` (771 b), `iter15_task48_commit.txt` (7 320 b), копии из HEAD `t48_head_src_p1c_metadata_model.py` (49 920 b), `t48_head_src_p1c_check_bsl_semantic.py` (57 720 b), `t48_head_tests_check_bsl_test_form_context.py` (13 506 b). Разведка: `t48_red_baseline.py` (6 479 b), `t48_union_probe.py` (7 632 b), `t48_union_probe2.py` (3 334 b), `t48_union_probe3.py` (3 906 b), `t48_probe_keys.py` (4 916 b), `t48_probe_keys.log` (6 291 b), `t48_probe_keys.stdout.log` (6 335 b). Правки документов: `t48_docs_edit.py` (55 345 b) и его отдельная копия записи `t48_ledger_record.md` (19 843 b), копии документов до правок `t48_base_design.md` (309 603 b), `t48_base_plan.md` (64 337 b), `t48_base_progress.md` (322 046 b). Скан трёх документов и их сверка с HEAD (шаг 12): `t48_scan_docs.py` (5 478 b), `t48_ledger_scan_bullet.py` (12 152 b), `t48_ledger_final.py` (16 025 b), `t48_ledger_diff_fix.py` (11 036 b), `t48_ledger_fix_len.py` (5 113 b), `iter15_task48_scan_docs.log` (5 322 b), `iter15_task48_scan_docs_head.log` (4 570 b), копии из HEAD `t48_head_design.md` (306 990 b), `t48_head_plan.md` (64 148 b), `t48_head_progress.md` (319 508 b) и сообщение коммита документов `iter15_task48_docs_commit.txt` (4 109 b). Правщики документов: `t48_docs_fix1.py` (1 734 b), `t48_docs_fix2.py` (11 801 b). Разведка `<Variant>`: `t48_variant_probe.py` (2 791 b) и её лог `t48_variant_probe.log` (894 b). Правка комментариев кода (F38): `t48_code_fix_comment.py` (3 053 b), `t48_code_fix_comment2.py` (2 420 b), сообщение коммита `iter15_task48_comment_fix.txt` (1 813 b), скан и сверка `t48_scan_comment_fix.py` (4 215 b), `iter15_task48_scan_p1c_fix.log` (747 b), `iter15_task48_scan_p1c_fix_head.log` (1 467 b) и копии из HEAD `t48_head2_src_p1c_metadata_model.py.py` (54 425 b), `t48_head2_src_p1c_check_bsl_semantic.py.py` (59 408 b), `t48_head2_tests_check_bsl_test_form_context.py.py` (26 434 b).

### Журнал итерации 15: Task 43 (свортка `ё` в `norm()` после `lower()` и одинаковая нормализация на стороне записи и чтения ключей, написания `STANDARD_ATTRIBUTES`, замер 48, коммиты `p1c 3aa061f` и `docs 5a06ecc`; запись дописана записью Task 50)

- **Что исполнено этой записью и почему она дописывается задним числом.** Task 43 исполнен раньше, чем началась нумерация этого плана: сам план (строка 3 файла `docs/superpowers/plans/2026-10-31-iteraciya-15-formnyj-kontekst.md`) записал, что прежний план закрыл Task 29–42, а `Task 43` «исполнен коммитом `p1c 3aa061f` и в лиджер ещё не записан — его дописывает Task 50». Шаги задачи: замер 48 (есть ли ключи с `ё` в таблицах имён платформы, в пакете и в тестах), правка тела `norm()` и шести мест чтения ключей, написания стандартных реквизитов в читателе, раздел 8 теста `p1c/tests/check_bsl/test_scope.py` (написан до правки кода и падал), пересъёмка гейта фикстуры после правки, скан текстов изменённого кода, коммит кода и коммит документов. Пуша нет: разрешения на пуш в этом разговоре не выдавалось.
- **Причина дописывания (шаг 3 плана Task 50).** План требует дописать в `progress.md` `Task 43` (исполнен раньше плана: свортка `ё/е` после `lower()` в `p1c/src/p1c/core/names.py`, написания `STANDARD_ATTRIBUTES`, коммит `3aa061f`) и по одной записи на `Task 44`–`Task 49` с коммитом, числами гейта и результатом прогонов. Из семи задач плана в лиджере не хватало трёх записей — этой, Task 44 и Task 49; записи Task 45, Task 46, Task 47 (шаги 1–2 и шаги 3–6) и Task 48 закрывали свои задачи своими заметками.
- **Замер 48 — в таблицах имён платформы ключей с `ё` нет.** Скрипт `m48_yo_keys.py`, предсказания `iter15_m48_predictions.md` (7 пунктов, записаны до прогона и после не переписаны), лог `m48_yo_keys.log`. База подсчёта — три обхода дерева `3aa061f`: слой данных `p1c/src/p1c/data` (15 файлов `.py`), весь пакет `p1c/src/p1c` (99 файлов) и тесты `p1c/tests` (101 файл). Измерено: в слое данных 7 файлов с `ё`, 12 строк, 1 quoted-строка; в пакете 70 / 468 / 69; в тестах 87 / 503 / 261. Подтверждены пункты 1–4 (в таблицах имён платформы ключей с `ё` нет, единственная quoted-строка слоя данных — `src/p1c/data/pin.py:130`) и пункт 5 (`Проведен` в слое данных есть — `src/p1c/data/platform_vocab.py:173` и `src/p1c/data/platform_predefined.py:62`; написаний `Проведён` и `Предопределённый` нет). Не подтверждены пункты 6–7: вместо «10–40 файлов, база 26 файлов» в тестах измерено 87 файлов с `ё` и 261 quoted-строка, и это документальные строки и символьные классы регулярных выражений (`check/sdbl/checks.py`, `bsl/exports.py`, `cf/test_writer.py`); написаний `Проведён` и `Предопределённый` в тестах тоже нет — `tests/load/test_standard_attributes.py:33-34` проверяет `Проведен` и `Предопределенный`. Отдельно зафиксировано имя из набора искажённых символов в `src/p1c/data/platform_vocab.py:1573` (файл никем в пакете не импортируется; имя снято позже коммитом `94b97b1`, в этом тексте оно не воспроизводится). Разбор — §7.5.12 дизайн-дока.
- **Пересъёмка гейта фикстуры после правки (без номера замера).** Команда — `python -m p1c.check.bsl.cli check examples/managed_app --root examples/managed_app --format json`; артефакт `iter15_gate_task43.json` (stderr `iter15_gate_task43.err`), предсказания `iter15_gate_task43_predictions.md` (4 пункта, до прогона), разбор причины расхождения `task43_gate_probe.py`. Результат: returncode 0, `summary.count` 2, `by_rule` — `{'scope': 2}`, обе находки с `official_code`, `stats` с `files` 8, `skipped_rules` 3 (`os_compat`, `queries`, `tests`). Гейт — 2 находки до правки кода и 2 после: свортка гейт не двигает, как и предсказывали пункты 2–3. Расхождение: пункт 1 приписывал второй находке имя `КонецПериода` (позиция `20:49`), факт — обе находки об `НачалоПериода` (позиции `6:28` и `20:49`). Причина измерена разбором: асимметрия инвентаря имён платформы — `КонецПериода` в `PLATFORM_NAMES` есть, `НачалоПериода` в нём нет, поэтому `конецпериода` сидит и в `global_functions`, и в `global_properties` (типа возврата нет), а `началопериода` нет нигде, и `resolve_type('конецпериода')` отвечает `None`. Эксперимент разведки (все написания заменены тем же именем с дописанной латинской буквой) даёт ровно 4 находки `IDS_STX_VAR_NOTDECLARED` — `6:28`, `9:28`, `20:49`, `20:64`. Разбор — §7.5.13 дизайн-дока; та же асимметрия записана сегодня в §7.2 файла `docs/evidence/p1c-data-defects.md` с ценой на корпусе (0 из 32 547 и 0 из 10 526). Следствие для Task 45: база метрики G равна 2 и закрывается каналом имён формы, а сузение подавления инвентаря оставлено вне итерации (§10 дизайн-дока).
- **RED до правки.** Раздел 8 в `p1c/tests/check_bsl/test_scope.py` (5 проверок: переменная и процедура модуля формы, написанные через `ё`, читаются написанием через `е`) написан до правки `norm()` и падал (`task43_scope_red.log`; промежуточные прогоны того же раздела — `task43_scope_run.log` и `task43_scope_re.log`). Причина падения разобрана отдельно (`task43_scope_cause.py`): сторона записи ключа сворачивала `ё`, сторона чтения — нет.
- **GREEN после правки.** `python scripts/run_tests.py core` — «тестов: 10, неудачно: 0» (`task43_green.log`); полный набор p1c — «тестов: 87, неудачно: 0» (`task43_p1c_full.log` и повтор `task43_p1c_full2.log`; база подсчёта — печатаемое число равно числу тестовых файлов, в этих логах по 87 строк `[ok]`); контур `effektivnost-otdela` — `python -m unittest discover -s tests` дал «Ran 303 tests / OK» (`task43_contour_full.log` и повтор `task43_contour_full2.log`). Правки готовили помощники `task43_infer_patch.py` (лог `task43_infer.log`) и `task43_model_patch.py` (лог `task43_model.log`), diff по `check/bsl/semantic.py` сохранён как `task43_diff_semantic.txt`; похожие символы проверял замер без номера `task43_homoglyph.py` (лог `task43_homoglyph.log`).
- **Отступление, записанное в сообщении коммита.** Таблица символов препроцессора оставлена на `lower()`: на дереве `3aa061f` это `check/bsl/semantic.py:918` и `:921`, и их единственный читатель — `p1c/src/p1c/bsl/parser.py:513` (вызов `symbols.get(t, symbols.get(low))`). Перевод одной стороны на `norm()` дал бы промах по ключу, потому что таблица и читатель сворачивали бы имя по-разному.
- **Скан текстов (изменённый код `p1c`, 9 файлов).** Первый проход — `scan_p1c_task43.log`: 119 флагов (GLUE 110, ABS-PATH 9) и 4 файла без флагов; повторный проход после снятия реальных склеек — `scan_p1c_task43b.log`: 117 (GLUE 108, ABS-PATH 9), те же 4 файла без флагов. Сверка с копиями из HEAD (`task43_scan_baseline.py`, логи `task43_scan_baseline.log`, `task43_scan_baseline.data.txt` и `task43_scan_baseline2.log`): во всех файлах, кроме теста, флагов ровно столько же, сколько в копии HEAD (`core/names.py` 0/0, `check/bsl/semantic.py` 0/0, `check/bsl/infer.py` 0/0, `check/bsl/server.py` 4/4, `load/reader.py` 0/0, `lsp/lsp_server.py` 1/1, `metadata/model.py` 22/22, `metadata/module_paths.py` 4/4); в `tests/check_bsl/test_scope.py` — 68 в копии HEAD и 88 в рабочем дереве до снятия склеек, и в логе стоит строка `TOTAL new flags across the 8 changed source files: 20`. Разбор 20 новых совпадений (`task43_scan_scope.py`, лог `task43_scan_scope.log`): 18 из них — артефакты самого правила сканера на последовательностях переноса строки и табуляции внутри кириллических литералов, и только 2 — настоящие склейки кириллицы с латиницей (строки 171 и 177: в слове «написанием» латинская буква 0x61 стояла внутри кириллического слова; `task43_fix_glue.log` показывает подмену на кириллический код 0x430, встреч — 2). Снято скриптом `task43_fix_glue_test.py`, после чего сверка даёт 86 / 86 / 0 (`task43_scan_scope2.log`). Закоммиченное состояние перепроверено сегодня при дописывании этой записи (`t50_task43_scan_verify.py`): файл из `3aa061f` — 11 657 b, 191 строка, 86 флагов GLUE, из них 86 артефактов разбора и 0 настоящих склеек; родительское состояние `00cad6c` — 10 051 b, 171 строка, 68 флагов и тоже 0 настоящих склеек (`iter15_task43_scan_verify.log`). Итог по настоящим склейкам в новом коде — 0.
- **Коммит кода.** В `p1c`: `3aa061f` (parent `00cad6c`, 2026-11-01 06:01), 9 файлов, +117 / −83: `src/p1c/check/bsl/infer.py` (29), `src/p1c/check/bsl/semantic.py` (58), `src/p1c/check/bsl/server.py` (3), `src/p1c/core/names.py` (9), `src/p1c/load/reader.py` (11), `src/p1c/lsp/lsp_server.py` (2), `src/p1c/metadata/model.py` (63), `src/p1c/metadata/module_paths.py` (5) и `tests/check_bsl/test_scope.py` (20). Subject — `norm: svortka yo/ye idet posle lower(); storony zapisi i chteniya klyuchej odinakovie`; тело — ASCII-транслитерацией из файла `msg_p1c_task43.txt`, в нём отступление по символам препроцессора и строка проверки («provery: test_scope vse proverki OK; polnyj nabor testa: testov 87, neudachno 0; kontur effektivnost-otdela: Ran 303 tests, OK»). Рабочее дерево `p1c` после коммита чистое; пуша нет.
- **Документы этой записи.** Коммит документов `docs 5a06ecc` (2026-11-01 05:51): 1 файл — дизайн-док итерации 15, 149 вставок и 8 снятых строк; subject — ASCII-транслитерацией из `msg_doc_task43.txt`, в нём названы итог правки Task 43, замер 48, разбор замера 43 postfactum (65 модулей `CommonForms`, 4 852 находки, дефект F17), пересъёмка гейта фикстуры 2 → 2 и база подсчёта в §7.5.8. Скан документов того дня — `scan_doc_task43.log` и его повтор `scan_doc_task43b.log`. Порядок обратный обычному: коммит документов сделан на 10 минут раньше коммита кода (`3aa061f` — 06:01); отклонение зафиксировано этой записью. Закрытие дефекта записано сегодня в §7.1 файла `docs/evidence/p1c-data-defects.md` (запись Task 50).
- **Судьба предсказаний.** Замер 48: 7 пунктов, подтверждены 5, разошлись 6 и 7 (разобранные числа — §7.5.12). Пересъёмка гейта: 4 пункта, подтверждены 3, в том числе число находок 2 и его неизменность после правки; разошёлся пункт 1 — имя второй находки, и расхождение не затронуло ни одно число гейта. Оба файла предсказаний после прогонов не переписывались.
- **Отклонения процесса этой задачи (дефектных номеров не получили, исправлены на месте).** (1) Прежний текст §7.5.13 ссылался на файл `platform_names.json` «107 имён», которого в пакете нет; исправлено в том же коммите документов. (2) Коммит документов раньше коммита кода (см. пункт про документы). (3) Ошибка предсказания про `КонецПериода` — не опечатка счёта, а неверная атрибуция имени находки; разобрана §7.5.13 дизайн-дока и сегодня — §7.2 файла `docs/evidence/p1c-data-defects.md`.
- **Номера замеров.** **48** — ключи с `ё` в таблицах имён платформы, в пакете и в тестах: **исполнен** (`m48_yo_keys.py`, `m48_yo_keys.log`, `iter15_m48_predictions.md`). Пересъёмка гейта фикстуры после правки — без номера (артефакты `iter15_gate_task43*`), как и разведка похожих символов.
- **Артефакты этой записи** (все в `<tmp>\opencode`, если не сказано иное). Замер 48: `m48_yo_keys.py` (1 388 b), `m48_yo_keys.log` (7 668 b), `iter15_m48_predictions.md` (2 530 b). пересъёмка гейта фикстуры: `iter15_gate_task43.json` (4 746 b), `iter15_gate_task43.err` (111 b), `iter15_gate_task43_predictions.md` (2 875 b), `task43_gate_probe.py` (2 482 b), `task43_gate_probe.log` (1 791 b). прогоны тестов и контура: `task43_scope_red.log` (3 764 b), `task43_scope_run.log` (3 764 b), `task43_scope_re.log` (3 774 b), `task43_scope_cause.py` (2 214 b), `task43_scope_cause.log` (1 124 b), `task43_green.log` (405 b), `task43_p1c_full.log` (3 328 b), `task43_p1c_full2.log` (3 342 b), `task43_contour_full.log` (4 800 b), `task43_contour_full2.log` (4 800 b). помощники правки: `task43_infer_patch.py` (1 759 b), `task43_infer.log` (45 b), `task43_model_patch.py` (4 744 b), `task43_model.log` (100 b), `task43_diff_semantic.txt` (5 813 b), `task43_homoglyph.py` (1 298 b), `task43_homoglyph.log` (1 035 b), `task43_fix_glue_test.py` (643 b), `task43_fix_glue.log` (260 b). скан и сверка с HEAD: `task43_scan_baseline.py` (3 302 b), `task43_scan_baseline.log` (1 256 b), `task43_scan_baseline.data.txt` (1 203 b), `task43_scan_baseline2.log` (1 203 b), `task43_scan_scope.py` (1 573 b), `task43_scan_scope.log` (350 b), `task43_scan_scope2.log` (115 b), `scan_p1c_task43.log` (4 461 b), `scan_p1c_task43b.log` (4 385 b), `scan_doc_task43.log` (940 b), `scan_doc_task43b.log` (921 b). сообщения коммитов: `msg_p1c_task43.txt` (988 b), `msg_doc_task43.txt` (352 b). перепроверка скана сегодня (запись Task 50): `t50_task43_scan_verify.py` (5 072 b), `iter15_task43_scan_verify.log` (772 b), `t50_t43after_test_scope.py` (11 657 b), `t50_t43before_test_scope.py` (10 051 b).

### Журнал итерации 15: Task 44 (индекс форм конфигурации: `FORM_ANCHOR_FOLDERS`, `form_key_of`, `TypeModel.forms`, `options["form"]` в канале `check/bsl`, замеры 55 и 59, коммит `p1c 35d7897`; запись дописана записью Task 50)

- **Что исполнено этой записью и почему она дописывается задним числом.** Task 44 исполнен 2026-11-01 12:36 коммитом `p1c 35d7897` (parent `3aa061f`), а в лиджер не попал: его заметка осталась черновиком `iter15_ledger_note.md`, и отдельного коммита документов этой задачи нет — ближайшие коммиты документов относятся к плану (Task 44–50 — `docs caa8e52` 2026-11-01 11:44) и к восьмому пакету правок p1c (`docs db21b1b` 2026-11-02 14:18). Запись дописывает Task 50 (шаг 3 плана). Числа замера 55 этой задачи перенесены сегодня в §7.5.20 дизайн-дока и в §13 файла `docs/evidence/tool-coverage.md`. Пуша нет: разрешения на пуш в этом разговоре не выдавалось.
- **Причина правки (шаги 1–2 плана Task 44).** Канал имён формы, который вводит Task 45, требует отличать модуль формы от прочих модулей и дать модулю формы его реквизиты. Индекс строится по записям форм в модели метаданных корпуса, а не по обходу папок выгрузки: иначе форма без файла модуля и форма с нестандартным путём выпадали бы из индекса.
- **Что введено в коде.** В `src/p1c/metadata/module_paths.py`: `FORM_ANCHOR_FOLDERS` — 20 имён папок-якорей (18 видовых плюс `CommonForms` и `SettingsStorages`), `_ANCHOR_NORMS`, `_FORM_FOLDERS` и `form_key_of(path)` (строки 155–177: части пути разбираются справа налево — `range(len(parts) - 1, -1, -1)`, а якорь, стоящий сразу за `Forms` или `CommonForms`, пропускается). В `src/p1c/metadata/loader.py`: `build_form_index(ctx, model)` и пополнение `ctx.forms` перед возвратом модели. В `src/p1c/metadata/model.py`: `FormContext` (строки 101–102: `key`, `name`, `owner`, `kind`, `attrs`, `obj_type=None`) и поле `TypeModel.forms` (строка 139). В канале `check/bsl`: `opts["form"] = ctx.forms.get(form_key_of(path))` — только когда модуль признан формным. Полей `composition`, `methods` и `commands` запись формы не дополнена: их содержимое в индексе того дня не измерено.
- **Замер 55 (шаг 1 плана) — базовая линия итерации до изменения кода.** Скрипт `m55_task44_base.py` с обёртками `m55_runner.py` и `m55_summary_runner.py` (обёртка запускает корпусный прогон `subprocess.run(..., capture_output=True, timeout=1500)` из `<p1c>` и пишет stdout и stderr бинарно), предсказания `iter15_m55_predictions.md` (записаны до прогона и после не переписаны), сводка `m55_task44_base.summary.log`. База подсчёта: корпус `<corpora_pulsar>`, один ключ `check` за проход, команда `python -m p1c.check.bsl.cli check <корпус> --root <корпус> --format json --out <артефакт>`, дерево `3aa061f`, `stats` с `files` 1 195 (файлов конфигурации) и 502 модуля формы на диске, `skipped_rules` 3 (`os_compat`, `queries`, `tests`). Итог `summary.count` 33 047 в 768 файлах с находками; разбиение по `module_kind_of`: формная строка 26 102 в 442 файлах, `common` 4 452 в 144, `object` 2 488 в 178, `command` 5 в 4. Объединение методов трёх формных типов по этому артефакту: 27 + 57 + 15 = 99, 81 различное имя (пересечений 18). `IDS_STX_PROC_NOTDEFINED` в формной строке 922 = 900 по 12 именам (их закрывает Task 48) плюс 22 по 6 именам. Реквизиты раскладки — 10 849 вхождений, имена композиции — 10 137 (из них `Элементы` 9 807, `ЭтаФорма` 172, `ВладелецФормы` 60, `Модифицированность` 51, `Команды` 46, `ТекущиеДанные` 1), пересечений 0, остаток 684 по 40 различным именам (крупнейшие: `УсловноеОформление` 312, `ОбработкаОшибок` 137, `КлючТекущегоВарианта` 50, `ТекущийЭлемент` 41). Реестр форм модели — 520 записей (442 объектных форм и 78 прочих видов), 520 различных путей, 511 записей с реквизитами и 9 без них. Разбор — §7.5.20 дизайн-дока и §13 файла `docs/evidence/tool-coverage.md`.
- **Замер 59 (шаг 4 плана) — правило якоря и покрытие индекса.** Скрипт `m59_formkeys.py` с логом `m59_formkeys.log`, перепроверка на абсолютном пути `m59b_abskeys.py` с логом `m59b_abskeys.log`, предсказания `iter15_m59_predictions.md` (записаны до прогона). База подсчёта — 520 записей форм модели (артефакт `m55_task44_after_pulsar.json`) и обход корпуса по файлам `*.bsl`. Измерено: 520 записей дают 520 различных ключей и 0 коллизий; новое правило и прежнее совпадают на относительных путях — 0 расхождений; абсолютный путь даёт тот же ключ у 520 записей из 520; прежнее правило (первый сегмент-якорь слева) на абсолютном пути даёт неверный ключ у 520 записей из 520. Первый промер дал 494 вместо 520, потому что сравнивался только первый сегмент после якоря: у 26 записей вида документов ложный якорь случайно совпадал с настоящей папкой вида; `m59b_abskeys.py` сравнивает ключ целиком — 520 расхождений и 0 случайных совпадений. Файл модуля формы есть у 502 записей из 520 (у 18 его нет), дисковых формных модулей 502, и ни один не остался вне индекса; файлов с формными находками 442, покрыто индексом 442; формных строк 26 102; `ctx.forms` — 520 ключей; фикстура `examples/managed_app` — 2 записи, покрыты обе. Разбор — §7.5.20 дизайн-дока.
- **Отклонение от формулировки плана Task 44 (шаги 4–5), причина измерена до правки.** План описывал поиск якоря по папке вида после имени объекта; измерено, что путь приходит абсолютным в трёх каналах — `src/p1c/check/bsl/server.py:244`, `src/p1c/cli/runner.py:199`, `src/p1c/lsp/lsp_server.py:257` — и относительным только в `src/p1c/check/bsl/cli.py:201`, а домашняя папка `Documents` носит то же имя, что и папка выгрузки документов. Поэтому якорь ищется справа налево. То же правило позднее потребовалось каналу владельца (восьмой пакет, коммит `823728a`, раздел 6 файла `docs/evidence/p1c-data-defects.md`).
- **RED до правки.** Тест `tests/metadata/test_form_index.py` написан до правки кода: 7 блоков, 36 проверок. Первое падение — `ImportError: cannot import name 'FormContext'` (класса ещё не было); после его появления тест падал на правиле якоря: путь вида `documents/rea/...` давал ключ не папки вида (`catalogs/...`). Отдельных логов тестовых прогонов этой задачи на диске нет; тексты падений записаны в черновнике заметки `iter15_ledger_note.md` и повторены здесь.
- **GREEN после правки.** По черновнику заметки `python scripts/run_tests.py` дал 88 файлов и 0 падений (было 87 — добавлен один тестовый файл), контур — 303 теста из 303; ни одним логом эти два числа этой задачи не подтверждены, и в записи они держатся как числа черновника. Первое подтверждённое логами число после Task 44 — 95 файлов и 0 падений в записи Task 45 (было 94; между задачами был восьмой пакет правок p1c), далее 96 / 0: `m65c_runtests.log` (замер 65c, Task 46), `iter15_task47_run_tests.log` и его повтор, `iter15_task48_runtests.log` и сегодняшний `m69_task50_runtests.log` (замер 69, §7.5.20 дизайн-дока). План ждал «87 → 90 тестовых файла» (шаг 3 плана Task 50); измерено 87 → 96, и расхождение объясняют записи Task 46 и Task 47: тестовых файлов добавляли и другие задачи итерации.
- **Гейт и корпус этой правки не изменились (шаг 6 плана).** Гейт фикстуры: `m55_task44_gate.json` до правки кода и `m55_task44_after_gate.json` и `m55_task44_after2_gate.json` после — по 4 744 b, 2 находки `НачалоПериода` (позиции `6:28` и `20:49`), `stats` с `files` 8. Корпус: повторные прогоны `m55_task44_after_pulsar.json` и `m55_task44_after2_pulsar.json` побайтово равны базовому артефакту (по 20 325 893 b, 33 047 находок, `stats` с `files` 1 195, 768 файлов с находками); сравнение `m55_task44_compare.py` (лог `m55_task44_compare.log`) даёт 0 расхождений по ключам находок. Правка не двигает ни корпус, ни гейт, и это ожидаемо: потребителей у индекса на этом шаге нет, их вводит Task 45.
- **Скан текстов (изменённый код `p1c`).** Отдельного лога скана этой задачи на диске нет, поэтому скан переснят сегодня копиями файлов из коммита `35d7897` и из его родителя `3aa061f` (`t50_scan_task44.py`, лог `iter15_task44_scan_commits.log`; сверка — мультимножества пар (паттерн, текст), а не номера строк — урок F31). По трём прежним файлам — 27 флагов до правки и 27 после (GLUE 22, ABS-PATH 5), различных пар 11 и 11 (GLUE 8, ABS-PATH 3), новых пар 0 и исчезнувших 0. Размеры файлов: `src/p1c/metadata/loader.py` 12 489 → 14 508 b, `src/p1c/metadata/model.py` 43 201 → 44 449 b, `src/p1c/metadata/module_paths.py` 8 764 → 12 843 b; нового файла до правки не было, после — `tests/metadata/test_form_index.py` 10 590 b, 0 флагов.
- **Коммит кода.** В `p1c`: `35d7897` (parent `3aa061f`, 2026-11-01 12:36), 4 файла, +277 / −1: `src/p1c/metadata/loader.py` (+45), `src/p1c/metadata/model.py` (+19), `src/p1c/metadata/module_paths.py` (+62) и `tests/metadata/test_form_index.py` (+152). Subject совпадает с формулировкой шага 7 плана: `metadata: index of configuration forms (form_key_of, TypeModel.forms, options[form])`; тело — ASCII-транслитерацией из `commit_msg.txt` (предшествующий черновик тела сохранён как `commit_msg2.txt`), в нём описаны поиск якоря справа налево, абсолютный путь, папка `Documents`, числа замера 59 и указание, что отклонение от формулировки плана переносится в лиджер — это и делает настоящая запись. Рабочее дерево `p1c` после коммита чистое; пуша нет.
- **Судьба предсказаний.** Замер 55: предсказания `iter15_m55_predictions.md` после прогона не переписывались; сводка и артефакт прогонов совпали с ожиданиями по числам базовой линии (33 047 / 768 / 26 102 / 442), расхождений по артефакту сравнения повторов — 0. Замер 59: предсказания после прогона не переписывались; разошёлся только первый промер правила (494 вместо 520) по причине, названной выше, и он переписан отдельным скриптом.
- **Отклонения процесса этой задачи (дефектных номеров не получили).** (1) Заметка задачи осталась черновиком `iter15_ledger_note.md`, коммита документов задачи нет — их заменяет эта запись. (2) Числа прогонов (88 файлов, 303/303) в черновнике не подтверждены логом; в записи они отделены от подтверждённых. (3) Лога скана этой задачи на диске нет — скан переснят сегодня копиями из коммита. (4) План ожидал 90 тестовых файлов к Task 50; измерено 96 — расхождение объяснено записями Task 46 и Task 47.
- **Номера замеров.** **55** — базовая линия корпуса и гейта до изменения кода: **исполнен** (`m55_task44_base.py`, `m55_task44_base.summary.log`, `iter15_m55_predictions.md`), и он назван базой сравнения плана. **59** — правило якоря и покрытие индекса: **исполнен** (`m59_formkeys.py`, `m59_formkeys.log`, `m59b_abskeys.py`, `m59b_abskeys.log`, `iter15_m59_predictions.md`); чисел замера 59 в дизайн-доке нет — они живут только в этой записи, а в абзаце нумерации дизайн-дока 59 значится занятым этими артефактами.
- **Артефакты этой записи** (все в `<tmp>\opencode`, если не сказано иное). замер 55: `m55_task44_base.py` (8 988 b), `m55_runner.py` (842 b), `m55_summary_runner.py` (483 b), `iter15_m55_predictions.md` (6 206 b), `m55_task44_base_pulsar.json` (20 325 893 b), `m55_task44_base.err` (117 b), `m55_task44_base.log` (0 b), `m55_task44_base.stdout.log` (6 246 b), `m55_task44_base.stderr.log` (0 b), `m55_task44_base.summary.log` (6 246 b), `m55_task44_gate.json` (4 744 b). повторы корпуса и гейта после правки: `m55_after_runner.py` (1 464 b), `m55_after2_runner.py` (1 377 b), `m55_task44_after_pulsar.json` (20 325 893 b), `m55_task44_after_pulsar.err` (117 b), `m55_task44_after_pulsar.log` (0 b), `m55_task44_after_gate.json` (4 744 b), `m55_task44_after_gate.err` (111 b), `m55_task44_after_gate.log` (0 b), `m55_task44_after2_pulsar.json` (20 325 893 b), `m55_task44_after2_pulsar.err` (117 b), `m55_task44_after2_pulsar.log` (0 b), `m55_task44_after2_gate.json` (4 744 b), `m55_task44_after2_gate.err` (111 b), `m55_task44_after2_gate.log` (0 b), `m55_task44_compare.py` (3 553 b), `m55_task44_compare.log` (1 549 b). замер 59: `m59_formkeys.py` (7 649 b), `m59_formkeys.log` (3 076 b), `m59b_abskeys.py` (2 789 b), `m59b_abskeys.log` (1 036 b), `iter15_m59_predictions.md` (5 481 b). разведка: `m55_inspect_prev.py` (1 449 b), `m55_shape.py` (497 b), `m55_fixture_forms.py` (1 146 b). сообщение коммита и черновник заметки: `commit_msg.txt` (790 b), `commit_msg2.txt` (1 683 b), `iter15_ledger_note.md` (13 158 b), `scan_design_4445.log` (1 031 b). пересъёмка скана сегодня (запись Task 50): `t50_scan_task44.py` (6 506 b), `iter15_task44_scan_commits.log` (1 616 b), `t50_t44before_loader.py` (12 489 b), `t50_t44after_loader.py` (14 508 b), `t50_t44before_model.py` (43 201 b), `t50_t44after_model.py` (44 449 b), `t50_t44before_module_paths.py` (8 764 b), `t50_t44after_module_paths.py` (12 843 b), `t50_t44after_test_form_index.py` (10 590 b).

### Журнал итерации 15: Task 49 (корпусный гейт итерации и сверка итога по обеим базам, замер 58, новый раздел 13 файла `docs/evidence/tool-coverage.md`, коммит `docs 156810c`; запись дописана записью Task 50)

- **Что исполнено этой записью и почему она дописывается задним числом.** Task 49 закрывал итерацию числами по шагам 1–5 плана: предсказания до прогона с явной базой каждой строки, корпусный прогон (замер 58) и его сводка по 11 кодам и 4 видам модулей, сверка «предсказано / получено / расхождение / причина», запись сводки в `docs/evidence/tool-coverage.md` (новый раздел «Итерация 15: формный канал контекста»), скан и коммит документов. Лиджер-заметки той задачи не было — её дописывает Task 50 (шаг 3 плана). Правки кода в `p1c` в этой задаче не выполнялись (задача сводит и записывает итог), поэтому прогоны тестов и контура в этой записи приводятся по повтору записью Task 50: замер 69 — 96 файлов тестов и 0 падений, контур 303 теста из 303 (`m69_task50_runtests.log`, §7.5.20 дизайн-дока). Пуша нет: разрешения на пуш в этом разговоре не выдавалось.
- **Замер 58 — корпусный прогон и его сверка с ожиданиями плана.** Скрипт `m58_task49_gate.py` (516 строк) с обёрткой корпусного прогона `m58_runner.py` (лог `m58_runner.log`), предсказания `iter15_m58_predictions.md` (174 строки, разделы А–И, записаны до прогона и после не переписаны), сводка `m58_task49_gate.summary.log` (151 строка), её stdout-копия и две прежние сборки (128 и 147 строк). Артефакты прогона: `m58_task49_pulsar.json` — побайтово равен артефакту Task 48 (`iter15_task48_pulsar.json`), потому что правок кода между задачами не было; гейт фикстуры `m58_task49_gate.json` — returncode 0, `summary.count` 0, `stats` с `files` 8, `skipped_rules` ровно 3 (`os_compat`, `queries`, `tests`), подпись контекста `4edf65fe906bbcb4…`. Итог корпуса: 10 526 находок в 610 файлах при `stats` с `files` 1 195 (файлов конфигурации); по `module_kind_of` — формная строка 4 264 в 293 файлах, `common` 3 979 в 143, `object` 2 279 в 171, `command` 4 в 3; дерево `bf0ea78`, длительности прогона 333.3 с (корпус) и 38.3 с (гейт).
- **Сверка по обеим базам (шаги 1 и 3 плана), обе базы названы до прогона.** База А — артефакт замера 55 (`m55_task44_base_pulsar.json`: 33 047 находок в 768 файлах с находками, формная строка 26 102 в 442 файлах, дерево `3aa061f`, база плана). База Б61 — артефакт замера 61 (`m61_fixed_pulsar.json`: 32 547 находок в 760 файлах, формная строка 26 177 в 442 файлах, дерево `823728a` — восьмой пакет правок p1c). К итогу от базы Б61 закрыто 22 022 находки, из них 21 914 в формной строке (26 177 → 4 264), открыта 1 находка — `IDS_STX_PROPERTYNOTFOUND` (`СтрокаТабличнойЧасти.Представления.ПараметрыПрописи`, `Catalogs/Валюты/Forms/ФормаЭлемента/Ext/Form/Module.bsl`, 182:17); её породил Task 47 и разобрал замер 66b (§7.5.18 дизайн-дока). К итогу от базы А закрыто 22 989 (формная строка — 22 082), открыто 468, из них 467 принадлежат восьмому пакету (замер 61), а одна — правке Task 47. Одиннадцать кодов формной строки и одиннадцать кодов корпуса по трём состояниям сведены таблицами §13 файла `docs/evidence/tool-coverage.md`; суммарные разности от базы Б61 — −21 913 по формной строке и −22 021 по корпусу. Файлы с находками: от базы А 768 → 610 (исчезло 161, появилось 3, стало меньше 432, стало больше 22), от базы Б61 760 → 610 (исчезло 150, появилось 0, стало меньше 320, стало больше 0). Методика — та же, что у замера 55: разбиение по `module_kind_of(path)`, имя находки — из последней скобочной группы текста, сравнение мультимножеств ключей (файл, код, строка, колонка, текст).
- **Гейт §8, критерий §12 п.2 и остаток шума (шаг 3 плана).** Метрика G закрыта: 2 находки в базовой линии итерации 14 → 0 (`m58_task49_gate.json`, и 0 открытых находок по всем кодам от базы Б61 в `m58_task49_pulsar.json`). Формные потолки итерации 15 (`BSL_CTX_NOT_AVAILABLE` 8, `BSL_CTX_CLIENT_ONLY` 7, `IDS_STX_PROC_DEFINED` 6, `IDS_STX_PARAMS_TOOMANY` 75) и корпусные потолки тех же трёх кодов (12 / 7 / 10) равны в обеих базах и в итоге; ни один потолок не превышен, и задача закрыта без возврата в задачу-владельца превышения. `IDS_STX_METHODNOTFOUND` и `IDS_STX_CTOR_NOTFOUND` от базы Б61 не выросли (по формной строке −34 и 0), `IDS_STX_PROPERTYNOTFOUND` вырос на одну находку Task 47 — заявленный вклад предпосылки §6. Остаток формного `IDS_STX_PROC_NOTDEFINED` — 16 находок в 5 именах (`Активизировать` 8, `Открыть` 4, `УстановитьТекущийВариант` 2, `РазблокироватьДанныеФормыДляРедактирования` 1, `УстановитьТекущиеПользовательскиеНастройки` 1); ни одного из этих имён в объединении 81 нет, и ни одно из них канал не замолчал.
- **Шесть разошедшихся ожиданий шага 1 плана, у каждого причина измерена до прогона; предсказания после прогона не переписывались.** (1) Длительность корпусного прогона 333.3 с вне предсказанного интервала — причина проверена повтором той же команды по тому же дереву и корпусу: артефакт вышел того же размера и с той же подписью, то есть это состояние машины, а не результата. (2) Длительность гейта 38.3 с против 2.2 с и 3.3 с в замерах 66 и 68 — та же причина. (3) Ожидание «`IDS_STX_PROPERTYNOTFOUND` 15 не выросли»: 15 — число базы А, в базе Б61 формная строка этого кода уже 258, корпусная 663 (восьмой пакет открыл 473, из них 467 по этому коду), а в цепи правок итерации рост равен одной находке на этапе Task 47. (4) Ожидание «строки `common`, `object` и `command` не меняются»: 4 452 / 2 488 / 5 — числа базы А, по базе Б61 это 4 010 / 2 356 / 4, итог 3 979 / 2 279 / 4, и весь сдвиг сделал Task 46 (140 закрытых — замер 65 и его построчный разбор 65b). (5) Ожидание остатка «22 вхождения в восьми именах» при сумме самого перечня 24 (дефект F33): по артефакту 16 находок в 5 именах — перечень плана сверен с артефактом замера 55, как требовал шаг 1 Task 44. (6) Плановая сумма вкладов (10 849 + 10 137 + 900 = 21 886, ожидаемый итог 4 216) с измерением не совпала: по базе А формная строка уменьшилась на 21 838 (закрыто 22 082 при 244 открытых), по базе Б61 — на 21 913 (закрыто 21 914 при 1 открытой); избыток закрытого 196 складывается из 156 находок `IDS_STX_VAR_NOTDECLARED` сверх плановой суммы реквизитов и композиции, 34 находок `IDS_STX_METHODNOTFOUND` (план их закрытия не предсказывал) и 6 вхождений `IDS_STX_PROC_NOTDEFINED`, отсутствующих в базе Б61; план не учитывал открытые `IDS_STX_PROPERTYNOTFOUND` — 244 по базе А и 1 по базе Б61; разность итогов 48 = 244 − 196.
- **Дефекты этого блока (номера продолжаются после F38; разбирать их отдельными разделами §7.5 не потребовалось, всё размещено в этой записи и в §7.5.20 дизайн-дока):**
  - **F41** — неверная атрибуция 468 открытых находок по базе А: первая сборка сводки приписывала их восьмому пакету целиком, измерено — 467 принадлежат восьмому пакету (замер 61) и 1 порождена правкой Task 47. Исправлен лог сводки (`m58_task49_gate.summary.log`, строка 95); файл предсказаний после прогона не переписывался.
  - **F42** — в описании скрипта сверки `t49_recon_diff.py` в кириллическом слове оказался иероглиф (флаг CJK сканера). Скрипт лежит в `<tmp>\opencode` и в репозиторий не попадал; исправлен до того, как его вывод был перенесён в документы.
  - **F43** — в `t49_recon_m61.py` допуск был записан как `>10d` вместо числового интервала, и в тех же скриптах сверки сгруппированы мелкие правки: предсказание 455 → 528 записано до прогона, сравнение сведено к одному совпадению, в раздел предсказаний по корпусу добавлены границы длительности прогона, в заголовке снята лишняя кириллическая буква. Ни одно число замера 58 от этих правок не изменилось.
  - **F44** — в сообщении коммита документов было «268 novyh strok» вместо измеренных 267 вставок; исправлено повторной записью сообщения (`417a5b2` → `156810c`) до того, как сообщение закрепилось в истории.
  - **F45** — скрипт скана документов `t49_scan_docs.py` упал на печати сводки: `TypeError: say() takes from 0 to 1 positional arguments but 4 were given`. Помощник печати исправлен на вариант со звёздочкой (`def say(*parts)`), артефакты прогона при этом не переписывались.
- **Скан текстов и их сверка с HEAD (шаг 5 плана).** `python -I` со `scan_texts.py` по изменённому документу: в рабочем дереве 5 флагов (все GLUE) и 18 вынесений вербатим-имён метаданных, в копии из HEAD — те же 5 флагов и те же 18 вынесений; сравнение мультимножеств пар (паттерн, текст) даёт 0 новых флагов и 0 исчезнувших (`iter15_task49_scan_head_pair.log`, прогоны `iter15_task49_scan_docs.log` и `iter15_task49_scan_docs_head.log`). Размеры: `docs/evidence/tool-coverage.md` 128 396 → 154 665 b и 1 172 → 1 439 строк, добавленный текст 26 269 b, одиночных CR 0 (файл LF-only), копия до правки побайтово равна копии из HEAD.
- **Коммит документов.** В `effektivnost-otdela`: `156810c` (parent `a801515`, 2026-11-05 13:08), 1 файл — `docs/evidence/tool-coverage.md`, 267 вставок. Subject — `evidence: korpusnyj gejt iteracii 15 - formnyj kanal konteksta (zamer 58)`; сообщение — ASCII-транслитерацией из `iter15_task49_docs_commit.txt`. Новый раздел 13 содержит полную строку прогона со складками, базу (1 195 файлов конфигурации, 502 модуля формы, 26 102 находки в базовой линии), две таблицы одиннадцати кодов «база → итог» с базой подсчёта каждой строки, поштучный свод закрытого и открытого по обеим базам, перечень артефактов замеров 55–58, остаток шума и сознательный компромисс — объединение клиентских и серверных методов (§11 дизайн-дока). Правок дизайн-дока, плана и `docs/evidence/p1c-data-defects.md` в этой задаче не было — их делает Task 50.
- **Судьба предсказаний.** Предсказания `iter15_m58_predictions.md` (разделы А–И) после прогона не переписывались; подтверждены итоговые числа корпуса, обе базы закрытого и открытого, равенство потолков, остаток шума и равенство артефакта прежнему прогону; разошлись шесть ожиданий плана — все они относятся к ожиданиям шага 1 плана, а не к предсказаниям скрипта, и разобраны выше. Первая и вторая сборки сводки (`.prev1` 128 строк, `.prev2` 147 строк) оставлены как есть: в них был дефект F41 и отсутствие части сверки по базе Б61.
- **Номера замеров.** **58** — корпусный гейт итерации и сверка итога: **исполнен** (`m58_task49_gate.py`, `m58_task49_gate.summary.log`, `iter15_m58_predictions.md`), закреплён абзацем нумерации дизайн-дока и разделом 13 файла `docs/evidence/tool-coverage.md`. Разведка `t49_timing_probe.py`, `t49_scan_docs.py`, `t49_recon_prior.py`, `t49_recon_diff.py`, `t49_recon_m61.py`, `t49_recon_resid.py`, `t49_docs_evidence.py` и `t49_list_artifacts.py` — без номера и без файла предсказаний, её вывод замером не считается.
- **Артефакты этой записи** (все в `<tmp>\opencode`, если не сказано иное). скрипты замера 58: `m58_task49_gate.py` (36 009 b), `m58_runner.py` (4 133 b), `m58_runner.log` (965 b), `iter15_m58_predictions.md` (18 044 b). сводка замера 58 и её прежние сборки: `m58_task49_gate.summary.log` (23 953 b), `m58_task49_gate.stdout.log` (24 161 b), `m58_task49_gate.summary.log.prev1` (17 585 b), `m58_task49_gate.summary.log.prev2` (22 101 b). артефакты прогонов замера 58: `m58_task49_pulsar.json` (6 400 757 b), `m58_task49_pulsar.err` (117 b), `m58_task49_pulsar.log` (0 b), `m58_task49_gate.json` (3 486 b), `m58_task49_gate.err` (111 b), `m58_task49_gate.log` (0 b). разведка сверки: `t49_timing_probe.py` (2 602 b), `t49_timing_probe.log` (300 b), `t49_timing_probe.json` (6 400 757 b), `t49_timing_probe_gate1.json` (3 486 b), `t49_timing_probe_gate2.json` (3 486 b), `t49_recon_prior.py` (7 125 b), `t49_recon_prior.log` (8 381 b), `t49_recon_diff.py` (4 673 b), `t49_recon_diff.log` (2 051 b), `t49_recon_m61.py` (9 868 b), `t49_recon_m61.log` (9 613 b), `t49_recon_m61.stdout.log` (9 756 b), `t49_recon_resid.py` (4 191 b), `t49_recon_resid.log` (5 429 b), `t49_docs_evidence.py` (29 997 b), `t49_scan_docs.py` (5 300 b), `t49_list_artifacts.py` (1 328 b), `t49_list_artifacts.log` (1 524 b). снимки документов и скан: `t49_base_progress.md` (350 517 b), `t49_head_progress.md` (347 925 b), `t49_base_toolcoverage.md` (128 396 b), `t49_head_toolcoverage.md` (128 396 b), `iter15_task49_scan_docs.log` (1 539 b), `iter15_task49_scan_docs_head.log` (1 723 b), `iter15_task49_scan_head_pair.log` (1 102 b), `iter15_task49_docs_commit.txt` (4 675 b).

### Журнал итерации 15: Task 50 (статусы блоков C и G в плане оптимизации, записи замеров 55–58 и 69 в дизайн-док новым разделом §7.5.20, новый раздел 7 файла `docs/evidence/p1c-data-defects.md`, дописанные записи лиджера Task 43 / Task 44 / Task 49 и эта запись, финальные прогоны итерации (замер 69), ревью итерации свежим ревьюером и правки документов по его замечаниям)

- **Что исполнено этой записью (шаги 1–6 плана Task 50 — строки 172–189 файла `docs/superpowers/plans/2026-10-31-iteraciya-15-formnyj-kontekst.md`).** Шаг 1 — статусы блоков C и G в `docs/план-оптимизации-p1c.md`; шаг 2 — записи замеров в дизайн-док и дополнение `docs/evidence/p1c-data-defects.md` (дефект свортки `ё`, закрыт Task 43); шаг 3 — дописанные записи лиджера `Task 43` и `Task 44`–`Task 49` (из семи задач плана своих записей не хватало трём — Task 43, Task 44 и Task 49) и эта запись про саму Task 50; шаг 4 — финальные прогоны итерации (замер 69); шаг 5 — скан изменённых документов и коммит; шаг 6 — ревью свежим ревьюером и правки по его замечаниям. Изменено пять документов репозитория `effektivnost-otdela`; правок кода в `p1c` не было — у Task 50 по плану нет шагов кода, и повтор корпусного прогона это подтверждает: артефакт замера 69 побайтово равен артефакту замера 58 (оба по 6 400 757 b), а `p1c` стоит на `bf0ea78` с чистым рабочим деревом. Пуша нет: разрешения на пуш в этом разговоре не выдавалось.

- **Шаг 1 — статусы блоков C и G (`docs/план-оптимизации-p1c.md`).** Правка — 3 фрагмента, +24 / −2, 197 → 219 строк файла (файл LF-only, одиночных CR 0). Строка C1 таблицы блока C (113) дополнена ссылкой на новый абзац; абзац «Статус блока C к итерации 14» (124–129) не тронут; новым фрагментом на строке 131 вставлен абзац «Статус блока C к итерации 15» (131–152, 22 строки): с очереди сняты те пункты, которые упёрлись в молчание канала контекста модуля формы — C1 (реквизиты раскладки и имена композиции, Task 45: формная строка `IDS_STX_VAR_NOTDECLARED` 21 508 → 528 по базе замера 61), стандартные свойства и методы объектных, ссылочных и записных типов (Task 46: 140 закрытых, из них 32 в формной строке), строгий тип реквизита `Объект` (Task 47), методы типа формы (Task 48: объединение 81 имени, формный `IDS_STX_PROC_NOTDEFINED` 916 → 16). Явно оставлены в очереди: `C3` (`types_without_ctor` 1 869), `C5`–`C10`, строгая типизация реквизитов с маппингом `cfg:…RecordManager.<Имя>`, типы элементов макета, свойства формы и свойства глобального контекста, сузение подавления инвентаря имён. Метрика блока G закрыта в строке метрики 202: 2 → 0 (артефакт `iter15_task45_gate.json` 3 434 b после `m63_task45_gate.json` 4 744 b с 2 находками, ноль подтверждён гейтами замеров 68, 58 и 69). Заголовок «## Блок G. Метрика успеха плана» после вставки 22 строк в блоке C стоит в строке 191; адрес блока в плане Task 50 (`:169`) — адрес состояния файла до этой правки, в HEAD `156810c` он точен. 1С в этой итерации не запускалась.

- **Шаг 2 — записи замеров в дизайн-док, и отклонение от формулировки шага (причина измерена до правки).** План просил добавить записи «55», «56», «57», «58» в §7.5.16; §7.5.16 занят чужой записью («Замеры 49–51 — семейство баз …», заголовок на строке 1529), и перенос или перебивка чужих записей сдвинули бы адреса разделов, на которые ссылаются другие документы — записанный ранее урок F34. Поэтому замеры 55, 56, 58 и 69 сведены новым разделом §7.5.20 «Замеры 55, 56, 58 и 69: базовая линия, `Объект.<имя>`, корпусный гейт, прогоны итерации» (2663–2913), а абзац «Номера замеров после §7.5.19 закреплены планом» перенесён в его конец (2873) и дополнен: 55, 56, 57 с подзамерами 57b…57h, 58 и 69 — исполнены, пометка «резерв» снята, следующий свободный номер — **70** (2888). План ждал «следующий свободный номер — 59»: номера 59–68 заняты прогонами канала владельца и задачами 45–48, и расхождение объясняют записи Task 45–48. Правка дизайн-дока — 30 фрагментов, +586 / −43, 2 809 → 3 352 строк; файл на диске CRLF (CR 3 352), копия из HEAD 335 090 b без CR.

- **Что правлено в дизайн-доке по разделам.** §4.1 (журнал решений): «22 иное» исправлено на «22 иное в шести именах» и добавлен абзац (503–509) о прежнем перечислении восьми имён на сумму 24 (дефект F33); §5.5: сноска правки Task 50 (333–339) о том, что из двух обещанных половин индекса исполнена только первая (запись дефекта F56); §7.5.9 и §7.5.15: заголовки перевыпущены с метками семейств («семейство имён раскладки», «семейство баз фикстур и манифеста читателя») — так снято двойное занятие номеров 45, 45b, 45c (дефект F49), сами замеры и их артефакты не переименованы; §7.5.16 и §7.5.17: три пометки о том, что адрес или вхождение относятся к прежнему дереву (1343–1348, 1361–1367, 1618–1620); §7.5.18/§7.5.19: пометка «(замер 58, Task 49) ещё не исполнен» заменена на «исполнен — запись §7.5.20 — и подтверждён повтором» (2408–2409); §7.5.20 (новый); §8: база тестов «96 файлов / 0 падений — замер 69 §7.5.20» вместо 87 (2952–2953) и добавлены исполненные артефакты гейта Task 45 (2918–2920); §9: 32 строки о том, что реально выбрано строителем (`FormContext` dataclass в `metadata/model.py`, 20 якорей локальной константой `FORM_ANCHOR_FOLDERS`, `FORM_COMPOSITION` списком из шести имён, `ctx.form_methods` словарём по нормализованному имени) и о том, что Task 43 исполнен раньше плана, а запись в лиджере дописана (2975–3006); §10: правка по замечаниям ревьюера (записи F49–F53, F55, F57 и перечень восьми отложенных замечаний уровня Minor с адресами); §11: причина остатка 16 измерена (3262–3287, дефект F55), третий порядок колонок и цена молчаливого затенения (3293–3304, F58) и переписанное под shipped-поведение описание правила ключа (3316–3331, F54).

- **Шаг 2 — `docs/evidence/p1c-data-defects.md`: новый раздел 7.** Правка — 2 фрагмента, +136 / −0, 425 → 561 строка (файл LF-only). Первый фрагмент — пометка от 2026-11-05 к прежнему пункту 4 раздела 6 (420–421): пункт описывает состояние на вечер 2026-11-02 и оставлен историей, теперешнее состояние плана и занятые номера — раздел 7. Второй фрагмент — сам раздел 7 (428–561): §7 (429) «Дополнение от 2026-11-05: свортка `ё` закрыта, и у инвентаря имён найдена асимметрия», §7.1 (435) — свортка `ё` в `norm()` закрыта (Task 43, коммит `3aa061f` от 2026-11-01), §7.2 (468) — инвентарь `PLATFORM_NAMES`: 487 имён из 973 есть имена членов типов, асимметрия мерится на обеих база (0 из 32 547 и 0 из 10 526), §7.3 (514) — очередь: у пяти имён формных вызовов нет сигнатур в трёх формных блоках таблицы сигнатур; цена закрытия остатка — 16 находок (8 + 4 + 2 + 1 + 1). Раздел называет адрес строки 560: «Правки кода в Task 50 нет: задача по плану не имеет шагов кода».

- **Шаг 3 — лиджер `.superpowers/sdd/effektivnost-otdela/progress.md`.** Дописаны три записи: Task 43 (заголовок на строке 2594), Task 44 (2611) и Task 49 (2629); записи Task 45 (1988), Task 46 (2079), Task 47 в двух кусках (2249 и 2373) и Task 48 (2540) стояли в файле и закрыли свои задачи своими заметками. Порядок записей не числовой — 43, 44 и 49 дописаны после 48, потому что их дописывает Task 50; в заголовках этих трёх записей это сказано («запись дописана записью Task 50»). Первая правка лиджера — один фрагмент +54 / −0 относительно HEAD `156810c` (2 592 → 2 646 строк). Эта запись дописана следом: правка лиджера этим коммитом — 107 строк вставок и 0 снятых, файл после дописывания — 2 699 строк. Байтовый размер лиджера после дописывания запись не называет, и размер этой записи не называет: правка цифр в строке меняет размер файла, и названное число стало бы неверным в момент записи (прецедент F39 и F40). Стабильные размеры: снимок файла до дописывания этой записи — `t50_ledger_before.md` (404 696 b, 2 646 строк, CR 2 646), копия из HEAD `t50_head_progress.md` (347 925 b, 2 592 строки, CR 0). Проверено, что ни один документ репозитория не ссылается на номера строк лиджера (поиск `progress.md:` по `docs/` — 0 совпадений), поэтому дописывание ничего не сдвигает в чужих цитатах; сдвигались бы только адреса разделов дизайн-дока, плана, файла дефектов и §13, и они в правках не менялись после того, как их пересняли (`t50_addr_verify.py`, запись F52).

- **Шаг 4 — финальные прогоны итерации (замер 69).** Скрипт `m69_final_gates.py` (24 408 b, 386 строк), предсказания `iter15_m69_predictions.md` (7 580 b, 84 строки, 20 пунктов, написаны до прогона и после не переписаны), сводка `m69_final_gates.log` (18 853 b, 157 строк), её stdout-копия (19 077 b), пустой stderr (0 b) и прежняя сборка сводки `m69_final_gates.prev1.log` (18 126 b, 153 строки), сохранённая как запись об отклонении процесса; дополнение `m69_skipped_rules.py` (4 049 b, 72 строки) с логом (2 728 b, 29 строк). Подтверждено 71 из 72 сверочных строк с расхождением 0: тесты `p1c` — 96 файлов и 0 падений (база плана — 87), `run_tests core` — 11 / 0, харнесс `test_form_context` — 65 проверок / 0 падений, контур — «Ran 303 tests» и `OK`; гейт фикстуры — код возврата 0, `stats` с `files` 8, `summary.count` 0, `skipped_rules` ровно 3 (`os_compat`, `queries`, `tests` — подтверждено отдельным прогоном дополнения во всех пяти гейтах итерации), stderr 111 b, JSON 3 486 b, подпись `4edf65fe906bbcb4…`, и артефакт побайтово равен гейтам Task 48 и Task 49; корпус — код возврата 1, stderr 117 b со строкой «[context] XML разобран: объектов 384, форм 520, модулей к сканированию 1670», `stats` с `files` 1 195, 10 526 находок в 610 файлах, JSON 6 400 757 b, подпись `726583f1b1ce9a3e…`, побайтовое равенство артефактам 58 и 68; строки по видам модулей — `form` 4 264 в 293, `common` 3 979 в 143, `object` 2 279 в 171, `command` 4 в 3; одиннадцать кодов формной строки и одиннадцать кодов корпуса равны замеру 58; закрыто 0 и открыто 0, файлов с находками 610 → 610; кодов, которых не предсказывали, 0; потолки §8 равны значениям; остаток `IDS_STX_PROC_NOTDEFINED` 16 находок в 5 именах — список имён совпал поштучно. Длительности записаны как признак состояния машины: тесты 118.3 с, `core` 19.9 с, харнесс 1.0 с, контур 15.7 с, гейт 1.4 с, корпус 52.1 с. Не подтверждён один пункт — длительность харнесса 1.0 с вне предсказанного интервала 3.0–120.0 с; тот же корпусный прогон давал 95.6 с (замер 66), 96.4 с (замер 68) и 333.3 с (замер 58) при побайтово равных артефактах, а правок кода между Task 49 и Task 50 не было. Критерий §12 п.2 закрыт (гейт 0 находок), критерий п.4 перевыполнен по числу тестовых файлов (96 при пороге «больше 87»); содержимое тестов этой итерации описано записями Task 46–48 и их логами.

- **Отклонение процесса шага 4 (записано дефектом F46).** Первая сборка сводки (`m69_final_gates.prev1.log`) выдала два пункта «непредсказанного» — сверка ставила кортеж против целого и строку против булевого значения, то есть расхождения породил формат сверки, а не измерение. Правка скрипта добавила сравнение по числу проверок харнесса и интервалы длительностей; прежная сборка сохранена как есть, сводка пересобрана, ни одно число замера от этого не изменилось. Предсказание 5 про `skipped_rules` сводкой не проверялось и измерено дополнением отдельно.

- **Сверка §13 файла `docs/evidence/tool-coverage.md` с числами Task 50 (шаги 2 и 6).** Правка — 4 фрагмента, +41 / −2, 1 439 → 1 478 строк (файл LF-only): добавлена причина остатка 16 (1356–1380, меряется `t50_resid_probe.py` и `t50_resid_probe2.py`, запись F55); исправлены имена логов базовой линии замера 55 — в §13 стояли `m55_task44_base_pulsar.log` и `m55_task44_base_pulsar.err`, на диске `m55_task44_base.log` (0 b) и `m55_task44_base.err` (117 b) (запись F47); к описанию `iter15_m58_predictions.md` дописано основание счёта строк (1445–1449: 174 строки файла, 83 строки разметки девяти таблиц, 74 — содержимое вместе с девятью шапками без строк-разделителей, истинных строк-предсказаний 62; запись F50); и вписан абзац-напоминание (1463–1471), что артефактов замера 69 в перечне §13 нет и перенос его чисел в перечень отложен записью §10 — §13 сводит замеры 55–58, а корпусный артефакт 69 побайтово равен артефакту 58. Ни одно число раздела от правки не сдвинулось.

- **Шаг 6 — ревью свежим ревьюером (как отправлен и что вернулось).** Ревьюер — subagent типа general (идентификатор `a9836545f8b557c7e`), шаблон `requesting-code-review`, base `00cad6c` → head `bf0ea78`: он читал план, лиджер, diff `p1c` за итерацию и раздел evidence, делал проходы сам (код → тесты → лиджер → дизайн-док → §13 → артефакты `<tmp>\opencode`), сабагентов не заводил, деревья `p1c` и `effektivnost-otdela`, индекс, HEAD и ветки не трогал и долгих корпусных прогонов не повторял. Отчёт сохранён как `t50_review_report.md` (296 871 b, 2 357 строк). Итог: «Ready to merge? With fixes», критичных замечаний нет, замечаний уровня Important — 8 (пронумерованы 1–8), уровня Minor — 11 (1–11), сильных сторон 8, отдельно перечислено 11 позиций «отложено от оценки», рекомендации пронумерованы 1, 2, 3, 4 и 6 (пункт 5 в перечне отсутствует). Ревьюер не смог выполнить `git log` (помощник классификации был недоступен) и потому судил по артефактам, а не по коммитам; размеры артефактов он сверил в восьми проверках и независимо подтвердил числа 96 / 11 / 65 / 303. Критических замечаний нет, поэтому возвратов в задачу-владельца (требование шага 6) не было: восемь Important закрыты правками документов, потому что ни одно из них не требует правки кода.

- **Как размечены замечания ревьюера (требование шага 6: минорные — в §10 дизайн-дока).** Восемь Important → записи F49–F56 (двойные номера замеров; расхождение числа строк файла предсказаний с диском; перечень номеров без артефактов предсказаний; расхождение «текущих адресов» §10 с деревом `bf0ea78`; ссылка на несуществующий файл; §11 о правиле ключа, которого в коде нет; неназванная причина остатка 16; неисполненное обещание §5.5). Одиннадцать Minor: #4 (молчаливое затенение типов и его цена) записано §11 дефектом F58, #11 (числа гейта Task 44) записано §10 дефектом F57, #10 (в лиджере нет записи про саму Task 50) снят этой записью, остальные восемь отложены и стоят в §10 со своими адресами — решение «отложить» обосновано тем, что у Task 50 по плану нет шагов кода и ни одно из них не даёт находок ни на фикстуре, ни на корпусе.

- **Что в выводах ревьюера измерено иначе и поэтому в документы не перенесено.** (1) Перечень номеров 44–69 переснят этим скриптом, а не скопирован из отчёта: `t50_pred_files.py` (3 795 b) и `t50_pred_files.log` (4 686 b) дают 17 номеров без файла предсказаний, и у 15 из них нет и докстринга с ожиданием в скрипте; предсказания замера 64 живут под именем задачи — `iter15_task45_predictions.md` (9 219 b, 85 строк), а не под именем `iter15_m64_predictions.md`. Проверка седьмого пункта внимания ревьюера («ни один замер не объявлен без артефакта») меряется этим перечнем. (2) По замечанию о ссылке на несуществующий файл измерено: `p1c/src/p1c/data/platform_vocab.py` жил с коммита `45a69af` и удалён коммитом `76a45b0` (2026-11-01 19:28) в 2 500 строк, коммит `94b97b1` снял ровно две строки искажённых имён (1573 и 2 500), файла `platform_predefined.py` в репозитории не было никогда; имя `Проведен` сегодня стоит в `p1c/src/p1c/data/platform_name_pairs.py:7564`. Адрес `:1573` был верен на том дереве, на котором мерился. (3) Числа `types_without_properties` 1 891 (план оптимизации, строка 129) и 1 885 (строка 203) не подтверждены ни одним замером итерации 15 — эта метрика здесь не считалась, поэтому оба числа оставлены как есть (запись F48), и сверять их между собой не с чем.

- **Дефекты этого блока (номера продолжаются после F45; записи F46–F48 — процессные, F49–F58 — по замечаниям ревьюера, F59 — класс CJK в помощниках):**
  - **F46** — первая сборка сводки замера 69 выдала два ложных пункта «непредсказанных сдвигов»: сравнение ставило кортеж против целого и строку против булевого значения. Исправлен формат сверки, прежняя сборка сохранена (`m69_final_gates.prev1.log`).
  - **F47** — в §13 имена логов базовой линии замера 55 были названы как `m55_task44_base_pulsar.log` и `m55_task44_base_pulsar.err`; на диске — `m55_task44_base.log` (0 b) и `m55_task44_base.err` (117 b). Исправлено правкой §13.
  - **F48** — `types_without_properties` 1 891 в абзаце статуса к итерации 14 против 1 885 в строке метрики блока G: ни один замер итерации 15 эту метрику не считал, оба числа оставлены как есть.
  - **F49** — номера 45, 45b и 45c заняты двумя разными семействами замеров. Снято метками семейств в заголовках §7.5.9 и §7.5.15; артефакты и прежние записи не переименованы.
  - **F50** — §13 называл «74 строки» для `iter15_m58_predictions.md` при 174 строках файла; основание счёта дописано к описанию (83 строки разметки девяти таблиц, 74 — содержимое с девятью шапками без строк-разделителей, истинных предсказаний 62).
  - **F51** — объявленные номера 65, 65b и 65c и номер 64 сверены перечнем по диску (`t50_pred_files.py`): у 17 номеров файла предсказаний нет, у 15 из них нет и докстринга с ожиданием; предсказания 64 лежат в файле под именем задачи.
  - **F52** — «текущие адреса» §10 сами расходились с деревом `bf0ea78`: расхождение подтверждено на пяти адресах абзаца из десяти и на трёх ссылках вне его (всего исправлено восемь); пересъёмка сделана одним проходом (`t50_addr_verify.py` 1 846 b, `t50_addr_verify.log` 19 870 b).
  - **F53** — ссылка §10 вела на файл, которого нет: `platform_vocab.py` удалён коммитом `76a45b0`, `platform_predefined.py` не существовал; в тексте правки названы коммиты и число строк удалённого файла (2 500).
  - **F54** — §11 описывал правило ключа, заменённое в Task 44: переписано под shipped-поведение (`form_key_of` — `p1c/src/p1c/metadata/module_paths.py:155-189`, цикл поиска якоря 175–181, пропуск якоря за `Forms`/`CommonForms` 178–179, обрезка по `Ext` 184–189, константа `FORM_ANCHOR_FOLDERS` 140–146; числа — замер 59).
  - **F55** — причина остатка 16 находок в 5 именах не была названа; измерена (`t50_resid_probe.py` 6 403 b с логом 7 973 b, `t50_resid_probe2.py` 5 560 b с логом 5 260 b): имена есть в парах имён, сигнатур в трёх формных блоках таблицы `platform_arities.py` нет — дыра покрытия таблиц, питающих объединение; работа в очереди с ценой 16 (8 + 4 + 2 + 1 + 1).
  - **F56** — обещание §5.5 про индекс команд не исполнено: записано сноской в §5.5 (333–339) и позицией в §9 (3000–3006).
  - **F57** — числа гейта Task 44 (88 файлов и 303 из 303) ни одним логом той задачи не подкреплены; риск снят не пересъёмкой, а перевыполнением критерия 4 §12 по замеру 69 (96 файлов при пороге «больше 87»). В той же записи Task 44 адрес `form_key_of(path)` «строки 155–177» на дереве `bf0ea78` расходится: функция занимает 155–189; историческая запись лиджера не переписывается.
  - **F58** — канал имён формы стоит до коллекций метаданных, общих модулей и глобальных свойств (`check/bsl/semantic.py:629-631`), поэтому реквизит с именем, совпадающим с именем коллекции или глобального свойства, затеняет его молча (`RType(None)`, `resolve_member` при неизвестном базовом типе ничего не сообщает — `:669-670`). Цена измерена: 34 находки `IDS_STX_METHODNOTFOUND` (1 863 → 1 829) в излишке закрытого 196.
  - **F59** — в кириллическом слове докстринга скрипта `m69_final_gates.py` (строка 16) оказался иероглиф — флаг CJK сканера, тот же класс, что F42. Скрипт лежит в `<tmp>\opencode` и в репозиторий не попадает, а его размер и число строк (24 408 b, 386 строк) процитированы в §7.5.20 дизайн-дока: переписывать объявленный артефакт после прогона — значит сделать цитату устаревшей, поэтому файл оставлен, и об этом сказано здесь. Ещё две строки этого класса — в черновнике этой записи `t50_rec50.md` (строка 7, заменён набело) и в отчёте ревьюера `t50_review_report.md` (строки 35, 70 и 1554 из 2 357; отчёт — вывод модели, в репозиторий не попадает). Скан пяти коммитимых документов даёт 0 флагов CJK. Следующий свободный номер дефекта — **F60**.
- **Что после Task 50 остаётся открытым (записано не для галочки, а потому что это не сделано).** Перенос чисел замера 69 в перечень артефактов §13 отложен и является работой следующей сводки (напоминание стоит в §13, строки 1463–1471); восемь отложенных замечаний ревьюера уровня Minor стоят в §10 со своими адресами; дополнение трёх формных блоков таблицы сигнатур (цена 16 находок) остаётся в очереди плана вместе с `TABULAR_METHODS`; пересъёмка логов Task 44 по копии коммитов — следующей итерации (F57); `C3` и `C5`–`C10` открыты в плане оптимизации; индекс команд (§5.5) не исполнен (F56); 1С в этой итерации не запускалась.

- **Скан текстов и сверка с HEAD (шаг 5 плана).** Сканер — `scan_texts.py`, прогоны через `python -I`, сравнение мультимножеств пар (паттерн, текст), а не номеров строк (урок F31). Первый прогон (`iter15_task50_scan_docs.log`, 3 650 b) был по четырём документам — дизайн-док, план оптимизации, файл дефектов данных и лиджер (§13 тогда ещё не был правлен): итог 0 новых флагов. Второй прогон после правки §13 (`iter15_task50_scan_docs2.log`, 4 678 b, и `iter15_task50_scan_pair2.log`, 577 b) дал 3 новых флага GLUE — все три внутри настоящего имени типа платформы `ЗаписьPDF` (дизайн-док, файл дефектов данных и §13). Это не опечатка склейки, поэтому снято узким механизмом сканера: в список дословных имён метаданных добавлена одна запись `ЗаписьPDF`, проверенная на диске как тип платформы (`p1c/src/p1c/data/platform_arities.py:12726`, файл 22 188 строк); раньше в этом списке было шесть имён, стало семь. Третий прогон (`iter15_task50_scan_docs3.log`, 4 538 b, и `iter15_task50_scan_pair3.log`, 577 b) — итог по пяти документам: новых флагов 0, исчезнувших 0; по документу — дизайн-док 0 флагов (вербатим-вынесений 28 против 27 в копии HEAD), план 0, файл дефектов данных 3 флага ANG в обоих состояниях, §13 — 5 флагов GLUE в обоих состояниях (вербатим 19 против 18), лиджер 13 (GLUE 11 и ANG 2) в обоих состояниях. Финальный прогон после дописывания этой записи — `iter15_task50_scan_docs4.log` и `iter15_task50_scan_pair4.log`; его итог назван здесь же заранее и проверяется прогоном сразу после дописывания и до коммита: новых флагов 0 и исчезнувших 0; расхождение пришлось бы исправлять в этой же записи, и только после этого документы уходят в коммит.

- **Коммит документов (шаг 5).** В `effektivnost-otdela`: этот коммит документов (parent `156810c`), 5 файлов, 894 вставок и 47 снятых строк: дизайн-док (+586 / −43), `docs/план-оптимизации-p1c.md` (+24 / −2), `docs/evidence/p1c-data-defects.md` (+136 / −0), `docs/evidence/tool-coverage.md` (+41 / −2) и лиджер (107 / −0). Subject — ровно тот, что предписан шагом 5 плана: `dokumentacii iteracii 15: statusy blokov C/G, zapisi zamjerov 55-58, lidzher task 43-49`; тело — ASCII-транслитерацией из файла `iter15_task50_docs_commit.txt` через `git commit -F`, с атрибуцией `Co-Authored-By: Claude Code <noreply@anthropic.com>`, и в теле дополнительно названы замер 69 (его в перечне плана не было, потому что план писался до него), новый §7.5.20, правки по замечаниям ревьюера F49–F58 и дописанные записи лиджера вместе с этой. Номер этого коммита запись не называет: она входит в тот же коммит, и назвать его номер значило бы изменить запись после того, как она закоммичена. Текст сообщения просканирован тем же сканером (`iter15_task50_scan_commit.log`). Пуша нет.

- **Судьба предсказаний.** `iter15_m69_predictions.md` (20 пунктов) написан до прогона и после прогона не переписан; разошёлся один пункт (длительность харнесса). Предсказаний замера 69 по одному пункту не хватало: сравнение `skipped_rules` сводкой не делалось, и оно мерялось отдельным скриптом, а не правкой файла предсказаний. Файлы предсказаний прежних замеров (в том числе `iter15_m58_predictions.md`) и прежние сборки сводок (`m58_task49_gate.summary.log.prev1` и `.prev2`, `m69_final_gates.prev1.log`) не переписывались: исторические записей замеров и имена артефактов в этом доме не правятся, к ним дописываются пояснения.

- **Номера замеров.** **69** — финальные прогоны итерации и повтор корпуса со сверкой с замером 58: **исполнен** (`m69_final_gates.py`, `m69_final_gates.log`, `iter15_m69_predictions.md`, `m69_task50_pulsar.json`, `m69_task50_gate.json`, `m69_skipped_rules.py` и его лог), закреплён §7.5.20 дизайн-дока (2663–2913) и абзацем нумерации (2873–2913). Следующий свободный номер — **70** (и в дизайн-доке 2888, и в §7.3 файла `docs/evidence/p1c-data-defects.md` 557). Разведка этой задачи замером не считается и файла предсказаний не имеет: `t50_preflight.py`, `t50_gc_probe.py`, `t50_gc_names.py`, `t50_gc_names2.py`, `t50_resid_probe.py`, `t50_resid_probe2.py`, `t50_leftover_probe.py`, `t50_anchor_probe.py`, `t50_anchor_probe2.py`, `t50_addr_verify.py`, `t50_pred_files.py`, `t50_task43_scan_verify.py`, `t50_scan_task44.py`, `t50_artifact_list.py`, `t50_diff_map.py`, `t50_final_stats.py`, `t50_doc_lengths.py`, `t50_doc_stats.py`, `t50_doc_heading.py`, `t50_doc_para2.py`, `t50_doc_style.py`, `t50_doc_verify.py`, `t50_doc_rewrap.py`, `t50_para_diag.py`.

- **Артефакты этой записи** (все в `<tmp>\opencode`, если не сказано иное). Прогоны замера 69: `m69_final_gates.py` (24 408 b), `m69_final_gates.log` (18 853 b), `m69_final_gates.stdout.log` (19 077 b), `m69_final_gates.stderr.log` (0 b), `m69_final_gates.prev1.log` (18 126 b), `m69_final_gates.stdout.prev1.log` (18 346 b), `m69_final_gates.stderr.prev1.log` (0 b), `m69_skipped_rules.py` (4 049 b), `m69_skipped_rules.log` (2 728 b), `iter15_m69_predictions.md` (7 580 b), `m69_task50_runtests.log` (3 704 b), `m69_task50_core.log` (448 b), `m69_task50_formtests.log` (8 872 b), `m69_task50_contour.log` (4 817 b), `m69_task50_gate.json` (3 486 b), `m69_task50_gate.err` (111 b), `m69_task50_gate.log` (0 b), `m69_task50_pulsar.json` (6 400 757 b), `m69_task50_pulsar.err` (117 b), `m69_task50_pulsar.log` (0 b). Правщики документов: `t50_design_edit.py` (48 808 b) с логом (1 221 b), `t50_plan_edit.py` (8 578 b) с логом (394 b), `t50_defects_edit.py` (15 882 b) с логом (453 b), `t50_ledger_records.py` (15 317 b) с логом (2 852 b), `t50_ledger_new_rows.md` (54 125 b, 54 строки). Разведка и сверки: `t50_resid_probe.py` (6 403 b) и его лог (7 973 b), `t50_resid_probe2.py` (5 560 b) и его лог (5 260 b), `t50_addr_verify.py` (1 846 b) и `t50_addr_verify.log` (19 870 b), `t50_pred_files.py` (3 795 b) и `t50_pred_files.log` (4 686 b), `t50_leftover_probe.py` (18 476 b) и его лог (14 436 b), `t50_gc_probe.py` (5 137 b) и `t50_gc_probe.log` (2 261 b), `t50_gc_names.py` (3 312 b) и `t50_gc_names2.py` (4 293 b) с их логами, `t50_preflight.py` (6 420 b) и `t50_preflight.log` (14 043 b), `t50_vocab_snapshot.txt` (91 094 b, 2 500 строк — снимок удалённого файла из коммита перед `76a45b0`). Измерение состояния документов: `t50_final_stats.py` (7 798 b) и `iter15_task50_final_stats.log` (6 312 b), `t50_diff_map.py` (4 099 b) и `iter15_task50_diff_map.log` (16 511 b), `t50_artifact_list.py` (2 079 b) и `iter15_task50_artifacts.log` (5 398 b, 112 файлов). Ревью: `t50_review_report.md` (296 871 b), `t50_review_dump.py` (2 849 b) и `t50_review_dump.log` (769 563 b), `t50_review_issues.md` (24 641 b), `t50_review_text.md` (7 205 b). Скан документов: `t50_scan_docs.py` (7 952 b), `iter15_task50_scan_docs.log` (3 650 b), `iter15_task50_scan_docs2.log` (4 678 b), `iter15_task50_scan_docs3.log` (4 538 b), `iter15_task50_scan_pair.log` (455 b), `iter15_task50_scan_pair2.log` (577 b), `iter15_task50_scan_pair3.log` (577 b) и финальный прогон с суффиксом «4», `iter15_task50_scan_commit.log`. Снимки и копии HEAD: `t50_ledger_before.md` (404 696 b), `t50_base_progress.md` (350 517 b), `t50_head_progress.md` (347 925 b), `t50_base_design.md` (337 899 b), `t50_head_design.md` (335 090 b), `t50_base_plan_optimizacii.md` и `t50_head_planopt.md` (по 41 698 b), `t50_base_defects.md` и `t50_head_defects.md` (по 40 690 b), `t50_head_coverage.md` (154 665 b). Черновики записей: `t50_rec43.md` (15 846 b), `t50_rec44.md` (15 952 b), `t50_rec49.md` (16 490 b), `t50_rec50.md` (22 202 b — черновик этой записи, набранный до ревью и заменённый набело: в нём семь названий артефактов, которых на диске нет, и незаполненные метки). Сообщение коммита: `iter15_task50_docs_commit.txt`. Набор самой этой записи и её дописывание: `t50_ledger_record.md` (набор с метками вместо чисел), `t50_ledger_record_final.md` (тот же набор после подстановки измеренных чисел) и `iter15_task50_ledger_append.log` (протокол дописывания: строки до и после, подставленные числа, сверка с `git diff --numstat`); их размеры запись не называет — эти файлы рождаются в том же прогоне, что и дописывание, и назвать их размер значило бы мерить файл, который ещё не дописан.

### Журнал итерации 15: сверка пяти критериев готовности §12 дизайн-дока с объявленными артефактами замеров (2026-11-06; новым блоком §12.1 того же дизайн-дока и этой записью лиджера)

- **Что исполнено этой записью и чем мерялось.** Раздел §12 «Критерии готовности» (строки 3333–3352 дизайн-дока, пять пунктов) сверен померочно с артефактами, которые объявлены прежними прогонами: сводкой замера 69 (`m69_final_gates.log`, 157 строк), его тестовым логом (`m69_task50_runtests.log`, 98 строк), перечнем файлов предсказаний (`t50_pred_files.log`), записями самого дизайн-дока (§4.1, §7.5.20, §9, §10, §11) и коммитом документов Task 50. Скрипт сверки — `k12_close_probe.py` (11 384 b), протокол — `iter15_k12_close.log`. Это не замер: нового прогона анализатора не делался ни разу, и номер замеру не выдаётся — следующий свободный остаётся **70**, следующий свободный номер дефекта — **F60** (новых дефектов сверка не нашла). Единственное новое измерение — git-факт о двух тестах пункта 4: их отсутствие в дереве `00cad6c` меряется `git cat-file -e` по интервалу `00cad6c..bf0ea78` в `p1c` (16 коммитов, 22 изменённых файла в `tests/`), и это единственное измерение, которого прежде ни в одном артефакте не было.

- **Пункт 1 (G закрыт) — закрыт.** Артефакт `m69_task50_gate.json` (3 486 b): `stats` с `files` 8 и `summary.count` 0, stderr прогона сохранён (`m69_task50_gate.err` 111 b), подпись `4edf65fe906bbcb4…`; в сводке замера 69 этот пункт сверяется отдельной строкой с расхождением 0, и побайтовое равенство гейтов Task 48, Task 49 и 69 подтверждено там же. Ноль на фикстуре подтверждают также гейты замеров 68 и 58.

- **Пункт 2 (корпусный гейт) — закрыт, отклонения уже разобраны записью §7.5.20, новых не появилось.** Одиннадцать кодов формной строки: база А 26 102 (строки 2693–2697 дизайн-дока) против итога 4 264 (строки 70–80 сводки замера 69); сумма уменьшения 21 838 при плановой 21 886 — расхождение записано в §7.5.20 как излишек закрытого 196 и открытые 244. Потолки §8 выдержаны по всем семи позициям (формные 8 / 7 / 6, корпусные 12 / 7 / 10): в сводке семь строк сверки В20 и В21 с расхождением 0. Из трёх кодов, которым пункт запрещает расти, `IDS_STX_METHODNOTFOUND` уменьшился (1 863 → 1 829), `IDS_STX_CTOR_NOTFOUND` не изменился (1 303 → 1 303), а `IDS_STX_PROPERTYNOTFOUND` вырос с 15 до 259 — и это число уже объяснено записью §7.5.20: 15 принадлежит базе А, в базе Б61 формная строка этого кода была 258 ещё до итерации (пакет 8 открыл 473 находки, 467 из них по этому коду), а в цепи правок этой итерации прирост равен одной находке на этапе Task 47 (258 → 259, замер 66). Непредсказанных сдвигов в повторе 69 относительно 58 — 0 кодов, закрыто 0 и открыто 0.

- **Пункт 3 (предпосылка §6 как самостоятельный замер) — закрыт, с одной незакрытой деталью, и она не новая.** Предпосылка мерялась до правок кода со своими предсказаниями: `iter15_m56_predictions.md` (9 801 b) и `iter15_m57_predictions.md` (11 678 b) — остаток первого звена 0 промахов у всех 44 измеренных типов владельца, «Ссылка» закрыла 286 промахов из 334 вместо ожидавших 287; после правок — прогоны с предсказаниями `iter15_m66_predictions.md` и `iter15_m66b_predictions.md`, гейты невключаемых типов `iter15_m57f_predictions.md` и `iter15_m57g_predictions.md`. Оценка «примерно 47 из 334» записана неверной (запись §7.5.17), критерием стал измеренный остаток, и решение о невключении стоит в двух названных пунктом местах: журнал §4.1 (строки 142, 143 и 145) и §10 (строка 3022). Список добавленных стандартных свойств назван местом объявления (§9, строки 2971–2973) и числом 140 закрытых (строка 2811). Незакрытая деталь ровно одна, и она записана раньше: у предсказаний прогонов Task 46 отдельного файла нет — прогон лежит под именем задачи (`iter15_task46_pulsar.json`), предсказания замера 64 живут в `iter15_task45_predictions.md` (9 219 b), а отсутствие файлов предсказаний у 17 номеров записано дефектом F51; перечнем `t50_pred_files.log` это подтверждено повторно, и в перечень номеров 44–69 добавлено, что файлов `iter15_m64_predictions.md`, `iter15_m65_predictions.md` и `iter15_task46_predictions.md` на диске нет вовсе.

- **Пункт 4 (тесты) — закрыт, и здесь снято единственное новое измерение.** `m69_task50_runtests.log`: строк «[ok]» 96 и «[fail]» 0, итоговая строка «тестов: 96, неудачно: 0» при пороге «больше 87». Два теста, названные пунктом по содержанию, — `tests/load/test_standard_attributes.py` (114 строк, докстринг «Стандартные свойства и методы объектных типов: то, чего нет в атрибутах выгрузки») и `tests/check_bsl/test_form_context.py` (321 строка; проверки «голый Объект в форме с obj_type», «реквизит объекта читается без находок», «отсутствующий член строгого типа», «строгость идёт и по второму звену цепочки») — меряются `git cat-file -e` как отсутствовавшие на `00cad6c` и как новые в этом интервале (+114 / −0 и +321 / −0). Число тестовых файлов сверено двумя способами, и они сошлись: список дерева `tests/` на `bf0ea78` и тот же глоб `*.py` с проверкой начала имени, каким пользуется `scripts/run_tests.py`, дают по 96 файла и равные множества (первая попытка сосчитать их фильтром по имени каталога дала 101 — пять файлов лежат в каталогах с именем `test_*`, сами так не называются; расхождение снято тем, что считать стало тем же способом, что и харнесс). Контур: «Ran 303 tests» и `OK` (`m69_task50_contour.log` 4 817 b).

- **Пункт 5 (документы закоммичены и проверены сканом) — закрыт с отложенной частью, названной заранее.** Пять документов ушли коммитом `8f00000` (5 файлов, +894 / −47), скан пяти документов дал 0 новых и 0 исчезнувших флагов (`iter15_task50_scan_docs4.log`, `iter15_task50_scan_pair4.log`). Отложено: чисел замера 69 в перечне артефактов §13 файла `docs/evidence/tool-coverage.md` нет (напоминание стоит в его строках 1463–1471), и восемь замечаний ревьюера уровня Minor стоят в §10 дизайн-дока со своими адресами.

- **Что правлено этой записью.** Дизайн-док: блок «### 12.1 Сверка критериев по мерке» дописан в конец файла, после строки 3352 (последняя строка раздела §12), и это единственная правка дизайн-дока — файл был 3 352 строк, стал 3 419 строк, вставок 67 и снятых 0. Выбор места не случаен: раздел §12 был последним в файле (разделов «## » после него — 0, меряется `k12_close_probe.py`), поэтому ни один адрес, на который ссылается другой документ, не сдвинулся; в файле до этой правки нет ни одного заголовка «12.1» (вхождение «12.1» одно — длительность «12.194s» в строке 2651). Лиджер: эта запись дописана в его конец одним блоком, как стоят прежние записи; правка лиджера этим коммитом — 24 строк вставок и 0 снятых, файл после дописывания — 2 723 строк. Байтовые размеры этих двух файлов запись не называет: правка цифр внутри строки меняет размер файла, и названное число стало бы неверным в момент записи (прецеденты F39 и F40). Ни один документ репозитория не ссылается на номера строк лиджера (проверено ранее: поиск `progress.md:` по `docs/` даёт 0 совпадений), а адреса разделов дизайн-дока, названные в §12.1 (142, 143, 145, 2693–2697, 2811, 2971–2973, 3022), лежат ниже дописанного блока и от дописывания не изменились.

- **Скан текстов и сверка с HEAD.** Сканер — домовый `scan_texts.py`, прогоны через `python -I`, сравнение мультимножеств пар (паттерн, текст) против копий из HEAD, а не номеров строк (урок F31); прогон `python -I t50_scan_docs.py 5` делает это по всем пяти документам сразу. Его итог назван в этой записи заранее и проверяется прогоном сразу после дописывания и до коммита: новых флагов 0 и исчезнувших 0. Расхождение пришлось бы исправлять в этой же записи.

- **Коммит.** В `effektivnost-otdela` — этот коммит (parent `8f00000`), 2 файла: дизайн-док (67 / −0) и лиджер (24 / −0), сумма 91 вставок и 0 снятых. Subject набран ASCII-транслитерацией, тело — из файла `iter15_k12_commit.txt` через `git commit -F`, с атрибуцией `Co-Authored-By: Claude Code <noreply@anthropic.com>`; текст сообщения просканирован тем же сканером. Номера этого коммита запись не называет: она входит в него же (урок Task 50). Пуша нет: разрешения на пуш в этом разговоре не выдавалось, ветка `feat/config-effektivnost` стоит на `8f00000` до этой правки, и `p1c` не тронут — он на `bf0ea78` с чистым рабочим деревом (оба дерева чистоту меряет `k12_close_probe.py`). Правок кода эта запись не делает: у сверки критериев их нет по смыслу.

- **Что после сверки остаётся открытым (список не изменился).** Перенос чисел замера 69 в перечень артефактов §13 (`docs/evidence/tool-coverage.md`, строки 1463–1471); восемь отложенных замечаний ревьюера уровня Minor в §10 дизайн-дока; дополнение трёх формных блоков таблицы сигнатур под пять имён формных вызовов (цена 16 находок — 8 + 4 + 2 + 1 + 1) вместе с `TABULAR_METHODS`; `C3` и `C5`–`C10` в плане оптимизации; индекс команд (§5.5, дефект F56); пересъёмка логов Task 44 (F57). 1С в этой итерации не запускалась.

- **Артефакты этой записи** (в `<tmp>\opencode`). Сверка: `k12_close_probe.py` (11 384 b) и `iter15_k12_close.log` — они созданы до правки документов и после правки не менялись, поэтому их размеры названы. Снимок состояния дизайн-дока до дописывания: `k12_design_before.md` (копия из HEAD `8f00000` командой `git show` — 406 741 b, 3 352 строк, CR 0) и `k12_design_working_before.md` (тот же рабочий файл до правки, но с снятым завершающим переводом строки — 410 092 b, 3 352 строк, CR 3 351, и потому CR в нём на один меньше, чем в самом файле на диске). Набор блока §12.1 — `k12_block_121.md` (LF), набор этой записи — `k12_ledger_record.md` (с метками вместо чисел) и `k12_ledger_record_final.md` (тот же набор после подстановки), дописывание обоих файлов и сверка с `git diff --numstat` — `k12_append.py` с протоколом `iter15_k12_append.log`; их размеры запись не называет, потому что эти файлы рождаются в том же прогоне, что и дописывание. Скан: `iter15_k12_scan_docs5.log` и `iter15_k12_scan_pair5.log`, копия сообщения коммита — `iter15_k12_commit.txt`.
