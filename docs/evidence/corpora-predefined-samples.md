# Что корпуса дают для Tasks 15 и 17 (предопределённые данные, значения перечисления, параметры сеанса)

Корпуса приняты: ['corpora_ai_chat', 'corpora_erp', 'corpora_lso', 'corpora_pulsar', 'corpora_ssl', 'corpora_uh']
Не приняты или отсутствующие ключи см. в `scripts/corpora.py` (`corpora.report`).

## 1. Где лежат предопределённые данные (по kind-каталогу)

Ограничение: 12 файлов `Ext/Predefined.xml` на kind-каталог каждого корпуса; счётчики — полное число найденного без ограничения.

- `Catalogs`: найдено 301, среди них самый маленький — `Catalogs/КартыСУЗ/Ext/Predefined.xml` в `corpora_lso` (536 байт)
- `Enums`: `Ext/Predefined.xml` не найден (каталоги в выборке: corpora_ai_chat, corpora_erp, corpora_lso, corpora_pulsar, corpora_ssl, corpora_uh)
- `ChartsOfCharacteristicTypes`: найдено 29, среди них самый маленький — `ChartsOfCharacteristicTypes/ОбъектыАдресацииЗадач/Ext/Predefined.xml` в `corpora_pulsar` (783 байт)
- `ChartsOfAccounts`: найдено 5, среди них самый маленький — `ChartsOfAccounts/Международный/Ext/Predefined.xml` в `corpora_erp` (1189 байт)
- `ChartsOfCalculationTypes`: найдено 2, среди них самый маленький — `ChartsOfCalculationTypes/УдалитьОсновныеНачисленияОрганизаций/Ext/Predefined.xml` в `corpora_uh` (584 байт)
- `ChartsOfConstants`: `Ext/Predefined.xml` не найден (каталоги в выборке: нет)
- `CommonReports`: `Ext/Predefined.xml` не найден (каталоги в выборке: нет)
- `InformationRegisters`: `Ext/Predefined.xml` не найден (каталоги в выборке: corpora_ai_chat, corpora_erp, corpora_lso, corpora_pulsar, corpora_ssl, corpora_uh)
- `DocumentNumbers`: `Ext/Predefined.xml` не найден (каталоги в выборке: нет)
- `BusinessProcesses`: `Ext/Predefined.xml` не найден (каталоги в выборке: corpora_erp, corpora_pulsar, corpora_ssl, corpora_uh)

Совпадение по kind-каталогу с тем, у каких видов в 1С бывают предопределённые данные: справочник, план видов характеристик, план счетов, план видов расчёта. У перечисления, регистра сведений, константы, общего отчёта, номера документа и бизнес-процесса отдельного файла предопределённых данных в корпусах нет.

### образец Catalogs: corpora_lso :: Catalogs/КартыСУЗ/Ext/Predefined.xml (536 байт)

```xml
﻿<?xml version="1.0" encoding="UTF-8"?>
<PredefinedData xmlns="http://v8.1c.ru/8.3/xcf/predef" xmlns:v8="http://v8.1c.ru/8.1/data/core" xmlns:xr="http://v8.1c.ru/8.3/xcf/readable" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:type="CatalogPredefinedItems" version="2.20">
	<Item id="3d264ff6-6322-4f12-992d-13c79911ec61">
		<Name>АвтоКарта</Name>
		<Code/>
		<Description>Авто карта</Description>
		<IsFolder>false</IsFolder>
	</Item>
</PredefinedData>
```

### образец Catalogs: corpora_lso :: Catalogs/ПрофилиГруппДоступа/Ext/Predefined.xml (551 байт)

```xml
﻿<?xml version="1.0" encoding="UTF-8"?>
<PredefinedData xmlns="http://v8.1c.ru/8.3/xcf/predef" xmlns:v8="http://v8.1c.ru/8.1/data/core" xmlns:xr="http://v8.1c.ru/8.3/xcf/readable" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:type="CatalogPredefinedItems" version="2.20">
	<Item id="6c4b0307-43a4-4141-9c35-3dd7e9586d41">
		<Name>Администратор</Name>
		<Code/>
		<Description>Администратор</Description>
		<IsFolder>false</IsFolder>
	</Item>
</PredefinedData>
```

