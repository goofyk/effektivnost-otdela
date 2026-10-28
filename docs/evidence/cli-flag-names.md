# Имена флагов платформы: что измерено и почему два имени лестниц в замере отсутствуют

Замер не запускает платформу. Источник имён — `p1c/src/p1c/data/test_cli_flags.json`
(снимок официальной таблицы имён исполняемых файлов платформы, `schema
p1c.data.test_cli_flags/v1`, `platform_version 8.3.27.1606`, `code_origin extracted`,
`dataset_version 1`). Вывод о том, что имя «существует» или «не существует», делается только
по членству в этом замере: own-контур не выдумывает имён и не чинит их на слух.

## 1. Что в замере есть

| измерено | число |
| --- | --- |
| файлов таблицы | 2 (`файл платформы 1`, `файл платформы 2`) |
| distinct-строк в файле 1 / файле 2 | 55 652 / 50 547 |
| flag-подобных имён в файле 1 / файле 2 | 426 / 415 |
| объединение имён по обоим файлам | **426 уникальных** |
| из них с косой чертой (`/Имя`) | 151 |
| из них с дефисом (`-Имя`) | 186 |
| флагов (`/Имя` + `-Имя`) в файле 1 | 337 |
| ключей вида `CmdLine/Имя` в файле 1 | 89 |
| группы по правилу файла | `other` 408, `test` 12, `debug` 6 |

Определение имени самого замера (цитата поля `definition`): «флаг — значение вида `/Имя` или
`-Имя`; ключ — значение вида `CmdLine/Имя`; значения с пробелом или знаком препинания не
входят». Правило групп (`group_rule`): «test, если имя содержит `test`, debug — если содержит
`debug`, иначе other». Сам замер отмечает (`note`): «В плане флагами отладки названы `-attach`,
`-http`, `-tcp`; по правилу группы они не содержат слова `debug`, поэтому относятся к группе
`other`. Это измерение, а не правило плана».

Семейства имён, относящиеся к нашему контуру (дословно из замера):

```
содержит '/Load'   -> ["/LoadCfg", "/LoadConfigFiles", "/LoadConfigFromFiles",
                       "/LoadExternalDataProcessorOrReportFromFiles"]        4 имени
содержит '/Dump'   -> ["/DumpCfg", "/DumpConfigFiles", "/DumpConfigToFiles", "/DumpDBCfg",
                       "/DumpDBCfgList", "/DumpExternalDataProcessorOrReportToFiles",
                       "/DumpIB", "/DumpResult"]                             8 имён
содержит '/Update' -> ["/UpdateCfg", "/UpdateDBCfg"]                        2 имени
содержит '/Check'  -> ["/CheckCanApplyConfigurationExtensions", "/CheckConfig", "/CheckModules"]
содержит '-list'   -> ["-listFile"]                                         1 имя
содержит '-Ext'    -> ["-ExtendedModulesCheck", "-Extension", "-ExternalConnection",
                       "-ExternalConnectionServer"]                         4 имени
```

Отдельно: в семействе `Config` (39 имён) есть `-updateConfigDumpInfo` и
`-updateConfigDumpInfoArchive` — имена, которые наш контур пока не проверял прогоном (см.
раздел 4).

## 2. Каждое имя наших лестниц сверено с замером

Сверка — проверка членства имени в объединении 426 имён (`exact=True/False`).

| имя в лестнице | в замере | что найдено вместо |
| --- | --- | --- |
| `/LoadConfigFromFiles` | да | `/LoadConfigFromFiles` |
| `/DumpConfigToFiles` | да | `/DumpConfigToFiles` |
| `/SetPredefinedDataUpdate` | да | `/SetPredefinedDataUpdate` |
| `-Extension` | да | `-Extension` |
| `-AllExtensions` | да | `-AllExtensions` |
| `-files` | да | `-files` |
| `-listFile` | да | `-listFile` |
| `-listfile` | **нет** | есть только `-listFile` |
| `-Format` | да | `-Format` |
| `/CheckCanApplyConfigurationExtensions` | да | `/CheckCanApplyConfigurationExtensions` |
| `-RebuildConfigurationExtensions` | да | `-RebuildConfigurationExtensions` |
| `/RebuildConfigurationExtensions` | **нет** | ничего (`variants=[]`) |
| `/UpdateDBCfg` | да | `/UpdateDBCfg` |
| `-Server` | да | `-Server` |
| `/UpdateCfg` | да | `/UpdateCfg` |
| `/LoadCfg` | да | `/LoadCfg` |
| `/IBCheckAndRepair` | да | `/IBCheckAndRepair` |
| `/RunScript` | да | `/RunScript` |
| `/TESTCLIENT` | да | `/TESTCLIENT` |
| `/TESTMANAGER` | да | `/TESTMANAGER` |
| `-testFile` | да | `-testFile` |
| `-testOut` | да | `-testOut` |
| `-TestOnly` | да | `-TestOnly` |
| `/AllowExecuteScheduledJobs` | да | `/AllowExecuteScheduledJobs` |
| `/EXECUTE` | да | `/EXECUTE` |
| `/LoadExternalDataProcessorOrReportFromFiles` | да | то же имя |
| `/DumpExternalDataProcessorOrReportToFiles` | да | то же имя |
| `/DumpCfg`, `/DumpDBCfg` | да | те же имена |
| `/DumpConfigFiles`, `/LoadConfigFiles` | да | те же имена (отдельная пара имён!) |
| `-CurrentUser` | да | `-CurrentUser` |
| `-CurrUserName` | нет | ничего |
| `/DisableStartupMessages`, `/DisableStartupDialogs`, `/Out`, `/IBConnectionString`, `/UC` | да | те же имена |

