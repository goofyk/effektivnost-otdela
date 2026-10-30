# План итерации 13: читатель `p1c` добирает языки, подсистемы, дескрипторы и содержимое макетов; счётчик classes становится манифестным

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (нативное выполнение в этой сессии) вместе с superpowers:test-driven-development — задачи связаны одной формой учёта (манифест прочитанных файлов) и одним корпусом-фикстурой, поэтому их пишет и выполняет один исполнитель; измерительные задачи (Task 27) идут тем же исполнителем, потому что 1С-прогоны нельзя параллелить. Steps use checkbox (`- [ ]`) syntax for tracking. Нумерация продолжается с `Task 21` прежнего плана `docs/superpowers/plans/2026-10-26-effektivnost-otdela.md`.

**Goal:** научить читатель `p1c` реально открывать `Languages/<Имя>.xml`, `Subsystems/<Имя>.xml`, дескрипторы `Roles/<Имя>.xml` и `Forms/<Имя>.xml`, дескрипторы макетов `Templates/<Имя>.xml` и содержимое схемы компоновки данных `Templates/<Имя>/Ext/Template.xml`, называть класс каждого реально прочитанного файла; перестроить `scripts/counts.py` на этот манифест; сделать один 1С-прогон `gate-16` и переснять матрицу покрытия.

**Architecture:** правки идут в двух репозиториях: читатель и его тесты — в `p1c` (`src/p1c/load/reader.py`, `src/p1c/load/cli.py`, `tests/load/`), манифестный счётчик и его тест — в контуре `effektivnost-otdela` (`scripts/counts.py`, `tests/test_contour.py`); матрица и документы контура переснимаются против нового артефакта `reports/gate-16.json`. Корпус конфигурации не меняется, меняется только то, что о нём известно инструментам.

**Tech Stack:** Python 3.15; тесты `p1c` — скрипты с `check()`/`fails` под runner `python scripts/run_tests.py` (в `p1c` `unittest discover` не применяется); тесты контура — stdlib `unittest` (`python -m unittest discover -s tests`); 1C:Enterprise 8.3.27.1606 в режимах `DESIGNER /LoadConfigFromFiles`, `/CheckModules`, `/DumpConfigToFiles` через `scripts/ib_loop.py`; форматы файлов конфигурации (MetaDataObject XML, `DataCompositionSchema` XML, BSL).

**Spec:** блок A таблицы `docs/план-оптимизации-p1c.md` (строки A3–A5 и метрика «число классов метаданных, пути файлов которых называет сам инструмент»), раздел «Статус блока A к итерации 12»; решение исполнителя итерации 13 в `.superpowers/sdd/effektivnost-otdela/progress.md`.

## Global Constraints

- Ответы и тексты документов — по-русски; имена флагов и режимов платформы — только из замера `p1c/src/p1c/data/test_cli_flags.json`, выдуманные значения помечать явно как неподтверждённые.
- 1С-прогоны строго по одному, не параллельно; тяжёлые обходы корпусов — вне окон 1С-замеров.
- Гейт-ИБ (`<tmp>\p1c_effektivnost\ib`) модифицирующими вариантами не трогать; модифицирующие варианты только на `<tmp>\p1c_effektivnost\probe_ib` с `--allow-mutating`. В этой итерации модифицирующих вариантов нет вовсе.
- `PREDICTIONS` записываются до прогона и после прогона не переписываются; непредсказанные шаги идут отдельным списком с причиной.
- Абсолютных путей в `scripts`, `probe`, `tests` и документах нет: только свёртки `<work>`, `<tmp>`, `<repo>`, `<dump>`, `<cfg>`, `<p1c>` и относительные пути репозитория.
- Строки `scripts/exec_probe.py` — не длиннее 115 символов; `progress.md` коммитится отдельно от кода и документов.
- Перед коммитом тексты проверять сканами на склейки латиницы с кириллицей, CJK, англицызмы и ABS-PATH.
- Значения в модели и в тестах — только из замеренных файлов корпуса; ничего «правдоподобного» по памяти платформенных форматов.
- Эталон `docs/expected-metadata.json` (`iteration: 5`, 22 класса, `files 31`, `bsl_module 8`, `object_module 6`) в этой итерации не меняется.
- `docs/canonical-rights.json` и контроль неподвижности прав (`scripts/rights.py`) не трогаются.

## Review Focus

