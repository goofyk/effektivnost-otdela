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
`reports/gate-16.json` (гейт, с которым матрица сверяется; `reports/gate-15.json` и
`reports/gate-14.json` — записи прежних прогонов того же гейта по тому же исходнику, посчитанные
читателем после правок A1/A2 и до них). Таблицы и блоки содержимого отчётов в этот
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
`probe/tool_coverage.py::PATH_EDGE` (строка 286) и `name_occurrences` (строки 289-304): если имя стоит
сразу после или сразу перед разделителем пути, эта встреча не засчитывается в покрытие и выносится
отдельным числом (`name_hits_path_echo_only`). Пример: `"root": "<repo>/cfg/ЭффективностьОтдела"` или
`"file": ".../Catalogs/Сотрудники.xml"` — инструмент напечатал путь, который мы ему же и передали.

**Правило 2. Пять классов измеряются только путём файла.** `PATH_ONLY_KINDS` (строка 109):
`role_rights`, `predefined_data`, `object_module`, `bsl_module`, `files`. Имя роли в отчёте не доказывает,
что инструмент прочитал `Roles/<роль>/Ext/Rights.xml`; имя справочника — что он прочитал
`*/Ext/Predefined.xml`. Имена этих классов в покрытие не засчитываются вообще.

**Правило 3. Имя сущности не мерится там, где имя передали мы сами.** У пяти прогонов
`names_counted: False` (строки 70-91): `load-object-catalog` (`p1c.load.cli object catalog.Сотрудники`),
`load-object-wrong-order`, `forms-form-element` (`p1c.check.forms.cli form ФормаЭлемента`),
`forms-form-wrong-order`, `sdbl-query-skd` (текст `<skd>` передаётся аргументом). В этих прогонах имя в
отчёте — эхо наших же слов; там засчитывается только путь файла макета.

Плюс два уточнения меры. Платформенные имена файлов `Form.xml`, `Module.bsl`, `Template.xml` именами
сущностей не считаются (`GENERIC_STEMS`, строка 105); имя сущности — каталог, в котором лежит её `Ext`
(`entity_name`, строки 174-187). Колонка «имён только как часть пути» считает имена и в отчёте, и в
консоли вместе (строки 338-342), а колонка «хитов только в консоли» считает только пути и засчитанные
имена, которых нет в JSON-отчёте (строки 334 и 336-337); поэтому у `cf-info-cfg-dir` эхо-имя есть, а хитов
только в консоли — нет: отчёта у того прогона нет вовсе, и имя появилось из текста traceback'а.

Раскладка, по которой считается мера: 31 файл, 22 класса макета (`cfg_files_by_kind`); класс `files` —
все 31 файл. Числа замера сверены с независимым счётчиком раскладки гейта (`counts_match`, строки
164-171): 22 класса против 22, расхождений ноль. Счётчик читателя `p1c.load` считает другое — манифест
фактически открытых файлов (`model.read_files`), и он даёт 30 файлов: не прочитан ровно
`Configuration.xml`. Об этом §5 и §12.

## 2. Матрица прогонов: код возврата, находки, покрытие

| прогон | команда прогона (ярлыки путей) | код возврата | находок в JSON-отчёте | файлов cfg в JSON-отчёте | имён cfg в JSON-отчёте | имён только как часть пути | хитов только в консоли |
|---|---|---|---|---|---|---|---|
| `load-model-dump` | `p1c.load.cli model <dump>` | 0 | 0 | 30 | 16 | 0 | 0 |
| `load-model-cfg` | `p1c.load.cli model <cfg>` | 0 | 0 | 30 | 16 | 0 | 0 |
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
| `cf-info-cfg-dir` | `p1c.cf.cli info <cfg>` | 2 | **нет JSON-отчёта** | 0 | 0 | 1 | 0 |

Артефакты: `reports/toolcov_runs.json` (`runs`, `matrix_by_kind`), коды возврата и дословный stderr —
`reports/toolcov_summary.txt`, содержимое от каждого отчёта — `reports/toolcov_<ярлык>.json`.

Код возврата отвечает только за дисциплину прогона, исходы живут в ключах отчёта. По 18 прогонам:
14 прогонов с кодом 0; два прогона с кодом 2 и без JSON-отчёта — `load-object-wrong-order`
(`stderr: Неверный порядок аргументов: «<dump>» — путь, а не имя. Канонический порядок:
p1c-load object <вид>.<имя> [корень]`) и `forms-form-wrong-order` (тот же текст, но
`p1c-check-forms form <имя формы> [корень]`); `bsl-check-cfg` — код 1 при 15 находках в отчёте;
`cf-info-cfg-dir` — код 2 без отчёта, `stderr: Книга .cf ожидается файлом, а передан каталог: <cfg>`
(§8).

Ни один из 18 прогонов ничего не вывел в stdout: сумма `stdout_chars` по всем прогонам 0, потому что
каждый успешный прогон писал отчёт в файл через `--format json --out reports/toolcov_<ярлык>.json`
(у `cf-info-cfg-dir` этих флагов нет вовсе — см. §8). Строка `[context] XML разобран: объектов 8,
форм 2, модулей к сканированию 20` стоит в stderr 11 прогонов из 18; у семи её нет (`graph-build-dump`,
`graph-roots-dump`, `metrics-top-dump`, `forms-events-dump`, `load-object-wrong-order`,
`forms-form-wrong-order`, `cf-info-cfg-dir`), у `diff-model-cfg-dump` она встречается дважды.

Число 20 — это очередь модулей читателя (`module_jobs` в `p1c/src/p1c/load/reader.py:920`, её длина
печатается в строке `reader.py:1118`), а не число `.bsl`-файлов на диске: из 20 слотов на диске лежат
8 — ровно те 8 `.bsl`, которые есть и в `<cfg>`, и в `<dump>`; остальные 12 указывают на модули,
которых в раскладке нет. Очередь замерена напрямую: `p1c.load.reader.load_configuration_model` вызвана
на `<dump>` с подменённым `p1c.load.scan.scan_one` (`probe/reader_module_queue.py`, артефакт
`reports/reader-module-queue.txt`), и аргументы этой подмены и есть содержимое очереди — 20 путей. Разложение: 17 слотов модулей объектов
(7 `ManagerModule.bsl`, 5 `ObjectModule.bsl`, 2 `RecordSetModule.bsl` у регистров,
3 `ValueManagerModule.bsl`) плюс 1 слот общего модуля и 2 слота модулей форм. Прежний замер давал 18:
слоты модулей форм читатель добавляет только с правки `dcf0112` (`reader.py:980`), до неё модули форм
в очередь не попадали. Отсутствующие слоты в `skipped_files` не пишутся: `scan_one` на отсутствующем
файле возвращает `read = False` без ошибки, и такой путь в манифест не попадает
(`reader.py:1154-1157`, объяснение — `reader.py:857-860`).

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
| `accumulation_register` | 1 | 1 | 1 | 0 | `load` |
| `bsl_module` | 8 | 4 | 0 | 0 | `bsl`, `forms`, `load`, `metrics` |
| `catalog` | 1 | 1 | 3 | 2 | `load` |
| `common_module` | 1 | 1 | 3 | 0 | `load` |
| `constant` | 1 | 1 | 1 | 0 | `load` |
| `data_processor` | 1 | 1 | 2 | 2 | `load` |
| `document` | 1 | 1 | 2 | 2 | `load` |
| `enum` | 1 | 1 | 1 | 0 | `load` |
| `files` | 31 | 4 | 0 | 0 | `bsl`, `forms`, `load`, `metrics` |
| `form_data` | 2 | 2 | 3 | 2 | `forms`, `load` |
| `form_descriptor` | 2 | 1 | 3 | 2 | `load` |
| `form_module` | 2 | 4 | 3 | 2 | `bsl`, `forms`, `load`, `metrics` |
| `information_register` | 1 | 1 | 2 | 1 | `load` |
| `language` | 1 | 1 | 1 | 0 | `load` |
| `object_module` | 6 | 3 | 0 | 0 | `bsl`, `load`, `metrics` |
| `predefined_data` | 1 | 1 | 0 | 0 | `load` |
| `report` | 1 | 1 | 1 | 0 | `load` |
| `report_template` | 1 | 1 | 1 | 0 | `load` |
| `report_template_data` | 1 | 1 | 1 | 0 | `load` |
| `role` | 2 | 1 | 1 | 0 | `load` |
| `role_rights` | 2 | 1 | 0 | 0 | `load` |
| `subsystem` | 1 | 1 | 1 | 3 | `load` |

Артефакт: `reports/toolcov_runs.json` (`matrix_by_kind`, `cfg_files_by_kind`, `cfg_names_by_kind`);
тот же носитель — `reports/tool-coverage-matrix-18.md`. Классы названы по гейту (`layout_source`),
число файлов — из замера раскладки.

Из 22 классов все 22 увидены инструментами по пути файла — и все 22 тем же инструментом `load`,
потому что счёт идёт по манифесту прочитанных файлов, а его записи создаёт читатель. Классов,
увиденных только по имени сущности, и классов, не увиденных ничем, в этом замере ноль; прежняя
раскладка этих же 22 классов — 7 по пути, 12 только по имени, 3 ничем — относится к замеру
`gate-15.json` и описана в §11.

