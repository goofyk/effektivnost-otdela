# Покрытие нашей конфигурации инструментами p1c: 18 прогонов восьми инструментов (замер)

Доказательство того, какие классы макетов рукописной конфигурации `cfg/ЭффективностьОтдела` инструменты
`p1c` действительно читают, а какие — нет. Мера независимая от самих инструментов: состав файлов и
классов замера считается раскладкой каталога (`scripts/layout.py`, те же правила, что в гейте), и уже
этот состав ищется в отчётах инструментов.

Метод: `probe/tool_coverage.py`. Восемь CLI-инструментов (`p1c.load`, `p1c.diff`, `p1c.graph`,
`p1c.metrics`, `p1c.check.bsl`, `p1c.check.forms`, `p1c.check.sdbl`, `p1c.cf`) запущены 18 раз по нашей
раскладке и по выгрузке `<work>\dump`. Платформа 1С при этом не запускается; изменения ни в раскладке,
ни в выгрузке не производятся — модифицирующие подкоманды `cf set` и `cf normalize` в матрицу не
включены.
Артефакты замера: `reports/toolcov_<ярлык>.json` (по одному на прогон), `reports/toolcov_runs.json`
(сводка прогонов и матрица классов), `reports/toolcov_summary.txt` (коды возврата и stderr),
`reports/tool-coverage-matrix-18.md` (матрица в том виде, в котором её переносит генератор),
`reports/gate-14.json` (гейт, с которым матрица сверяется). Таблицы и блоки содержимого отчётов в этот
документ переносит `probe/render_query_tables.py` дословно из этих артефактов; он же их пересчитывает
при `--check`.

Абсолютные пути свёрнуты в ярлыки: `<cfg>` — `cfg\ЭффективностьОтдела` внутри репозитория,
`<dump>` и `<work>` — каталог выгрузки и рабочий каталог замера из `local.paths.json`, `<p1c>` — корень
исходников `p1c`, `<repo>` — корень репозитория, `<skd>` — текст `<query>` макета компоновки данных
нашего отчёта (`Reports/ОтчётЗагрузки/Templates/ОсновнаяСхемаКомпоновкиДанных/Ext/Template.xml`).

## 1. Две меры покрытия: путь файла макета и имя сущности

Инструмент «видит» сущность двумя разными способами, и они измеряются раздельно.

1. **Путь файла** (`path_hits`): дословный относительный posix-путь файла макета (`files`,
   `bsl_module`, `form_data`, `form_module`, `object_module`) ищется в JSON-отчёте инструмента
   (`probe/tool_coverage.py::hits_for`). Если путь в отчёте есть — инструмент этот файл упомянул.
2. **Имя сущности** (`name_hits`): имя объекта, формы или макета (`Сотрудники`, `ФормаЭлемента`,
   `ОсновнаяСхемаКомпоновкиДанных`) ищется в тексте отчёта как отдельное слово.

Три правила, без которых мера врёт.

