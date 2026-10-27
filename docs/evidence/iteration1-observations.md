# Наблюдения итерации 1 — что платформа 8.3.27.1606 требует от рукописной конфигурации

Замеры по прогонам `reports/gate-01.json`, `reports/gate-02.json` (загрузка `/LoadConfigFromFiles`
временно файловой базы) и по каноническим выгрузкам корпусов `ИИ Чат 1С\Project`,
`ConfigSrc1C\SRC\UH`, `Пульсар\SRC`. Ничего из корпусов в репозиторий не переносится: здесь только
выводы о формате.

## 1. `InternalInfo` обязателен — его отсутствие прерывает загрузку

Диагнозы платформы (текст дословно, файл + узел):

```
Файл - …/Configuration.xml, узел - Configuration: Отсутствует внутренняя информация (узел InternalInfo) для объекта Configuration.
Файл - …/Catalogs/Сотрудники.xml, узел - Catalog: … для объекта Catalog.
Файл - …/Documents/ФактРаботы.xml, узел - Document: … для объекта Document.
Файл - …/Enums/ГрейдыСпециалистов.xml, узел - Enum: … для объекта Enum.
Файл - …/Constants/НормаЧасовВМесяц.xml, узел - Constant: … для объекта Constant.
Файл - …/InformationRegisters/ПланЗагрузки.xml, узел - InformationRegister: … для объекта InformationRegister.
Файл - …/AccumulationRegisters/ЗатратыВремени.xml, узел - AccumulationRegister: … для объекта AccumulationRegister.
Файл - …/Reports/ОтчётЗагрузки.xml, узел - Report: … для объекта Report.
```

Вывод: `InternalInfo` — не деталь, а условие чтения файла метаданных. При этом он **не нужен**
у `Role`, `CommonModule`, `Language`, `Subsystem`, `Template` (проверено по каноническим выгрузкам:
у этих видов узла нет).

Узел идёт **перед** `Properties`.

### Состав узла по видам (канон из выгрузок)

| Вид | Узлов | Имена генерируемых типов (порядок канона) |
| --- | --- | --- |
| Configuration | 7 `xr:ContainedObject` | фиксированные `xr:ClassId` платформы + свои `xr:ObjectId` |
| Catalog | 5 | `CatalogObject/Object`, `CatalogRef/Ref`, `CatalogSelection/Selection`, `CatalogList/List`, `CatalogManager/Manager` |
| Document | 5 | `DocumentObject/Object`, `DocumentRef/Ref`, `DocumentSelection/Selection`, `DocumentList/List`, `DocumentManager/Manager` |
| Enum | 3 | `EnumRef/Ref`, `EnumManager/Manager`, `EnumList/List` |
| Constant | 3 | `ConstantManager/Manager`, `ConstantValueManager/ValueManager`, `ConstantValueKey/ValueKey` |
| InformationRegister | 7 | `…Record/Record`, `…Manager/Manager`, `…Selection/Selection`, `…List/List`, `…RecordSet/RecordSet`, `…RecordKey/RecordKey`, `…RecordManager/RecordManager` |
| AccumulationRegister | 6 | `…Record/Record`, `…Manager/Manager`, `…Selection/Selection`, `…List/List`, `…RecordSet/RecordSet`, `…RecordKey/RecordKey` |
| Report | 2 | `ReportObject/Object`, `ReportManager/Manager` |
| CatalogTabularSection | 2 | `CatalogTabularSection.<Каталог>.<Секция>` category `TabularSection` + `CatalogTabularSectionRow.…` category `TabularSectionRow` |

Форма узла: `GeneratedType` содержит `TypeId` и `ValueId`; у конфигурации — `ContainedObject`
с `ClassId` (константы платформы, одинаковы во всех выгрузках) и `ObjectId`.

`ClassId` конфигурации (постоянные значения платформы, наблюдены в двух независимых выгрузках):
`9cd510cd-abfc-11d4-9434-004095e12fc7`, `9fcd25a0-4822-11d4-9414-008048da11f9`,
`e3687481-0a87-462c-a166-9f34594f9bba`, `9de14907-ec23-4a07-96f0-85521cb6b53b`,
`51f2d5d8-ea4d-4064-8892-82951750031e`, `e68182ea-4237-4383-967f-90c1e3370bc7`,
`fb282519-d103-4dd3-bc12-cb271d631dfc`.

