# Наблюдения Task 1 (платформа 8.3.27.1606)

Номера наблюдений соответствуют плану (раздел «Поправки плана», B1/B2) и журналу.

## C. Полный цикл на реальной конфигурации (копия)
- исходных файлов: 239
- create: код 0, 1.0 с, байт вывода 188
- load: код 0, 4.0 с, байт вывода 3
- check: код 101, 3.0 с, байт вывода 346
- dump: код 0, 3.0 с, байт вывода 3
  диагностика /CheckModules: {ОбщийМодуль.ГПН_ИИ_ДействияСОтветомКлиент.Модуль(206,10)}: Процедура или функция с указанным именем не определена (ПрочитатьJSON)
  диагностика /CheckModules: Поля = <<?>>ПрочитатьJSON(Чтение, Истина); (Проверка: Веб-клиент)

## B1. `/LoadConfigFromFiles` с каталогом, которого нет
- контур отказывает до запуска платформы: код 2, причина: каталога конфигурации нет: --cfg называет каталог, которого не существует
- платформа напрямую: код 1, байт вывода 123, уложилось
  вывод: Файл не обнаружен 'C:\Users\goof0\AppData\Local\Temp\opencode\p1c_effektivnost\каталога-нет'
- вывод: молчания нет; и контур, и платформа сообщают об отсутствии каталога

## B2. `/DumpConfigToFiles` после неудачной загрузки поверх хорошего дампа
- файлов в каталоге выгрузки: до 239, после 239
- свежих файлов после выгрузки: 3 — ['ConfigDumpInfo.xml', 'Configuration.xml', 'Languages/Русский.xml']
- имя корневого объекта выгрузки: 'Конфигурация'
- числа выгрузки по независимому счётчику: {"bsl_module": 78, "catalog": 10, "common_form": 4, "common_module": 36, "common_picture": 4, "constant": 4, "data_processor": 6, "defined_type": 3, "enum": 10, "files": 239, "form_data": 17, "form_descriptor": 13, "form_module": 17, "information_register": 7, "language": 1, "object_module": 61, "report": 2, "report_template": 3, "report_template_data": 3, "role": 3, "role_rights": 3, "session_parameter": 3, "subsystem": 3}
- код загрузки битой конфигурации: 1, код выгрузки: 0
  вывод загрузки: Ошибка XDTO в файле - ЭффективностьОтдела.xml, при чтении свойства: Content
  вывод загрузки: Ошибка преобразования данных XDTO:
  вывод загрузки: Чтение объекта типа: {http://v8.1c.ru/8.3/xcf/readable}MDListType - [20,1]
  вывод загрузки: Проверка дополнительного свойства:
  вывод загрузки: форма: Текст
  вывод загрузки: имя:
- вывод: платформа не затирает прежний дамп; признак провала — расхождение имени корневого объекта с именем исходника и свежие файлы, а не число файлов каталога

## B2b. Три повтора загрузки одного и того же битого каталога
- коды прогонов: 1, 1, 1
- разные тексты первой ошибки: ["Ошибка XDTO в файле - ЭффективностьОтдела.xml, при чтении свойства: Content", "Файл - РасчётПоказателей.xml: ошибка формата документа - читаемое свойство не соответствует ожидаемому. Текущее ChildObjects, ожидаемое CommonModule."]
  попытка 0: код 1, 2.0 с, байт 386, строк вывода 4
  попытка 1: код 1, 2.0 с, байт 254, строк вывода 1
  попытка 2: код 1, 2.0 с, байт 386, строк вывода 4
- вывод: текст первой ошибки между прогонами не стабилен — вывод пишут целиком, признак провала ищут в кодах и составе выгрузки

## D. Гейт на реальной конфигурации: что видит независимый счётчик и что — читатель p1c
- код гейта: 1 (шаг платформы вернул ненулевой код: [{"step": "check", "code": 101}])
- коды платформы: load 0, check 101
- файлов выгрузки: 239, свежих (записанных этим шагом): 239
- имя корневого объекта: исходник 'Конфигурация', выгрузка 'Конфигурация'
- пофайловая сверка: идентично 230, различается 9, только в источнике 0, только в выгрузке 0
- расхождение чисел источника и выгрузки: {}
- числа независимого счётчика (источник): {"bsl_module": 78, "catalog": 10, "common_form": 4, "common_module": 36, "common_picture": 4, "constant": 4, "data_processor": 6, "defined_type": 3, "enum": 10, "files": 239, "form_data": 17, "form_descriptor": 13, "form_module": 17, "information_register": 7, "language": 1, "object_module": 61, "report": 2, "report_template": 3, "report_template_data": 3, "role": 3, "role_rights": 3, "session_parameter": 3, "subsystem": 3}
- числа независимого счётчика (выгрузка): {"bsl_module": 78, "catalog": 10, "common_form": 4, "common_module": 36, "common_picture": 4, "constant": 4, "data_processor": 6, "defined_type": 3, "enum": 10, "files": 239, "form_data": 17, "form_descriptor": 13, "form_module": 17, "information_register": 7, "language": 1, "object_module": 61, "report": 2, "report_template": 3, "report_template_data": 3, "role": 3, "role_rights": 3, "session_parameter": 3, "subsystem": 3}
- числа читателя p1c.load (источник): {"catalog": 10, "common_form": 4, "common_module": 36, "constant": 4, "data_processor": 6, "enum": 10, "form_data": 17, "information_register": 7, "report": 2}
- числа читателя p1c.load (выгрузка): {"catalog": 10, "common_form": 4, "common_module": 36, "constant": 4, "data_processor": 6, "enum": 10, "form_data": 17, "information_register": 7, "report": 2}
- читатель p1c.load не сообщает ни о чём из этого: ["bsl_module", "common_picture", "defined_type", "files", "form_descriptor", "form_module", "language", "object_module", "report_template", "report_template_data", "role", "role_rights", "session_parameter", "subsystem"]
  различается файл: Catalogs/ГПН_ИИ_Диалоги.xml
  различается файл: Catalogs/ГПН_ИИ_Подключения.xml
  различается файл: Catalogs/ГПН_ИИ_Подключения/Forms/ФормаПодключения/Ext/Form.xml
  различается файл: ConfigDumpInfo.xml
  различается файл: DataProcessors/ГПН_ИИ_ИнициализацияНастроек/Templates/НастройкиПоОкружениям/Ext/Template.xml
  различается файл: DataProcessors/ГПН_ИИ_МастерНастройки/Forms/ФормаМастера/Ext/Form.xml
  различается файл: DataProcessors/ГПН_ИИ_НастройкиАдминистратора/Forms/ФормаНастроек/Ext/Form.xml
  различается файл: InformationRegisters/ГПН_ИИ_ЗамерыПроизводительности.xml
  различается файл: Roles/ГПН_ИИ_Пользователь/Ext/Rights.xml