- Манифест обязан создаваться в точке фактического открытия файла, а не «по раскладке папок»: иначе он повторяет `layout.py` и перестаёт быть доказательством, что инструмент читал файл.
- Класс `files` манифеста (30) против `files 31` у layout — различие ровно в одном файле `Configuration.xml`, который читатель не открывает; это записывается как факт и как граница паритета, а не как ошибка и не закрывается чтением корневого дескриптора.
- Манифестные пути обязаны нормализоваться тем же `base`, что и остальные пути модели (у EDT снимается `src/`), иначе четыре теста паритета `m1 == m2` расходятся на двух фикстурах `p1c/examples`.
- Класс `bsl_module 8` в манифестной сверке намеренно пересекается с `object_module 6` и `form_module 2`: это разные наблюдения об одном множестве файлов, и пересечение надо объяснить в тесте, а не «починить» вычитанием.
- Открытие `Forms/<Имя>/Ext/Form/Module.bsl` — решение с последствиями: либо модуль формы идёт в `module_jobs` (и у записи формы появляются `exports`, и меняется `skipped_module_files`), либо `form_module` называется только по открытым файлам манифеста. Оба варианта оставляют `test_scan.py:62-71` (форма `skipped_files` и сообщение `[context] модулей не прочитано: 1`) зелёным — проверять на факте.
- Матрица мерит хиты по тексту JSON-отчёта, поэтому пути манифеста должны попасть в вывод `load model` (`MODEL_KEYS` и payload `{"model": model}`); без этого пересъёмка даст те же 7 классов по пути.
- `role` как класс обязан появиться именно путём файла `Roles/<Имя>.xml`, а не именем роли в отчёте: `PATH_ONLY_KINDS` в `probe/tool_coverage.py` при этом не расширяется, и это надо проверить, а не предполагать.

---

### Task 21: фикстурный корпус `p1c/examples/managed_app` (копия замеренного `cfg`)

**Files:**
- Create: `examples/managed_app/` в репозитории `p1c` — копия `cfg/ЭффективностьОтдела` (31 файл, включая `Languages/Русский.xml`, `Subsystems/ЭффективностьОтдела.xml`, `Roles/СотрудникОтдела.xml`, `Roles/СотрудникОтдела/Ext/Rights.xml`, `Catalogs/Сотрудники/Forms/ФормаЭлемента.xml` и `…/Ext/Form.xml` и `…/Ext/Form/Module.bsl`, `Reports/ОтчётЗагрузки/Templates/ОсновнаяСхемаКомпоновкиДанных.xml` и `…/Ext/Template.xml`, `Catalogs/Сотрудники/Ext/Predefined.xml`, `Configuration.xml`)
- Create: `p1c/tests/load/test_fixture_corpus.py`

**Interfaces:**
- Produces: `examples/managed_app` — корпус layout-раскладки конфигуратора (не EDT), на котором дальше проверяются все новые классы; относительные posix-пути файлов совпадают с путями `layout_counts("cfg/ЭффективностьОтдела")` в контуре.
- Consumes: замеренный список 31 файла корпуса контура.

- [x] **Step 1: Write the failing test** `tests/load/test_fixture_corpus.py` (форма `check()`/`fails` по образцу `tests/load/test_rights_predefined.py`): корпус существует, содержит ровно 31 файл, и sha256 каждого файла совпадает с sha256 парного файла корпуса контура; ожидается `FAILED` (каталога нет).
- [x] **Step 2: Run to verify it fails** — `python tests/load/test_fixture_corpus.py`, ожидается отказ «каталог корпуса отсутствует».
- [x] **Step 3: Implement** — скопировать `cfg/ЭффективностьОтдела` в `examples/managed_app` без изменений содержимого (никакой перекодировки, BOM и CRLF сохраняются как есть).
- [x] **Step 4: Run to verify it passes** — `python tests/load/test_fixture_corpus.py`, ожидается 31 совпадение sha256 и код 0.
- [x] **Step 5: Сверка с layout-числами** — в контуре `python -c`-скриптом (файлом во временном каталоге, не однострочником с кавычками) вызвать `scripts/layout.py::layout_counts` на `examples/managed_app` и убедиться, что получается те же 22 класса и те же числа, что для `cfg/ЭффективностьОтдела` (в том числе `files 31`, `bsl_module 8`, `object_module 6`, `form_descriptor 2`, `role 2`).
- [x] **Step 6: Commit** в `p1c` — отдельным коммитом фикстуры и её теста.

### Task 22: манифест прочитанных файлов как форма учёта А5