**Правило 1. Имя вплотную к `/` или `\` — это отражённый в отчёте путь, а не найденная сущность.**
`probe/tool_coverage.py::PATH_EDGE` (строка 283) и `name_occurrences` (строки 286-301): если имя стоит
сразу после или сразу перед разделителем пути, эта встреча не засчитывается в покрытие и выносится
отдельным числом (`name_hits_path_echo_only`). Пример: `"root": "<repo>/cfg/ЭффективностьОтдела"` или
`"file": ".../Catalogs/Сотрудники.xml"` — инструмент напечатал путь, который мы ему же и передали.

**Правило 2. Пять классов измеряются только путём файла.** `PATH_ONLY_KINDS` (строка 106):
`role_rights`, `predefined_data`, `object_module`, `bsl_module`, `files`. Имя роли в отчёте не доказывает,
что инструмент прочитал `Roles/<роль>/Ext/Rights.xml`; имя справочника — что он прочитал
`*/Ext/Predefined.xml`. Имена этих классов в покрытие не засчитываются вообще.

**Правило 3. Имя сущности не мерится там, где имя передали мы сами.** У пяти прогонов
`names_counted: False` (строки 67-88): `load-object-catalog` (`p1c.load.cli object catalog.Сотрудники`),
`load-object-wrong-order`, `forms-form-element` (`p1c.check.forms.cli form ФормаЭлемента`),
`forms-form-wrong-order`, `sdbl-query-skd` (текст `<skd>` передаётся аргументом). В этих прогонах имя в
отчёте — эхо наших же слов; там засчитывается только путь файла макета.

Плюс два уточнения меры. Платформенные имена файлов `Form.xml`, `Module.bsl`, `Template.xml` именами
сущностей не считаются (`GENERIC_STEMS`, строка 102); имя сущности — каталог, в котором лежит её `Ext`
(`entity_name`, строки 171-184). Колонка «имён только как часть пути» считает имена и в отчёте, и в
консоли вместе (строки 335-339), а колонка «хитов только в консоли» считает только пути и засчитанные
имена, которых нет в JSON-отчёте (строки 331-333); поэтому у `cf-info-cfg-dir` эхо-имя есть, а хитов
только в консоли — нет: отчёта у того прогона нет вовсе, и имя появилось из текста traceback'а.

Раскладка, по которой считается мера: 31 файл, 22 класса макета (`cfg_files_by_kind`); класс `files` —
все 31 файл. Числа замера сверены с независимым счётчиком гейта (`counts_match`, строки 161-168).

## 2. Матрица прогонов: код возврата, находки, покрытие

| прогон | команда прогона (ярлыки путей) | код возврата | находок в JSON-отчёте | файлов cfg в JSON-отчёте | имён cfg в JSON-отчёте | имён только как часть пути | хитов только в консоли |
|---|---|---|---|---|---|---|---|
| `load-model-dump` | `p1c.load.cli model <dump>` | 0 | 0 | 4 | 11 | 0 | 0 |
| `load-model-cfg` | `p1c.load.cli model <cfg>` | 0 | 0 | 4 | 11 | 1 | 0 |
| `load-forms-dump` | `p1c.load.cli forms <dump>` | 0 | 0 | 4 | 4 | 0 | 0 |
| `load-object-catalog` | `p1c.load.cli object catalog.Сотрудники <dump>` | 0 | 0 | 2 | 0 | 0 | 0 |
| `load-object-wrong-order` | `p1c.load.cli object <dump> catalog.Сотрудники` | 2 | **нет JSON-отчёта** | 0 | 0 | 0 | 0 |
| `load-qualifiers-dump` | `p1c.load.cli qualifiers <dump>` | 0 | 0 | 0 | 4 | 0 | 0 |
| `diff-model-cfg-dump` | `p1c.diff.cli model <cfg> <dump>` | 0 | 0 | 0 | 2 | 1 | 0 |
| `graph-build-dump` | `p1c.graph.cli build <dump>` | 0 | 0 | 0 | 7 | 0 | 0 |
| `graph-roots-dump` | `p1c.graph.cli roots <dump>` | 0 | 0 | 0 | 6 | 0 | 0 |
| `metrics-top-dump` | `p1c.metrics.cli top <dump>` | 0 | 0 | 7 | 1 | 6 | 0 |
| `bsl-check-cfg` | `p1c.check.bsl.cli check <cfg> --root <dump>` | 1 | 15 | 3 | 0 | 5 | 0 |
| `forms-check-dump` | `p1c.check.forms.cli check <dump>` | 0 | 0 | 0 | 0 | 0 | 0 |
| `forms-events-dump` | `p1c.check.forms.cli events <dump>` | 0 | 0 | 0 | 0 | 0 | 0 |
| `forms-form-element` | `p1c.check.forms.cli form ФормаЭлемента <dump>` | 0 | 0 | 2 | 0 | 0 | 0 |
| `forms-form-wrong-order` | `p1c.check.forms.cli form <dump> ФормаЭлемента` | 2 | **нет JSON-отчёта** | 0 | 0 | 0 | 0 |
| `sdbl-check-cfg` | `p1c.check.sdbl.cli check <cfg> --root <dump>` | 0 | 0 | 0 | 0 | 0 | 0 |
| `sdbl-query-skd` | `p1c.check.sdbl.cli query <skd> --root <dump>` | 0 | 0 | 0 | 0 | 0 | 0 |
| `cf-info-cfg-dir` | `p1c.cf.cli info <cfg>` | 1 | **нет JSON-отчёта** | 0 | 0 | 1 | 0 |

Артефакты: `reports/toolcov_runs.json` (`runs`, `matrix_by_kind`), коды возврата и дословный stderr —
`reports/toolcov_summary.txt`, содержимое от каждого отчёта — `reports/toolcov_<ярлык>.json`.

Код возврата отвечает только за дисциплину прогона, исходы живут в ключах отчёта. По 18 прогонам:
14 прогонов с кодом 0; два прогона с кодом 2 и без JSON-отчёта — `load-object-wrong-order`
(`stderr: Корень выгрузки не найден: catalog.Сотрудники`) и `forms-form-wrong-order`
(`stderr: Корень выгрузки не найден: ФормаЭлемента`); `bsl-check-cfg` — код 1 при 15 находках в отчёте;
`cf-info-cfg-dir` — код 1 без отчёта (по нему traceback, §8).

Ни один из 18 прогонов ничего не вывел в stdout: сумма `stdout_chars` по всем прогонам 0, потому что
каждый успешный прогон писал отчёт в файл через `--format json --out reports/toolcov_<ярлык>.json`
(у `cf-info-cfg-dir` этих флагов нет вовсе — см. §8). Строка `[context] XML разобран: объектов 8,
форм 2, модулей к сканированию 18` стоит в stderr 11 прогонов из 18; у семи её нет (`graph-build-dump`,
`graph-roots-dump`, `metrics-top-dump`, `forms-events-dump`, `load-object-wrong-order`,
`forms-form-wrong-order`, `cf-info-cfg-dir`), у `diff-model-cfg-dump` она встречается дважды.

Два прогона с кодом 2 — это не «поломанная конфигурация», а форма команды. Правильный порядок
позиционных аргументов измерен по исходникам CLI: для `load object` и `check.forms form` сначала имя
(ключ объекта или имя формы), затем корень выгрузки
(`p1c/src/p1c/load/cli.py:124-131`, `p1c/src/p1c/check/forms/cli.py:195-202`). Подсказка `--help`
этого порядка не описывает: позиционный остаток там назван «корень выгрузки», и лишь дополнительно
указано, что для `object` это ключ `<вид>.<имя>`, а для `form` — имя формы
(`p1c/src/p1c/load/cli.py:114`, `p1c/src/p1c/check/forms/cli.py:180`); в docstring модулей корень тоже
описан как просто «аргумент» (`load/cli.py:9`, `check/forms/cli.py:11`). Оба порядка оставлены в
матрице как отдельные прогоны, чтобы противоречие подсказки и кода было видно числами.

## 3. Матрица классов макета: кто что видит

| класс макета (гейт `layout_source`) | файлов в cfg | инструментов видят путь файла | инструментов видят имя сущности | инструментов видят имя только как часть пути | какие инструменты (по пути файла) |
|---|---|---|---|---|---|
| `accumulation_register` | 1 | 0 | 1 | 0 | **ни один инструмент** |
| `bsl_module` | 8 | 4 | 0 | 0 | `bsl`, `forms`, `load`, `metrics` |
| `catalog` | 1 | 0 | 3 | 2 | **ни один инструмент** |
| `common_module` | 1 | 0 | 3 | 0 | **ни один инструмент** |
| `constant` | 1 | 0 | 1 | 0 | **ни один инструмент** |
| `data_processor` | 1 | 0 | 2 | 2 | **ни один инструмент** |
| `document` | 1 | 0 | 2 | 2 | **ни один инструмент** |
| `enum` | 1 | 0 | 1 | 0 | **ни один инструмент** |
| `files` | 31 | 4 | 0 | 0 | `bsl`, `forms`, `load`, `metrics` |
| `form_data` | 2 | 2 | 3 | 2 | `forms`, `load` |
| `form_descriptor` | 2 | 0 | 3 | 2 | **ни один инструмент** |
| `form_module` | 2 | 4 | 3 | 2 | `bsl`, `forms`, `load`, `metrics` |
| `information_register` | 1 | 0 | 2 | 1 | **ни один инструмент** |
| `language` | 1 | 0 | 0 | 0 | **ни один инструмент** |
| `object_module` | 6 | 2 | 0 | 0 | `bsl`, `metrics` |
| `predefined_data` | 1 | 0 | 0 | 0 | **ни один инструмент** |
| `report` | 1 | 0 | 1 | 0 | **ни один инструмент** |
| `report_template` | 1 | 0 | 0 | 0 | **ни один инструмент** |
| `report_template_data` | 1 | 0 | 0 | 0 | **ни один инструмент** |
| `role` | 2 | 0 | 0 | 0 | **ни один инструмент** |
| `role_rights` | 2 | 0 | 0 | 0 | **ни один инструмент** |
| `subsystem` | 1 | 0 | 0 | 4 | **ни один инструмент** |

Артефакт: `reports/toolcov_runs.json` (`matrix_by_kind`, `cfg_files_by_kind`, `cfg_names_by_kind`);
тот же носитель — `reports/tool-coverage-matrix-18.md`. Классы названы по гейту (`layout_source`),
число файлов — из замера раскладки.

Из 22 классов: 5 увидены инструментами по пути файла (`bsl_module`, `files`, `form_data`,
`form_module`, `object_module`), 10 — только по имени сущности (`accumulation_register`, `catalog`,
`common_module`, `constant`, `data_processor`, `document`, `enum`, `form_descriptor`,
`information_register`, `report`), 7 — ни по пути, ни по имени (`language`, `predefined_data`,
`report_template`, `report_template_data`, `role`, `role_rights`, `subsystem`).

Показательно сравнение двух модулей одного и того же объекта. Модуль формы
(`Catalogs/Сотрудники/Forms/ФормаЭлемента/Ext/Form/Module.bsl`) виден по пути четырьмя инструментами
(`bsl`, `forms`, `load`, `metrics`) и по имени тремя (`diff`, `graph`, `load`). Модуль объекта
(`Catalogs/Сотрудники/Ext/ObjectModule.bsl`, класс `object_module`) — только путём и только двумя
инструментами (`bsl`, `metrics`): ни `load`, ни `diff`, ни `graph`, ни `forms` его в своём отчёте не
называют. Класс `form_descriptor` (файл `Forms/ФормаЭлемента.xml`, 2 файла) не увиден ни одним
инструментом по пути, хотя имя формы в отчётах есть.

## 4. Имена, которые в отчётах встречаются только как часть пути

| класс макета | файлов cfg | инструменты, где имя сущности только часть пути | эхо-имя (прогон) |
|---|---|---|---|
| `catalog` | 1 | `bsl`, `metrics` | `Сотрудники` (`metrics-top-dump`), `Сотрудники` (`bsl-check-cfg`) |
| `data_processor` | 1 | `bsl`, `metrics` | `ВыгрузкаЗатратCSV` (`metrics-top-dump`), `ВыгрузкаЗатратCSV` (`bsl-check-cfg`) |
| `document` | 1 | `bsl`, `metrics` | `ФактРаботы` (`metrics-top-dump`), `ФактРаботы` (`bsl-check-cfg`) |
| `form_data` | 2 | `bsl`, `metrics` | `ФормаВыгрузки` (`metrics-top-dump`), `ФормаЭлемента` (`metrics-top-dump`), `ФормаВыгрузки` (`bsl-check-cfg`) |
| `form_descriptor` | 2 | `bsl`, `metrics` | `ФормаВыгрузки` (`metrics-top-dump`), `ФормаЭлемента` (`metrics-top-dump`), `ФормаВыгрузки` (`bsl-check-cfg`) |
| `form_module` | 2 | `bsl`, `metrics` | `ФормаВыгрузки` (`metrics-top-dump`), `ФормаЭлемента` (`metrics-top-dump`), `ФормаВыгрузки` (`bsl-check-cfg`) |
| `information_register` | 1 | `metrics` | `ПланЗагрузки` (`metrics-top-dump`) |
| `subsystem` | 1 | `bsl`, `cf`, `diff`, `load` | `ЭффективностьОтдела` (`load-model-cfg`), `ЭффективностьОтдела` (`diff-model-cfg-dump`), `ЭффективностьОтдела` (`bsl-check-cfg`), `ЭффективностьОтдела` (`cf-info-cfg-dir`) |

Артефакт: `reports/toolcov_runs.json` (`name_hits_path_echo_only` каждого прогона).

Три вещи, которые эта таблица объясняет лучше любых рассуждений.

Имя подсистемы `ЭффективностьОтдела` ни один инструмент не назвал как сущность: оно всплывает только
как отражённый путь — в `load-model-cfg` (ключ `context_effective…config.root`), в `diff-model-cfg-dump`
(ключ `old`), в `bsl-check-cfg` (в абсолютных путях `file` всех 15 находок) и в `cf-info-cfg-dir`
(в тексте traceback'а). Проверено по артефактам: в `reports/toolcov_bsl-check-cfg.json` подстрока
`ЭффективностьОтдела` встречается 15 раз и всякий раз внутри пути к файлу, в
`reports/toolcov_diff-model-cfg-dump.json` — 1 раз как значение `old`, в
`reports/toolcov_load-model-cfg.json` — 1 раз как значение `root`.

Имена `Сотрудники`, `ВыгрузкаЗатратCSV`, `ФактРаботы`, `ФормаВыгрузки`, `ФормаЭлемента`,
`ПланЗагрузки` у `metrics-top-dump` — эхо (7 классов-эхо, но 6 различных имён: `ФормаВыгрузки` и
`ФормаЭлемента` попадают в три класса форм сразу). Засчитанное имя у этого инструмента ровно одно —
`РасчётПоказателей` (общий модуль), потому что в рейтинге `top` имена объектов стоят внутри путей
`DataProcessors/ВыгрузкаЗатратCSV/Ext/ObjectModule.bsl`, а имя общего модуля — отдельным значением
`kind_of_module`/узла. У `bsl-check-cfg` то же самое: 7 классов-эхо, 5 различных имён
(`Сотрудники`, `ВыгрузкаЗатратCSV`, `ФактРаботы`, `ФормаВыгрузки`, `ЭффективностьОтдела`), засчитанных
имён — ноль. `ПланЗагрузки` среди них нет, хотя модуль
`InformationRegisters/ПланЗагрузки/Ext/ManagerModule.bsl` прочитан (`stats.files 8`): в отчёт попали пути
только трёх файлов, где находки есть (`Catalogs/Сотрудники/Ext/ObjectModule.bsl`,
`DataProcessors/ВыгрузкаЗатратCSV/Forms/ФормаВыгрузки/Ext/Form/Module.bsl`,
`Documents/ФактРаботы/Ext/ObjectModule.bsl`). Имя сущности в этом отчёте видно лишь там, где инструмент
напечатал путь к находке, — поэтому оно и отнесено к эхо, а не к покрытию.

Эти колонки считают различные имена, а не число встреч: одно и то же имя в нескольких классах макета
считается один раз внутри прогона, но учитывается в каждом из этих классов в матрице §3.

## 5. Сверка с гейтом: независимые числа раскладки против того, что назвали инструменты

```text
kinds_total 22
gate_artifact `gate-14.json`
tools 8: `bsl`, `cf`, `diff`, `forms`, `graph`, `load`, `metrics`, `sdbl`
layout_counts_match: want 22 classes, got 22 classes, mismatch 0 (пусто)
gate_tool_counts_source 10 classes: accumulation_register 1, catalog 1, common_module 1, constant 1, data_processor 1, document 1, enum 1, form_data 2, information_register 1, report 1
gate_tool_blind_kinds 12: `bsl_module`, `files`, `form_descriptor`, `form_module`, `language`, `object_module`, `predefined_data`, `report_template`, `report_template_data`, `role`, `role_rights`, `subsystem`
reader_vs_gate.load-model-cfg: equal_to_gate_tool_counts_source true, diff_reader_vs_gate 0 (пусто)
reader_vs_gate.load-model-dump: equal_to_gate_tool_counts_source true, diff_reader_vs_gate 0 (пусто)
kinds seen by path 5: `bsl_module`, `files`, `form_data`, `form_module`, `object_module`
kinds seen by name only 10: `accumulation_register`, `catalog`, `common_module`, `constant`, `data_processor`, `document`, `enum`, `form_descriptor`, `information_register`, `report`
kinds seen by no tool 7: `language`, `predefined_data`, `report_template`, `report_template_data`, `role`, `role_rights`, `subsystem`
runs 18, sum of stdout_chars 0
runs logging the context line 11 of 18
  [context] XML разобран: объектов 8, форм 2, модулей к сканированию 18
  runs without it: `load-object-wrong-order`, `graph-build-dump`, `graph-roots-dump`, `metrics-top-dump`, `forms-events-dump`, `forms-form-wrong-order`, `cf-info-cfg-dir`