Отсутствуют ровно два имени из тех, что мы хотели бы написать: `-listfile` и
`/RebuildConfigurationExtensions`.

## 3. Следствие для контура и для инструментов p1c

1. **Регистр имени — часть имени, а не оформление.** В корпусе БСП одно и то же назначение
   живёт в двух написаниях: комментарий-синопсис и четыре корпуса пишут `-listfile`
   (`reports/corpora-cli-usage-16.json`: `listfile` — 10 вхождений), код БСП пишет `-listFile`
   (`listFile` — 3 вхождения), а таблица имён платформы знает только `-listFile`. Наш контур
   держит измеренное имя (`-listFile`) и требует этого же в тесте
   `tests/test_exec_probe.py::test_variant_flags_are_measured`; поэтому вариант `-listfile` в
   лестницу **не добавлен**: добавить его означало бы утверждать, что платформа принимает имя,
   которого в измеренной таблице нет. Вопрос «принимает ли платформа `-listfile` как вариант
   написания» остаётся **неизмеренным** (для ответа нужен прогон, а не сверка имён), и он
   записан в `docs/слепые-пятна.md`.

2. **Косая черта у `RebuildConfigurationExtensions` — вымысел.** Таблица знает только
   `-RebuildConfigurationExtensions` (дефис), и контур пишет именно её:
   `scripts/exec_probe.py:407` → `"load-rebuild-extensions": ["-RebuildConfigurationExtensions"]`.
   Слэш-форма в контуре не появляется нигде — не из экономии, а из замера: имени
   `/RebuildConfigurationExtensions` в таблице нет (`variants=[]`).

3. **Пара `/DumpConfigFiles` / `/LoadConfigFiles` существует рядом с
   `/DumpConfigToFiles` / `/LoadConfigFromFiles`.** Это две разные пары имён в одной таблице,
   а не опечатка. Наш контур прогоняет только пару `…ToFiles`/`…FromFiles`; прогона пары
   `…ConfigFiles` не делалось, поэтому утверждать, что они делают одно и то же, нельзя.

4. **Имена, про которые нельзя сказать «несуществующие» без замера.** Именно поэтому контур
   не «чинит» имена сам: вывод о несуществующем имени звучит только как «этого имени нет в
   `test_cli_flags.json`». Например `RunScript` в таблице есть, а в шести корпусах его
   употреблений **0** (`reports/corpora-cli-usage-16.json`) — это не опровергает существование
   имени, но означает, что канона его употребления в живых конфигурациях нет
   (см. `docs/evidence/exec-modes-and-negatives.md`).

## 4. Что с этим делать (часть плана оптимизации p1c)

1. В p1c есть `p1c/src/p1c/data/test_cli_flags.json`, но нет ни одного места, где имена
   флагов проверялись бы по нему: контур p1c собирает argv сам
   (`p1c/src/p1c/test/run.py`, `p1c/src/p1c/debug/debug.py` — битая сборка аргументов, см.
   `docs/evidence/exec-modes-and-negatives.md`). Проверка «имя флага есть в таблице имён»
   — дешёвый статический контроль, который стоит добавить, потому что замер уже лежит в
   репозитории p1c.
2. Имена `-updateConfigDumpInfo` / `-updateConfigDumpInfoArchive` — кандидаты на следующий
   замер: они относятся к `ConfigDumpInfo.xml`, а наш контроль уже показал, что 29 атрибутов
   `configVersion` в этом файле меняются на каждую загрузку
   (`docs/evidence/modifier-effects.md`).
3. Регистр имени (`-listFile` против написания `-listfile` из комментариев БСП) — измерить
   прогоном на временной ИБ, а не решать по корпусам: корпуса измеряют, как пишет БСП, а не
   как принимает платформа.