**Files:**
- Modify: `p1c/src/p1c/load/reader.py` (собрать модель и точки открытия: цикл коллекций `720-798`, `Roles` `803-809`, `CommonModules` `811-821`, `CommonAttributes` `825-831`, `CommonForms` `834-839`, фазы 2–3 `846-923`)
- Create: `p1c/tests/load/test_read_manifest.py`

**Interfaces:**
- Produces: `load_configuration_model(root, …)` возвращает ключ `read_files` — список записей `{"path": <posix относительно base>, "kind": <таксон>}`; путь нормализуется тем же `base`, что и `path` у записей прав, предопределённых данных и форм (`701-703`, `714`); класс присваивает парсер, открывший файл. Классы на этом этапе: девять дескрипторов коллекций, `object_module`, `role_rights`, `predefined_data`.
- Consumes: фикстура `examples/managed_app` (Task 21) и прежние фикстуры `examples/designer_dump`, `examples/edt_project`.

- [x] **Step 1: Write the failing test** `tests/load/test_read_manifest.py`: для `examples/designer_dump` манифест непустой и содержит пару `("Roles/ПолныеПрава/Ext/Rights.xml", "role_rights")`, `("Catalogs/Номенклатура/Ext/ManagerModule.bsl", "object_module")`; для `examples/edt_project` тот же файл записан без `src/`; ожидается отказ (ключа `read_files` нет).
- [x] **Step 2: Run to verify the reason of the failure** — `python tests/load/test_read_manifest.py`, убедиться, что причина — отсутствие ключа, а не ошибка парсинга (отказали ровно 27 проверок манифеста, `skipped_files` при этом на месте).
- [x] **Step 3: Implement минимально** — одна точка `_opened(rel_path, kind)` в читателе, вызываемая там, где файл реально открывается (дескриптор коллекции перед `parse_object_xml`, файл модуля перед `_read_module`, `Ext/Rights.xml` перед `parse_rights_xml`, `Ext/Predefined.xml` перед `parse_predefined_xml`); никакого обхода папок «для количества». Отступление от формулировки: файл модуля в `Ext/` называется после того как скан подтвердил чтение (`scan_one` возвращает `read`), потому что отсутствующий и нечитаемый модуль дают одинаковый пустой список экспортов и иначе манифест был бы нечестным.
- [x] **Step 4: Run tests to verify they pass** — `python tests/load/test_read_manifest.py`, затем `python scripts/run_tests.py`; особое внимание к четырём тестам полного паритета модели (`tests/load/test_reader.py:82`, `tests/load/test_sources.py:44`, `tests/load/test_rights_predefined.py:149`, `tests/metadata/test_loader.py:85`): манифест в них попадает как общий ключ, поэтому пути обязаны совпасть на обеих фикстурах. Правки этих четырёх тестов не понадобились.
- [x] **Step 5: Commit** — код читателя и его тест одним коммитом в `p1c`.

### Task 23: языки, подсистемы и дескрипторы ролей

**Files:**
- Modify: `p1c/src/p1c/load/reader.py` (`COLLECTIONS_MAP` `76-137`, блок `Roles` `803-809`, ключи модели `709-711`)
- Modify: `p1c/src/p1c/load/cli.py` (`MODEL_KEYS` `69-70`, `_measure` `73-75`) — перенесено в Task 25: правка ключей отчёта без теста в этой задаче осталась бы непроверенной
- Create: `p1c/tests/load/test_languages_subsystems_roles.py`

**Interfaces:**
- Produces: ключи модели `languages`, `subsystems`, `role_descriptors`; записи дословные из замеренных файлов: язык — `name`, `synonym` (текст `v8:item`/`v8:lang ru`/`v8:content`), `language_code`, `path`; подсистема — `name`, `synonym`, `content` (9 строк `Catalog.Сотрудники` … `CommonModule.РасчётПоказателей`), `path`; дескриптор роли — `name`, `synonym`, `comment`, `path`. Манифестные пары: `("Languages/Русский.xml", "language")`, `("Subsystems/ЭффективностьОтдела.xml", "subsystem")`, `("Roles/СотрудникОтдела.xml", "role")`.
- Consumes: Task 22 (`_opened`), фикстура `examples/managed_app`.

