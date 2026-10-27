# Что платформа делает с рукописной конфигурацией при загрузке: четыре класса отличий выгрузки

Доказательство зеленой итерации и разбор того, какие отличия выгрузки — норма платформы, а какие
значат, что мы написали неканонически.

Инструменты: `scripts/gate.py` (гейт), `probe/dump_vs_source.py` (классификация берёт из
`gate.file_diff`, показывает контекст первого различия), `scripts/rights.py` (состав прав в
источнике и в выгрузке). Замеры без повторной ручной работы: `reports/gate-04.json` (первый
успешный `load`), `reports/gate-05.json` (первая зелёная итерация),
`%TEMP%\opencode\p1c_effektivnost\gate04.txt`, `gate05.txt`, `type_qualifiers.txt`.

## Зелёная итерация (gate-05)

```
python scripts/gate.py --cfg "cfg/ЭффективностьОтдела" --out reports/gate-05.json --timeout 240
гейт: код 0
```

| шаг | код | секунды | байт вывода |
| --- | --- | --- | --- |
| `load` (`/LoadConfigFromFiles`) | **0** | 3.0 | 3 (BOM, то есть пусто) |
| `check` (`/CheckModules`) | **0** | 2.0 | 73 («Синтаксических ошибок не обнаружено!») |
| `dump` (`/DumpConfigToCenter`) | **0** | 2.0 | 3 |

- выгрузка: 25 файлов, все 25 свежие (`dump_fresh_files == dump_files`);
- `layout_source == layout_dump`: `files 24` (после того как контур перестал считать файлом
  платформы `ConfigDumpInfo.xml`), `role 2`, `role_rights 2`, `subsystem 1`, `language 1`,
  `object_module 4`, `bsl_module 5`, `form_descriptor 1`, `form_module 1`, `form_data 1`,
  `report_template 1`, `report_template_data 1`, справочник/документ/2 регистра/константа/перечисление/
  отчёт/общий модуль по 1;
- `expected_mismatch {}` — числа совпали с эталоном `docs/expected-metadata.json`, заданным
  спецификацией до сборки;
- `rights.code 0` (2 файла прав, 8 блоков `<object>`, 43 права в источнике);
- `diagnostic_findings []`, `step_problems []`;
- покрытие инструментов: `tool_counts_source` видит 9 видов, слепых зон 11 —
  `bsl_module`, `files`, `form_descriptor`, `form_module`, `language`, `object_module`,
  `report_template`, `report_template_data`, `role`, `role_rights`, `subsystem`.

## Класс 1. Завершающий перевод строки (артефакт сравнения, не различие конфигурации)

Замер gate-04: 8 файлов из 19 «отличающихся» отличались только этим. Признак в замерах
`probe/dump_vs_source.py`: позиция первого различия равна длине файла выгрузки, источник в этой
позиции содержит `'\n'`, выгрузка — `''` (`Enums/ГрейдыСпециалистов.xml`, `Languages/Русский.xml`,
`Reports/ОтчётЗагрузки.xml`, `CommonModules/РасчётПоказателей.xml` и ещё 4). `fc.exe` по такому
файлу говорит «no differences encountered».

Контур нормализует завершающие переводы строки (`gate.file_diff.normalized` = снять BOM, `CRLF→LF`,
`rstrip(b"\r\n")`). После этого gate-05: `same 15`, `differ 9`, `only_source []`, `only_dump []`.

## Класс 2. `ConfigDumpInfo.xml` — файл платформы, а не лишняя метаданная

Замер gate-04: `only_dump: ["ConfigDumpInfo.xml"]`. Замер корпусов: файл есть в **каждой** из шести
канонических выгрузок (`corpora_erp`, `corpora_uh`, `corpora_ssl`, `corpora_lso`,
`corpora_pulsar`, `corpora_ai_chat`; `corpora_cf` — не выгрузка, его там нет).

Контур называет его отдельно: `gate.PLATFORM_ADDED_FILES = ("ConfigDumpInfo.xml",)`,
`file_diff` возвращает `platform_added`, а `layout.layout_counts(..., ignore=PLATFORM_ADDED_FILES)`
не считает его файлом конфигурации. Без этого выгрузка навсегда оказывалась бы на файл «длиннее»
источника, и гейт отказывал бы по причине, которую нельзя исправить.

## Класс 3. Платформа дописывает свойства, которые мы не написали (норма)