### образец ChartsOfCharacteristicTypes: corpora_pulsar :: ChartsOfCharacteristicTypes/ОбъектыАдресацииЗадач/Ext/Predefined.xml (783 байт)

```xml
﻿<?xml version="1.0" encoding="UTF-8"?>
<PredefinedData xmlns="http://v8.1c.ru/8.3/xcf/predef" xmlns:v8="http://v8.1c.ru/8.1/data/core" xmlns:xr="http://v8.1c.ru/8.3/xcf/readable" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:type="PlanOfCharacteristicKindPredefinedItems" version="2.20">
	<Item id="58db8b99-289e-4ef3-a2d8-c4ec1aa03f40">
		<Name>ВсеОбъектыАдресации</Name>
		<Code/>
		<Description>Все объекты адресации</Description>
		<Type>
			<v8:Type>xs:string</v8:Type>
			<v8:StringQualifiers>
				<v8:Length>10</v8:Length>
				<v8:AllowedLength>Variable</v8:AllowedLength>
			</v8:StringQualifiers>
		</Type>
		<IsFolder>false</IsFolder>
	</Item>
</PredefinedData>
```

### образец ChartsOfCharacteristicTypes: corpora_uh :: ChartsOfCharacteristicTypes/РазделыДатЗапретаИзменения/Ext/Predefined.xml (827 байт)

```xml
﻿<?xml version="1.0" encoding="UTF-8"?>
<PredefinedData xmlns="http://v8.1c.ru/8.3/xcf/predef" xmlns:v8="http://v8.1c.ru/8.1/data/core" xmlns:xr="http://v8.1c.ru/8.3/xcf/readable" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:type="PlanOfCharacteristicKindPredefinedItems" version="2.20">
	<Item id="942d99dc-3fa8-478d-8e93-6d1c26536c6c">
		<Name>УдалитьБухгалтерскийУчет</Name>
		<Code/>
		<Description>(не используется) Бухгалтерский учет</Description>
		<Type>
			<v8:Type xmlns:d4p1="http://v8.1c.ru/8.1/data/enterprise/current-config">d4p1:ChartOfCharacteristicTypesRef.РазделыДатЗапретаИзменения</v8:Type>
		</Type>
		<IsFolder>false</IsFolder>
	</Item>
</PredefinedData>
```

## 2. Значения перечисления — это метаданные, а не предопределённые данные

Считаем все описания верхнего уровня kind-каталога (не глубже), не больше 4000 файлов на kind-каталог каждого корпуса.

- `predefined-тег` — `<PredefinedData>` или `<PredefinedData ...>`.
- `PredefinedDataUpdate` — способ обновления предопределённых данных (`Auto`/`Manual`), он есть у каждого справочника и данными не является.
- `PredefinedDataName` — реквизит «предопределённый» у обычной записи справочника (`<xr:StandardAttribute name="PredefinedDataName">`), тоже не предопределённые данные.
- `EnumValue` — значения перечисления как дочерние метаданные внутри `Enums/<Имя>.xml`.

### kind `Enums`

| корпус | описаний | predefined-тег | PredefinedDataUpdate | PredefinedDataName | EnumValue |
|---|---|---|---|---|---|
| corpora_ai_chat | 10 | 0 | 0 | 0 | 29 |
| corpora_erp | 1616 | 0 | 0 | 0 | 12996 |
| corpora_lso | 189 | 0 | 0 | 0 | 976 |
| corpora_pulsar | 67 | 0 | 0 | 0 | 328 |
| corpora_ssl | 138 | 0 | 0 | 0 | 586 |
| corpora_uh | 1318 | 0 | 0 | 0 | 9407 |

### kind `Catalogs`

| корпус | описаний | predefined-тег | PredefinedDataUpdate | PredefinedDataName | EnumValue |
|---|---|---|---|---|---|
| corpora_ai_chat | 10 | 0 | 10 | 1 | 0 |
| corpora_erp | 1079 | 0 | 1079 | 1079 | 0 |
| corpora_lso | 158 | 0 | 158 | 150 | 0 |
| corpora_pulsar | 44 | 0 | 44 | 35 | 0 |
| corpora_ssl | 116 | 0 | 116 | 114 | 0 |
| corpora_uh | 844 | 0 | 844 | 814 | 0 |