```

Артефакты: `reports/toolcov_runs.json` (`layout_counts_match`, `gate_*`, `reader_vs_gate`,
`kinds_seen_by_*`), `reports/gate-14.json`.

Сверка сходится во всех трёх местах. Состав классов замера (22) и независимый счётчик гейта
(`layout_counts`) совпадают: расхождений ноль. Читатель `p1c.load` в обоих прогонах модели (`model` по
выгрузке и по `cfg`) назвал ровно те же 10 классов и в тех же количествах, что и `tool_counts_source`
гейта, — различий ноль; это значит, что расхождение «что видит инструмент» против «что лежит в
каталоге» — не ошибка замера, а свойство инструментов.

Слепые классы по гейту — 12 (`tool_blind_kinds`): это ровно 22 минус те 10, которые `p1c.load` назвал.
Из этих 12 семь (`language`, `predefined_data`, `report_template`, `report_template_data`, `role`,
`role_rights`, `subsystem`) не увидены ни одним инструментом матрицы вообще. Оставшиеся пять закрыты
другими инструментами, но не читателем: `bsl_module` (8 файлов), `files` (31) и `object_module` (6) —
только по пути файла; `form_module` (2) — и по пути, и по имени; `form_descriptor` (2) — только по
имени. Именно поэтому в матрице 5 классов «по пути» и 10 «по имени»: у пяти классов из
`PATH_ONLY_KINDS` собственного имени сущности нет (`cfg_names_by_kind` содержит 17 ключей — ровно без
`bsl_module`, `files`, `object_module`, `predefined_data`, `role_rights`).

Права ролей при этом настроены и проверены независимо: гейт `reports/gate-14.json` даёт
`rights.code 0` (`rights_files 2`, `object_blocks 17`, `rights 79`) и `rights_immobility.code 0`
(`source_blocks 17`, `dump_blocks 17`, `source_rights 79`, `dump_rights 79`, ничего не потеряно и
ничего не добавлено). Ни один из восьми инструментов матрицы эти файлы не прочитал: `role` и
`role_rights` — 0 по обеим мерам. То есть права в нашей конфигурации есть, а в `p1c` их нет.

Подпись контекста в 15 написанных JSON-отчётах приняла ровно два значения:
`d8d5d85c4c154616…` у 14 прогонов (модель взята из `<work>\dump`) и `39a6a09601089858…` у единственного
прогона `load-model-cfg` (модель взята из репозиторного `cfg\ЭффективностьОтдела`) —
`reports/toolcov_*.json`, ключ `context_signature`. Это та же зависимость, что уже разобрана в
`docs/evidence/sdbl-controls.md` §3: подпись зависит от написания пути корня, а не от содержимого.

## 6. Что именно лежит в отчётах читателей (`p1c.load`, `p1c.diff`, `p1c.graph`, `p1c.metrics`)

```text
load-model-dump  (exit 0)
  keys: `model`
  model.collections = 8: `Документы`, `Константы`, `Обработки`, `Отчеты`, `Перечисления`, `РегистрыНакопления`, `РегистрыСведений`, `Справочники`
  model.common_attributes = 0
  model.common_forms = 0
  model.common_modules = 1: `РасчётПоказателей`
  model.enums = 1: `ГрейдыСпециалистов`
  model.global_functions = 0
  model.objects = 8: `accumulation_register.ЗатратыВремени`, `catalog.Сотрудники`, `constant.НормаЧасовВМесяц`, `data_processor.ВыгрузкаЗатратCSV`, `document.ФактРаботы`, `enum.ГрейдыСпециалистов`, `information_register.ПланЗагрузки`, `report.ОтчётЗагрузки`
  model.skipped_files = 0

load-model-cfg  (exit 0)
  keys: `model`
  model.collections = 8: `Документы`, `Константы`, `Обработки`, `Отчеты`, `Перечисления`, `РегистрыНакопления`, `РегистрыСведений`, `Справочники`
  model.common_attributes = 0
  model.common_forms = 0
  model.common_modules = 1: `РасчётПоказателей`
  model.enums = 1: `ГрейдыСпециалистов`
  model.global_functions = 0
  model.objects = 8: `accumulation_register.ЗатратыВремени`, `catalog.Сотрудники`, `constant.НормаЧасовВМесяц`, `data_processor.ВыгрузкаЗатратCSV`, `document.ФактРаботы`, `enum.ГрейдыСпециалистов`, `information_register.ПланЗагрузки`, `report.ОтчётЗагрузки`
  model.skipped_files = 0

load-forms-dump  (exit 0)
  keys: `count`, `forms`
  forms 2, count 2
  form `ФормаЭлемента`: kind `catalog`, object `Сотрудники`, attributes 2, items 6, events 3, commands 1
  form `ФормаВыгрузки`: kind `data_processor`, object `ВыгрузкаЗатратCSV`, attributes 5, items 6, events 1, commands 2

load-object-catalog  (exit 0)
  keys: `object`
  object.attributes 8
  object.commands 0 (пусто)
  object.forms 1
  object.kind `catalog`
  object.manager_methods 13
  object.name `Сотрудники`
  object.object_methods 6
  object.record_methods 0 (пусто)
  object.ref_methods 3
  object.tabular_sections 1
  object.attributes (8): `Код`, `Наименование`, `ПометкаУдаления`, `Предопределённый`, `ЭтоГруппа`, `Ставка`, `Грейд`, `ДатаПриёма`
  object.forms (1): `ФормаЭлемента`
  object.manager_methods (13): `Выбрать`, `НайтиПоКоду`, `НайтиПоНаименованию`, `НайтиПоРеквизиту`, `СоздатьЭлемент`, `СоздатьГруппу`, `ПустаяСсылка`, `ПолучитьФорму`, `ПолучитьФормуСписка`, `ПолучитьФормуВыбора`, `ПолучитьФормуНовогоЭлемента`, `ПолучитьФормуГруппы`, `ПолучитьСсылку`
  object.object_methods (6): `Записать`, `Удалить`, `Скопировать`, `ПолучитьФорму`, `ПолучитьСсылкуНового`, `СравнитьСотрудников`
  object.ref_methods (3): `ПолучитьОбъект`, `ПолучитьФорму`, `СравнитьСотрудников`
  object.tabular_sections (1): `ИсторияГрейдов`

load-qualifiers-dump  (exit 0)
  keys: `count`, `qualifiers`
  qualifiers 8, count 8
  qualifier `accumulation_register.ЗатратыВремени`.`Часы`: type `Число`
  qualifier `catalog.Сотрудники`.`Ставка`: type `Число`
  qualifier `catalog.Сотрудники`.`ДатаПриёма`: type `Дата`
  qualifier `catalog.Сотрудники`.`ПериодНачала`: type `Дата`
  qualifier `catalog.Сотрудники`.`ПериодОкончания`: type `Дата`
  qualifier `document.ФактРаботы`.`Содержание`: type `Строка`
  qualifier `document.ФактРаботы`.`Часы`: type `Число`
  qualifier `information_register.ПланЗагрузки`.`ПланЧасы`: type `Число`

diff-model-cfg-dump  (exit 0)
  keys: `changes`, `new`, `old`
  changes.common_attributes +0/~0/-0
  changes.common_forms +0/~0/-0
  changes.common_modules +0/~0/-0
  changes.enums +0/~0/-0
  changes.global_functions +0/~0/-0
  changes.objects +0/~1/-0
  - objects.catalog.Сотрудники — forms +0/~1/-0
    - forms.ФормаЭлемента — events +0/~0/-0

graph-build-dump  (exit 0)
  keys: `stats`, `top_fan_out`
  stats.edges 102
  stats.edges_by_kind: common 4, global 40, module 9, object 1, platform 11, unresolved 37
  stats.modules 8
  stats.nodes 33
  stats.parsed 8
  stats.unresolved 37
  top_fan_out 20: `object:ВыгрузкаЗатратCSV:СформироватьТекстВыгрузки` calls 22 … `common:РасчётПоказателей:НормаЧасовЗаМесяц` calls 1

graph-roots-dump  (exit 0)
  keys: `roots`, `stats`
  stats.edges 102
  stats.edges_by_kind: common 4, global 40, module 9, object 1, platform 11, unresolved 37
  stats.modules 8
  stats.nodes 33
  stats.parsed 8
  stats.unresolved 37
  roots 15
  roots[0:5]: `common:РасчётПоказателей:ОценкаТриТочки`, `common:РасчётПоказателей:РазбросОценки`, `form:ФормаВыгрузки:ВыгрузитьВCSV`, `form:ФормаВыгрузки:ПослеВыбораФайла`, `form:ФормаВыгрузки:ПриСозданииНаСервере`
  roots[5:10]: `form:ФормаВыгрузки:СформироватьВыгрузку`, `form:ФормаЭлемента:ПередЗаписью`, `form:ФормаЭлемента:ПослеЗаписи`, `form:ФормаЭлемента:ПриСозданииНаСервере`, `form:ФормаЭлемента:РассчитатьЁмкость`
  roots[10:15]: `object:ПланЗагрузки:ПланПоСотрудникамЗаПериод`, `object:ПланЗагрузки:ПланСотрудникаЗаПериод`, `object:Сотрудники:ПередЗаписью`, `object:Сотрудники:СравнитьСотрудников`, `object:ФактРаботы:ОбработкаПроведения`

metrics-top-dump  (exit 0)
  keys: `by`, `source`, `top`
  by `complexity`, top 20, source `<work>\dump`
  top `ЗначениеКолонкиCSV` (`DataProcessors/ВыгрузкаЗатратCSV/Ext/ObjectModule.bsl`:144): complexity 6, statements 8, code_lines 11, max_nesting 1, kind_of_module `object`, annotation (пусто), exported false
  top `РасчётПоказателейНаСервере` (`Catalogs/Сотрудники/Forms/ФормаЭлемента/Ext/Form/Module.bsl`:42): complexity 1, statements 1, code_lines 2, max_nesting 0, kind_of_module `form`, annotation `НаСервере`, exported false