## 2. Значения перечислений нельзя подбирать на слух

```
Неверное значение перечисления - Turnover          (RegisterType регистра накопления)
Неверное значение перечисления - Daily              (InformationRegisterPeriodicity)
```

Наблюдённые допустимые значения (по всем файлам корпуса UH):

- `RegisterType`: `Balance`, `Turnovers`
- `InformationRegisterPeriodicity`: `Day`, `Month`, `Quarter`, `Year`, `Second`, `RecorderPosition`, `Nonperiodical`
- `SequenceFilling`: `AutoFill`, `AutoFillOff`
- `Posting`: `Allow`, `Deny`; `RealTimePosting`: `Allow`, `Deny`
- `NumberType`: `Number`, `String`; `NumberPeriodicity`: `Day`, `Nonperiodical`, `Year`
- `DataCompositionTotalPlacement` (в макете СКД): `None`, `Begin`, `End`, `BeginAndEnd`, `Auto`
  — «Above»/«Bottom», которые подсказывает интуиция, платформой отвергаются.

## 3. Лишнее свойство так же ломает загрузку, как и отсутствующий файл

```
Неверное свойство объекта метаданных. Свойство ExtendedPresentation не входит
в состав объекта метаданных Form. - ExtendedPresentation
```

Канон дескриптора управляемой формы (`Forms/<Имя>.xml`): `Name`, `Synonym`, `Comment`,
`FormType`, `IncludeHelpInContents`, `UsePurposes`. `ExtendedPresentation` у `Form` отсутствует,
хотя есть у `Report`, `Constant`, `Catalog` и `Document`.

## 4. Форма — это три файла, и дескриптор не содержит описания формы

- декларация у родителя: `<Form>ФормаЭлемента</Form>` (только имя, без `uuid` и без `Properties`);
- `Forms/ФормаЭлемента.xml` — дескриптор метаданных;
- `Forms/ФормаЭлемента/Ext/Form.xml` — описание формы (XDTO logform);
- `Forms/ФормаЭлемента/Ext/Form/Module.bsl` — модуль формы.

Канон порядка верхнего уровня в `Ext/Form.xml` (наблюдён по 435 формам корпусов):
`AutoCommandBar`, `Events`, `ChildItems`, `Attributes`, `Commands`, `Parameters`.

## 5. Слепые пятна инструментов, подтверждённые этой итерацией

- **Зелёный `/CheckModules` не доказывает, что проверены твои модули.** В gate-02 загрузка
  отвергла конфигурацию (код 1), а `/CheckModules` на той же базе вернул код 0 и
  «Синтаксических ошибок не обнаружено!» — потому что в базе осталась прежнее (пустое) состояние.
  Инструмент, который смотрит только на код или только на текст «ошибок нет», даёт ложный зелёный.
- **`/DumpConfigToFiles` после провала загрузки возвращает 3 свежих файла пустой конфигурации**
  (`ConfigDumpInfo.xml`, `Configuration.xml` с именем корневого объекта `Конфигурация`,
  `Languages/Русский.xml`) и не трогает прежний дамп. Признак провала — имя корневого объекта
  выгрузки (`Конфигурация`) ≠ имени в исходнике (`ЭффективностьОтдела`).
- **Признак файловой базы 8.3.27 — `1Cv8.1CD`**, а не «классические» `1Cv8.8cd`. Без базы
  `/LoadConfigFromFiles` сообщает «Информационная база не обнаружена!» с кодом 1 — неотличимо от
  битого каталога конфигурации, поэтому контур различает эти случаи до запуска платформы
  (`ib_loop.ib_exists`, `gate.loop_steps`).
- **`CREATEINFOBASE` на существующей базе** → «Указанная информационная база уже существует.»
  (код 1): повторный `create` должен пропускаться, а не выполняться.
