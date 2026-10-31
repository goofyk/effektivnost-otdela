# План итерации 14a: читатель `p1c` — команды, общие коллекции, одиночные макеты и ограждающий разбор XML

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (нативное выполнение в этой сессии) вместе с superpowers:test-driven-development — задачи связаны одной формой учёта (манифест прочитанных файлов) и одним читателем `p1c`, поэтому их пишет и выполняет один исполнитель. Steps use checkbox (`- [ ]`) syntax for tracking. Нумерация продолжается с `Task 29` (прежний план `docs/superpowers/plans/2026-10-30-iteraciya-13-chitatel-manifest.md` закрыл Task 21–28). В этой итерации 1С-прогонов нет: всё меряется офлайн reader/runner-прогонами, фикстурами и тестами `p1c`.

**Goal:** добрать остаток блока A читателя `p1c`, который итерация 13 оставила незакрытым: открывать и называть командные модули (`Commands/<Имя>/Ext/CommandModule.bsl`), дескрипторы и содержимое общих коллекций (`CommonCommands`, `CommandGroups`, `CommonPictures`, `CommonTemplates`, `CommonForms`), одиночные дескрипторы макетов `Templates/<Имя>.xml` без каталога, коллекции вне `COLLECTIONS_MAP` (`SettingsStorages`, `FilterCriteria`), и заменить непройденное исключение разбора XML на запись диагноза; затем свести манифест с раскладкой и закрепить фикстурами и evidence.

**Architecture:** правки идут в репозитории `p1c` (`src/p1c/load/reader.py`, `tests/load/`); измеритель паритета и его закрепление — в контуре `effektivnost-otdela` (`scripts/manifest_gaps.py`, `tests/test_manifest_gaps.py` — оба сейчас не закоммичены); фикстура зазоров читателя — `p1c/examples/reader_gaps`. Корпус конфигурации не меняется; меняется только то, что о нём известно читателю.

**Tech Stack:** Python 3.15; тесты `p1c` — скрипты с `check()`/`fails` под runner `python scripts/run_tests.py` (в `p1c` `unittest discover` не применяется); тесты контура — stdlib `unittest` (`python -m unittest discover -s tests`); форматы файлов конфигурации (MetaDataObject XML, BSL).

**Spec:** блок A таблицы `docs/план-оптимизации-p1c.md` (`:14-69`), особенно строки A3, A5 и финал «Статус блока A к итерации 13» (`:66-69`); решение исполнителя итерации 14 — в `.superpowers/sdd/effektivnost-otdela/progress.md`.

## Global Constraints

- Ответы и тексты документов — по-русски; имена флагов и режимов платформы — только из замера `p1c/src/p1c/data/test_cli_flags.json`, выдуманные значения помечать явно как неподтверждённые.
- 1С-прогоны в этой итерации не выполняются: офлайн-проверка читателя — `python -B -m p1c.load.cli model <корпус>` и `python scripts/run_tests.py`; тяжёлые обходы корпусов — только по одному ключу и вне зависимости от каких-либо 1С-окон.
- Гейт-ИБ (`<tmp>\p1c_effektivnost\ib`) модифицирующими вариантами не трогать; модифицирующих вариантов в этой итерации нет вовсе.
- `PREDICTIONS`/`EXPECTATIONS` записываются до прогона и после прогона не переписываются; непредсказанные шаги идут отдельным списком с причиной.
- Абсолютных путей в `scripts`, `probe`, `tests` и документах нет: только свёртки `<work>`, `<tmp>`, `<repo>`, `<dump>`, `<cfg>`, `<p1c>` и относительные пути репозитория.
- Перед коммитом тексты проверять сканами `<tmp>\opencode\scan_texts.py` на склейки латиницы с кириллицей, CJK, англицызмы (корень «хелп») и ABS-PATH.
- Значения в модели и в тестах — только из замеренных файлов корпуса; ничего «правдоподобного» по памяти платформенных форматов.
- `command_descriptors` не выдумывать: отдельного файла `Commands/<Имя>.xml` нет ни в одном корпусе и фикстуре (замер ниже), поэтому класс `command_descriptor` остаётся 0 у раскладки и у манифеста; командный модуль — единственный читаемый файл команд.
- Файл `scripts/layout.py` — независимая линейка; его гэпы и формулировки не менять. `scripts/manifest_gaps.py` и `tests/test_manifest_gaps.py` — закрепляются в этой итерации (они untracked), и их таксономия приводится в соответствие с фактическими классами манифеста.