- [x] **Step 1: Write the failing test** на три класса: ожидается `languages == [{"name": "Русский", "synonym": "Русский", "language_code": "ru", "path": "Languages/Русский.xml"}]` (значения — из замеренного файла), подсистема с 9 строками `content` в порядке файла, и ровно две записи `role_descriptors` с путями `Roles/СотрудникОтдела.xml` и `Roles/АдминистраторСистемы.xml` (в фикстуре `examples/managed_app` и в `cfg` именно эти имена; прежде в шаге было указано `Roles/ПолныеПрава.xml` — имя из другой фикстуры `examples/designer_dump`, в боевом корпусе такой роли нет); плюс проверки манифестных пар. Отказ — ключей нет.
- [x] **Step 2: Run to verify the reason** — `python tests/load/test_languages_subsystems_roles.py`; отказали 16 проверок, две из них — ошибки самого теста (ссылка `Catalog.Сотрудники` проверялась полным именем вместо короткого `Сотрудники`; вместо множества ключей сравнивался список с дублями), исправлены в тесте до реализации.
- [x] **Step 3: Implement** — три парсера (`parse_language_xml`, `parse_subsystem_xml`, `parse_role_descriptor_xml`) в том же стиле, что `parse_rights_xml` (`594-607`): `ET.parse` → `_local`/`_find`/`_text`; `_local` снимает пространство имён, поэтому `Synonym` читается тем же `_text`, что и остальные свойства; вложенность `v8:item` разворачивается одной вспомогательной функцией, которая возвращает текст `v8:content`. Открытие дескриптора роли — до чтения `Ext/Rights.xml`, класс `role`. Отступление: свойства читаются двумя вспомогательными функциями `_descriptor_properties` (находит `Properties` внутри любого корневого элемента) и `_property_text` (текст элемента либо текст `v8:content` внутри `v8:item`) — у дескрипторов коллекций обёртка над `Properties` различается, а `Synonym` и `Comment` лежат не простым текстом. Обходы `Languages`, `Subsystems` и `Roles` сделаны отдельным циклом после цикла коллекций и перед чтением `Ext/Rights.xml`. Правка `cli.py` (`MODEL_KEYS`) из списка файлов этой задачи перенесена в Task 25, где для неё есть тест.
- [x] **Step 4: Run tests to verify they pass** — новый тест зелёный, `python scripts/run_tests.py`: тестов 77, неудачно 0; четыре паритетных теста правок не потребовали.
- [x] **Step 5: Commit** в `p1c` — `a220ef7` (`src/p1c/load/reader.py`, `tests/load/test_languages_subsystems_roles.py`).

### Task 24: дескрипторы форм, дескрипторы макетов и содержимое схемы компоновки данных

**Files:**
- Modify: `p1c/src/p1c/load/reader.py` (цикл коллекций `720-798` — обход `Forms` и `Templates` внутри папки объекта; блок `CommonForms` `834-839`; `parse_form_xml` `519-564`)
- Modify: `p1c/tests/load/test_read_manifest.py` (докстринг и проверка «модуль формы ещё не назван» — после того как модуль формы стал назван)
- Create: `p1c/tests/load/test_forms_templates.py`

**Interfaces:**
- Produces: ключи `form_descriptors` (`name`, `synonym`, `form_type`, `use_purposes` (`PlatformApplication`, `MobilePlatformApplication`), `path`), `templates` (`name`, `synonym`, `template_type` — дословно `DataCompositionSchema`, `path`) и `template_data` (разбор `Ext/Template.xml` с корнем `DataCompositionSchema` без обёртки `MetaDataObject`: имена источников данных, наборы данных с `xsi:type`, имена полей и `dataPath`, текст `<query>`); манифестные пары `form_descriptor`, `form_data`, `report_template`, `report_template_data`, `form_module`.
- Consumes: Task 22; замеренный текст `Ext/Template.xml` (152 строки).