### kind `ChartsOfCharacteristicTypes`

| корпус | описаний | predefined-тег | PredefinedDataUpdate | PredefinedDataName | EnumValue |
|---|---|---|---|---|---|
| corpora_erp | 16 | 0 | 16 | 16 | 0 |
| corpora_lso | 8 | 0 | 8 | 7 | 0 |
| corpora_pulsar | 1 | 0 | 1 | 1 | 0 |
| corpora_ssl | 5 | 0 | 5 | 5 | 0 |
| corpora_uh | 17 | 0 | 17 | 17 | 0 |

### kind `ChartsOfAccounts`

| корпус | описаний | predefined-тег | PredefinedDataUpdate | PredefinedDataName | EnumValue |
|---|---|---|---|---|---|
| corpora_erp | 2 | 0 | 2 | 2 | 0 |
| corpora_ssl | 1 | 0 | 1 | 1 | 0 |
| corpora_uh | 2 | 0 | 2 | 2 | 0 |

### kind `ChartsOfCalculationTypes`

| корпус | описаний | predefined-тег | PredefinedDataUpdate | PredefinedDataName | EnumValue |
|---|---|---|---|---|---|
| corpora_erp | 2 | 0 | 2 | 2 | 0 |
| corpora_ssl | 1 | 0 | 1 | 1 | 0 |
| corpora_uh | 3 | 0 | 3 | 3 | 0 |

### kind `InformationRegisters`

| корпус | описаний | predefined-тег | PredefinedDataUpdate | PredefinedDataName | EnumValue |
|---|---|---|---|---|---|
| corpora_ai_chat | 7 | 0 | 0 | 0 | 0 |
| corpora_erp | 1599 | 0 | 0 | 0 | 0 |
| corpora_lso | 269 | 0 | 0 | 0 | 0 |
| corpora_pulsar | 114 | 0 | 0 | 0 | 0 |
| corpora_ssl | 273 | 0 | 0 | 0 | 0 |
| corpora_uh | 1369 | 0 | 0 | 0 | 0 |

Вывод: предопределённых данных у перечисления в файловой выгрузке нет ни в одном корпусе — его значения (`EnumValue`) описаны внутри самого метаданного и при загрузке становятся значениями перечисления, а не предопределёнными записями. Значит для нашей сборки канонично держать значения в `Enums/<Имя>.xml` и не придумывать перечислению `Ext/Predefined.xml`. Предопределённые данные добавляем там, где их пишет платформа: справочник `Сотрудники`.
## 3. Образец значения перечисления (`EnumValue`) в описании

### corpora_ai_chat :: Enums::ГПН_ИИ_ОкружениеAPIM.xml (3176 байт)

```xml
<EnumValue uuid="437881bd-813a-4e2d-82d0-0a6adff79cd8">
				<Properties>
					<Name>Тест</Name>
					<Synonym>
						<v8:item>
							<v8:lang>ru</v8:lang>
							<v8:content>Тест</v8:content>
						</v8:item>
					</Synonym>
					<Comment/>
				</Properties>
			</EnumValue>
			<EnumValue uuid="742bf724-a3ff-420b-b484-298d754dc306">
				<Properties>
					<Name>Прод</Name>
					<Synonym>
						<v8:item>
							<v8:lang>ru</v8:lang>
							<v8:content>Прод</v8:content>
						</v8:item>
					</Synonym>
					<Comment/>
				</Properties>
			</EnumValue>
		</ChildObjects>
	</Enum>
</MetaDataObject>
```

## 4. Блок `<PredefinedData>` внутри описания метаданного

Читаем описания метаданных верхнего уровня kind-каталога (не глубже), до 80 файлов на kind-каталог корпуса.

`<PredefinedData>` внутри описаний метаданных не найден: в принятых корпусах предопределённые данные лежат отдельными файлами `Ext/Predefined.xml`. Значит для нашей сборки канонична именно отдельная форма.
## 5. `<SessionParameters>` в описании конфигурации