## Review Focus

- Манифест обязан создаваться в точке фактического открытия файла, а не «по раскладке папок»: класс дескриптора присваивает парсер, открывший XML; класс модуля — фаза сканирования, и только когда `scan_one` вернул `read=True` (отсутствующий и нечитаемый модуль манифеста не получает — правило итерации 13).
- Класс дескрипторов общих коллекций обязан совпадать с именем в `scripts/layout.py::KIND_FOLDERS` (`common_command`, `common_form`, `common_picture`, `common_template`, `settings_storage`, `filter_criteria`, `command_group`), иначе сверка `counts_from_model` против `layout_counts` расходится; классы содержимого (`common_command_module`, `common_picture_data`, …) раскладкой не считаются и выбираются по конвенции читателя `<x>_module`/`<x>_data`.
- `Commands/<Имя>.xml` — фикция роадмапа: замер по 7 корпусам и 3 фикстурам даёт 0 таких файлов. Декларации команд лежат в XML владельца объекта (`<ChildObjects><Command>`) и в дескрипторах `CommonCommands/<Имя>.xml`; командный модуль — `Commands/<Имя>/Ext/CommandModule.bsl`. Формулировку роадмапа `:66` правит эта задача.
- Ограждающий разбор XML (Task 32) не должен менять поведение `skipped_files` для модулей (`reader.py:1149-1160`): диагноз разбора — это записи о *файлах*, которые нельзя разобрать, а не о модулях сканирования; причины гейта в `core/rules.py`/`core/rules.json` не трогаются.
- `load/scan.py:34-39` не меняется: ограждающий разбор относится только к 11 точкам `ET.parse` в `reader.py`.

---

### Task 29: командные модули и декларации команд

**Files:**
- Modify: `p1c/src/p1c/load/reader.py` (команды объекта `981-983`, `module_jobs` `920`, фаза слияния `1165-1169`, `parse_object_xml` `420-489` — разбор `ChildObjects/Command` `451-484`)
- Modify: `p1c/tests/load/test_read_manifest.py` (негативные пины `92-97` → позитивные)
- Create: `p1c/tests/load/test_commands.py`

**Interfaces:**
- Produces: командный модуль объекта читается сканом и называется `command_module` (`Commands/<Имя>/Ext/CommandModule.bsl`); в `module_jobs` он идёт с ключом `("команда", rel(module))` и классом `command_module`, его `exports` прикрепляются к записи команды в фазе 3; нечитаемый модуль — в `skipped_files`, как у форм.
- Записи `obj["commands"]` (сейчас `{"name", "module"}`) дополняются полями декларации из `<ChildObjects><Command><Properties>` XML владельца, если она есть (замер пульсара: `Name`, `Synonym`, `Comment`, `Group`, `CommandParameterType`, `ParameterUseMode`, `ModifiesData`, `Representation`, `ToolTip`, `Picture`, `Shortcut`, `OnMainServerUnavalableBehavior`); если декларации нет (фикстуры `designer_dump`, `edt_project`), запись остаётся `{"name", "module", "exports"}`.
- Команды формы (`Form/Commands/Command` в `Ext/Form.xml`) — вне области этой задачи: это не слепой класс, их читает проверка форм; граница фиксируется в журнале.
- Consumes: фикстуры `examples/designer_dump` (1 командный модуль `Catalogs/Номенклатура/Commands/Печать/Ext/CommandModule.bsl`, декларации нет) и `examples/edt_project` (тот же файл под `src/`); офлайн-замер пульсара (44 объектных командных модуля, 26 владельцев с декларациями).