Замер `probe/dump_vs_source.py` на gate-05 — все отличия этого класса *добавлением*:

| файл | источника | выгрузки | что добавлено платформой |
| --- | --- | --- | --- |
| `Catalogs/Сотрудники.xml` | 10 304 | 13 368 | `<LevelCount>2</LevelCount>`, `ChoiceFoldersAndItems`, `ChoiceParameterLinks`, `ChoiceParameters`, `QuickInfo`… |
| `Documents/ФактРаботы.xml` | 6 256 | 8 360 | свойства перед `NumberType` (в т. ч. `…erator/>`, `AutoNumber…`) |
| `InformationRegisters/ПланЗагрузки.xml` | 6 060 | 6 820 | `FillFromFillingValue`, `FillValue xsi:nil="true"`, свойства перед `FillChecking` |
| `Constants/НормаЧасовВМесяц.xml` | 2 708 | 3 222 | `ChoiceFoldersAndItems`, `ChoiceParameterLinks`, `ChoiceParameters`, `QuickInfo` (различие в конце блока свойств) |
| `Configuration.xml` | 4 815 | 10 924 | `AdditionalFullTextSearchDictionaries`, `CommonSettingsStorage`, `ReportsUserSettingsStorage`… |
| `Subsystems/ЭффективностьОтдела.xml` | 2 163 | 2 235 | `UseOneCommand`, `Explanation`, `Picture` перед `Content` |
| `Catalogs/Сотрудники/Forms/ФормаЭлемента/Ext/Form.xml` | 5 017 | 5 071 | `UseForFoldersAndItems` |

Вывод: «выгрузка короче/длиннее по байтам» не является ни доказательством дефекта, ни критерием
провала. Доказательством служат: коды платформы, сверка состава файлов (без пропусков), сверка
чисел метаданных и эталона, и отдельная проверка того, что платформа *не выбросила* и *не переписала*
содержимое (классы 4 и 5 ниже).

## Класс 4. Найденный дефект: придуманный узел qualifiers платформа приняла молча и обнулила разрядность

Мы написали во всех числовых реквизитах:

```xml
<v8:Type>xs:decimal</v8:Type>
<v8:DecimalQualifiers><v8:Precision>2</v8:Precision></v8:DecimalQualifiers>
```

Загрузка прошла с кодом 0, а в выгрузке оказалось:

```xml
<v8:NumberQualifiers><v8:Digits>0</v8:Digits><v8:FractionDigits>0</v8:FractionDigits><v8:AllowedSign>Any</v8:AllowedSign>
```

То есть дробная разрядность `Часы` (и `Ставка`, и константа `НормаЧасовВМесяц`, и реквизиты
`ПланЗагрузки`, и реквизит формы) стала нулевой. Замер канона
(`probe/corpora_type_qualifiers.py`, 15 157 XML-файлов шести корпусов):

| узел | встреч в каноне |
| --- | --- |
| `v8:NumberQualifiers` | 6 050 |
| `v8:Digits` / `v8:FractionDigits` / `v8:AllowedSign` | 6 050 / 6 050 / 6 050 (бывают только вместе с `NumberQualifiers`) |
| **`v8:DecimalQualifiers`** | **0** |
| **`v8:Precision`** | **0** |

Частые значения канона: `Digits` 10 (787), 15 (327), 1 (229), 5 (106); `FractionDigits` 0 (1409),
2 (204), 3 (156); `AllowedSign` `Any` (1214), `Nonnegative` (595).

Исправление: во всех шести местах (справочник `Ставка`, форма `ОценкаЁмкости`, документ `Часы`,
регистр `Часы`, ресурс регистра `Часы`, константа) написан канонический
`NumberQualifiers/Digits/FractionDigits/AllowedSign` (`Any` для ресурса регистра оборотов,
`Nonnegative` для ставок, планов и фактов). После исправления `AccumulationRegisters/ЗатратыВремени.xml`
совпал с выгрузкой платформы байт в байт (попал в `same`), а `probe/corpora_type_qualifiers.py`
больше не находит в нашей конфигурации неканонических узлов.