- [x] **Step 1: Write the failing test**: дескрипторов форм ровно 2 с `form_type == "Managed"`; содержимое формы 2 (уже читаемые `Ext/Form.xml`); модулей формы 2 (пути `…/Ext/Form/Module.bsl`); дескриптор макета ровно 1 с `template_type == "DataCompositionSchema"`; содержимое макета — источник `ИсточникДанных1`, набор `НаборДанных1`, поля `Сотрудник` и … (по замеренному файлу), непустой текст запроса. Отказ — ключей `form_descriptors`/`templates`/`template_data` и пар `form_descriptor`/`report_template`/`report_template_data` нет. Отступление: обращения к полям записей формы в тесте сделаны через `get(...) or []`, иначе падение на первом же отсутствующем ключе снимало `Traceback` и скрывало остальные проверки (RED обязан показывать все проверки).
- [x] **Step 2: Run to verify the reason.** — отказали 26 проверок из 35, все по отсутствующим ключам и манифестным парам; остальные 9 проверок уже были зелёными (содержимое формы читалось и раньше).
- [x] **Step 3: Implement** — `parse_template_descriptor_xml`, `parse_template_data_xml`; обход `Forms` и `Templates` внутри папки объекта там же, где сейчас собираются формы (дескриптор читается как отдельный файл и получает свою манифестную пару, содержимое `Ext/…` — свою). Решение по модулям форм: выбран вариант с `module_jobs` — путь модуля формы добавляется в задания сканирования, и у записей форм (объектных и общих) появляется ключ `exports` из этого модуля; он проверяется тестом. `module_jobs` стал тройками `(ключ, путь, класс)`, чтобы класс брался из задания, а не подставлялся в фазе слияния единым `object_module` (иначе модуль формы нельзя было бы назвать `form_module`). Содержимое общих форм (`CommonForms/Имя/Ext/Form.xml`) тоже названо `form_data`, и её модуль сканируется как `form_module` — раскладка относит общие формы к тем же классам. `xsi:type` набора данных читается функцией `_xsi_type` (атрибут ищется по локальному имени, префикс пространства имён не фиксирован). `tests/load/test_scan.py:62-71` остался зелёным.
- [x] **Step 4: Run tests to verify they pass** — новый тест зелёный; `python scripts/run_tests.py`: тестов 78, неудачно 0 (в том числе `tests/core/test_wording.py` и `tests/core/test_layers.py`). Манифест фикстурного корпуса — 30 записей из 31 файла, не прочитан ровно `Configuration.xml`; `bsl_module 8` = `object_module 6` + `form_module 2`.
- [x] **Step 5: Commit** в `p1c` — `dcf0112` (`src/p1c/load/reader.py`, `tests/load/test_forms_templates.py`, `tests/load/test_read_manifest.py`: докстринг и проверка «модуль формы ещё не назван» заменены позитивной проверкой класса `form_module` и проверкой, что манифест корпуса называет каждый файл корпуса кроме `Configuration.xml`).

### Task 25: манифест и новые ключи попадают в отчёт `load model`

**Files:**
- Modify: `p1c/src/p1c/load/cli.py` (`MODEL_KEYS` `69-70`, `_measure` `73-75`, `cmd_model` `86-89`, `COMMANDS` `141-142`)
- Create: `p1c/tests/load/test_model_report_paths.py`

**Interfaces:**
- Produces: вывод `load model` содержит записи манифеста (posix-пути с экранированием `\/` читаются как дословные пути) и новые ключи-записи `languages`, `subsystems`, `role_descriptors`, `form_descriptors`, `templates`, `template_data`. Манифест в `MODEL_KEYS` не входит по той же причине, что `skipped_files`: это провенанс и диагноз, а не содержимое источника (решение зафиксировать в журнале).
- Consumes: Tasks 22–24.

- [x] **Step 1: Write the failing test** — `p1c/tests/load/test_model_report_paths.py`: четыре раздела (пути манифеста в выводе `json` и `text`; записи шести новых ключей в модели отчёта; выходные коды корпусов; манифест и диагноз не считаются записями источника). Форма проверки кодов — как `tests/load/test_rights_predefined.py:52-61` (`run_code`).
  - Отступление от формулировки: «пустой каталог → 1» по замеру неверно. Пустой каталог и корпус без признаков раскладки дают код **2** с сообщением «Не удалось определить раскладку…» — это ошибка аргумента (раскладка не опознана), а не пустой источник; код 1 даёт распознанный, но пустой корпус (`Configuration.xml` без остальных файлов). Тест проверяет оба случая.
  - Отступление: RED-кейсом выбран корпус `Configuration.xml` + один дескриптор (`Languages/Русский.xml`, `Subsystems/ЭффективностьОтдела.xml`, `Roles/СотрудникОтдела.xml` по отдельности): до пополнения `MODEL_KEYS` он давал код 1 («источник пустой»), после — код 0. Кейс «прочитано только содержимое макета» из теста убран: такой корпус заодно даёт запись объекта `Report.ОтчётЗагрузки` (из `Configuration.xml`), поэтому его код не свидетельствует о новом ключе.
