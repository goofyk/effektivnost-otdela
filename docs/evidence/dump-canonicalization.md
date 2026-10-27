# Что платформа делает с рукописной конфигурацией при загрузке: семь классов отличий выгрузки

Доказательство двух зелёных итераций и разбор того, какие отличия выгрузки — норма платформы, а какие
значат, что мы написали неканонически.

Инструменты: `scripts/gate.py` (гейт), `probe/dump_vs_source.py` (классификация берёт из
`gate.file_diff`, показывает контекст первого различия), `scripts/rights.py` (состав прав в
источнике и в выгрузке), `probe/role_dump_vs_source.py` (описания ролей: UUID и переводы).
Замеры без повторной ручной работы: `reports/gate-04.json` (первый успешный `load`),
`reports/gate-05.json` (первая зелёная итерация), `reports/gate-06.json` (найденная платформенная
добавка права), `reports/gate-07.json` и `reports/gate-08.json` (вторая зелёная итерация:
права неподвижны), `%TEMP%\opencode\p1c_effektivnost\gate04.txt`, `gate05.txt`,
`type_qualifiers.txt`.

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

## Зелёная итерация 2 (gate-07, gate-08): права неподвижны

После того как файл прав был переписан по канону (описывать только выдаваемые права, блок
`Configuration.` с явным `DataAdministration`, `setForNewObjects=false`), гейт прогнан дважды
подряд:

```
python scripts/gate.py --cfg "cfg/ЭффективностьОтдела" --out reports/gate-07.json --timeout 240
гейт: код 0
python scripts/gate.py --cfg "cfg/ЭффективностьОтдела" --out reports/gate-08.json --timeout 240
гейт: код 0
```

| шаг | код | секунды | байт вывода |
| --- | --- | --- | --- |
| `load` (`/LoadConfigFromFiles`) | **0** | 3.0 | 3 (BOM, то есть пусто) |
| `check` (`/CheckModules`) | **0** | 2.0 | 73 («Синтаксических ошибок не обнаружено!») |
| `dump` (`/DumpConfigToFiles`) | **0** | 2.0 | 3 |

- выгрузка: 25 файлов, все 25 свежие; `layout_source == layout_dump` (`files 24`);
  `expected_mismatch {}`; `diagnostic_findings []`, `step_problems []`;
- **`rights_immobility.code 0`**: `source_blocks 15 == dump_blocks 15`,
  `source_rights 75 == dump_rights 75`, `dropped []`, `added []` — платформа не выбросила и не
  добавила ни одного права. Это то совпадение, которого не хватало в классе 5: после него
  допустима формулировка «права роли настроены» (и она закреплена гейтом: несовпадение состава
  прав — код 1, отсутствие выгрузки — код 2);
- `diff_files`: `same 15`, **`reordered 2`** (оба `Roles/*/Ext/Rights.xml`), `differ 7` — все семь
  отличия относятся к классу 3 (платформа дописывает свойства), `platform_added
  ["ConfigDumpInfo.xml"]`, `only_source []`, `only_dump []`.

### Промежуточный замер (gate-06): единственная платформенная добавка права

Перед тем как состав совпал, гейт поймал ровно одно расхождение:

```
"rights_immobility": {"code": 1, "added": ["Roles/АдминистраторСистемы/Ext/Rights.xml: платформа
добавила право DataAdministration объекта Configuration.ЭффективностьОтдела (значение true),
которого в исходнике нет"], "counts": {"source_rights": 74, "dump_rights": 75}}
```

Замер канона `docs/canonical-rights-configuration.json` (1360 блоков `Configuration.` во всех
корпусах): `DataAdministration` встречается 15 раз, **все 15 — `true`**; из 14 блоков с
`Administration=true` 14 имеют и `DataAdministration`, случаев `Administration` без
`DataAdministration` — 0. То есть платформа выдаёт это право автоматически, и канонический
исходник обязан писать его явно. После явной записи составы сравнялись (75 == 75).

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
3. **Неподвижность прав** — переписать файл прав так, как его выкладывает платформа, и проверить,
   что после загрузки состав прав в выгрузке совпадает с источником. Этот замер сделан:
   `gate-07`/`gate-08`, `rights_immobility.code 0` (15 блоков и 75 прав с обеих сторон,
   `dropped []`, `added []`) — см. «Зелёная итерация 2» в начале документа. До него формулировка
   «права роли настроены» не допускалась, и гейт это закрепил: несовпадение состава прав — код 1,
   отсутствие выгрузки — код 2;
4. Платформа при этом **не отвергает** висячие ссылки в правах (`roles_only` в лестнице 3
   `docs/evidence/load-bisect.md`): «правильность» прав может проверить только контур.