Цена, если бы контур не сравнивал файлы: конфигурация «работала» бы, но `Часы` и `Ставка`
округлялись бы до целых, и ни один инструмент p1c об этом не сообщил бы (`p1c-load model`
qualifier'ы не сравнивает, `p1c-diff` сравнивает модели, а не файлы).

## Класс 5. Найденный дефект: платформа переписывает права роли, и это видно только контуру

`scripts/rights.py` на источнике и на выгрузке (замер):

| файл прав | источник | выгрузка |
| --- | --- | --- |
| `Roles/АдминистраторСистемы/Ext/Rights.xml` | `setForNewObjects=true`, 1 блок, 9 прав | `setForNewObjects=true`, **0 блоков**, 0 прав |
| `Roles/СотрудникОтдела/Ext/Rights.xml` | `setForNewObjects=false`, 7 блоков, 34 права | `setForNewObjects=false`, **6 блоков**, **19 прав** |

Что именно делает платформа (наблюдение по блокам):

- роль с `setForNewObjects=true` (`АдминистраторСистемы`): все перечисленные права **сняты** —
  права на все объекты выдаются автоматически, и описывать их в файле бессмысленно;
- у роли `СотрудникОтдела` блок `Configuration.ЭффективностьОтдела` (права `Administration`,
  `Automation`, `ExternalConnection`, `TechnicalSpecialistMode`, `ThickClient`) **исчез** целиком;
- `Catalog.Сотрудники`: было `Delete, InputByString, Insert, InteractiveDelete, InteractiveInsert,
  Read, Update, View` → осталось `InputByString, Read, View`;
- `Document.ФактРаботы`: было `Delete, Insert, InteractiveDelete, InteractiveInsert,
  InteractivePosting, InteractivePostingRegular, Read, Update, View` → стало
  `Edit, Insert, InteractiveInsert, InteractivePosting, InteractivePostingRegular, Posting, Read,
  Update, View` (платформа **добавила** `Edit` и `Posting`, которых мы не писали, и **сняла**
  `Delete`, `InteractiveDelete`);
- `InformationRegister.ПланЗагрузки` `Read, Set, Update, View` → `Read, View`;
  `AccumulationRegister.ЗатратыВремени` `Read, TotalsControl, View` → `Read, View`;
  `Report.ОтчётЗагрузки` `Read, Use, View` → `Use, View`;
  `Constant.НормаЧасовВМесяц` `Read, Update` → `Read`.

Вывод для контура и для плана оптимизации p1c:

1. Ни один инструмент p1c права не читает (слепая зона, `docs/evidence/load-bisect.md`), поэтому
   переписывание прав платформой для инструментов невидимо целиком: ни `p1c-load`, ни
   `p1c-check-forms`, ни `p1c-check-bsl` не могут сообщить, что роль получила 19 прав вместо 34.
2. Контур это видит (`rights.check` на источнике и на выгрузке) и обязан сравнивать эти два
   состава — иначе «роль заведена» неотличимо от «роль означает не то, что мы написали».
3. Следующий замер (запланирован): **неподвижность прав** — переписать файл прав так, как его
   выкладывает платформа, и проверить, что после загрузки выгрузки состав прав совпадает с
   источником (`rights.check(source) == rights.check(dump)`). Пока такого совпадения нет, намерение
   роли нельзя считать зафиксированным, и формулировка «права роли настроены» не допускается.
4. Платформа при этом **не отвергает** висячие ссылки в правах (`roles_only` в лестнице 3
   `docs/evidence/load-bisect.md`): «правильность» прав может проверить только контур.

## Что из этого стало шагом контура

- `gate.file_diff` — нормализация BOM/переводов строк + отдельный список `platform_added`
  (`tests/test_dump_compare.py`);
- `layout.layout_counts(..., ignore=PLATFORM_ADDED_FILES)` — числа метаданных выгрузки не включают
  файлы платформы;
- `scripts/rights.py` + `gate` шаг 1b — статическая проверка прав по измеренному канону
  `docs/canonical-rights.json` (1672 файла, 103 686 блоков, вида `Enum.` — 0);
- `probe/dump_vs_source.py` — объяснение каждого отличия (кто его внёс: мы или платформа);
- `probe/our_event_handlers.py` — обработчики событий модулей объекта против официальных страниц
  событий (`CatalogObject.BeforeWrite` = 1 параметр `<Отказ>`, `DocumentObject.Posting` = 2/2,
  `InformationRegisterRecordSet.BeforeWrite` = 2/2): наша `ПередЗаписью(Отказ, Замечание, Параметр)`
  была находкой, `ПриНовомОбъекте()` — мёртвым кодом (0 встреч в 5 601 каноническом
  `Ext/ObjectModule.bsl` и 0 встреч `ПриНовомОбъекте` в 15 055 канонических `.bsl`).