- [x] **Step 2: Run to verify the reason.** — отказали 5 проверок из 35: три кода корпусов с одним дескриптором (было 1 вместо 0), «MODEL_KEYS содержит новые ключи-записи» и «каждый новый ключ даёт ровно одну запись источника» (`_measure` по прежним ключам даёт 0). Причина подтверждена: выходной код зависит только от `_measure`, а тот строится по `MODEL_KEYS`. Разделы (1)–(2) — пути манифеста и записи новых ключей в выводе — были зелёными и до правки: `cmd_model` печатает прочитанную модель целиком, поэтому пополнения `MODEL_KEYS` для вывода не требовалось (замер: JSON 66572 символа, текстовый вывод 1451 строка, все шесть ключей и `read_files` в них уже присутствовали).
- [x] **Step 3: Implement** — `MODEL_KEYS` пополнен только ключами-записями `languages`, `subsystems`, `role_descriptors`, `form_descriptors`, `templates`, `template_data` (комментарий объясняет, что дескриптор — такая же запись источника, как объект или роль, и почему `read_files`/`skipped_files` в счётчик не входят). Payload `cmd_model` и `COMMANDS` не тронуты: правка `cli.py` из Files-списка задачи (строки `cmd_model`, `COMMANDS`) свелась к `MODEL_KEYS`.
- [x] **Step 4: Run tests to verify they pass** — новый тест зелёный (35 проверок); `python scripts/run_tests.py`: тестов 79, неудачно 0; `python scripts/run_tests.py --smoke`: 93, неудачно 0.
- [x] **Step 5: Commit** в `p1c` — `900ae8d` (`src/p1c/load/cli.py`, `tests/load/test_model_report_paths.py`).

### Task 26: манифестный `counts_from_model` и паритет имён классов в контуре

**Files:**
- Modify: `scripts/counts.py` (`counts_from_model` `16-55`; `object_counts` `72-94` и её тексты `:79`, `:92-93` не менять)
- Modify: `tests/test_contour.py` (`CountsTest` `77-160`, в том числе `:84-88`, `:89-107`, докстринг `:115-116` и `assertNotIn("role", got)` `:127`)
- Create: запись паритета в `tests/test_contour.py`

**Interfaces:**
- Produces: `counts_from_model(model)` возвращает классы из пар `path`/`kind` манифеста; `files` = длина манифеста; `bsl_module` = число манифестных записей с путём на `.bsl`; `skipped_module_files` остаётся record-производным; record-производные `form_data` и `command_module` исчезают.
- Consumes: модель читателя `p1c` (Task 22–24) и `scripts/layout.py::layout_counts` как независимый источник.

- [x] **Step 1: Write the failing test** (RED): в `tests/test_contour.py::CountsTest` — пять тестов (три переписаны, два новых): `test_counts_come_from_manifest_pairs`, `test_model_keys_without_manifest_pairs_count_as_nothing`, `test_skipped_module_files_stay_record_derived`, `test_corpus_manifest_counts_the_measured_classes` (ожидание — ровно 22 имени: `language 1`, `subsystem 1`, `role 2`, `role_rights 2`, `predefined_data 1`, `form_descriptor 2`, `form_data 2`, `form_module 2`, `report_template 1`, `report_template_data 1`, `object_module 6`, `bsl_module 8`, `files 30` и девять дескрипторов коллекций), `test_corpus_manifest_names_match_the_layout_counter` (22 имени, различие только `files` [31, 30], незакрытый файл ровно `Configuration.xml`). Корпусные тесты читают `cfg/ЭффективностьОтдела` тем же вызовом читателя, что и гейт; без `local.paths.json` — `skipTest`.
- [x] **Step 2: Run to verify the reason** — `python -m unittest tests.test_contour.CountsTest -v`: отказали 4 теста из 8, и все четыре — assertions о классах, импорт целый: `test_counts_come_from_manifest_pairs` (получено `{}`: прежний счётчик манифест не читает), `test_model_keys_without_manifest_pairs_count_as_nothing` (прежний счётчик выдал из ключей модели `catalog 2, command_module 1, common_attribute 1, common_form 1, common_module 2, form_data 2, predefined_data 1, role_rights 1`), корпусный счётчик (12 имён против 22) и сверка имён (12 против 22). Зелёными до правки кода были 4 теста: `test_compare_detects_mismatch`, `test_skipped_module_files_stay_record_derived` (записи диагноза счётчик считал и раньше) и оба теста отказа читателя.
- [x] **Step 3: Implement минимально** — `counts_from_model` считает по парам `path`/`kind` манифеста `read_files`; `files` = длина манифеста; `bsl_module` = число манифестных записей с путём на `.bsl`; `skipped_module_files` по-прежнему из записей `skipped_files`. Счёт по ключам модели исчез полностью: record-производные `form_data` и `command_module`, как и `common_form`, больше не появляются. Смысл прежних тестов сохранён в новой форме: `role` (дескриптор `Roles/<Имя>.xml`) возникает только как манифестная пара, созданная парсером, и не возникает, если открыт только `Ext/Rights.xml` — это та же проверка, что прежний `assertNotIn("role", got)`. `object_counts` и её тексты не тронуты.
- [x] **Step 4: Run tests to verify they pass** — `python -m unittest discover -s tests`: тестов 300, отказов 0, ошибок 0 (в том числе четыре новых корпусных проверки `CountsTest` прогнаны, не пропущены).
- [x] **Step 5: Сверка без платформы** — режима `--offline` у `probe/tool_coverage.py` нет (проверено по `main` `434-533`), поэтому сверка сделана прямыми вызовами `layout_files`, `layout_counts`, `counts_from_model` и `reader_kind_counts` по `cfg/ЭффективностьОтдела` (обход 31 файла, вне окна 1С-замеров): `layout_files` — 22 класса и `counts_match` без расхождений; `tool_blind_kinds` = `[]`; единственное числовое различие — `files` `[31, 30]`; `kinds_seen_by_path` по манифесту читателя — 22, не видных путей нет.
  - Замер сохранён отдельно: `counts_from_model` даёт 22 имени, `layout_counts` — те же 22 имени; `reader_kind_counts` по модели читателя возвращает тот же набор (с `files 30`).