Показательно сравнение двух модулей одного и того же объекта. Модуль формы
(`Catalogs/Сотрудники/Forms/ФормаЭлемента/Ext/Form/Module.bsl`) виден по пути четырьмя инструментами
(`bsl`, `forms`, `load`, `metrics`) и по имени тремя (`diff`, `graph`, `load`). Модуль объекта
(`Catalogs/Сотрудники/Ext/ObjectModule.bsl`, класс `object_module`) — путём тремя инструментами
(`bsl`, `load`, `metrics`): `load` его называет, потому что открывает как файл манифеста
(`object_module` 6), а `diff`, `graph` и `forms` его в своём отчёте не называют. Класс
`form_descriptor` (файл `Forms/ФормаЭлемента.xml`, 2 файла) по пути увиден только `load` — дескриптор
формы читатель открывает отдельно от её макета.

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
| `subsystem` | 1 | `bsl`, `cf`, `diff` | `ЭффективностьОтдела` (`diff-model-cfg-dump`), `ЭффективностьОтдела` (`bsl-check-cfg`), `ЭффективностьОтдела` (`cf-info-cfg-dir`) |

Артефакт: `reports/toolcov_runs.json` (`name_hits_path_echo_only` каждого прогона).

Три вещи, которые эта таблица объясняет лучше любых рассуждений.