- [ ] **Step 1: Write the failing test** `tests/load/test_commands.py` (форма `check()`/`fails`): для `examples/designer_dump` манифест содержит пару `("Catalogs/Номенклатура/Commands/Печать/Ext/CommandModule.bsl", "command_module")`; запись команды `catalog.Номенклатура` имеет `commands == [{"name": "Печать", "module": "Catalogs/Номенклатура/Commands/Печать/Ext/CommandModule.bsl", "exports": ...}]`; для `examples/edt_project` путь без `src/`. В `tests/load/test_read_manifest.py` пины `:93-94` («модуль команды не назван прочитанным», «класс command_module не объявлен») заменить позитивными. Ожидается отказ (класса `command_module` в манифесте нет).
- [ ] **Step 2: Run to verify the reason** — `python tests/load/test_commands.py`; причина отказа — отсутствие пары `command_module` (модуль в `module_jobs` не добавлен), а не ошибка парсинга.
- [ ] **Step 3: Implement минимально** — в блоке команд `981-983` вместо списка `{"name","module"}` строить список с декларацией из владельца (помощник в `parse_object_xml` для `<ChildObjects><Command>` либо отдельный `_parse_commands`), и добавлять каждый существующий `CommandModule.bsl` в `module_jobs` с ключом `("команда", rel(...))` и классом `command_module`; в фазе 3 (`1165-1169`) прикрепить `exports` к записи команды по ключу. Формулировку `parse_object_xml` `:423-426` («команды … в XML объекта не перечислены») поправить на замеренную: декларация `<Command>` бывает в `ChildObjects` владельца, модуль — отдельным файлом.
- [ ] **Step 4: Run tests to verify they pass** — `python tests/load/test_commands.py`, затем `python scripts/run_tests.py` (базово 79 тестов, 0 неудач; ожидается рост на новый файл). Проверить, что четыре паритетных теста не разошлись (манифест фикстур `designer_dump`/`edt_project` вырос на одну пару `command_module`, а корпусного `managed_app` не коснулся — команд там нет).
- [ ] **Step 5: Офлайн-замер пульсара** — `python -B -m p1c.load.cli model <пульсар>` (или `load_configuration_model(..., parallel=False)` скриптом во временном каталоге) и сравнить: манифест должен назвать `command_module` ровно 44 (объектных командных модуля), а `CommonCommands/*/Ext/CommandModule.bsl` на этом шаге ещё не читается (47 остаются незакрытыми до Task 30). Замер записать в журнал.
- [ ] **Step 6: Commit** в `p1c` — код читателя и оба теста одним коммитом.

### Task 30: дескрипторы и содержимое `CommonCommands`, `CommandGroups`, `CommonPictures`, `CommonTemplates`, `CommonForms`

**Files:**
- Modify: `p1c/src/p1c/load/reader.py` (модель `890-894` — новые ключи; блок общих коллекций после `CommonForms` `1104-1113`; помощники дескрипторов `parse_role_descriptor_xml` `744-756`, `_descriptor_properties` `666-673`, `_property_text` `675-...`)
- Create: `p1c/tests/load/test_common_collections.py`

**Interfaces:**
- Produces: ключи модели `common_commands`, `command_groups`, `common_pictures`, `common_templates` (списки) и дополненный `common_forms`; манифестные пары для дескрипторов с классами `common_command`, `command_group`, `common_picture`, `common_template`, `common_form` (имена совпадают с `layout.py::KIND_FOLDERS`), для содержимого — `common_command_module` (`CommonCommands/<Имя>/Ext/CommandModule.bsl`), `common_picture_data` (`Ext/Picture.xml`), `common_picture_content` (`Ext/Picture/Picture.*`), `common_template_data` (`Ext/Template.{xml,bin,txt}` и `Ext/Template/ru.html`), `form_data` (`Ext/Form.xml`, уже читается), `help` (`Ext/Help.xml`) и `form_module` (`Ext/Form/Module.bsl`, уже читается для `CommonForms`).
- Поля дескрипторов — из замеренных образцов: `CommonCommands` — `Name, Synonym, Comment, Group, Representation, ToolTip, Picture, Shortcut, IncludeHelpInContents, CommandParameterType, ParameterUseMode, ModifiesData, OnMainServerUnavalableBehavior` (13); `CommonPictures` — `Name, Synonym, Comment, AvailabilityForChoice, AvailabilityForAppearance` (5); `CommonTemplates` — `Name, Synonym, Comment, TemplateType` (4); `CommonForms` — `Name, Synonym, Comment, FormType, IncludeHelpInContents, UsePurposes, UseStandardCommands, ExtendedPresentation, Explanation` (9); `CommandGroups` — только имя и представление (по образцу дескриптора).
- Consumes: Task 29 (`_opened`, очередь `module_jobs`); фикстуры `examples/designer_dump`/`edt_project` (общих коллекций нет — только проверка «не падает»); офлайн-замер пульсара (дескрипторы: `CommonCommands` 47, `CommonPictures` 403, `CommonTemplates` 13, `CommonForms` 65, `CommandGroups` 7; содержимое по расширениям — `t30_shapes_pulsar.txt`).