- [x] **Step 6: Commit** — `f1833b1` (`scripts/counts.py`, `tests/test_contour.py`). Артефакты прежних гейтов (`gate-14.json`, `gate-15.json`) не переписываются: `tool_counts_source` в них — запись прежнего замера (10 и 12 классов); пустым `tool_blind_kinds` станет в новом гейте (`scripts/gate.py:370-371` — формула та же).

### Task 27: один 1С-прогон `gate-16`, пересъёмка матрицы и документов

**Files:**
- Create: `reports/gate-16.json` (артефакт прогона)
- Modify: `probe/tool_coverage.py` (только `GATE_ARTIFACT` `:58` → `reports/gate-16.json`)
- Modify: `docs/evidence/tool-coverage.md` (пересъёмка матрицы), `docs/слепые-пятна.md`, `docs/итог-боевой-проверки.md`, `docs/план-оптимизации-p1c.md` («Статус блока A к итерации 13», строки A3–A5)
- Modify: `.superpowers/sdd/effektivnost-otdela/progress.md` (журнал итерации 13 — отдельный коммит)

**Interfaces:**
- Produces: `gate-16.json` с `layout_source` = 22 класса и `tool_counts_source`, построенным манифестным читателем; `tool_blind_kinds = sorted(set(layout_source) - set(tool_counts_source))` (ожидание — пустой список).
- Consumes: `scripts/gate.py` (флаги `--cfg --out --expected --bin --ib --dump --p1c --local --canon --timeout --no-platform`), `scripts/ib_loop.py` (шаги `create`, `load`, `check`, `dump`), `probe/tool_coverage.py`, `probe/render_query_tables.py`.