```

Артефакты: `reports/toolcov_load-model-dump.json`, `reports/toolcov_load-model-cfg.json`,
`reports/toolcov_load-forms-dump.json`, `reports/toolcov_load-object-catalog.json`,
`reports/toolcov_load-qualifiers-dump.json`, `reports/toolcov_diff-model-cfg-dump.json`,
`reports/toolcov_graph-build-dump.json`, `reports/toolcov_graph-roots-dump.json`,
`reports/toolcov_metrics-top-dump.json`.

Модель метаданных (`model`) описывает объектный мир конфигурации восемью коллекциями и восемью
объектами, называет один общий модуль и одно перечисление — и содержит нули по трём ключам
(`common_attributes`, `common_forms`, `global_functions`). В ключах модели нет ни подсистем, ни ролей,
ни языка, ни параметров сеанса, ни предопределённых данных, ни макетов: то, что лежит в
`ConfigDumpInfo.xml`, `Languages/`, `SubSystems/`, `Roles/`, `*/Ext/Predefined.xml` и
`Templates/*/Ext/Template.xml`, моделью не представляется. Отсюда и семь классов «ни один инструмент».

`load object catalog.Сотрудники` возвращает 8 реквизитов, 1 табличную секцию (`ИсторияГрейдов`), 1 форму
и три списка методов (`manager_methods 13`, `object_methods 6`, `ref_methods 3`). Наши собственные
методы в этих списках — `СравнитьСотрудников` (в `object_methods` и `ref_methods`) и
`ПередЗаписью` (его видно `p1c.graph` в корнях: `object:Сотрудники:ПередЗаписью`); остальное —
перечисление платформенного API справочника, а не то, что написано в нашем модуле. Различение «что
написано нами» и «что обещает платформа» в этом отчёте не размечено.

`p1c.graph` считает все восемь модулей прочитанными (`modules 8`, `parsed 8`) и 102 ребра, из которых
37 — `unresolved` (треть всех рёбер). `roots` называет 15 процедур-вершин, и восемь из них — обработчики
двух форм: `form:ФормаВыгрузки:ВыгрузитьВCSV`, `form:ФормаВыгрузки:ПослеВыбораФайла`,
`form:ФормаВыгрузки:ПриСозданииНаСервере`, `form:ФормаВыгрузки:СформироватьВыгрузку`,
`form:ФормаЭлемента:ПередЗаписью`, `form:ФормаЭлемента:ПослеЗаписи`,
`form:ФормаЭлемента:ПриСозданииНаСервере`, `form:ФормаЭлемента:РассчитатьЁмкость`. Оставшиеся семь —
`common:РасчётПоказателей:ОценкаТриТочки`, `common:РасчётПоказателей:РазбросОценки`,
`object:ПланЗагрузки:ПланПоСотрудникамЗаПериод`, `object:ПланЗагрузки:ПланСотрудникаЗаПериод`,
`object:Сотрудники:ПередЗаписью`, `object:Сотрудники:СравнитьСотрудников` и
`object:ФактРаботы:ОбработкаПроведения`. Имена платформенных обработчиков (`ПриСозданииНаСервере`,
`ПередЗаписью`, `ОбработкаПроведения`) график использует как вершины, но справочника допустимых
событий при них не держит — это разобрано в §7.

`p1c.metrics` читает 7 файлов модулей, но засчитанное имя сущности в его отчёте ровно одно —
`РасчётПоказателей` (§4). В верхней строке рейтинга `annotation` пусто, а у
`РасчётПоказателейНаСервере` указан `annotation НаСервере` и
`kind_of_module form` — директивы контекста инструмент различает частично.

`p1c.diff model <cfg> <dump>` нашёл одно изменение объекта: `changes.objects +0/~1/-0`,
`- objects.catalog.Сотрудники — forms +0/~1/-0`, и внутри этой формы `forms.ФормаЭлемента — events
+0/~0/-0`. То есть сравнение увидело изменённую форму справочника, но список её событий посчитал
неизменным: `events` в отчёте — это перечисление имён событий, а не содержимое модуля формы, поэтому
правки в `Ext/Form/Module.bsl` в этой разнице не отражаются. Причина, по которой `p1c.diff` именно так
считает события, по артефакту не устанавливается.

## 7. Содержимое проверок: `check.forms`, `check.sdbl` и два «неправильных порядка»

```text
load-object-wrong-order  (exit 2, нет JSON-отчёта)
  argv: p1c.load.cli object <dump> catalog.Сотрудники
  stderr: Корень выгрузки не найден: catalog.Сотрудники

forms-form-wrong-order  (exit 2, нет JSON-отчёта)
  argv: p1c.check.forms.cli form <dump> ФормаЭлемента
  stderr: Корень выгрузки не найден: ФормаЭлемента

bsl-check-cfg  (exit 1)
  keys: `results`, `skipped_rules`, `stats`, `summary`
  stats.files 8
  summary.by_code_origin: official_code 15
  summary.by_grounding: official_code 12, official_page 3
  summary.by_rule: names 4, scope 11
  summary.by_severity: error 15
  summary.count 15
  skipped_rules: `os_compat` (`нет контекста: target_os`), `queries` (`нет контекста: check_queries`), `tests` (`правило отключено`)

forms-check-dump  (exit 0)
  keys: `results`, `skipped`, `skipped_rules`, `summary`
  summary.by_code_origin 0 (пусто)
  summary.by_grounding 0 (пусто)
  summary.by_rule 0 (пусто)
  summary.by_severity 0 (пусто)
  summary.count 0
  skipped_rules: `execution_context` (`нет контекста: execution_context`), `os_compat` (`нет контекста: target_os`), `tests` (`правило отключено`)

forms-events-dump  (exit 0)
  keys: `count`, `events`, `page`
  page `ClientApplicationForm`, count 26, events 26
  events: `ActivationProcessing`, `AddInDetachmentOnError`, `BeforeClose`, `BeforeLoadDataFromSettingsAtServer`, `BeforeReopenFromOtherServer`, `ChoiceProcessing`, `CollaborationSystemUsersAutoComplete`, `CollaborationSystemUsersChoiceFormGetProcessing`, `ExternalEvent`, `FillCheckProcessingAtServer`, `NavigationProcessing`, `NewWriteProcessing`, `NotificationProcessing`, `OnChangeDisplaySettings`, `OnClose`, `OnCreateAtServer`, `OnLoadDataFromSettingsAtServer`, `OnMainServerAvailabilityChange`, `OnOpen`, `OnPasteFromClipboard`, `OnReopen`, `OnReopenFromOtherServer`, `OnSaveDataInSettingsAtServer`, `URLGetProcessing`, `URLListGetProcessing`, `URLProcessing`
  event `ActivationProcessing`: min_args 2, max_args 2, params `<АктивныйОбъект>`, `<Источник>`, availability `thin_client`, `web_client`, `mobile_client`, `server`, `thick_client`, `mobile_app_client`, `mobile_app_server`, `mobile_standalone_server`
  event `BeforeClose`: min_args 4, max_args 4, params `<Отказ>`, `<ЗавершениеРаботы>`, `<ТекстПредупреждения>`, `<СтандартнаяОбработка>`, availability `thin_client`, `web_client`, `mobile_client`, `server`, `thick_client`, `mobile_app_client`
  event `OnCreateAtServer`: min_args 2, max_args 2, params `<Отказ>`, `<СтандартнаяОбработка>`, availability `thin_client`, `web_client`, `server`, `thick_client`, `mobile_app_server`, `mobile_standalone_server`
  absent from this list: `AfterWrite`, `BeforeWrite`

forms-form-element  (exit 0)
  keys: `form`, `results`, `skipped`, `skipped_rules`
  skipped_rules: `execution_context` (`нет контекста: execution_context`), `os_compat` (`нет контекста: target_os`), `tests` (`правило отключено`)
  form.attributes 2
  form.commands 1
  form.items 6
  form.kind `catalog`
  form.module `Catalogs/Сотрудники/Forms/ФормаЭлемента/Ext/Form/Module.bsl`
  form.name `ФормаЭлемента`
  form.object `Сотрудники`
  form.path `Catalogs/Сотрудники/Forms/ФормаЭлемента/Ext/Form.xml`
  form.attribute `Объект`: type `СправочникОбъект.Сотрудники`, qualifier null
  form.attribute `ОценкаЁмкости`: type `Число`, qualifier {"kind": "КвалификаторыЧисла", "values": {"ДопустимыйЗнак": "Неотрицательный", "Разрядность": 8, "РазрядностьДробнойЧасти": 2}}
  form.item `ГруппаКарточкиСотрудника`: kind `UsualGroup`, data_path (пусто), parent (пусто), readonly false
  form.item `Наименование`: kind `InputField`, data_path `Объект.Description`, parent `ГруппаКарточкиСотрудника`, readonly false
  form.item `Ставка`: kind `InputField`, data_path `Объект.Ставка`, parent `ГруппаКарточкиСотрудника`, readonly false
  form.item `Грейд`: kind `InputField`, data_path `Объект.Грейд`, parent `ГруппаКарточкиСотрудника`, readonly false
  form.item `ДатаПриёма`: kind `InputField`, data_path `Объект.ДатаПриёма`, parent `ГруппаКарточкиСотрудника`, readonly false
  form.item `ОценкаЁмкости`: kind `LabelField`, data_path `ОценкаЁмкости`, parent (пусто), readonly false
  form.event `AfterWrite`: handler `ПослеЗаписи`, scope `form`, kind (пусто), owner (пусто)
  form.event `BeforeWrite`: handler `ПередЗаписью`, scope `form`, kind (пусто), owner (пусто)
  form.event `OnCreateAtServer`: handler `ПриСозданииНаСервере`, scope `form`, kind (пусто), owner (пусто)
  form.command `РассчитатьЁмкость`: action `РассчитатьЁмкость`, standard false

sdbl-check-cfg  (exit 0)
  keys: `results`, `schema_available`, `skipped_rules`, `stats`, `summary`
  stats.field_ok 20
  stats.field_refs 23
  stats.files 8
  stats.name_object 5
  stats.name_object_ok 5
  stats.name_temp 2
  stats.name_temp_ok 2
  stats.param_used 9
  stats.queries 3
  stats.skip_field_fields_unknown 3
  stats.skip_vt_no_help_fields 1
  stats.sources 7
  stats.src_object 4
  stats.src_temp 2
  stats.src_virtual_table 1
  summary.by_code_origin 0 (пусто)
  summary.by_grounding 0 (пусто)
  summary.by_rule 0 (пусто)
  summary.by_severity 0 (пусто)
  summary.count 0
  skipped_rules: `execution_context` (`нет контекста: execution_context`), `os_compat` (`нет контекста: target_os`), `tests` (`правило отключено`)
  schema_available true

sdbl-query-skd  (exit 0)
  keys: `results`, `schema_available`, `skipped_rules`, `stats`, `summary`
  stats.field_ok 13
  stats.field_refs 13
  stats.name_object 3
  stats.name_object_ok 3
  stats.queries 1
  stats.sources 5
  stats.src_object 3
  stats.src_temp 2
  summary.by_code_origin 0 (пусто)
  summary.by_grounding 0 (пусто)
  summary.by_rule 0 (пусто)
  summary.by_severity 0 (пусто)
  summary.count 0
  skipped_rules: `execution_context` (`нет контекста: execution_context`), `os_compat` (`нет контекста: target_os`), `tests` (`правило отключено`)
  schema_available true

```

Артефакты: `reports/toolcov_bsl-check-cfg.json`, `reports/toolcov_forms-check-dump.json`,
`reports/toolcov_forms-events-dump.json`, `reports/toolcov_forms-form-element.json`,
`reports/toolcov_sdbl-check-cfg.json`, `reports/toolcov_sdbl-query-skd.json`,
`reports/toolcov_load-object-wrong-order.json` и `reports/toolcov_forms-form-wrong-order.json` — этих
двух файлов нет: прогон не пишет JSON-отчёт (в `reports/toolcov_runs.json` у них поля `code`,
`stderr_text` и `report_file: null`).

Главная несостыковка — события форм. `check.forms events` без флага `--kind` выдаёт список из 26
событий страницы `ClientApplicationForm`, и в этом списке нет `AfterWrite` и `BeforeWrite` (в файле
`reports/toolcov_forms-events-dump.json` этих имён нет; строка `absent from this list: AfterWrite,
BeforeWrite` в блоке выше — пометка нашего генератора таблиц `probe/render_query_tables.py:868`,
инструмент такой строки не печатает). При этом справочник событий формы в `p1c` всё-таки есть:
`p1c/src/p1c/check/forms/checks.py:39-56` задаёт `FORM_PAGE = "ClientApplicationForm"` и `OBJECT_PAGE` —
соответствие вида объекта метаданных официальной странице расширения формы, а
`p1c/src/p1c/data/platform_arities.py::EVENT_SIGNATURES` содержит 135 страниц, из них 29 с именем вида
`… form extension`. Проверено прогоном той же команды с `--kind` (`probe/forms_kind_events.py`,
артефакты `reports/forms-events-kind-19.json` и `reports/forms-events-kind-19.txt`; платформу
этот замер не запускает):

```text
(без --kind)             exit 0  count 26  AfterWrite=False BeforeWrite=False
catalog                  exit 0  count 33  AfterWrite=True BeforeWrite=True
document                 exit 0  count 33  AfterWrite=True BeforeWrite=True
constant                 exit 0  count 32  AfterWrite=True BeforeWrite=True
information_register     exit 0  count 32  AfterWrite=True BeforeWrite=True
task                     exit 0  count 34  AfterWrite=True BeforeWrite=True
business_process         exit 0  count 34  AfterWrite=True BeforeWrite=True
data_processor           exit 0  count 26  AfterWrite=False BeforeWrite=False
report                   exit 0  count 33  AfterWrite=False BeforeWrite=False
accumulation_register    exit 0  count 26  AfterWrite=False BeforeWrite=False
calculation_register     exit 0  count 26  AfterWrite=False BeforeWrite=False
chart_of_characteristics exit 0  count 26  AfterWrite=False BeforeWrite=False
accounting_register      exit 0  count 26  AfterWrite=False BeforeWrite=False
chart_of_accounts        exit 0  count 26  AfterWrite=False BeforeWrite=False
chart_of_calculation     exit 0  count 26  AfterWrite=False BeforeWrite=False
zzz-netakogo-vida        exit 0  count 26  AfterWrite=False BeforeWrite=False
```

Значит, по умолчанию инструмент называет только базовую страницу, а страница расширения формы этого вида
добавляет свои имена (ничего из базовых 26 при этом не теряется — во всех прогонах `--kind` базовый список
остается подмножеством результата):

- `catalog` и `document` — прирост 7 имён: `AfterWrite`, `AfterWriteAtServer`, `BeforeWrite`,
  `BeforeWriteAtServer`, `OnReadAtServer`, `OnWriteAtServer`, `ValueChoice` (26 → 33);
- `constant` и `information_register` — прирост 6 (те же без `ValueChoice`, 26 → 32);
- `task` — прирост 8 (к списку `catalog` добавляется `BeforeExecute`, 26 → 34), `business_process` —
  прирост 8 (вместо `BeforeExecute` — `BeforeStart`, 26 → 34);
- `report` — прирост 7 имён вариантов и настроек: `BeforeLoadUserSettingsAtServer`,
  `BeforeLoadVariantAtServer`, `OnLoadUserSettingsAtServer`, `OnLoadVariantAtServer`,
  `OnSaveUserSettingsAtServer`, `OnSaveVariantAtServer`, `OnUpdateUserSettingSetAtServer` (26 → 33),
  и ни одного события записи в этом списке нет;
- `data_processor`, `accumulation_register`, `calculation_register`, `chart_of_characteristics` — прирост
  нулевой: `checks.is_managed_page` (строки 143-146) отвергает их страницы, потому что в данных
  `EVENT_SIGNATURES` у их событий указана доступность только `thick_client`. События записи `AfterWrite`,
  `BeforeWrite`, `OnWrite` на странице `Accumulation register record set form extension` записаны, но как
  управляемые не засчитаны; `is_managed_page` для этой страницы — `false`.
- `accounting_register`, `chart_of_accounts`, `chart_of_calculation` — тот же нулевой прирост: их страницы
  в справочнике есть (3, 4 и 4 события соответственно, колонка «страниц в справочнике» и «событий на
  странице» в `reports/forms-events-kind-19.txt`), но `is_managed_page` для всех трёх — `false`, поэтому
  список событий остаётся равным 26.
- Имя вида, которого в `OBJECT_PAGE` нет (`zzz-netakogo-vida`), даёт `exit 0`, страницу
  `ClientApplicationForm`, 26 имён и пустой `stderr`: `--kind` переданное имя не проверяет, и неизвестный
  вид в выводе неотличим от случая «флаг не передан».
- Расположение флага измерено отдельно: `--kind <вид> events <корень>` и `events <корень> --kind <вид>`
  дают одинаковые списки для `catalog`, `document`, `report`, `data_processor`, `accumulation_register`
  (пять прогонов, таблица «расположение флага» в `reports/forms-events-kind-19.txt`, колонка «совпадает
  со списком после подкоманды» — `true` во всех пяти). У этой команды порядок токенов не спорен, в отличие
  от `load object` и `check.forms form` (раздел «Порядок позиционных аргументов» выше).

При этом `check.forms check` по нашей выгрузке эти события разрешает: `results []` и `skipped []`, то
есть ни одно событие не попало в «не подтверждено официальной страницей» — потому что там вид формы
известен из раскладки и `checks.py:231` вызывает `event_page(имя, вид формы)`. А вот `check.forms form`
и `check.forms events` этого не делают: в отчёте `form ФормаЭлемента` события лежат как
`AfterWrite` → обработчик `ПослеЗаписи`, `BeforeWrite` → `ПередЗаписью`, `OnCreateAtServer` →
`ПриСозданииНаСервере` со `scope form`, но `kind` и `owner` у них пустые (`reports/toolcov_forms-form-element.json`,
там же `form.kind` — `catalog`, `form.object` — `Сотрудники`, `form.path` и `form.module` —
относительные пути файлов). То есть вид объекта в отчёте есть, но к каждому событию он не приписан, и
команда перечисления событий его не использует.

`check.sdbl check` по нашей конфигурации прочитал 8 файлов модулей (`stats.files 8`) и нашёл 3 запроса в 7
источниках (`src_object 4`, `src_temp 2`, `src_virtual_table 1`), проверил 23 ссылок на поля
(`field_refs 23`), из них разрешил 20 (`field_ok 20`), разрешил 5 имён объектов (`name_object 5`,
`name_object_ok 5`) и обе временные таблицы (`name_temp 2`, `name_temp_ok 2`) — при `results []` и
`summary.count 0`. Три ссылки на поля помечены пропущенными (`skip_field_fields_unknown 3`) и один
источник-виртуальная таблица пропущен из-за отсутствия описания её полей (`skip_vt_no_help_fields 1`):
поля `ЗатратыВремени` и `ПланЗагрузки` инструмент не знает. Код возврата 0 при этом не отличает
«проверено и чисто» от «проверять было нечего» — различие видно только в `stats`.

`check.sdbl query <skd>` по тексту нашего макета: 1 запрос, 5 источников (`src_object 3`, `src_temp 2`),
13 ссылок на поля и все 13 разрешены (`field_ok 13`), 3 имени объектов разрешены (`name_object 3`,
`name_object_ok 3`), `results []`. Ни один из этих прогонов не прочитал сам файл макета
`Reports/ОтчётЗагрузки/Templates/ОсновнаяСхемаКомпоновкиДанных/Ext/Template.xml` (в матрице §2 у обоих
`sdbl`-прогонов 0 путей): текст запроса из SKD-шаблонов читает обход `*.bsl`-модулей
(`p1c/src/p1c/check/sdbl/cli.py:145-157`, `rglob("*.bsl")` — строка 151), а не макеты компоновки данных.

Два прогона с кодом 2 стоят отдельно и служат контролем порядка токенов: у `load object` и
`check.forms form` корень должен идти после имени, и в обратном порядке CLI принимает первый позиционный
аргумент за имя сущности и отвечает `Корень выгрузки не найден: catalog.Сотрудники` /
`Корень выгрузки не найден: ФормаЭлемента`, кодом 2 и без отчёта.

## 8. Падение `p1c.cf` на нашей раскладке

```text
cf-info-cfg-dir  (exit 1, нет JSON-отчёта)
  argv: p1c.cf.cli info <cfg>
  Traceback (most recent call last):
  File "<p1c>\p1c\cf\cli.py", line 221, in <module>
  File "<p1c>\p1c\cf\cli.py", line 216, in main
  File "<p1c>\p1c\cf\cli.py", line 70, in cmd_info
  File "<p1c>\p1c\cf\cli.py", line 65, in _storage
  File "<p1c>\p1c\cf\storage.py", line 88, in __init__
  PermissionError: [Errno 13] Permission denied: '<repo>\cfg\ЭффективностьОтдела'
```

Артефакт: `reports/toolcov_runs.json` (`stderr_text` прогона `cf-info-cfg-dir`); отдельного JSON-отчёта
нет, потому что у подкоманды `cf info` нет флагов `--format` и `--out` — они есть только у `extract`,
`set` и `normalize` (`p1c/src/p1c/cf/cli.py:171-184` и `:187-212`), поэтому прогон шёл с
`writes_report: False` (`probe/tool_coverage.py:89`).

Наша конфигурация — xml-выгрузка из каталога, `.cf`-файла у неё нет; `cf` ждёт файл архива. Передан
каталог `cfg\ЭффективностьОтдела` — и вместо сообщения об ошибке пользователь получает traceback:
`p1c/src/p1c/cf/cli.py` (кадры 221 → 216 → 70 → 65) доходит до `p1c/src/p1c/cf/storage.py:88` и падает
по `PermissionError: [Errno 13] Permission denied`. Кадры 221/216/70/65 — места вызова; определения —
`def _storage` (строка 60), `def cmd_info` (строка 68), `def main` (строка 160): противоречия в
обратной трассировке нет, она читается как цепочка вызовов. Ошибка не переведена в отчёт `p1c.result/v1`
и не имеет кода, отличного от «упал».

## 9. Находки `p1c.check.bsl` по нашей конфигурации: 15 строк и их разбор

| код | текст находки | строка | файл cfg | строка исходника | grounding |
|---|---|---|---|---|---|
| `IDS_STX_VAR_NOTDECLARED` | Переменная не определена (Ставка) | 11 | `Catalogs/Сотрудники/Ext/ObjectModule.bsl` | `Если Ставка <= 0 Тогда` | official_code |
| `IDS_STX_VAR_NOTDECLARED` | Переменная не определена (ДатаПриёма) | 17 | `Catalogs/Сотрудники/Ext/ObjectModule.bsl` | `Если Не ЗначениеЗаполнено(ДатаПриёма) Тогда` | official_code |
| `IDS_STX_VAR_NOTDECLARED` | Переменная не определена (НачалоПериода) | 6 | `DataProcessors/ВыгрузкаЗатратCSV/Forms/ФормаВыгрузки/Ext/Form/Module.bsl` | `Если Не ЗначениеЗаполнено(НачалоПериода) Тогда` | official_code |
| `IDS_STX_VAR_NOTDECLARED` | Переменная не определена (НачалоПериода) | 20 | `DataProcessors/ВыгрузкаЗатратCSV/Forms/ФормаВыгрузки/Ext/Form/Module.bsl` | `ДанныеВыгрузки = СформироватьВыгрузкуНаСервере(НачалоПериода, КонецПериода);` | official_code |
| `IDS_STX_CTOR_NOTFOUND` | Конструктор не найден | 25 | `DataProcessors/ВыгрузкаЗатратCSV/Forms/ФормаВыгрузки/Ext/Form/Module.bsl` | `Сообщение = Новый СообщениеПользователю;` | official_code |
| `IDS_STX_METHODNOTFOUND` | Метод объекта не обнаружен (СообщениеПользователю.Текст) | 26 | `DataProcessors/ВыгрузкаЗатратCSV/Forms/ФормаВыгрузки/Ext/Form/Module.bsl` | `Сообщение.Текст = "За выбранный период затрат времени нет. Проверьте границы периода и записи регистра ЗатратыВремени.";` | official_page |
| `IDS_STX_METHODNOTFOUND` | Метод объекта не обнаружен (СообщениеПользователю.Поле) | 27 | `DataProcessors/ВыгрузкаЗатратCSV/Forms/ФормаВыгрузки/Ext/Form/Module.bsl` | `Сообщение.Поле = "ТекстВыгрузки";` | official_page |
| `IDS_STX_METHODNOTFOUND` | Метод объекта не обнаружен (СообщениеПользователю.Сообщить) | 29 | `DataProcessors/ВыгрузкаЗатратCSV/Forms/ФормаВыгрузки/Ext/Form/Module.bsl` | `Сообщение.Сообщить();` | official_page |
| `IDS_STX_VAR_NOTDECLARED` | Переменная не определена (Сотрудник) | 6 | `Documents/ФактРаботы/Ext/ObjectModule.bsl` | `Если Не ЗначениеЗаполнено(Сотрудник) Тогда` | official_code |
| `IDS_STX_VAR_NOTDECLARED` | Переменная не определена (Часы) | 12 | `Documents/ФактРаботы/Ext/ObjectModule.bsl` | `Если Часы <= 0 Тогда` | official_code |
| `IDS_STX_VAR_NOTDECLARED` | Переменная не определена (Движения) | 18 | `Documents/ФактРаботы/Ext/ObjectModule.bsl` | `Движения.ЗатратыВремени.Заполнять(Истина);` | official_code |
| `IDS_STX_VAR_NOTDECLARED` | Переменная не определена (Движения) | 19 | `Documents/ФактРаботы/Ext/ObjectModule.bsl` | `Движения.ЗатратыВремени.Очистить();` | official_code |
| `IDS_STX_VAR_NOTDECLARED` | Переменная не определена (Движения) | 21 | `Documents/ФактРаботы/Ext/ObjectModule.bsl` | `Строка = Движения.ЗатратыВремени.Добавить();` | official_code |
| `IDS_STX_VAR_NOTDECLARED` | Переменная не определена (Сотрудник) | 24 | `Documents/ФактРаботы/Ext/ObjectModule.bsl` | `Строка.Сотрудник = Сотрудник;` | official_code |
| `IDS_STX_VAR_NOTDECLARED` | Переменная не определена (Часы) | 25 | `Documents/ФактРаботы/Ext/ObjectModule.bsl` | `Строка.Часы = Часы;` | official_code |

Артефакт: `reports/toolcov_bsl-check-cfg.json` (`results`, `stats`, `summary`); строки исходника в
последней колонке таблицы генератор берёт из самих файлов `cfg` (`probe/render_query_tables.py`).
Прогон: `p1c.check.bsl.cli check <cfg> --root <dump>` — 8 прочитанных файлов модулей, 15 находок,
`by_rule: names 4, scope 11`, `by_severity: error 15`, `by_grounding: official_code 12, official_page 3`.

Разбор по происхождению, с опорой на уже измеренное.

**11 из 15 — шум канона 1С, а не дефект сборки.** Восемь находок `IDS_STX_VAR_NOTDECLARED` на
`Ставка`, `ДатаПриёма`, `Сотрудник`, `Часы`, `НачалоПериода` — это неявные реквизиты: в модулях объекта
справочника/документа и в модуле управляемой формы реквизиты доступны по имени без `Объект.`, и так
написано во всех корпусах. Три находки на `Движения` (`Движения.ЗатратыВремени.Заполнять`,
`.Очистить`, `.Добавить`) — неявное свойство документ-модуля. Обе группы уже разобраны в
`docs/evidence/tool-probe-negative-cases.md` §4 (11 находок на неполоманной конфигурации, 10 из них —
на валидном коде) и в `docs/evidence/canonical-queries.md` (пометки «шум самомера» для `Движения.`).
Отдельное правило из того же замера: запускать проверку надо на каталоге с `--root` — на одиночном
файле `CommonModules/РасчётПоказателей/Ext/Module.bsl` появляется ещё и `IDS_STX_VAR_NOTDECLARED
(РасчётПоказателей)`: без корня-модели инструмент теряет контекст сущности, и набор находок на том же коде
оказывается другим.

**4 находки — реальный пробел в данных `p1c`, а не шум.** `Сообщение = Новый СообщениеПользователю;`
(`IDS_STX_CTOR_NOTFOUND`), `.Текст`, `.Поле`, `.Сообщить` (`IDS_STX_METHODNOTFOUND`). Проверено по
корпусам (`reports/corpora-msg-ctor-18.json`, скрипт замера — вне репозитория): конструктор
`Новый СообщениеПользователю` написан 26426 раз в 3820 файлах из 50309 `.bsl`-файлов шести корпусов
(ERP 13720 в 1948 файлах, УХ 12590 в 1791, СЛ 64 в 41, ЛСО 40 в 29, Пульсар 8 в 7, ИИ-чат 4 в 4; имя
`СообщениеПользователю` всего — 28810 встреч), а в исходниках `p1c` — 0 встреч `Новый
СообщениеПользователю` и 3 встречи самого имени в двух файлах данных (`p1c/src/p1c/data/test_api.json`
1, `p1c/src/p1c/data/platform_arities.py` 2).

Почему именно эти четыре строки стали находками — измерено по самому дереву `p1c`
(`reports/p1c-ctor-data-23.json`, скрипт замера — вне репозитория):

- Таблица `TYPE_CONSTRUCTORS` (`p1c/src/p1c/data/platform_arities.py:22189`) — 22 записей, и таблицей
  конструкторов типов она не является: её имена — события и методы (`AfterWrite`, `AfterWriteAtServer`,
  `BeforeWrite`, `BeforeWriteAtServer`, `OnReadAtServer`, `Read`, `Write`, `ValueChoice`, `ВыборЗначения`,
  `Записать`, `ПередЗаписью`, `ПослеЗаписи`, `ПриЗаписиНаСервере`, `ПриЧтенииНаСервере`, `Прочитать` и
  другие). Записей с именами `СообщениеПользователю`, `Массив`, `ТекстовыйДокумент` в ней нет. Слово
  `TYPE_CONSTRUCTORS` встречается в дереве `p1c` ровно 2 раза: определение в файле данных и строка
  сборки в `p1c/scripts/extract_help_arities.py:252`; обращений к ней внутри пакета `p1c/src/p1c` — 0.
  Таблица собрана и никем не читается.
- Таблица `TYPE_SIGNATURES` (`platform_arities.py:999`) — 1885 записей, и у всех 1885 ровно один ключ
  `methods`: записей с ключом `ctor` — 0, с ключом `properties` — 0. Запись `СообщениеПользователю`
  (`platform_arities.py:18739`) существует, методов у неё 1 — `УстановитьДанные` (`min_args 1`,
  `max_args 1`, `returns null`, доступность в 9 режимах); имён `Текст`, `Поле`, `Сообщить` в этой записи
  нет.
- Тип, который видит проверка, собирается не из этих таблиц, а вручную: `builtin_type_model()`
  (`p1c/src/p1c/metadata/model.py`) регистрирует 1913 типов, `СообщениеПользователю` среди них есть как
  `kind collection`, но `ctor_arities` пусто, методов 1 (`установитьданные`), свойств 0,
  `dynamic_members false`. Арности конструктора в модели есть только у типов из вручную написанных
  таблиц `SCALARS` (12), `COLLECTIONS` (12, из них 9 с `ctor_arities`) и `EXTRA_TYPES` (27);
  `СообщениеПользователю` и `ТекстовыйДокумент` нет ни в одной из них, `Массив` есть и его
  `ctor_arities` — `(0, 1)`. Без арностей конструктора остаются 1869 типов из 1913.
- Строки, которые выдают эти находки: `p1c/src/p1c/check/bsl/semantic.py:739` `if not t.ctor_arities:`
  (комментарий «тип не создаётся оператором Новый») → `:741` `self.err("IDS_STX_CTOR_NOTFOUND", …)`;
  `:649-655` ищут имя среди `methods`, потом `properties`, потом `dynamic_members`, а `:658-661`
  выбирают код по `kind` типа (`IDS_STX_PROPERTYNOTFOUND` для `ref`, `enum_ref`, `enum_manager`,
  `ts_row`, `tabular`, `qualifier`, иначе `IDS_STX_METHODNOTFOUND`) и `:662` его выдают.

**Находка по строке `&Сервер` из отчёта убрана, и убрана она потому, что она была дефектом нашей
сборки.** Прежний отчёт содержал находку на отдельную директиву `&Сервер` в
`InformationRegisters/ПланЗагрузки/Ext/ManagerModule.bsl`. Корпусной замер (`reports/corpora-server-annotation-18.json`,
паттерны `^\x{FEFF}?\s*&Сервер\s*$`, `&Сервер$`, `&Сервер\p{L}` по тем же шести корпусам, 50309
`.bsl`-файлов) даёт: контрольный счётчик канонической директивы `&НаСервере` — 317861 встреч (ERP 174928
в 10269 файлах, УХ 126750 в 7644, СЛ 6849 в 1082, ЛСО 5665 в 988, Пульсар 3578 в 506, ИИ-чат 91 в 20);
написание `&Сервер` — 8 встреч (ERP 3 в 2 файлах, УХ 3 в 2, SSL 2 в 1, ЛСО, Пульсар и ИИ-чат — 0).
Подстрока `&Сервер` не входит в `&НаСервере`: в `&НаСервере` после амперсанда стоит `На`, поэтому 8 — это
отдельные написания, а не часть 317861. И все 8 стоят внутри текста запроса как имена
параметров (`&СерверПодписи` в `CommonModules/СервисКриптографииDSSСлужебный/Ext/Module.bsl` ERP:2892
и :2893, SSL:2922 и :2923, УХ:2844 и :2845; `&СерверДокументооборота` в
`DataProcessors/ДокументооборотСКонтролирующимиОрганами/Forms/КонтейнерКлиентскихМетодов/Ext/Form/Module.bsl`
ERP:24974, УХ:20828; все эти строки — продолженные, с префиксом `|`). Standalone-строк, где директива
`&Сервер` стоит вся на строке и не продолжается буквой, — 0 из 50309 файлов. Написание `&Сервер`
корпусно не подтверждено, директива из модуля убрана, после `python scripts/normalize_text.py` гейт
`reports/gate-14.json` даёт код 0, а `p1c.check.bsl` по нашей конфигурации теперь даёт 15 находок, и
строки `&Сервер` в таблице выше нет.

Два счётчика несопоставимы, и расхождение между ними разложено измерением — `reports/corpora-token-skip-20.json`
(три ripgrep-счётчика по тем же шести корпусам) и `reports/corpora-bsl-sizes-21.json` (размер каждого
`.bsl`-файла корпусов, содержимое не читалось).

- Обход тех же 50309 `.bsl`-файлов даёт 214 файлов крупнее лимита `max_module_bytes 1048576`
  (`corpora-bsl-sizes-21.json`: ERP 120, УХ 84, Пульсар 4, SSL 4, ЛСО 2, ИИ-чат 0; их суммарный объём
  401742608 байт из 2690063711 байт всех `.bsl` корпусов). В `corpora-bsl-15.json` пропущены ровно они:
  `files_skipped_over_limit 214` и `files_read 50095 = 50309 − 214`.
- Счётчик целого токена `&НаСервере` (с границей слова после имени) по всем файлам — 300926, из них
  24065 приходятся на файлы выше лимита. Остаток `300926 − 24065 = 276861` — ровно то число, которое
  стоит в `corpora-bsl-15.json` против `&НаСервере`, и он сходится по каждому корпусу: ERP 153419,
  УХ 109644, SSL 5853, ЛСО 4903, Пульсар 2971, ИИ-чат 71.
- Счётчик подстроки `&НаСервере` — 317861. Разница `317861 − 300926 = 16935` разложена дословно:
  отдельный обход собрал все написания вида `&НаСервере` плюс ещё буквы/цифры/подчёркивание — 16935
  встреч, 3 различных написания (`&НаСервереБезКонтекста` 16920, `&НаСервереБезконтекста` 10,
  `&НаСерверебезКонтекста` 5). То есть `na_token + vocab = na_any` держит ровно и по каждому корпусу
  (ERP `167219 + 7709 = 174928`, УХ `119665 + 7085 = 126750`, SSL `5853 + 996 = 6849`,
  ЛСО `4903 + 762 = 5665`, Пульсар `3215 + 363 = 3578`, ИИ-чат `71 + 20 = 91`). В артефакте контроль
  `na_token_equals_vocab_exact_name` дал `false` по причине написания шаблона: словарь требует
  хотя бы одного символа после имени, поэтому самого `&НаСервере` в нём нет (`vocab_exact_name 0`) —
  это свойство шаблона замера, а не расхождение счётчиков.
- Разница подстрочного счётчика с числом `corpora-bsl-15.json` — 41000 (`16935 + 24065 = 41000`).
- `&Сервер` целым токеном — 0 встреч во всех шести корпусах, в том числе 0 в файлах выше лимита.
- Счётчики `corpora-token-skip-20.json` чувствительны к регистру: все шаблоны начинаются с `&НаСервере`,
  поэтому написания со сбитым регистром в них не попадают. В словаре `corpora-bsl-15.json` (18335
  различных токенов) они есть отдельными ключами: `&НаСервереБезконтекста` 10, `&НаСерверебезКонтекста` 5,
  `&Насервере` 10, `&наСервере` 4, `&наСервереБезКонтекста` 3. Наш словарь даёт `&НаСервереБезконтекста` 10
  и `&НаСерверебезКонтекста` 5 — ровно те же числа (ERP 7 и 0, УХ 3 и 5), и обе суммы в `corpora-bsl-15.json`
  не теряются файлами выше лимита. Оставшиеся три написания (`&Насервере`, `&наСервере`,
  `&наСервереБезКонтекста`) нашим шаблоном не измерялись: им не предшествует `&НаСервере`.
- Счётчик `&НаСервереБезКонтекста` сходится с `corpora-bsl-15.json` по той же схеме, что и `&НаСервере`:
  по всем файлам 16920, в `corpora-bsl-15.json` — 15275; разность `16920 − 15275 = 1645` лежит в файлах
  выше лимита (ERP `7702 − 6866 = 836`, УХ `7077 − 6281 = 796`, Пульсар `363 − 350 = 13`, SSL 996 = 996,
  ЛСО 762 = 762, ИИ-чат 20 = 20; `836 + 796 + 13 = 1645`).

Причина, по которой `&СерверДокументооборота` нет среди 18335 различных токенов `corpora-bsl-15.json`
(в них есть `&СерверПодписи` 6 и `&СсылкаСервера` 3, но нет `&Сервер`), теперь тоже измерена: носители
этого написания превышают лимит обхода. `DataProcessors/ДокументооборотСКонтролирующимиОрганами/Forms/КонтейнерКлиентскихМетодов/Ext/Form/Module.bsl`
— 7498805 байт в ERP (4-й по величине `.bsl` корпуса) и 6916020 байт в УХ (2-й по величине), а носители
`&СерверПодписи` под лимит попадают: `CommonModules/СервисКриптографииDSSСлужебный/Ext/Module.bsl` —
491317 байт (ERP), 475668 (УХ), 488339 (SSL). Отсюда 6 встреч `&СерверПодписи` в токенах есть, а 2 встреч
`&СерверДокументооборота` нет: их файл не читался.

Ни один из этих замеров не утверждает, что платформа делает с директивой `&Сервер`: headless-исполнения
модулей командной строкой подтвердить не удалось (`docs/evidence/exec-modes-and-negatives.md`), поэтому
дефект исправлен по корпусному канону, а не по вердикту платформы.

## 10. Следствие для инструментов p1c

1. **Права ролей читаются только вне инструментов.** 2 файла `Roles/*/Ext/Rights.xml`, 17 блоков
   объектов и 79 прав подтверждены гейтом (`rights.immobile`, код 0), а `p1c` их не читает: `role` и
   `role_rights` — ноль по обеим мерам. Роль в нашей конфигурации — настроенная, и ни один инструмент
   этого не увидит.
2. **Предопределённые данные, макеты, язык и подсистемы — вне поля зрения читателей.** Классы
   `predefined_data`, `report_template`, `report_template_data`, `language`, `subsystem` не увидены ни
   по пути, ни по имени; ключей таких в модели `p1c.load` нет (§6). Наш SKD-запрос лежит в
   `Templates/*/Ext/Template.xml`, и `p1c.check.sdbl` его не читает (§7) — он проверил 3 запроса только
   потому, что они написаны в `.bsl`-модулях.
3. **Модули уровня конфигурации не доходят до читателя.** `object_module` (6 файлов) виден по пути двум
   инструментам из восьми; `load`, `diff`, `graph`, `forms` путей модулей объекта в отчётах не называют.
4. **Справочник событий формы в `p1c` есть, но команды им не пользуются.** `check.forms form` оставляет
   `kind` и `owner` пустыми у всех трёх обработчиков `ФормаЭлемента`, хотя `form.kind` в том же отчёте —
   `catalog`. `check.forms events` без `--kind` перечисляет 26 событий только базовой страницы
   `ClientApplicationForm`, где `AfterWrite`/`BeforeWrite` отсутствуют; явный `--kind` включает страницу
   расширения формы этого вида (`catalog` и `document` — 33 события, `constant` и
   `information_register` — 32, `task` и `business_process` — 34), где они есть. Для
   `data_processor`, `accumulation_register`, `calculation_register`, `chart_of_characteristics`,
   `accounting_register`, `chart_of_accounts` и `chart_of_calculation` прирост нулевой: их страницы есть в
   данных `EVENT_SIGNATURES`, но `is_managed_page` (`p1c/src/p1c/check/forms/checks.py:143-146`) отвергает
   их, потому что там указана доступность только `thick_client` (§7). Заведомо неизвестное имя вида
   (`--kind zzz-netakogo-vida`) даёт ровно то же, что отсутствующий флаг: `exit 0`, базовая страница и 26
   имён при пустом `stderr`.
5. **Модель `p1c.load` не представляет часть конфигурации**, поэтому её «полнота» не равна полноте
   раскладки: 10 классов из 22.
6. **Код возврата не сообщает, что было прочитано**: `check.sdbl` и `check.forms` дают 0 с пустым
   `results` при непустом `stats`, `cf` падает traceback'ом без отчёта, два прогона дают 2 без отчёта.
7. **Форма argv у `load object` и `check.forms form` расходится с подсказкой**, и это видно только
   прогоном в неправильном порядке.
8. **Треть рёбер графа (`37` из `102`) осталась неразрешённой** — разрешения имён платформенных методов и
   свойств в графе вызовов нет, хотя сами имена (`ОбработкаПроведения`, `ПриСозданииНаСервере`) график
   использует как вершины.
9. **Подпись контекста зависит от написания пути корня** (два значения на 15 отчётах при идентичном
   содержимом проверок) — уже описанный дефект, здесь подтверждённый ещё раз.
10. **Сведения о конструкторах и свойствах встроенных типов до проверки не доходят.** Таблица
    `TYPE_CONSTRUCTORS` (22 записи, 0 обращений внутри пакета) никем не используется; у всех 1885
    записей `TYPE_SIGNATURES` есть только `methods` — ни `ctor`, ни `properties`. В модели, которую
    видит `check.bsl`, арности конструктора заданы вручную лишь для 12 `SCALARS` + 12 `COLLECTIONS` +
    27 `EXTRA_TYPES`, а 1869 типов из 1913 остаются без конструктора: `Новый <Тип>` вне этого списка
    даёт `IDS_STX_CTOR_NOTFOUND`, а любое свойство такого типа — `IDS_STX_METHODNOTFOUND` (§9). Так
    4 из 15 находок по нашей конфигурации берутся из неполноты данных `p1c`, а не из кода.

## 11. Что с этим делать (часть плана оптимизации p1c)

1. Добавить в `p1c.load` чтение `Roles/*/Ext/Rights.xml` и `*/Ext/Predefined.xml`, а в модель — ключи
   `roles`, `subsystems`, `languages`, `session_parameters`, `templates`; иначе классы `role`,
   `role_rights`, `predefined_data`, `subsystem`, `language`, `report_template`, `report_template_data`
   останутся слепыми.
2. Сделать страницу расширения формы видом по умолчанию, а не флагом: `check.forms events` без `--kind`
   должен принимать вид формы, а `check.forms form` — заполнять `kind`/`owner` по `form.kind`. Данные для
   этого уже есть: `OBJECT_PAGE` (`p1c/src/p1c/check/forms/checks.py:42+`) и `EVENT_SIGNATURES`
   (`p1c/src/p1c/data/platform_arities.py`, 135 страниц, 29 из них вида `… form extension`). Отдельно
   решить, как отмечать страницы с доступностью только `thick_client` (`data_processor`,
   `accumulation_register`, `calculation_register`, `chart_of_characteristics`, `accounting_register`,
   `chart_of_accounts`, `chart_of_calculation`): сейчас они возвращают 26 базовых имён, хотя сигнатуры
   `AfterWrite`/`BeforeWrite`/`OnWrite` в этих данных записаны. И переданное `--kind` имя надо проверять по
   `OBJECT_PAGE`: `zzz-netakogo-vida` даёт `exit 0` и те же 26 имён при пустом `stderr` (§7).
3. Включить в отчёты модели `p1c.load` пути модулей уровня конфигурации (`Ext/ObjectModule.bsl`,
   `Ext/ManagerModule.bsl`) — сейчас их видят только `bsl` и `metrics`.
4. Считать обход `*.bsl` в `check.sdbl` полным обходом макетов тоже: читать `<query>` из
   `Templates/*/Ext/Template.xml` и `CommonForms`/`Forms/*/Ext/Form.xml` наряду с модулями. Сейчас обход
   строится из `queries_in_module(ctx)` (`p1c/src/p1c/check/sdbl/cli.py:145`), который берёт
   `ctx.modules()` (`:148`), а счётчик `files_read` (`:150`) считает те же модули с пометкой `src_bsl`
   (`:154`); SKD-запросы в этот обход не попадают (§7).
5. Разрешать поля виртуальных таблиц регистра (`skip_vt_no_help_fields`, `skip_field_fields_unknown`) по
   данным метаданных выгрузки: описания полей `ЗатратыВремени` и `ПланЗагрузки` есть в
   `AccumulationRegisters/ЗатратыВремени.xml` и `InformationRegisters/ПланЗагрузки.xml`, и модель их уже
   знает как объекты.
6. Отличать «проверено и чисто» от «проверять было нечего»: отдельный код (или отдельный ключ отчёта)
   при `schema_available false` или `stats.files == 0`, и явное перечисление фактически прочитанных
   файлов в каждом отчёте.
7. Починить сборку позиционных аргументов у `load object` и `check.forms form` так, чтобы порядок,
   обещанный подсказкой, работал, и сообщать о неразобранном аргументе до обращения к корню: сейчас
   ответ — `Корень выгрузки не найден: <имя>` и код 2 без отчёта.
8. `p1c.cf`: не принимать каталог вместо `.cf` (проверка до открытия — `p1c/src/p1c/cf/storage.py:88`),
   вернуть ошибку в формате `p1c.result/v1` вместо traceback'а, и добавить `--format`/`--out` подкомандам
   `info`, `list`, `cat` (`p1c/src/p1c/cf/cli.py:171-184`) — сейчас они не пишут машинный отчёт вообще.
9. Пополнить `PLATFORM_ANNOTATIONS` (`p1c/src/p1c/data/platform_directives.py:44`, где сейчас только
   `Вместо`, `ИзменениеИКонтроль`, `Перед`, `После`) семейством контекстных аннотаций (`&НаСервере`,
   `&НаКлиенте`, `&НаСервереБезКонтекста`, `&НаКлиентеНаСервереБезКонтекста`), и внести тип
   `СообщениеПользователю` в те таблицы модели, которые она действительно читает (`COLLECTIONS` или
   `EXTRA_TYPES` в `p1c/src/p1c/metadata/model.py`), с арностями конструктора, свойствами `Текст` и
   `Поле` и методом `Сообщить`: 26426 написаний конструктора в корпусах против нуля в `p1c` (§9). Это же
   касается канона неявных реквизитов и `Движения.` — их надо распознавать как канон, а не выдавать
   `IDS_STX_VAR_NOTDECLARED`: 11 из 15 нынешних находок по нашей конфигурации — именно такой шум.
10. Добавить в `p1c` аналог платформенных `/CheckConfig`, `/CheckModules`, `-ExtendedModulesCheck`:
    неподтверждённая headless-проверка модулей остаётся самой крупной слепой зоной (замеры —
    `docs/evidence/exec-modes-and-negatives.md`).
11. Сообщать о пределе обхода как о непроверенной части, а не молчать: `max_module_bytes 1048576`
    не читает 214 модулей корпусов (401742608 байт из 2690063711), и именно поэтому в словаре
    `corpora-bsl-15.json` нет написания `&СерверДокументооборота` (§9). Отдельно — сверка имён
    аннотаций по эталонному написанию: корпуса пишут `&НаСервереБезконтекста` 10,
    `&НаСерверебезКонтекста` 5, `&Насервере` 10, `&наСервере` 4, `&наСервереБезКонтекста` 3; словарь
    `corpora-bsl-15.json` эти написания различает, но сопоставление с эталонным именем их не находит.
12. Разобраться с данными конструкторов в `p1c/src/p1c/data/platform_arities.py`. Таблица
    `TYPE_CONSTRUCTORS` (22 записи) пишется сборщиком `p1c/scripts/extract_help_arities.py:252`,
    содержит имена событий и методов (`AfterWrite`, `ПередЗаписью`, `ВыборЗначения`, `Записать`,
    `Прочитать`) вместо конструкторов встроенных типов, и не читается ни одним кодом внутри пакета
    `p1c/src/p1c` — её либо удаляют, либо делают настоящим источником арностей `Новый <Тип>`. Связанная
    работа — harvest арностей конструкторов и свойств встроенных типов: 0 из 1885 записей
    `TYPE_SIGNATURES` не содержат ни `ctor`, ни `properties`, и из-за этого 1869 типов из 1913 в модели
    остаются без конструктора (§9 и §10, пункт 10).

## 12. Честная граница меры

- Матрица мерит то, что инструмент **назвал** в своём отчёте или консоли. Она не мерит, что именно
  инструмент прочитал с диска: путь мог появиться из напечатанного аргумента, а имя — из строки
  контекста. Именно поэтому имена вплотную к `/` вынесены отдельно (§4), а хиты консоли — отдельно от
  хитов отчёта.
- Матрица мерит покрытие восьми инструментов по 18 командам, не по всем подкомандам `p1c`.
  Модифицирующие подкоманды `cf set` и `cf normalize` в замер не включены; подкоманды, которые
  требовали бы запуска платформы, в этом замере не участвовали вовсе.
- Мера не утверждает, что прочитанное содержимое корректно: `p1c.metrics` прочитал 7 файлов модулей, а
  имя сущности в его отчёте ровно одно; `p1c.load` назвал 10 классов из 22. Числа колонки «имён cfg» — это
  имена, которые встречаются в отчёте, а не оценка полноты.
- `context_signature` и `context_effective` из отчётов в таблицы и блоки содержимого не переносится
  (`probe/render_query_tables.py::SKIP_REPORT_KEYS`), чтобы абсолютные пути не попадали в документ;
  числа подписей в §5 приведены по первым 16 шестнадцатеричным разрядам значений из артефактов.
- Строки исходника в таблице §9 — дословный текст из файлов `cfg`; колонка «строка» — номер строки,
  который сообщил инструмент, а не выверенный нами.
- Ни одно утверждение этого документа не опирается на запуск платформы 1С: все 18 прогонов — вызовы
  Python-модулей `p1c` и обход каталога; корпусные замеры §9 — ripgrep по `*.bsl` и размеры файлов
  (`stat`), содержимое 214 модулей крупнее лимита в корпусах не читалось ни в одном из замеров.