- [ ] **Step 1: Write the failing test** `tests/load/test_common_collections.py`: на фикстуре с синтезированным дескриптором `CommonCommands/Имя.xml` (минимальный MetaDataObject XML, скопированный из образца пульсара) манифест содержит `("CommonCommands/Имя.xml", "common_command")` и `("CommonCommands/Имя/Ext/CommandModule.bsl", "common_command_module")`, а модель — запись `common_commands` с `name`, `synonym`, `group`, `picture`, `exports`; аналогично по одному смоук-кейсу на `CommonPictures`/`CommonTemplates`/`CommonForms`/`CommandGroups` (дескриптор назван правильным классом). Ожидается отказ (ключей и пар нет).
- [ ] **Step 2: Run to verify the reason** — `python tests/load/test_common_collections.py`; причина — отсутствие веток чтения общих коллекций (не ошибка парсинга).
- [ ] **Step 3: Implement минимально** — один блок после `CommonForms` `1104-1113`, который для каждой из пяти папок читает дескрипторы `_opened(xml, <класс раскладки>)` и кладёт их в новые ключи модели через `_descriptor_properties`/`_property_text` (те же помощники, что у ролей), а содержимое (`Ext/CommandModule.bsl`, `Ext/Picture.xml`, `Ext/Template.*`, `Ext/Help.xml`) — `_opened(..., <класс содержимого>)`; модули общих команд и общих форм — в `module_jobs`. `Ext/Picture/Picture.*` (бинарные `.zip/.png/.svg/.bmp/.gif/.ico`) читаются как факт существования (`_opened`) без разбора содержимого — класс `common_picture_content`.
- [ ] **Step 4: Run tests to verify they pass** — новый тест зелёный; `python scripts/run_tests.py` (0 неудач). Четыре паритетных теста не меняются: `managed_app` общих коллекций не имеет.
- [ ] **Step 5: Офлайн-замер пульсара** — прогнать читателя и сверить классы: `common_command 47`, `common_picture 403`, `common_template 13`, `common_form 65`, `command_group 7`, `common_command_module 47`, `common_picture_data 403`, `common_picture_content 403`, `common_template_data 16`, `form_data` (общие формы) 65, `form_module` (общие формы) 65, `help 41` (общие формы). Замер записать в журнал.
- [ ] **Step 6: Commit** в `p1c` — код читателя и тест одним коммитом.

### Task 31: одиночные дескрипторы `Templates/<Имя>.xml` и коллекции вне `COLLECTIONS_MAP` (`SettingsStorages`, `FilterCriteria`)

**Files:**
- Modify: `p1c/src/p1c/load/reader.py` (обход `Templates` внутри объекта `995-1007` — учесть дескриптор без каталога; новые блоки `SettingsStorages` и `FilterCriteria` после `CommonForms`; модель `890-894`)
- Create: `p1c/tests/load/test_single_templates_storages.py`

**Interfaces:**
- Produces: одиночный дескриптор макета `Templates/<Имя>.xml` без каталога `<Имя>/` читается и называется `report_template` (замер `ssl`: 3 таких — `Catalogs/МашиночитаемыеДоверенности/Templates/{ЗначенияОграничений,КлассификаторПолномочий,Ограничения}.xml`); ключи модели `settings_storages` (`name`, `synonym`, `comment`; дескриптор — `MetaDataObject → SettingsStorage → Properties` из 7 полей + `ChildObjects/Form`) и `filter_criteria` (`name`, `synonym`, `comment`, `type`; дескриптор `MetaDataObject → FilterCriterion`); манифестные классы `settings_storage`, `filter_criteria`.
- Содержимое `SettingsStorages/<Имя>/Ext/ManagerModule.bsl` и его `Forms/<Имя>/**` читается как `object_module`/`form_data`/`form_module`/`help` по тем же правилам, что у объектов (замер пульсара: 1 `Ext/ManagerModule.bsl`, 13 форм с `Ext/Form.xml` + `Ext/Form/Module.bsl`, 8 `Ext/Help.xml` + 8 `Ext/Help/ru.html`). Содержимого у `FilterCriteria` нет (замер: 1 дескриптор, 0 файлов).
- Consumes: Task 29–30 (`_opened`, `module_jobs`); фикстуры и офлайн-замер `ssl`/пульсара.