Имя подсистемы `ЭффективностьОтдела` инструментом `load` названо сущностью потому, что в отчёте
читателя оно стоит значением, а не внутри пути; в замере `gate-16.json` таких мест в
`reports/toolcov_load-model-dump.json` четыре: `model.subsystems[0].name = "ЭффективностьОтдела"`
(дескриптор `Subsystems/Имя.xml` читатель открывает с задачи 23),
`model.roles.СотрудникОтдела.objects[0].name = "Subsystem.ЭффективностьОтдела"`,
`model.roles.АдминистраторСистемы.objects[1].name = "Subsystem.ЭффективностьОтдела"` и
`model.roles.АдминистраторСистемы.objects[0].name = "Configuration.ЭффективностьОтдела"` (имя
конфигурации из тех же `Rights.xml`). Точка после `Subsystem.` или `Configuration.` разделителем пути
не считается, поэтому все четыре встречи засчитаны покрытием. Две оставшиеся встречи того же имени —
путь: `model.read_files[16].path` и `model.subsystems[0].path`. В матрице §3 имя подсистемы засчитано
одним инструментом (`load`), а `bsl`, `cf` и `diff` называют его только как часть пути (§4). До правок
A1/A2 (замер `gate-14.json`, где класс `role_rights` был слепым) имя всплывало только как отражённый
путь — в `load-model-cfg` (ключ `context_effective…config.root`), в `diff-model-cfg-dump` (ключ `old`),
в `bsl-check-cfg` (в абсолютных путях `file` всех 15 находок) и в `cf-info-cfg-dir` (в тексте
traceback'а). Проверено по артефактам: в `reports/toolcov_bsl-check-cfg.json` подстрока
`ЭффективностьОтдела` встречается 15 раз и всякий раз внутри пути к файлу, в
`reports/toolcov_diff-model-cfg-dump.json` — 1 раз как значение `old`.

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
gate_artifact `gate-16.json`
tools 8: `bsl`, `cf`, `diff`, `forms`, `graph`, `load`, `metrics`, `sdbl`
layout_counts_match: want 22 classes, got 22 classes, mismatch 0 (пусто)
gate_tool_counts_source 22 classes: accumulation_register 1, bsl_module 8, catalog 1, common_module 1, constant 1, data_processor 1, document 1, enum 1, files 30, form_data 2, form_descriptor 2, form_module 2, information_register 1, language 1, object_module 6, predefined_data 1, report 1, report_template 1, report_template_data 1, role 2, role_rights 2, subsystem 1
gate_tool_blind_kinds 0:
reader_vs_gate.load-model-cfg: equal_to_gate_tool_counts_source true, diff_reader_vs_gate 0 (пусто)
reader_vs_gate.load-model-dump: equal_to_gate_tool_counts_source true, diff_reader_vs_gate 0 (пусто)
kinds seen by path 22: `accumulation_register`, `bsl_module`, `catalog`, `common_module`, `constant`, `data_processor`, `document`, `enum`, `files`, `form_data`, `form_descriptor`, `form_module`, `information_register`, `language`, `object_module`, `predefined_data`, `report`, `report_template`, `report_template_data`, `role`, `role_rights`, `subsystem`
kinds seen by name only 0:
kinds seen by no tool 0:
runs 18, sum of stdout_chars 0
runs logging the context line 11 of 18
  [context] XML разобран: объектов 8, форм 2, модулей к сканированию 20
  runs without it: `load-object-wrong-order`, `graph-build-dump`, `graph-roots-dump`, `metrics-top-dump`, `forms-events-dump`, `forms-form-wrong-order`, `cf-info-cfg-dir`
```

Артефакты: `reports/toolcov_runs.json` (`layout_counts_match`, `gate_*`, `reader_vs_gate`,
`kinds_seen_by_*`), `reports/gate-16.json`.

Сверка состава классов сходится: 22 класса замера против независимого счётчика гейта (`layout_counts`)
— расхождений ноль. Сходится и сверка читателя с гейтом: `gate-16.json` (шаги `load` 8.0 с, `check`
2.0 с, `dump` 2.0 с, код возврата 0) называет все 22 класса `tool_counts_source`, поэтому
`diff_reader_vs_gate` пуст в обоих модельных прогонов, а `equal_to_gate_tool_counts_source` — `true`.
Единственное числовое расхождение внутри самого гейта — класс `files`: `tool_counts_source.files = 30`
против `layout_source.files = 31`; объяснить его можно только одним образом — у манифеста читателя
нет ровно одной записи, и по количеству отсутствующих файлов это `Configuration.xml` (§1).

Записи прежних сверок сохраняются как запись замеренных прогонов. `gate-15.json` (тот же корпус, читатель
после правок A1/A2) называл 12 классов, `gate-14.json` (тот же корпус, читатель до правок A1/A2) — 10,
и против него `equal_to_gate_tool_counts_source` было `false`, а `diff_reader_vs_gate` давало ровно две
пары: `predefined_data [1, 0]` и `role_rights [2, 0]` (первое число — у читателя, второе — у гейта),
остальные 10 классов совпадали и по составу, и по количествам, в том числе `form_data 2`.

Слепых классов по гейту в нынешнем замере ноль: `gate_tool_blind_kinds` пуст — 22 названных против 22
в счётчике. Прежние замеры дают 10 слепых в `gate-15.json` и 12 в `gate-14.json`. Из десяти прежних
слепых закрыты все: `predefined_data` и `role_rights` — путём файла инструментом `load` (задачи 21–22),
`language`, `role`, `subsystem` — дескрипторами `Languages/<Имя>.xml`, `Roles/<Имя>.xml`,
`Subsystems/<Имя>.xml` (задача 23), `report_template` и `report_template_data` — дескриптором макета и
его содержимым (задача 25), `bsl_module`, `files`, `object_module`, `form_module` и `form_descriptor` —
манифестом модулей и дескрипторов форм (задачи 21, 24, 26). В прежнем замере семь из десяти закрывали
другие инструменты матрицы, а не читатель; теперь все 22 закрывает читатель, потому что счёт идёт по
манифесту прочитанных файлов.

Пять классов не имеют собственного имени сущности: `cfg_names_by_kind` содержит 17 ключей — ровно без
`bsl_module`, `files`, `object_module`, `predefined_data`, `role_rights` (`PATH_ONLY_KINDS` в
`probe/tool_coverage.py:109`). В прежнем счёте по ключам модели они и составляли те 7 классов «по пути
файла», а 12 классов «по имени» и 3 «ничем» — ключи модели, которых теперь нет в записях счётчика
(§11).

Права ролей при этом настроены и проверены независимо: гейт `reports/gate-16.json` даёт
`rights.code 0` (`rights_files 2`, `object_blocks 17`, `rights 79`) и `rights_immobility.code 0`
(`source_blocks 17`, `dump_blocks 17`, `source_rights 79`, `dump_rights 79`, ничего не потеряно и
ничего не добавлено) — ровно те же числа, что и `gate-15.json`, потому что исходник между этими
двумя прогонами не менялся. Читатель `p1c.load` называет оба файла прав (`role_rights` 2), даёт ровно
те же числа, что и гейт (`Roles/АдминистраторСистемы/Ext/Rights.xml` — 9 блоков и 57 прав,
`Roles/СотрудникОтдела/Ext/Rights.xml` — 8 блоков и 22 права), и одну запись предопределённых данных
`catalog.Сотрудники` с 6 строками. Дескрипторы ролей (`Roles/АдминистраторСистемы.xml`,
`Roles/СотрудникОтдела.xml`) с задачи 23 прочитаны и названы классом `role` (2), поэтому у этого класса
в матрице §3 стоит 1 инструмент по пути; описание роли при этом ограничено именем, синонимом и
комментарием (§10 пункт 1).

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
  model.form_descriptors = 2: `ФормаЭлемента`, `ФормаВыгрузки`
  model.global_functions = 0
  model.languages = 1: `Русский`
  model.objects = 8: `accumulation_register.ЗатратыВремени`, `catalog.Сотрудники`, `constant.НормаЧасовВМесяц`, `data_processor.ВыгрузкаЗатратCSV`, `document.ФактРаботы`, `enum.ГрейдыСпециалистов`, `information_register.ПланЗагрузки`, `report.ОтчётЗагрузки`
  model.predefined_data = 1: `catalog.Сотрудники`
  model.read_files = 30: accumulation_register 1, catalog 1, common_module 1, constant 1, data_processor 1, document 1, enum 1, form_data 2, form_descriptor 2, form_module 2, information_register 1, language 1, object_module 6, predefined_data 1, report 1, report_template 1, report_template_data 1, role 2, role_rights 2, subsystem 1
  model.role_descriptors = 2: `АдминистраторСистемы`, `СотрудникОтдела`
  model.roles = 2: `АдминистраторСистемы`, `СотрудникОтдела`
  model.skipped_files = 0
  model.subsystems = 1: `ЭффективностьОтдела`
  model.template_data = 1: `ОсновнаяСхемаКомпоновкиДанных`
  model.templates = 1: `ОсновнаяСхемаКомпоновкиДанных`

load-model-cfg  (exit 0)
  keys: `model`
  model.collections = 8: `Документы`, `Константы`, `Обработки`, `Отчеты`, `Перечисления`, `РегистрыНакопления`, `РегистрыСведений`, `Справочники`
  model.common_attributes = 0
  model.common_forms = 0
  model.common_modules = 1: `РасчётПоказателей`
  model.enums = 1: `ГрейдыСпециалистов`
  model.form_descriptors = 2: `ФормаЭлемента`, `ФормаВыгрузки`
  model.global_functions = 0
  model.languages = 1: `Русский`
  model.objects = 8: `accumulation_register.ЗатратыВремени`, `catalog.Сотрудники`, `constant.НормаЧасовВМесяц`, `data_processor.ВыгрузкаЗатратCSV`, `document.ФактРаботы`, `enum.ГрейдыСпециалистов`, `information_register.ПланЗагрузки`, `report.ОтчётЗагрузки`
  model.predefined_data = 1: `catalog.Сотрудники`
  model.read_files = 30: accumulation_register 1, catalog 1, common_module 1, constant 1, data_processor 1, document 1, enum 1, form_data 2, form_descriptor 2, form_module 2, information_register 1, language 1, object_module 6, predefined_data 1, report 1, report_template 1, report_template_data 1, role 2, role_rights 2, subsystem 1
  model.role_descriptors = 2: `АдминистраторСистемы`, `СотрудникОтдела`
  model.roles = 2: `АдминистраторСистемы`, `СотрудникОтдела`
  model.skipped_files = 0
  model.subsystems = 1: `ЭффективностьОтдела`
  model.template_data = 1: `ОсновнаяСхемаКомпоновкиДанных`
  model.templates = 1: `ОсновнаяСхемаКомпоновкиДанных`

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
объектами, называет один общий модуль и одно перечисление, два права ролей и одну запись
предопределённых данных — и содержит нули по трём ключам (`common_attributes`, `common_forms`,
`global_functions`). Роли (`model.roles`, 2 записи) описаны четырьмя полями: `name`, `path`
(`Roles/<Имя>/Ext/Rights.xml`), `flags` — три флага файла прав, и `objects` — список блоков прав, где
у каждого блока имя носителя права и словарь прав со значениями, записанными дословно (в нашей
конфигурации все 79 значений — `true`): 9 блоков и 57 прав у `АдминистраторСистемы`, 8 блоков и 22
права у `СотрудникОтдела`. Имена блоков записаны как в файле, в том числе
`Configuration.ЭффективностьОтдела` и `Subsystem.ЭффективностьОтдела` — из-за последнего имени
подсистема оказалась названа сущностью. Предопределённые данные (`model.predefined_data`, 1 запись
`catalog.Сотрудники`) — это `object`, `kind`, `path` и плоский список `items` из 6 строк с полями
`parent`, `uuid`, `name`, `code` (ведущие нули сохранены: `000000001`…`000000006`), `description` и
`is_folder`; группами считаются 2 строки из шести.

В ключах модели по-прежнему нет ни подсистемы отдельным ключом, ни языка, ни параметров сеанса, ни
макетов компоновки данных, и дескрипторы ролей (`Roles/<Имя>.xml`) читателем не открываются: то, что
лежит в `ConfigDumpInfo.xml`, `Languages/`, `SubSystems/`, `Roles/<Имя>.xml` и
`Templates/*/Ext/Template.xml`, моделью не представляется. Отсюда три класса «ни по пути, ни по
имени» (`language`, `report_template`, `report_template_data`) и ноль покрытия по пути файла у
класса `role`.

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
  stderr: Неверный порядок аргументов: «<work>\dump» — путь, а не имя. Канонический порядок: p1c-load object <вид>.<имя> [корень]

forms-form-wrong-order  (exit 2, нет JSON-отчёта)
  argv: p1c.check.forms.cli form <dump> ФормаЭлемента
  stderr: Неверный порядок аргументов: «<work>\dump» — путь, а не имя. Канонический порядок: p1c-check-forms form <имя формы> [корень]

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
  form.exports 0 (пусто)
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
`sdbl`-прогонов 0 путей): текст запроса в прогон `query` передаёт сам замер — `probe/tool_coverage.py`
достаёт `<query>` из файла макета (`:213-219`) и подаёт его позиционным аргументом
(`p1c/src/p1c/check/sdbl/cli.py:347` — `args.query_text = args.rest[0]`), а обход `check` строится по
списку файлов `_files` (`p1c/src/p1c/check/sdbl/cli.py:151-160`, `rglob("*.bsl")` — строка 157) и
макеты компоновки данных не читает.

Два прогона с кодом 2 стоят отдельно и служат контролем порядка токенов: у `load object` и
`check.forms form` корень должен идти после имени, и в обратном порядке CLI распознаёт первый
позиционный аргумент как путь, а не как имя, отвечает `Неверный порядок аргументов: «<dump>» — путь,
а не имя. Канонический порядок: …` кодом 2 и без отчёта (`p1c/src/p1c/core/writers.py:298-306`,
автоперестановки нет: подставив корень вместо имени, инструмент дал бы ответ о другом объекте).

## 8. `p1c.cf` на нашей раскладке: каталог вместо книги `.cf`

```text
cf-info-cfg-dir  (exit 2, нет JSON-отчёта)
  argv: p1c.cf.cli info <cfg>
```

Дословный stderr того же прогона (`reports/toolcov_runs.json`, ключ `stderr_text`, он же в
`reports/toolcov_summary.txt`): `Книга .cf ожидается файлом, а передан каталог: <cfg>`. Отдельного
JSON-отчёта нет, потому что у подкоманды `cf info` нет флагов `--format` и `--out` — они есть только у
`extract`, `set` и `normalize` (`p1c/src/p1c/cf/cli.py:171-184` и `:187-212`), поэтому прогон шёл с
`writes_report: False` (`probe/tool_coverage.py:92`).

Наша конфигурация — xml-выгрузка из каталога, `.cf`-файла у неё нет; `cf` ждёт файл книги. Передан
каталог `cfg\ЭффективностьОтдела`. Нынешняя правка проверяет это до обращения к читателю книги:
`p1c/src/p1c/cf/cli.py:93-101` (`if p.is_dir(): … W.error("Книга .cf ожидается файлом, а передан
каталог: …")` — строки 97-100), и прогон заканчивается кодом 2 с одной строкой вместо traceback'а.
Ключевой комментарий правки — каталог на месте книги должен выглядеть как ошибка аргумента, а не как
аварийный отказ инструмента.

Так этот прогон выглядел **до** правки обвязки (тот же артефакт замера на дереве `p1c` до правок,
1479 байт stderr):

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

Кадры 221/216/70/65 — места вызова; определения — `def _storage` (строка 60), `def cmd_info`
(строка 68), `def main` (строка 160): противоречия в обратной трассировке нет, она читается как
цепочка вызовов. Ошибка не была переведена в отчёт `p1c.result/v1` и не имела кода, отличного от
«упал». Машинно-читаемого отчёта не было и после правки: подкоманды `info`, `list` и `cat` принимают
`--format` и `--out`, но в этом прогоне они не переданы.

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

1. **Права ролей читает один инструмент, и то через модель; дескрипторы ролей — тот же инструмент, но
   только как файлы.** 2 файла `Roles/*/Ext/Rights.xml`, 17 блоков объектов и 79 прав подтверждены гейтом
   (`rights_immobility.code 0` в `reports/gate-16.json`), и ровно те же числа даёт `p1c.load model`:
   `model.roles` — 2 записи, 17 блоков, 79 прав (в `<cfg>` и в `<dump>`). Класс `role_rights` закрыт путём
   файла инструментом `load` (1 из 8). Класс `role` с задачи 23 тоже закрыт `load`: `model.role_descriptors`
   — 2 записи с `name`, `synonym`, `comment` и путём дескриптора. Это ровно те три поля, которые есть в
   самом дескрипторе (`Roles/СотрудникОтдела.xml` — 1194 символа, в `<Properties>` только `Name`, `Synonym`
   и `Comment`); права роли лежат в `Ext/Rights.xml`, и ни один инструмент кроме `load` ни дескриптор, ни
   файл прав не называет.
2. **Подсистемы, языки, макеты и их содержимое закрыты тем же читателем — но без проверки содержимого.**
   `model.subsystems` — 1 запись с `content` из 9 позиций (в том числе `CommonModule.РасчётПоказателей`),
   `model.languages` — 1 запись с `language_code = ru`, `model.templates` — 1 запись с
   `template_type = DataCompositionSchema`, и её содержимое — `model.template_data` с 1 вычисляемым полем
   (`КоэффициентЗагрузки`), 1 набором данных (6 полей, запрос 1097 символов) и ключами `data_sources`,
   `kind`, `name`, `object`, `path`. Имя подсистемы названо сущностью в четырёх местах отчёта (§4). Проверки
   этому содержимому нет: `p1c.check.sdbl` макет не читает (§7), поэтому SKD-запрос `ОтчётЗагрузки` в
   3 проверенных запроса не вошёл — проверены только запросы, написанные в `.bsl`-модулях.
3. **Модули доходят до читателя как файлы, но не как сущности.** `object_module` (6 файлов) назван и
   читателем: это 5 модулей объектов в `Ext/` плюс `CommonModules/РасчётПоказателей/Ext/Module.bsl` — общий
   модуль и модули форм получили в манифесте собственные таксоны (`common_module` 1, `form_module` 2), а
   модули объектов делят таксон с независимым счётчиком раскладки. Путём такой файл виден тремя
   инструментами (`bsl`, `load`, `metrics`); `diff`, `graph` и `forms` путей модулей объекта в отчётах не
   называют. Отдельной записи «модуль» в модели нет: экспорты модулей объектов лежат в записях самих
   объектов (`manager_methods`, `object_methods`, `record_methods` — `p1c/src/p1c/load/reader.py:1185-1195`),
   у общего модуля есть `spec["exports"]` (`reader.py:1210`), у формы — `form["exports"]`
   (`reader.py:1167-1169`, правка `dcf0112`).
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
   раскладки: по счётчику читателя (`reader_kind_counts`) названо 22 класса из 22 счётчика
   `gate-16.json`; прежние прогоны того же гейта давали 12 классов (`gate-15.json`, читатель после правок
   A1/A2) и 10 классов (`gate-14.json`, тот же гейт, посчитанный читателем до этих правок). Из закрытого
   в модельном содержимом предопределённых данных (`predefined_data` — 1 запись `catalog.Сотрудники` с
   6 строками) проверка не извлекает ничего: `check.bsl` и `check.sdbl` этих строк не видят. Три вида
   файлов, названных планом, в этом корпусе отсутствуют — папок `CommonPictures`, `SettingsStorages` и
   `SessionParameters` в `cfg\ЭффективностьОтдела` нет (проверяется списком каталога: 12 папок и
   `Configuration.xml`), поэтому они не закрыты ничем и проверить их на этом корпусе нельзя.
6. **Код возврата не сообщает, что было прочитано**: `check.sdbl` и `check.forms` дают 0 с пустым
   `results` при непустом `stats`, `cf` отвечает код 2 о неверном аргументе без отчёта, два прогона
   дают 2 без отчёта.
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
   останутся слепыми. Сделано (итерация 11): `roles` и `predefined_data` — закрыты, чтение обоих
   классов файлов добавлено. Сделано (итерация 13, задачи 23 и 25): добавлены чтение
   `Languages/<Имя>.xml`, `Subsystems/<Имя>.xml`, `Roles/<Имя>.xml`,
   `<объект>/Forms/<Имя>.xml`, `<объект>/…/Templates/<Имя>.xml` и `Templates/<Имя>/Ext/Template.xml` и
   ключи модели `languages`, `subsystems`, `role_descriptors`, `form_descriptors`, `templates`,
   `template_data`; классы `language`, `role`, `subsystem`, `report_template`, `report_template_data`
   закрыты. `session_parameters` в модель не добавлен: папки `SessionParameters` в раскладке корпуса нет
   (§10, пункт 5).
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
   `Ext/ManagerModule.bsl`) — сейчас их видят только `bsl` и `metrics`. Сделано (итерация 13, задачи 21 и
   26): модель возвращает `read_files` — пары «путь + класс» для каждого фактически открытого файла, и
   матрица считает по нему, поэтому `object_module` (6 файлов) и `common_module` (1) названы ещё и
   инструментом `load` (в матрице §3 — 3 и 1 инструмента по пути). Осталось незакрытым: отдельного ключа
   модели для модуля уровня конфигурации нет — содержимое этих модулей приходит в модель как экспорты
   объектов и общих модулей (§10, пункт 3).
4. Считать обход `*.bsl` в `check.sdbl` полным обходом макетов тоже: читать `<query>` из
   `Templates/*/Ext/Template.xml` и `CommonForms`/`Forms/*/Ext/Form.xml` наряду с модулями. Сейчас обход
   `check` берёт список файлов `_files(args, context)` (`p1c/src/p1c/check/sdbl/cli.py:151-160`,
   `rglob("*.bsl")` — строка 157), проходит по нему (`cmd_check`, `:213`) и считает те же файлы в
   `stats["files"]` (`:237`); подкоманда `query` читает не файл, а текст запроса из позиционного
   аргумента (`:347`), поэтому SKD-макеты в этот обход не попадают (§7). Сделано наполовину
   (итерация 13, задача 25):
   содержимое `Templates/<Имя>/Ext/Template.xml` читает читатель модели и складывает его в
   `model.template_data` (1 набор данных, 6 полей, запрос 1097 символов), но `check.sdbl` этого ключа не
   читает: обход идёт по `.bsl`-модулям, и SKD-запрос отчёта в 3 проверенных запроса не вошёл.
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

Статус к итерации 10. Пункты 7 и 8 закрыты правкой обвязки `p1c`. После этой правки матрица
переснята (см. ниже «Статус пересчёта»), и §2, §7 и §8 описывают уже нынешний прогон: коды 2 у
`cf-info-cfg-dir`, `load-object-wrong-order` и `forms-form-wrong-order` с текстами, в которых назван
канонический порядок позиционных аргументов (имя, затем корень), вместо traceback'а в 1479 байт у
`cf`. Прежний вид этих строк сохранён только в §8 — как запись замеренного прогона до правки.
Подкоманды `info`, `list` и `cat` принимают `--format` и `--out` и пишут отчёт `p1c.result/v1`;
текстовый вывод остаётся значением по умолчанию. Пункт 6 закрыт частично: структурные слои различают
прочитанный источник (код 0) и прочитанный пустой (код 1), но `check.forms` и `check.sdbl` продолжают
задавать код 1 порогом находок, и отдельного ключа отчёта о непроверенной части правка не вводила.
Ошибка недоступного источника сообщается кодом 2 без отчёта: каталог раскладки на месте книги `.cf` —
неверный аргумент, а не пустой источник.

Статус к итерации 11 (правка A1 и A2 читателя `p1c.load`). Пункт 1 закрыт наполовину: чтение
`Roles/*/Ext/Rights.xml` и `<объект>/Ext/Predefined.xml` добавлено, ключи `roles` и
`predefined_data` в модель добавлены; `subsystems`, `languages`, `session_parameters`, `templates` —
нет. Матрица переснята тем же методом, 18 прогонов восьми инструментов, платформа 1С не запускалась,
изменений ни в раскладке, ни в выгрузке не производилось; прежний замер воспроизведён изолированно на
дереве `p1c` до правок (`746b66b`), чтобы различия были числами, а не рассуждением. Что изменилось в
артефактах:

| что меряется | до правок A1/A2 | после правок A1/A2 |
|---|---|---|
| файлов cfg в отчёте `load-model-cfg` и `load-model-dump` | 4 и 4 | 7 и 7 |
| имён cfg в отчёте этих же прогонов | 11 и 11 | 14 и 14 |
| эхо-имя `ЭффективностьОтдела` у `load-model-cfg` | есть (1) | нет (0) |
| классы, закрытые хотя бы одним инструментом по пути файла | 5 | 7 |
| классы, закрытые только именем сущности | 10 | 12 |
| классы, не закрытые ни по пути, ни по имени | 7 | 3 |
| `predefined_data` по пути файла | 0 инструментов | 1 (`load`) |
| `role_rights` по пути файла | 0 инструментов | 1 (`load`) |
| `role` и `subsystem` по имени сущности | 0 и 0 | 1 и 1 (оба — `load`) |
| счётчик читателя (`reader_kind_counts`) | 10 классов | 12 классов |
| `reader_vs_gate` у обоих прогонов модели | совпадение с гейтом, различий 0 | против `gate-15.json` — различий 0; против прежнего артефакта `gate-14.json` было различий 2: `predefined_data [1, 0]`, `role_rights [2, 0]` |

Различие в строке `reader_vs_gate` было отставанием артефакта, а не расхождением замера:
`gate-14.json` посчитан тем же читателем до правок A1/A2. Это проверено прогоном `gate-15.json`
(итерация 12: шаги `load` 6.0 с, `check` 2.0 с, `dump` 2.0 с, код возврата 0, тот же `cfg` — 31 файл
без изменений с прогона `gate-14`). В нём `tool_counts_source` 12 классов и `tool_blind_kinds` 10, и
сверка читателя с гейтом даёт пустой `diff_reader_vs_gate` в обоих модельных прогонов. Обхода корпусов
для этого не требовалось: `scripts/gate.py:366-371` считает эти две величины по одному исходнику
`cfg` (через `scripts/counts.py:object_counts`), корпуса в расчёте не участвуют; цена — один цикл
платформы (`load`, `check`, `dump`), и он выполнен на гейт-ИБ.

Статус к итерации 12 (прогон `gate-15.json`). Состав закрытого в пункте 1 не изменился: три класса
(`language`, `report_template`, `report_template_data`) по-прежнему не закрыты ни по пути, ни по имени;
`role` закрыт именем сущности, но не путём файла — дескриптор `Roles/<Имя>.xml` читателем не читается.
Изменилось то, что числам гейта теперь можно верить как живым: `tool_counts_source` 12 классов,
`tool_blind_kinds` 10. Матрица после смены артефакта (`GATE_ARTIFACT`, `probe/tool_coverage.py:56` в том
замере, ныне `:59`)
переснята теми же 18 прогонами восьми инструментов без запуска платформы и даёт те же 7 / 12 / 3 из
22 классов; изменились ровно семь строк блока §5 — ярлык артефакта, `gate_tool_counts_source`,
`gate_tool_blind_kinds` и обе строки `reader_vs_gate`.

Статус к итерации 13 (читатель `p1c.load` + манифест прочитанных файлов). Пункт 1 закрыт целиком, кроме
`session_parameters`: папок `SessionParameters`, `SettingsStorages` и `CommonPictures` в раскладке корпуса
нет, и на этом корпусе их закрыть нельзя. Пункт 3 закрыт: пути модулей уровня конфигурации называет сам
читатель. Пункт 4 закрыт со стороны читателя (`model.template_data`), но не со стороны `check.sdbl`.
Счётчик матрицы перестроен на манифест: `GATE_ARTIFACT = "gate-16.json"` (`probe/tool_coverage.py:59`),
классы берутся из пар `model.read_files` (§1), счёт по ключам модели из кода замера удалён. Платформа 1С
в этой итерации запускалась один раз — `gate-16.json` (шаги `load` 8.0 с, `check` 2.0 с, `dump` 2.0 с,
код возврата 0, без `--allow-mutating`), и в том же прогоне сверена неподвижность прав
(`rights_immobility.code 0`). Обходов корпусов не было. Различие `gate-16.json` с `gate-15.json` — ровно
четыре ключа: `steps`, `tool_counts_source`, `tool_counts_dump`, `tool_blind_kinds`. Что изменилось в
артефактах:

| что меряется | прежний замер (артефакт `gate-15.json`, 18 прогонов) | нынешний замер (артефакт `gate-16.json`, 18 прогонов) |
|---|---|---|
| классы, закрытые хотя бы одним инструментом по пути файла | 7 из 22 | 22 из 22 |
| классы, закрытые только именем сущности | 12 | 0 |
| классы, не закрытые ни по пути, ни по имени | 3 | 0 |
| `tool_counts_source` у гейта | 12 классов | 22 класса |
| `tool_blind_kinds` у гейта | 10 классов | пусто |
| файлов cfg в отчёте `load-model-cfg` и `load-model-dump` | 7 и 7 | 30 и 30 |
| имён cfg в отчёте этих же прогонов | 14 и 14 | 16 и 16 |
| `language`, `role`, `subsystem` по пути файла | 0, 0, 0 инструмента | 1 (`load`), 1 (`load`), 1 (`load`) |
| `report_template`, `report_template_data` | 0 и 0 инструмента | 1 (`load`) и 1 (`load`) |
| `form_descriptor` по пути файла | 0 инструмента | 1 (`load`) |
| `object_module` по пути файла | 2 (`bsl`, `metrics`) | 3 (`bsl`, `load`, `metrics`) |
| файлов в классе `files` у независимого счётчика раскладки и у манифеста | 31 и 31 | 31 и 30 |
| строка `[context] … модулей к сканированию` | 18 | 20 |

Причина последнего различия разобрана в §1: у манифеста нет ровно одной записи — `Configuration.xml`,
единственного файла корня раскладки, который читатель не открывает как файл метаданных. Рост очереди
модулей с 18 до 20 — слоты модулей форм, которые читатель добавляет с правки `dcf0112` (§2).

Статус к итерации 14 (блок A: читатель добрал общие коллекции и ограждающий разбор XML). Остаток блока A,
названный в итерации 13 незакрытым, закрыт: командные модули читаются как `command_module` (декларации команд
лежат inline в XML владельца — отдельного файла `Commands/<Имя>.xml` в выгрузке нет, замер по 7 корпусам и
3 фикстурам), дескрипторы и содержимое `CommonCommands`/`CommandGroups`/`CommonPictures`/`CommonTemplates`/
`CommonForms` названы классами раскладки, одиночные макеты `Templates/<Имя>.xml` без каталога читаются как
`report_template`, `SettingsStorages` и `FilterCriteria` — как `settings_storage`/`filter_criteria`, а битый
XML даёт запись `model.xml_diagnostics {"path","kind","error"}` вместо падения. Замеры офлайн (1С не
запускалась): пульсар — `common_command 47`, `command_group 7`, `common_picture 403`, `common_template 13`,
`common_form 65`, `command_module 44`, `settings_storage 1`, `filter_criteria 1`; ssl — 3 одиночных макета;
фикстура `p1c/examples/reader_gaps` (27 файлов) закрывает все классы, единственный непрочитанный файл —
`Configuration.xml` (`tests/test_manifest_gaps.py`, измеритель `scripts/manifest_gaps.py`).

Статус к итерации 14 (блок C: канонические неявные члены и арности конструкторов). Находки `check.bsl`
по `examples/managed_app` упали с 15 (11 «scope» + 1 «ctor» + 3 «method», §9) до 2: канал «владелец
модуля» разрешает реквизиты и табличные части объекта в его модуле (`module_owner` в
`metadata/module_paths.py`), канонический член `Движения` у документов — тип с `dynamic_members`,
а тип `СообщениеПользователю` получил `ctor (0,)`, свойства `Текст`/`Поле` и метод `Сообщить`
(`EXTRA_TYPES`). Оставшиеся 2 находки — неявные реквизиты в модуле формы (канал владельца для форм
не введён). Мёртвая таблица `TYPE_CONSTRUCTORS` (22 записи имён событий/методов, не читалась нигде)
удалена из `data/platform_arities.py` и генератора `scripts/extract_help_arities.py`; арности задаются
только в `metadata/model.py`. Пересчёт `builtin_type_model()`: 1914 типов, с `ctor_arities` 45
(было 44), `dynamic_members` 6 (было 5); `types_without_ctor`/`types_without_properties` 1869 / 1891.
1С в этой итерации не запускалась.

## 12. Честная граница меры

- Матрица мерит то, что инструмент **назвал** в своём отчёте или консоли. Кроме одного случая — счёт
  классов манифеста (`model.read_files` в отчётах `p1c.load`): это записью фиксировано, что читатель
  действительно открыл с диска (§1). Остальные меры остаются мерами называния: путь мог появиться из
  напечатанного аргумента, а имя — из строки контекста. Именно поэтому имена вплотную к `/` вынесены
  отдельно (§4), а хиты консоли — отдельно от хитов отчёта.
- Матрица мерит покрытие восьми инструментов по 18 командам, не по всем подкомандам `p1c`.
  Модифицирующие подкоманды `cf set` и `cf normalize` в замер не включены; подкоманды, которые
  требовали бы запуска платформы, в этом замере не участвовали вовсе.
- Мера не утверждает, что прочитанное содержимое корректно: `p1c.metrics` прочитал 7 файлов модулей, а
  имя сущности в его отчёте ровно одно; `p1c.load` назвал 22 класса из 22 — но это классы **открытых
  файлов**, а не утверждение, что их содержимое разобрано: дескрипторы макета и языка дают только имя,
  синоним и путь (§10, пункт 2). Числа колонки «имён cfg» — это имена, которые встречаются в отчёте, а
  не оценка полноты.
- Две численные меры одного артефакта не сравниваются напрямую. Колонки §2 — **различные** пути и
  **различные** имена внутри прогона (`probe/tool_coverage.py:414-416`: пути и имена собираются в
  множество по всем классам, повтор не считается),
  поэтому у модельных прогонов 30 файлов и 16 имён. Счётчик читателя в §5 — число **классов**
  манифеста, которые читатель назвал (`reader_kind_counts`), у него 22. Сводка, которую печатает консоль
  замера, — суммы хитов по классам (`probe/tool_coverage.py:518` и `:521-524`), и это третья величина.
- Матрица §2, §3, §4 и §5 переснята после правок читателя `p1c.load` (итерации 12–13) и соответствует
  нынешним артефактам `reports/toolcov_*.json` и `reports/gate-16.json`. Прежние числа (4 файла и 11 имён
  у модельных прогонов, 7 / 12 / 3 класса по трём категориям в замере `gate-15.json`, 5 / 10 / 7 в замере
  `gate-14.json`, код 1 и traceback у `cf-info-cfg-dir`, `reader_vs_gate` с двумя различиями) сохранены
  только как запись прежних замеров: в таблицах статуса §11 и в блоке «до правки» §8. Артефакты
  `reports/gate-14.json` и `reports/gate-15.json` при этом не перезаписывались: они на диске остаются
  записью того же гейта, посчитанного читателем до правок A1/A2 и до правок итерации 13.
- `context_signature` и `context_effective` из отчётов в таблицы и блоки содержимого не переносится
  (`probe/render_query_tables.py::SKIP_REPORT_KEYS`), чтобы абсолютные пути не попадали в документ;
  числа подписей в §5 приведены по первым 16 шестнадцатеричным разрядам значений из артефактов.
- Строки исходника в таблице §9 — дословный текст из файлов `cfg`; колонка «строка» — номер строки,
  который сообщил инструмент, а не выверенный нами.
- Ни один из 18 прогонов матрицы не запускает платформу 1С: это вызовы Python-модулей `p1c` и обход
  каталога. Числа §5 опираются на артефакты гейта, а они — записи прогонов платформы (`gate-16.json`:
  `load`, `check`, `dump`; `gate-15.json` и `gate-14.json`: те же три шага), и в этих прогонах раскладка
  не менялась: модифицирующих флагов не передавалось, `dump_files` и `dump_fresh_files` — 32 файла,
  `diff_files` пуст. Корпусные замеры §9 — ripgrep по `*.bsl` и размеры файлов (`stat`), содержимое 214
  модулей крупнее лимита в корпусах не читалось ни в одном из замеров.

## 13. Итерация 15: формный канал контекста

Итерация 15 даёт модулю формы канал контекста: имена формы разрешаются в `resolve_varref`
(Task 45), стандартные свойства объектных типов добавлены в читатель (Task 46), тип `Объект`
выбран строго по пяти семействам типов (Task 47), а 81 различное имя методов трёх формных типов
объединено в кеш `TypeModel.form_methods` и подключено к `check_call` (замер 67 и Task 48).
Этот раздел — итог итерации: финальный корпусный прогон (замер 58, Task 49) с полной командой
прогона, его признаками, базой подсчёта каждой строки, таблицами одиннадцати кодов «база → итог»
в двух уровнях, закрытым и открытым поштучно, остатком шума и сознательным компромиссом.

**Две базы подсчёта.** У итерации две базовые линии, и каждая строка этого раздела названа своей.
- **База `55`** — `m55_task44_base_pulsar.json` (замер 55, дерево `p1c 3aa061f`): 1 195 файлов,
  33 047 находок в 768 файлах с находками, формная строка 26 102 находки в 442 файлах, подпись
  контекста `9739925d…`. Эта линия — база плана итерации 15 (Task 44).
- **База `61`** — `m61_fixed_pulsar.json` (замер 61, дерево `p1c 823728a`): 1 195 файлов,
  32 547 находок в 760 файлах с находками, формная строка 26 177 находок в 442 файлах, подпись
  контекста `726583f1…29726`. Это правка канала владельца на абсолютном пути (пакет 8, вне плана
  итерации 15): она закрыла 973 находки и открыла 473, из них 467 — `IDS_STX_PROPERTYNOTFOUND`.
  Запись «Пакет 8» лиджера назначает базой сравнения Task 45–49 именно артефакты `m61_*`,
  поэтому итог сверяется по обеим базам и в таблицах стоят оба числа.

**Команда прогона (замер 58, шаг 2 плана Task 49).** Оба прогона — из `<p1c>` и только через
python-обёртку `m58_runner.py` (`subprocess.run` с `timeout` 1 500, `PYTHONPATH` = `<p1c>\src`,
stdout и stderr пишутся байтами):

```text
cd <p1c>
python -m p1c.check.bsl.cli check "<corpora_pulsar>" \
    --root "<corpora_pulsar>" \
    --format json \
    --out <tmp>\opencode\m58_task49_pulsar.json
```

Корпус `<corpora_pulsar>` (строка `corpora_pulsar` файла `local.paths.json`) использован только на
чтение: один ключ `check`, модифицирующих опций CLI не передавалось, позиционный аргумент и
`--root` — один и тот же путь, JSON-отчёт записан вне корпуса. Тот же скрипт первым прогоном
считает гейт фикстуры `examples/managed_app` ровно той же командой и с теми же опциями
(`--out <tmp>\opencode\m58_task49_gate.json`). Строка stderr корпуса дословно:

```text
[context] XML разобран: объектов 384, форм 520, модулей к сканированию 1670
```

**Признаки обоих прогонов** (`m58_runner.log`, дерево `p1c` HEAD `bf0ea78`):

| прогон | код возврата | длительность | stdout | stderr | размер JSON-отчёта | `stats` | находок | файлов с находками | подпись контекста |
|---|---|---|---|---|---|---|---|---|---|
| гейт фикстуры `examples/managed_app` | 0 | 38.3 с | 0 b | 111 b | 3 486 b | `files` 8 | 0 | 0 | `4edf65fe…` |
| корпус `<corpora_pulsar>` | 1 | 333.3 с | 0 b | 117 b | 6 400 757 b | `files` 1 195 | 10 526 | 610 | `726583f1…29726` |

Побайтовое воспроизведение доказано: артефакт `m58_task49_pulsar.json` равен артефакту замера 68
`iter15_task48_pulsar.json` (по 6 400 757 b, побайтово равны, мультимножества находок равны,
подписи контекста равны), а артефакт гейта равен `iter15_task48_gate.json` (по 3 486 b, счёт
находок 0 у обоих). Правка комментариев `p1c bf0ea78`, сделанная после замера 68, не сдвинула ни
одной находки — разность по каждому из одиннадцати кодов равна 0.

**Длительность — свойство машины, не дерева.** Первый прогон дня дал 38.3 с (гейт) и 333.3 с
(корпус), хотя в замерах 66 и 68 те же прогоны занимали 2.2 с и 3.3 с (гейт) и 95.6 с и 96.4 с
(корпус). Повтор той же команды по тому же дереву и корпусу (`t49_timing_probe.py`, разведка без
номера замера) дал 1.6 с и 1.2 с (гейт) и 58.7 с (корпус) при побайтово тех же артефактах
(3 486 b и 6 400 757 b). Поэтому сравнение прогонов в этом разделе ведётся по составу находок,
а длительность приводится как признак прогона, не как мера правки.

**Состав корпуса и формных модулей.** `stats.files` — 1 195 файлов модулей во всех семи
прогонах цепи. Формных модулей корпуса по `module_kind_of` — 502: 437 под `Forms/` и 65 под
`CommonForms/` (520 записей `Ext/Form.xml` минус 18 записей без модуля на диске). Из них с
находками в базовой линии 442, без находок 60; прочие модули — 693. Разбиение по видам
модулей и имена находок считаются той же методикой, что в Task 44: `module_kind_of(path)`, имя —
из последней скобочной группы текста, ключ находки — (файл, код, строка, колонка, текст),
сравнение — мультимножествами ключей.

**Цепь корпусных прогонов итерации 15.** Строки по видам модулей (находки / файлы с находками);
сравниваются только прогоны с идентичными опциями CLI, идентичным корпусом и одним ключом:

| прогон | дерево `p1c` | формная строка | `common` | `object` | `command` | сумма | файлов с находками |
|---|---|---|---|---|---|---|---|
| база `55` (Task 44) | `3aa061f` | 26 102 / 442 | 4 452 / 144 | 2 488 / 178 | 5 / 4 | 33 047 | 768 |
| база `61` (пакет 8) | `823728a` | 26 177 / 442 | 4 010 / 143 | 2 356 / 172 | 4 / 3 | 32 547 | 760 |
| после Task 45 | после правок Task 45 | 5 197 / 373 | 4 010 / 143 | 2 356 / 172 | 4 / 3 | 11 567 | 691 |
| после Task 46 | после правок Task 46 | 5 165 / 373 | 3 979 / 143 | 2 279 / 171 | 4 / 3 | 11 427 | 690 |
| после Task 47 | `688f9b7` | 5 164 / 373 | 3 979 / 143 | 2 279 / 171 | 4 / 3 | 11 426 | 690 |
| после Task 48 (замер 68) | `db6b424` | 4 264 / 293 | 3 979 / 143 | 2 279 / 171 | 4 / 3 | 10 526 | 610 |
| **замер 58 (Task 49)** | `bf0ea78` | **4 264 / 293** | **3 979 / 143** | **2 279 / 171** | **4 / 3** | **10 526** | **610** |

Артефакты строк: `m55_task44_base_pulsar.json`, `m61_fixed_pulsar.json`,
`iter15_task45_pulsar.json`, `iter15_task46_pulsar.json`, `iter15_task47_pulsar.json`,
`iter15_task48_pulsar.json`, `m58_task49_pulsar.json`. Подпись контекста у прогонов `61`, 45, 46,
47, 68 и 58 одинакова (`726583f1…29726`), у базы `55` — иная (`9739925d…`): правка пакета 8
изменила и метаданные канала, и код, поэтому база `55` остаётся базой плана, а не базой итога.

**Одиннадцать кодов: формная строка (база → итог).** Разность считается от базы `61`, потому что
к итогу применены правки Task 45–48, а пакет 8 — до них:

| код | база `55` | база `61` | итог (замер 58) | разность от базы `61` |
|---|---|---|---|---|
| `IDS_STX_VAR_NOTDECLARED` | 21 670 | 21 508 | 528 | −20 980 |
| `IDS_STX_METHODNOTFOUND` | 1 863 | 1 863 | 1 829 | −34 |
| `IDS_STX_CTOR_NOTFOUND` | 1 303 | 1 303 | 1 303 | 0 |
| `IDS_STX_PROPERTYNOTFOUND` | 15 | 258 | 259 | +1 |
| `IDS_STX_TYPE_NOTDEFINED` | 231 | 231 | 231 | 0 |
| `IDS_STX_PROC_NOTDEFINED` | 922 | 916 | 16 | −900 |
| `IDS_STX_PARAMS_TOOMANY` | 75 | 75 | 75 | 0 |
| `BSL_CTX_NOT_AVAILABLE` | 8 | 8 | 8 | 0 |
| `BSL_CTX_CLIENT_ONLY` | 7 | 7 | 7 | 0 |
| `IDS_STX_PROC_DEFINED` | 6 | 6 | 6 | 0 |
| `IDS_STX_PARAMS_NOTENOUGH` | 2 | 2 | 2 | 0 |
| **сумма формной строки** | **26 102** | **26 177** | **4 264** | **−21 913** |

**Одиннадцать кодов: весь корпус (база → итог).** Других кодов в прогоне 58 нет; ни одного из
перечисленных одиннадцати в прогоне не отсутствует — сумма строки равна своду отчёта
(`summary.count` 10 526):

| код | база `55` | база `61` | итог (замер 58) | разность от базы `61` |
|---|---|---|---|---|
| `IDS_STX_VAR_NOTDECLARED` | 22 971 | 22 013 | 960 | −21 053 |
| `IDS_STX_METHODNOTFOUND` | 5 602 | 5 602 | 5 533 | −69 |
| `IDS_STX_CTOR_NOTFOUND` | 2 593 | 2 593 | 2 593 | 0 |
| `IDS_STX_PROPERTYNOTFOUND` | 196 | 663 | 664 | +1 |
| `IDS_STX_PROC_NOTDEFINED` | 1 001 | 992 | 92 | −900 |
| `IDS_STX_TYPE_NOTDEFINED` | 479 | 479 | 479 | 0 |
| `IDS_STX_PARAMS_TOOMANY` | 165 | 165 | 165 | 0 |
| `BSL_CTX_NOT_AVAILABLE` | 12 | 12 | 12 | 0 |
| `IDS_STX_PARAMS_NOTENOUGH` | 11 | 11 | 11 | 0 |
| `IDS_STX_PROC_DEFINED` | 10 | 10 | 10 | 0 |
| `BSL_CTX_CLIENT_ONLY` | 7 | 7 | 7 | 0 |
| **сумма корпуса** | **33 047** | **32 547** | **10 526** | **−22 021** |

**Закрытое и открытое поштучно** (разность мультимножеств ключей находок; в скобках — из них
формная строка):

| сравнение | код | закрыто | открыто |
|---|---|---|---|
| база `55` → итог | `IDS_STX_VAR_NOTDECLARED` | 22 011 (21 142) | 0 (0) |
| база `55` → итог | `IDS_STX_PROC_NOTDEFINED` | 909 (906) | 0 (0) |
| база `55` → итог | `IDS_STX_METHODNOTFOUND` | 69 (34) | 0 (0) |
| база `55` → итог | `IDS_STX_PROPERTYNOTFOUND` | 0 (0) | 468 (244) |
| **база `55` → итог, всего** |  | **22 989 (22 082)** | **468 (244)** |
| база `61` → итог | `IDS_STX_VAR_NOTDECLARED` | 21 053 (20 980) | 0 (0) |
| база `61` → итог | `IDS_STX_PROC_NOTDEFINED` | 900 (900) | 0 (0) |
| база `61` → итог | `IDS_STX_METHODNOTFOUND` | 69 (34) | 0 (0) |
| база `61` → итог | `IDS_STX_PROPERTYNOTFOUND` | 0 (0) | 1 (1) |
| **база `61` → итог, всего** |  | **22 022 (21 914)** | **1 (1)** |

Файлы с находками: от базы `55` — 768 → 610 (исчезло 161, появилось 3, стало меньше 432, стало
больше 22); от базы `61` — 760 → 610 (исчезло 150, появилось 0, стало меньше 320, стало больше 0).
Три различия в колонке «появилось» объясняются одной правкой: пакет 8 (база `61`) открыл 3 файла,
в которых раньше не было ни одной находки, — они остались в итоге.

Единственная открытая находка на пути от базы `61` к итогу — `IDS_STX_PROPERTYNOTFOUND` в модуле
формы (`СтрокаТабличнойЧасти.Представления.ПараметрыПрописи`, `Catalogs/Валюты/Forms/ФормаЭлемента/
Ext/Form/Module.bsl` 182:17); её породил Task 47, и она разобрана построчно замером 66b. Остальные
467 открытых вхождений того же кода принадлежат правке пакета 8 (замер 61), а не правкам
итерации 15: по базе `61` рост `IDS_STX_PROPERTYNOTFOUND` равен одной находке.

**Гейт §8 и критерий §12 п.2.** Фикстурный гейт `examples/managed_app`: 2 находки в базовой
линии итерации 14 → 0 (код возврата 0, `stats` с `files` 8, счёт находок 0). Формные потолки
итерации 15 и их значения в обоих базах и в итоге: `BSL_CTX_NOT_AVAILABLE` 8 (8 / 8 / 8),
`BSL_CTX_CLIENT_ONLY` 7 (7 / 7 / 7), `IDS_STX_PROC_DEFINED` 6 (6 / 6 / 6), `IDS_STX_PARAMS_TOOMANY`
75 (75 / 75 / 75). По всему корпусу: `BSL_CTX_NOT_AVAILABLE` 12 (12 / 12 / 12),
`BSL_CTX_CLIENT_ONLY` 7 (7 / 7 / 7), `IDS_STX_PROC_DEFINED` 10 (10 / 10 / 10). Ни один потолок не
превышен; `IDS_STX_METHODNOTFOUND` и `IDS_STX_CTOR_NOTFOUND` от базы `61` не выросли (−34 по
формной строке и 0), `IDS_STX_PROPERTYNOTFOUND` вырос на одну находку Task 47 — это и есть
заявленный в §12 п.2 вклад предпосылки §6, разложенный замерами 65b и 66b.

**Остаток шума `IDS_STX_PROC_NOTDEFINED` в формной строке.** По итоговому артефакту — 16 находок
в 5 именах: `Активизировать` 8, `Открыть` 4, `УстановитьТекущийВариант` 2,
`РазблокироватьДанныеФормыДляРедактирования` 1, `УстановитьТекущиеПользовательскиеНастройки` 1.
Ни одного из этих пяти имён в объединении 81 имени нет, и ни одно из них канал не замолчал.
По артефакту замера 55 (база плана) остаток того же кода — 22 находки в 6 именах: те же пять
имён плюс `ОбновитьИнтерфейс` 6.
План Task 49 (шаг 1) и шаг 5 плана Task 48 называли остатком «22 вхождения» по списку из восьми
имён на сумму 24. Из этого списка два имени — `ОбновитьОтображениеДанных` 1 и
`ОткрытьСправкуФормы` 1 — входят в объединение 81 имени и закрываются каналом, поэтому 24 − 2 =
22 и есть остаток базы `55` (шесть имён), а сумма самого списка — 24, а не 22: это дефект F33
текста плана, исправленный в §11 дизайн-дока. Разница между 22 и итоговыми 16 — те же 6
вхождений `ОбновитьИнтерфейс`: в артефакте замера 61 (база, назначенная записью «Пакет 8») и во
всех последующих прогонах цепи этого имени в формной строке `IDS_STX_PROC_NOTDEFINED` нет вовсе
— 922 → 916 между артефактами `55` и `61`. Причина названа разбором дизайн-дока по замерам
67 (§В) и 68 (§Д): обращения этого имени разрешает `ctx.global_functions`. Остальные 76
находок кода (92 − 16) лежат в
модулях `common`, `object` и `command` — канал формных методов к ним не применяется, и это не
остаток формного шума.

**Причина остатка 16 измерена правкой Task 50 (дефект F55 дизайн-дока, `t50_resid_probe.py` и
`t50_resid_probe2.py`).** Объединение 81 имени собирается из трёх блоков методов формных типов в
`p1c/src/p1c/data/platform_arities.py`: `Форма` — строки 19995–20024 (27 имён),
`ФормаКлиентскогоПриложения` — 20026–20085 (57), `ТестируемаяФорма` — 19606–19623 (15), и
объединение имён ровно этих блоков (со свёрткой `ё` → `е`) даёт 81 имя при 0 расхождений в обе
стороны с кешем `ctx.form_methods` на встроенной модели. Ни одного из пяти имён остатка в этих
блоках нет. `Активизировать` и `РазблокироватьДанныеФормыДляРедактирования` не стоят отдельной
записью нигде в файле (его словари: глобального контекста 9–998, типов 999–21248, событий
21249–22188), `УстановитьТекущиеПользовательскиеНастройки` (17882) и `УстановитьТекущийВариант`
(17883) имеют по одной сигнатуре, но стоят под блоком типа `Расширение формы клиентского
приложения для отчета` (начинается со строки 17865) — методами формного типа они не являются;
имени `Открыть` в словаре глобального контекста нет вовсе, а его 12 записей-членов относятся к
другим типам (первые две — `ЗаписьPDF` 12743 и `ЗаписьТекста` 12818, затем `ЧтениеТекста` 20342
и ещё девять). Имя `ОбновитьИнтерфейс`, снятое между базами `55` и `61`, в файле тоже не стоит
отдельной записью ни в одном словаре. Все шесть имён есть только как пары имён
(`p1c/src/p1c/data/platform_name_pairs.py`: 2713, 7218, 8422, 8423 и 9263 — в блоке пар имён
членов типов 2649–9834, 492 — в блоке пар глобального контекста 36–662) и как 11 пар
`Активизировать` и одной пары `Открыть` в тестовом наборе `p1c/src/p1c/data/test_api.json`
(283 391 b, 302 записи, читается тестом `p1c/tests/data/test_api.py:30`) — сигнатур там нет.
Значит остаток — дыра покрытия таблиц сигнатур, питающих объединение, а не шум разбора:
закрывается он дополнением трёх формных блоков генератором `p1c/scripts/extract_help_arities.py`,
но требует своего замера (от объединения 81 имени зависят числа замеров 67 и 68), и его цена —
8 + 4 + 2 + 1 + 1 = 16 находок. Очередь и порядок работы записаны §11 дизайн-дока, записью F55
раздела §10 того же файла и §7.3 файла `docs/evidence/p1c-data-defects.md`.

**Сознательный компромисс: объединение клиентских и серверных методов (§11 дизайн-дока).**
Модуль формы нельзя отнести ни к одному из трёх формных типов: `<Variant>` в 520 записей
`Ext/Form.xml` корпуса не встречается ни в одной раскладке, а `TYPE_SIGNATURES` даёт методы трёх
типов по отдельности (27 + 57 + 15 = 99 методов, 81 различное имя, разногласие арностей у 2
имён). Принято объединение: минимальная арность имени — минимум из `min_args` всех типов, где
имя найдено, максимальная — максимум из `max_args`; `availability` — объединение наборов;
`has_return` — «хотя бы у одного типа». Цена принята по измерению, а не по оценке (замер 67
симулировал включение канала до правки кода): закрыто 900 находок `IDS_STX_PROC_NOTDEFINED`
ровно по 12 именам при 0 открытых находок по всем кодам; формные `IDS_STX_PARAMS_TOOMANY` 75 и
`IDS_STX_PARAMS_NOTENOUGH` 2 не сдвинулись — расширение арности не породило ни одной новой
находки о параметрах; `BSL_CTX_CLIENT_ONLY` 7 и `BSL_CTX_NOT_AVAILABLE` 8 тоже не сдвинулись.
Восемь имён-коллизий с глобальным контекстом остались за `ctx.global_functions`: ветка канала
стоит после его блока, поэтому приоритет глобального контекста и его арности сохранён.

**Что разошлось с ожиданиями плана Task 49 (шаг 1).** Ожидания шага 1 плана записаны по базе `55`,
а итог сверяется по обеим базам; расхождения разобраны, предсказания после прогона не
переписывались:
1. «`IDS_STX_PROPERTYNOTFOUND` 15 не выросли» — 15 есть число базы `55`; в базе `61` формная
   строка этого кода уже 258, корпусная 663. От базы `61` к итогу рост — 1 находка (Task 47).
2. «строки `common` 4 452, `object` 2 488, `command` 5 не изменились» — это числа базы `55`. По
   базе `61` они 4 010 / 2 356 / 4, а к итогу дают 3 979 / 2 279 / 4; весь сдвиг сделал Task 46
   (140 закрытых находок, разложенных замерами 65 и 65b).
3. «остаток — 22 вхождения по перечню из восьми имён» — см. абзац об остатке шума выше.
4. «формная строка 26 102 уменьшается на 10 849 + 10 137 + 900» (сумма 21 886, ожидаемый итог
   4 216) с итогом не совпало: по базе `55` формная строка уменьшилась на 21 838 (закрыто
   22 082, открыто 244), по базе `61` — на 21 913 (закрыто 21 914, открыто 1). Избыток закрытого
   196 = 156 (`IDS_STX_VAR_NOTDECLARED` сверх плановой суммы реквизитов и композиции: закрыта и
   часть «иных» 684 — остаток 528) + 34 (`IDS_STX_METHODNOTFOUND`, план их закрытия не
   предсказывал) + 6 (`IDS_STX_PROC_NOTDEFINED` имени, отсутствующего в базе `61`); разность
   итогов 48 = 244 открытые находки минус 196 излишка закрытого.
5. Длительность прогона (333.3 с против предсказанного интервала 70–140 с) и длительность гейта
   (38.3 с против 2.2 с и 3.3 с в замерах 66 и 68) — разбор в абзаце о длительности; артефакты
   обоих прогонов побайтово равны артефактам замера 68.

**Артефакты замеров 55–58** (все в `<tmp>\opencode`; номера 59–68 заняты прежними прогонами
канала владельца и задачами 45–48, их артефакты перечислены в записях лиджера «Пакет 8» и
Task 45–48):
- **замер 55** (Task 44, базовая линия): `m55_task44_base.py` (8 988 b),
  `iter15_m55_predictions.md` (6 206 b), `m55_task44_base.summary.log` и
  `m55_task44_base.stdout.log` (по 6 246 b), `m55_task44_base_pulsar.json` (20 325 893 b),
  `m55_task44_base.log` (0 b), `m55_task44_base.err` (117 b),
  `m55_task44_base.stderr.log` (0 b), `m55_task44_gate.json` (4 744 b), повторные прогоны
  `m55_task44_after_pulsar.json` и `m55_task44_after2_pulsar.json` (по 20 325 893 b, `.log` 0 b,
  `.err` по 117 b) с `m55_task44_after_gate.json` и `m55_task44_after2_gate.json` (по 4 744 b),
  сверка `m55_task44_compare.py` (3 553 b) и `m55_task44_compare.log` (1 549 b), обёртки
  `m55_runner.py` (842 b), `m55_after_runner.py` (1 464 b), `m55_after2_runner.py` (1 377 b),
  `m55_summary_runner.py` (483 b), `m55_shape.py` (497 b), `m55_fixture_forms.py` (1 146 b).
- **замер 56** (Task 46): `m56_task46_ownerkinds.py` (12 971 b) и `m56_task46_ownerkinds.log`
  (17 033 b), `iter15_m56_predictions.md` (9 801 b), `m56_crosscheck_findings.py` (4 897 b) и
  `m56_crosscheck_findings.log` (12 205 b), `m56_probe_model.py` (4 460 b) и
  `m56_probe_model.log` (3 579 b).
- **замер 57 и его ветка 57b…57h** (Task 47): `m57_task47_strict.py` (15 163 b) и
  `m57_task47_strict.log` (6 954 b), `iter15_m57_predictions.md` (11 678 b),
  `m57b_probe_types.py` (10 776 b) и `m57b_probe_types.log` (32 608 b),
  `m57c_prior_artifacts.py` (7 327 b) и `m57c_prior_artifacts.log` (10 377 b),
  `m57d_arity_probe.py` (10 245 b) и `m57d_arity_probe.log` (2 451 b),
  `m57e_chain_residual.py` (8 597 b) и `m57e_chain_residual.log` (28 636 b),
  `m57f_gate_types.py` (12 737 b) с `m57f_gate_types.log` и `m57f_gate_types.stdout.log`
  (по 63 781 b) и `iter15_m57f_predictions.md` (7 231 b), `m57g_gate_forms.py` (7 506 b),
  `m57g_gate_forms.log` (4 581 b) и `iter15_m57g_predictions.md` (3 544 b),
  `m57h_oblast_lines.py` (8 031 b) с `m57h_oblast_lines.log` (3 574 b),
  `m57h_oblast_lines.first.log` (3 643 b) и `m57h_run.log` (3 574 b).
- **замер 58** (Task 49, этот раздел): `m58_runner.py` (4 133 b) и `m58_runner.log` (965 b),
  `iter15_m58_predictions.md` (18 044 b, 74 строки предсказаний в таблицах разделов А–И,
  написан до прогона и после прогона не переписан; правкой Task 50 к этому описанию дописано
  основание счёта — дефект F50 дизайн-дока: 174 строки файла, 83 строки разметки девяти таблиц
  — 9 шапок, 9 строк-разделителей и 65 строк содержимого; 74 — содержимое вместе с девятью
  шапками, без строк-разделителей; истинных строк-предсказаний 62, потому что строки содержимого
  71, 90 и 113 — контрольные «Сумма»), `m58_task49_pulsar.json` (6 400 757 b),
  `m58_task49_pulsar.log` (0 b), `m58_task49_pulsar.err` (117 b), `m58_task49_gate.json`
  (3 486 b), `m58_task49_gate.log` (0 b), `m58_task49_gate.err` (111 b),
  `m58_task49_gate.py` (36 009 b), `m58_task49_gate.summary.log` (23 953 b) с сохранёнными
  прежними сборками `m58_task49_gate.summary.log.prev1` (17 585 b) и
  `m58_task49_gate.summary.log.prev2` (22 101 b), `m58_task49_gate.stdout.log` (24 161 b).
- **разведка Task 49** (замером не считается, файла предсказаний нет): `t49_recon_prior.py`
  (7 125 b) и `t49_recon_prior.log` (8 381 b), `t49_recon_diff.py` (4 673 b) и
  `t49_recon_diff.log` (2 051 b), `t49_timing_probe.py` (2 602 b), `t49_timing_probe.log`
  (300 b) и `t49_timing_probe.json` (6 400 757 b) с `t49_timing_probe_gate1.json` и
  `t49_timing_probe_gate2.json` (по 3 486 b), `t49_recon_m61.py` (9 868 b) с
  `t49_recon_m61.log` и `t49_recon_m61.stdout.log` (9 613 b и 9 756 b), `t49_recon_resid.py`
  (4 191 b) и `t49_recon_resid.log` (5 429 b).

**Артефактов замера 69 в этом перечне нет, и это записано здесь.** Прогоны Task 50 §13 не
переснимает: он сводит замеры 55–58 и их сверку с двумя базами. Числа финального прогона итерации
стоят в §7.5.20 дизайн-дока и в записи `Task 50` лиджера (артефакты `iter15_m69_predictions.md`,
`m69_final_gates.py`, `m69_final_gates.log`, `m69_task50_pulsar.json`, `m69_task50_gate.json`),
и от них ни одно число этого раздела не сдвинулось: корпусный артефакт замера 69 побайтово равен
артефакту замера 58 (оба по 6 400 757 b), а гейт равен `m58_task49_gate.json` по размеру и
подписи. Перенос чисел 69 в перечень артефактов §13 отложен записью §10 дизайн-дока и является
работой следующей сводки; эта строка стоит здесь как напоминание об отложенном, чтобы §13
читался полным перечнем замеров итерации.

**Граница этого замера.** Task 49 не менял код `p1c` и не запускал тесты: числа тестов
(`tests/check_bsl/test_form_context.py` — 65 проверок и 0 падений, `scripts/run_tests.py` —
96 файлов и 0 падений, контур — 303 из 303) принадлежат записи Task 48 и в этом разделе не
пересняты. Корпус читался один раз за проход, каждого — по одному ключу `check`; повторные
прогоны той же команды (`t49_timing_probe.py`) служили только проверке длительности и
воспроизводимости артефакта. Платформа 1С в этой итерации не запускалась.
