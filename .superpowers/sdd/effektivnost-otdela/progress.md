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
- Открытая граница итерации: ни один класс исполнения (Task 12–14) не подтверждён — живость форм,
  отчёта и обработки проверяется статикой (`p1c.check.bsl`, `p1c.check.forms`) и GUI; следующий
  замер исполнения возможен только в изолированной ИБ, живую ИБ пользователя трогать нельзя.