- `corpora_ai_chat`: `SessionParameters` в описании конфигурации нет
- `corpora_erp`: `SessionParameters` в описании конфигурации нет
- `corpora_lso`: `SessionParameters` в описании конфигурации нет
- `corpora_pulsar`: `SessionParameters` в описании конфигурации нет
- `corpora_ssl`: `SessionParameters` в описании конфигурации нет
- `corpora_uh`: `SessionParameters` в описании конфигурации нет

`SessionParameters` нет ни в одной принятой выгрузке. Для нашей сборки это не канон, а проверка: добавим — узнаем, принимает ли платформа форму, которой нет в реальных конфигурациях, и видит ли её p1c.
## 6. Как устроена папка обработки (DataProcessor)

### corpora_ai_chat: самая маленькая обработка `ГПН_ИИ_НастройкиАдминистратора` (описание 2726 байт)

```
ГПН_ИИ_НастройкиАдминистратора.xml 2726
DIR  ГПН_ИИ_НастройкиАдминистратора/Ext
    118 ГПН_ИИ_НастройкиАдминистратора/Ext/ManagerModule.bsl
    114 ГПН_ИИ_НастройкиАдминистратора/Ext/ObjectModule.bsl
DIR  ГПН_ИИ_НастройкиАдминистратора/Forms
DIR  ГПН_ИИ_НастройкиАдминистратора/Forms/ФормаНастроек
   1559 ГПН_ИИ_НастройкиАдминистратора/Forms/ФормаНастроек.xml
DIR  ГПН_ИИ_НастройкиАдминистратора/Forms/ФормаНастроек/Ext
DIR  ГПН_ИИ_НастройкиАдминистратора/Forms/ФормаНастроек/Ext/Form
 104059 ГПН_ИИ_НастройкиАдминистратора/Forms/ФормаНастроек/Ext/Form.xml
  13470 ГПН_ИИ_НастройкиАдминистратора/Forms/ФормаНастроек/Ext/Form/Module.bsl
```

### corpora_erp: самая маленькая обработка `ПечатьМ11` (описание 2125 байт)

```
ПечатьМ11.xml 2125
DIR  ПечатьМ11/Ext
  22716 ПечатьМ11/Ext/ManagerModule.bsl
DIR  ПечатьМ11/Templates
DIR  ПечатьМ11/Templates/ПФ_MXL_М11
   1369 ПечатьМ11/Templates/ПФ_MXL_М11.xml
DIR  ПечатьМ11/Templates/ПФ_MXL_М11/Ext
  80809 ПечатьМ11/Templates/ПФ_MXL_М11/Ext/Template.xml
```

### corpora_lso: самая маленькая обработка `УчебныеЗаданияСУЗ` (описание 2032 байт)

```
УчебныеЗаданияСУЗ.xml 2032
DIR  УчебныеЗаданияСУЗ/Ext
  27745 УчебныеЗаданияСУЗ/Ext/ObjectModule.bsl
```

### corpora_pulsar: самая маленькая обработка `ЗаполнениеГрафиковРаботы` (описание 2095 байт)

```
ЗаполнениеГрафиковРаботы.xml 2095
DIR  ЗаполнениеГрафиковРаботы/Ext
   3960 ЗаполнениеГрафиковРаботы/Ext/ManagerModule.bsl
```

### corpora_ssl: самая маленькая обработка `ЗаполнениеГрафиковРаботы` (описание 2095 байт)

```
ЗаполнениеГрафиковРаботы.xml 2095
DIR  ЗаполнениеГрафиковРаботы/Ext
   4434 ЗаполнениеГрафиковРаботы/Ext/ManagerModule.bsl
```

### corpora_uh: самая маленькая обработка `ОбходКоллекции` (описание 2015 байт)

```
ОбходКоллекции.xml 2015
DIR  ОбходКоллекции/Ext
   3326 ОбходКоллекции/Ext/ManagerModule.bsl
  21851 ОбходКоллекции/Ext/ObjectModule.bsl
```