## Класс 6. Платформа переставляет блоки прав, не меняя их состава (не дефект)

Замер gate-07 на двух файлах прав: длина источника и выгрузки совпадает побайтово —
`Roles/АдминистраторСистемы/Ext/Rights.xml` 4951 символа и 4951,
`Roles/СотрудникОтдела/Ext/Rights.xml` 2201 и 2201, — при этом `rights.immobile` даёт
`dropped []`, `added []`, а первый отличающийся символ стоит внутри файла: блоки `<object>`
выгрузка выкладывает в другом порядке.

Контур называет такие файлы отдельным классом `reordered` (`gate.file_diff`): «содержимое
переписано» и «блоки переставлены» — разные утверждения, и второе дефектом не является. Тест
`tests/test_dump_compare.py` закрепляет границу: перестановка плюс потерянная строка — это уже
`differ`, а не `reordered` (перестановка не должна маскировать потерянное право).

## Класс 7. Найденный дефект: неканонический код языка `RU` платформа приняла молча

Мы написали `<LanguageCode>RU</LanguageCode>`, а все тексты объектов помечены
`<v8:lang>ru</v8:lang>` (строчными). Замер `probe/corpora_language_codes.py` (записан в
`docs/canonical-languages.json`, 8 файлов языков шести корпусов):

| `LanguageCode` | встреч | имя языка | встреч |
| --- | --- | --- | --- |
| `ru` | 6 | Русский | 6 |
| `en` | 2 | Английский | 2 |

Коды `<v8:lang>` в описаниях объектов: `ru` во всех шести корпусах (ERP — ещё и `en` 12 743
раза, UH — `en` 27, LSO — `en` 3). Строчный код языка — канон 6/6.

Платформа наш `RU` сохранила без изменений (`Languages/Русский.xml` в выгрузке gate-08:
`<LanguageCode>RU</LanguageCode>`) — то есть расхождение канона она не заметила и не сообщила.
Исправлено на `ru`; эта находка возможна только потому, что контур сверяет исходник с каноном
корпусов: ни один инструмент p1c язык конфигурации не читает (слепая зона `language`).

## Наблюдение: UUID роли платформа сохраняет побайтово, канонический UUID — артефакт шаблона

Роль `АдминистраторСистемы` мы написали с выдуманным UUID `6b1e3a24-1c77-4c0a-90d1-0a2f4c6e8021`.
Замер корпусов (`probe/corpora_role_uuids.py`): у роли с таким именем UUID **одинаковый во всех
пяти** канонических выгрузках — `76702e9e-fa7a-4b98-befa-f9b37db2dae0` (а у роли `ПолныеПрава`
он разный), то есть это значение шаблона конфигурации, а не системное требование платформы.

Замер `probe/role_dump_vs_source.py` на выгрузке gate-08: UUID и набор переводов (`ru`)
сохранены без изменений (источник 1262 байта, выгрузка 1260 — различие относится к классу 1:
завершающий перевод строки). Вывод: менять UUID на «канонический» не нужно; наш остаётся, и
платформа его не переписывает.

## Что из этого стало шагом контура

- `gate.file_diff` — нормализация BOM/переводов строк + отдельные списки `platform_added` и
  `reordered` (`tests/test_dump_compare.py`);
- `layout.layout_counts(..., ignore=PLATFORM_ADDED_FILES)` — числа метаданных выгрузки не включают
  файлы платформы;
- `scripts/rights.py` + `gate` шаги 1b и 3b — статическая проверка прав по измеренному канону
  `docs/canonical-rights.json` (1672 файла, 103 686 блоков, вида `Enum.` — 0) и сверка
  неподвижности прав между источником и выгрузкой (`rights.immobile`);
- `probe/dump_vs_source.py` — объяснение каждого отличия (кто его внёс: мы или платформа);
- `probe/role_dump_vs_source.py` — описания ролей в источнике и в выгрузке (UUID, переводы);
- `probe/corpora_language_codes.py` → `docs/canonical-languages.json` — канон кода языка;
- `probe/our_event_handlers.py` — обработчики событий модулей объекта против официальных страниц
  событий (`CatalogObject.BeforeWrite` = 1 параметр `<Отказ>`, `DocumentObject.Posting` = 2/2,
  `InformationRegisterRecordSet.BeforeWrite` = 2/2): наша `ПередЗаписью(Отказ, Замечание, Параметр)`
  была находкой, `ПриНовомОбъекте()` — мёртвым кодом (0 встреч в 5 601 каноническом
  `Ext/ObjectModule.bsl` и 0 встреч `ПриНовомОбъекте` в 15 055 канонических `.bsl`).