- [ ] **Step 1: Write the failing test** `tests/load/test_single_templates_storages.py`: (1) синтезированный каталог с одиночным `Reports/О/Templates/М.xml` без `М/` — манифест содержит `("Reports/О/Templates/М.xml", "report_template")` и запись `templates` с `name == "М"`; (2) синтезированный `SettingsStorages/Х.xml` и `FilterCriteria/Ф.xml` (копии образцов пульсара) — манифестные пары `settings_storage`/`filter_criteria` и ключи модели. Ожидается отказ.
- [ ] **Step 2: Run to verify the reason** — тест падает на отсутствии пар (одиночный дескриптор не обходится, потому что читатель итерирует только подкаталоги `Templates`).
- [ ] **Step 3: Implement минимально** — в обходе `Templates` `995-1007` рядом с подкаталогами читать дескрипторы `templates_dir.glob("*.xml")`, у которых нет парного каталога (или читать все `*.xml`, а содержимое — только если каталог есть, чтобы не задваивать); добавить блоки `SettingsStorages` (с `Ext/ManagerModule.bsl` в `module_jobs` и чтением `Forms/`) и `FilterCriteria` (только дескриптор).
- [ ] **Step 4: Run tests to verify they pass** — новый тест зелёный; `python scripts/run_tests.py` (0 неудач); корпус `managed_app` без изменений (одиночных макетов и этих коллекций там нет).
- [ ] **Step 5: Офлайн-замер** — на `ssl` одиночные макеты 3 названы `report_template` (без падения), на пульсаре `settings_storage 1` + содержимое 56 файлов и `filter_criteria 1`. Замер записать в журнал.
- [ ] **Step 6: Commit** в `p1c`.

### Task 32: ограждающий разбор XML — диагноз вместо падения

**Files:**
- Modify: `p1c/src/p1c/load/reader.py` (11 точек `ET.parse`: `428, 494, 536, 610, 635, 691, 705, 715, 747, 760, 778`; модель `890-894` — ключ `xml_diagnostics`)
- Create: `p1c/tests/load/test_xml_diagnostics.py`

**Interfaces:**
- Produces: единый помощник разбора XML, который вместо `ET.ParseError` пишет в `model["xml_diagnostics"]` запись `{"path", "kind", "error"}` и возвращает «пустой» результат, как если бы узел не был найден; поведение `skipped_files` (`1149-1160`) не меняется.
- Consumes: фикстуры и синтезированный невалидный XML (например, `Roles/ПолныеПрава/Ext/Rights.xml` с обрезанным байтом, по образцу `test_read_manifest.py:104-119`).

- [ ] **Step 1: Write the failing test** `tests/load/test_xml_diagnostics.py`: каталог с валидным `Configuration.xml` и невалидным `Roles/Р/Ext/Rights.xml` (битые байты) — `load_configuration_model` не падает, а возвращает `xml_diagnostics` с записью `{"path": "Roles/Р/Ext/Rights.xml", "kind": "role_rights", "error": ...}` и пустой записью прав; остальные файлы читаются как обычно. Ожидается отказ (сейчас — необработанное `ParseError`).
- [ ] **Step 2: Run to verify the reason** — тест падает с `Traceback` на `ET.ParseError` (не AssertionError), что и есть диагноз.
- [ ] **Step 3: Implement минимально** — обёртка `_parse_xml(path, kind)` (или `_try_parse`), которую используют все 11 точек; каждая точка получает `kind` — тот же класс, что `_opened` для этого файла; при ошибке — запись диагноза и возврат пустого значения. Точки, где разбор уже условный (например, дескрипторы коллекций в цикле), получают тот же путь отказа.
- [ ] **Step 4: Run tests to verify they pass** — новый тест зелёный; `python scripts/run_tests.py` (0 неудач); проверка, что `test_read_manifest.py:104-119` (нечитаемый модуль в `skipped_files`) не затронут.
- [ ] **Step 5: Commit** в `p1c`.