- [x] **Step 1: Записать `PREDICTIONS` до прогона** в журнал: ожидаемые код 0, `layout_source` 22 класса с числами `files 31`, `bsl_module 8`, `object_module 6`, `form_descriptor 2`, `form_data 2`, `form_module 2`, `role 2`, `role_rights 2`, `predefined_data 1`, `language 1`, `subsystem 1`, `report_template 1`, `report_template_data 1` и по 1 у девяти дескрипторов коллекций; `tool_blind_kinds == []`; `rights` 17 блоков / 79 прав; длительности шагов `load` ≈ 6 с, `check` ≈ 2 с, `dump` ≈ 2 с. — Записано до прогона (`f6330c7`), после прогона не переписывалось; сверка — журнал Task 27.
- [x] **Step 2: Проверить состояние гейт-ИБ без модификаций** — только чтение. Формулировка этой строки плана по замеру неверна: каталог выгрузки существует (32 файла, свежайшая запись 2026-10-29 21:21 — след прогона `gate-15`), его создал прежний прогон, а шаг `dump` эти файлы перезаписывает; различение старых файлов делает проверка свежести (`dump_files 32` = `dump_fresh_files 32`). ИБ тоже существует (11 файлов, та же запись), поэтому `create`-шаг не понадобился: `create_code null`, `ib_ready_before true`.
- [x] **Step 3: Единственный прогон** — `python scripts/gate.py --cfg "cfg/ЭффективностьОтдела" --out reports/gate-16.json --canon docs/canonical-rights.json --timeout 240` (`bin`, `ib`, `dump`, `p1c` — из `local.paths.json`); без `--allow-mutating`, один раз, без повторов «для устойчивости». — Прогнан один раз, код 0, артефакт 8438 байт; шаги по замеренным `started`/`seconds`: `load` начался 07:45:11 (8.0 с), `check` 07:45:19 (2.0 с), `dump` 07:45:21 (2.0 с, закончился 07:45:23).
- [x] **Step 4: Разобрать артефакт скриптом** (артефакт JSON консоли читается скриптом во временном каталоге, а не просмотром файла консоли) и сравнить с `PREDICTIONS`; всё непредсказанное — отдельным списком с причиной, `PREDICTIONS` не переписывать. — Разобран ключ за ключом: `steps`, `layout_source`/`layout_dump`/`layout_compare`, `tool_counts_source`/`tool_counts_dump`/`tool_blind_kinds`, `diff_files`, `rights`, `metadata` (в нём живут `expected_mismatch` и `hard_problems`), плюс побайтова сверка с `gate-15.json`. Итог — журнал Task 27.
- [x] **Step 5: Пересъёмка матрицы** — `GATE_ARTIFACT` переведён на `gate-16.json` (`probe/tool_coverage.py:59`), `python probe/tool_coverage.py`: 18 прогонов восьми инструментов, `kinds 22` — 22 по пути файла, 0 только именем, 0 без инструмента; `reader vs gate: 22 equal=True diff={}` у обоих reader-прогонов. Прежний снимок матрицы сохранён отдельно и сверен прогон за прогоном: 16 из 18 прогонов идентичны, изменились только `load-model-cfg` и `load-model-dump` (пути 16 → 68, имена 18 → 21).
- [x] **Step 6: Проверить ожидание по слепым классам**: `no_tool` обязан стать 0 — стал (0 вместо 3). Закрыто по путям манифеста (`reports/toolcov_runs.json`, прогон `load-model-cfg`): `language` — `Languages/Русский.xml`;
  `subsystem` — `Subsystems/ЭффективностьОтдела.xml`; `role` — дескрипторы `Roles/АдминистраторСистемы.xml` и
  `Roles/СотрудникОтдела.xml`; `report_template` —
  `Reports/ОтчётЗагрузки/Templates/ОсновнаяСхемаКомпоновкиДанных.xml`; `report_template_data` —
  `Reports/ОтчётЗагрузки/Templates/ОсновнаяСхемаКомпоновкиДанных/Ext/Template.xml`; сверх ожиданий тем же
  способом закрыты `predefined_data` (`Catalogs/Сотрудники/Ext/Predefined.xml`), `role_rights`
  (`Roles/АдминистраторСистемы/Ext/Rights.xml`, `Roles/СотрудникОтдела/Ext/Rights.xml`) и `form_descriptor`
  (`Catalogs/Сотрудники/Forms/ФормаЭлемента.xml`,
  `DataProcessors/ВыгрузкаЗатратCSV/Forms/ФормаВыгрузки.xml`). Имена `Subsystems/ConfigGenerationSettingsStorageMap.xml`,
  `Templates/ОтчётПоЗатратам.xml` и `Schema.dcsset` в первой записи этого пункта были выдуманы и исправлены
  по замеру: каталога `SettingsStorages` в `cfg/ЭффективностьОтдела` нет, макет отчёта называется
  `ОсновнаяСхемаКомпоновкиДанных`, а не `ОтчётПоЗатратам`.
- [x] **Step 7: Таблицы запросов** — `python probe/render_query_tables.py` (28 фрагментов), затем `python probe/render_query_tables.py --check`: код 0, `fragments: 28 checked lines: 692`, `unused fragments: none`. До правки прозы `--check` был красный (код 1) на четырёх документах.
- [x] **Step 8: Поправить документы** (`docs/слепые-пятна.md`, `docs/итог-боевой-проверки.md`, `docs/план-оптимизации-p1c.md`): прежние числа (12, 10, 7, 5/10/7) остаются как запись прежних прогонов `gate-14.json` / `gate-15.json`; новые числа — только из `gate-16.json` и из переснятой матрицы.
- [ ] **Step 9: Сканы текстов** на склейки латиницы с кириллицей, CJK, англицызмы и ABS-PATH — по всем изменённым файлам обоих репозиториев.
- [ ] **Step 10: Коммиты** — сначала код и тесты (`p1c` — кириллицей через `git commit -F <файл UTF-8 без BOM>`), затем документы контура, затем `progress.md` отдельно; в конце `git status --porcelain` пуст в обоих репозиториях.