### Task 33: паритет манифеста и раскладки, фикстура `reader_gaps`, evidence и закрепление измерителя

**Files:**
- Create: `p1c/examples/reader_gaps/` (фикстура зазоров: командный модуль без декларации, общие коллекции, одиночный макет, битые права)
- Modify: `effektivnost-otdela/scripts/manifest_gaps.py` (таксономия `GAP_KINDS` `27-44` → фактические классы манифеста читателя) и `effektivnost-otdela/tests/test_manifest_gaps.py` (новый)
- Modify: `effektivnost-otdela/docs/evidence/tool-coverage.md` (новый раздел итерации 14), `docs/план-оптимизации-p1c.md` (формулировка `:66-68` про `Commands/<Имя>.xml` и одиночные макеты — заменить замеренной; статус блока A к итерации 14)
- Modify: `.superpowers/sdd/effektivnost-otdela/progress.md` (журнал — отдельным коммитом)

**Interfaces:**
- Produces: фикстура `p1c/examples/reader_gaps`, на которой `python scripts/manifest_gaps.py --src <p1c>/src` печатает нулевой список GAP-классов (манифест закрывает всё, что видит раскладка); `tests/test_manifest_gaps.py` закрепляет это как unittest.
- Consumes: Tasks 29–32; `scripts/layout.py::layout_counts`, `scripts/counts.py::counts_from_model`.

- [ ] **Step 1: Write the failing test** `tests/test_manifest_gaps.py` (контура): на фикстуре `p1c/examples/reader_gaps` вызвать `layout_counts` и `counts_from_model(load_configuration_model(...))` и проверить, что имена классов раскладки (`report_template`, `command_module`, `common_command`, `common_picture`, `common_template`, `common_form`, `settings_storage`, `filter_criteria`, `command_group`, …) все присутствуют в манифесте с теми же числами, а `files` различается ровно на непрочитанный `Configuration.xml`. Ожидается отказ (фикстуры нет и/или измеритель неверен).
- [ ] **Step 2: Run to verify the reason** — тест падает на отсутствии фикстуры/несовпадении классов.
- [ ] **Step 3: Implement минимально** — собрать `p1c/examples/reader_gaps` из минимальных файлов (командный модуль, по одному дескриптору каждой общей коллекции, одиночный макет, валидный `Configuration.xml` + битый `Rights.xml`); привести `GAP_KINDS` в `manifest_gaps.py` к фактическим классам манифеста (дескрипторы — имена `layout.py`, содержимое — конвенция читателя), так чтобы `gaps()` на фикстуре давал `{}`.
- [ ] **Step 4: Run tests to verify they pass** — `python -m unittest tests.test_manifest_gaps -v` в контуре (0 отказов); `python scripts/run_tests.py` в `p1c` (0 неудач); `python scripts/manifest_gaps.py --src <p1c>/src` на `cfg`, фикстурах и пульсаре — список незакрытых классов записать в журнал (ожидается: на `cfg` GAP пуст, как и в итерации 13).
- [ ] **Step 5: Поправить документы** — `docs/план-оптимизации-p1c.md:66-68`: заменить «дескрипторы `Commands/<Имя>.xml`» на замеренное (файла нет; читаются командные модули `Commands/<Имя>/Ext/CommandModule.bsl` и декларации `<Command>` в XML владельца); добавить статус блока A к итерации 14. В `docs/evidence/tool-coverage.md` — новый раздел с числами этой итерации.
- [ ] **Step 6: Сканы текстов** `<tmp>\opencode\scan_texts.py` по изменённым файлам обоих репозиториев.
- [ ] **Step 7: Коммиты** — `p1c`: фикстура и её правки; контур: `manifest_gaps.py` + тест, затем документы, затем `progress.md` отдельно; финал — `git status --porcelain` пуст в обоих репозиториях.
