# Модификаторы `/LoadConfigFromFiles`: что действительно делает каждый хвост команды

Замер: шесть лестниц модификаторов прогнаны целиком на отдельной временной ИБ, затем то же самое
повторено на уже загруженной ИБ. Каждый шаг окружён выгрузкой состояния ИБ ДО шага и выгрузкой ПОСЛЕ
него, плюс третья выгрузка того же состояния (без шага между второй и третьей). Первоисточник чисел —
отчёты `reports/effect-16-predefined-full.json`, `effect-16-extensions-full.json`,
`effect-16-loadopts-full.json`, `effect-16-update-full.json`, `effect-16-modes-full.json`,
`effect-16-repeat-full.json`, `effect-16-loadopts-shared.json`; все таблицы этого файла собраны из них
скриптом, а не переписаны на глаз.

## 0. Как воспроизвести

Лестницы живые (меняют состояние ИБ), поэтому идут на отдельной временной ИБ: `probe/modifier_effect.py`
отказывается принимать ИБ гейта (ключ `ib` из `local.paths.json`) и требует `--allow-mutating`.

```
# если временной ИБ ещё нет — создать шагом create (тот же контур, что у гейта)
python scripts/ib_loop.py create --bin "<bin>" --ib "<полигон>\probe_ib"

python probe/modifier_effect.py --ladder predefined --ib "<полигон>\probe_ib" \
    --dump-root "<полигон>\probe_effect_full\predefined" --fresh-ib --allow-mutating \
    --json reports/effect-16-predefined-full.json
# те же семь флагов для --ladder extensions / loadopts / update / modes

# `repeat` и `loadopts-shared` идут на уже загруженной ИБ: без --fresh-ib
python probe/modifier_effect.py --ladder repeat --ib "<полигон>\probe_ib" \
    --dump-root "<полигон>\probe_effect_full\repeat" --allow-mutating \
    --json reports/effect-16-repeat-full.json
```

Хвосты шагов берутся из `scripts/exec_probe.py:VARIANT_TAIL` (строки 376–422) дословно. Формы
«модификатор ПЕРЕД `/LoadConfigFromFiles`» в лестницу сознательно не вводились: лестница меняет ровно
один токен формы команды, а две позиции — это уже два токена. Для позиции сделан отдельный рукописный
контроль (§11).

Зачем `--fresh-ib`: первый прогон (`reports/effect-16-predefined.json`, без этого режима) показал шаги по
1.0 с вместо эталонных 2.0 с, шесть совпадающих выгрузок и неизменённый `PredefinedDataUpdate`. На уже
загруженной ИБ «никаких изменений» неотличимо от «загрузка не делалась», поэтому каждый шаг начинается с
пустой ИБ, а контроль «без изменений» перенесён в прогоны `repeat` и `loadopts-shared`.

Ни одной таблицы в этом файле не набрано от руки: `python probe/render_effect_tables.py` собирает их из
`reports/effect-16-*.json` и пишет фрагментами, помеченными `<!--TABLE имя-->` / `<!--OUT имя-->`; в текст
документа они подставлены по этим маркерам (`--inject <документ>`). Проверка
`python probe/render_effect_tables.py --check` перечитывает отчёты и сверяет, что каждая строка
сгенерированной таблицы дословно стоит в документе: 143 строки семнадцати фрагментов, расхождений нет. Это
защита от самого частого способа испортить доказательство — переписать число вручную. Фрагмент
`OUT loadopts-shared` генерируется, но в документе не используется: у того отчёта нет счётчиков строк
вывода (`out_line_stats` появился позже него), поэтому его вывод там приведён в байтах.

## 1. Объём замеров

| прогон | шагов лестницы | загрузок (с восстановлением) | `CREATEINFOBASE` | выгрузок | свежая ИБ на шаг |
|---|---|---|---|---|---|
| predefined | 7 | 8 | 8 | 24 | да |
| extensions | 9 | 10 | 10 | 30 | да |
| loadopts | 9 | 10 | 10 | 30 | да |
| update | 6 | 7 | 7 | 21 | да |
| modes | 2 | 3 | 3 | 9 | да |
| repeat | 3 | 4 | 0 | 12 | нет |
| loadopts-shared | 9 | 10 | 0 | 30 | нет |
| **шесть `-full`** | 36 | 42 | 38 | 126 | да (кроме `repeat`) |
| **все семь прогонов** | 45 | 52 | 38 | 156 | — |

На каждый шаг приходится три выгрузки: `NN_<variant>_before`, `NN_<variant>`, `NN_<variant>_after2`.
Отсюда `dump_codes` = 3 × (шаги + восстановление). Шаг восстановления — полный
`/LoadConfigFromFiles <каталог конфигурации>`, он же служит точкой сравнения раскладки с исходником.

## 2. Как читать таблицы

- `было → стало` — файлы и байты выгрузки состояния ИБ до шага и после него. `3ф/11873Б` — ИБ без
  конфигурации (в выгрузке только `Configuration.xml`, `ConfigDumpInfo.xml`, `Languages/Русский.xml`);
  `32ф/140181Б` — полная раскладка нашей конфигурации (31 объект + 1 язык).
- `uuid = исходник?` — совпадает ли идентификатор конфигурации в выгрузке с идентификатором исходника
  `6b1e3a24-1c77-4c0a-90d1-0a2f4c6e8001`. Проверено как двусвязность: совпадение ⇔ полная раскладка
  (ожидание `full-load-keeps-source-uuid`, сбылось во всех семи прогонах, 52 доказательства).
- `что изменилось` — ключи `changed_by_step` из `ConfigDumpInfo.xml`. `config_versions (29)` означает,
  что платформа переписала 29 атрибутов `configVersion` (каждая пара «старое → новое» различается).
- `/Out` вида «3 Б / 0 стр.» — файл вывода содержит только UTF-8 BOM, содержимого нет. В рукописных
  контролях тот же пустой вывод встречается как 0 Б. «Пустой вывод» не является признаком ни успеха, ни
  отказа.
- `сек` — время прогона шага: 48 шагов идут по 2.0 с, 2 шага по 3.0 с (`load-ok` в лестнице `loadopts`
  и шаг восстановления в лестнице `update`), 2 шага по 4.0 с (оба `-AllExtensions`).

## 3. `/SetPredefinedDataUpdate`: загрузку отменяет позиция модификатора, а не его значение

| # | вариант | хвост команды | код | сек | `/Out` | было → стало | uuid = исходник? | что изменилось |
|---|---|---|---|---|---|---|---|---|
| 0 | load-ok | `/LoadConfigFromFiles` <каталог конфигурации> | 0 | 2.0 | 3 Б / 0 стр. | 3ф/11873Б → 32ф/140181Б | да | bytes, config_uuid, counts, files, predefined_data, predefined_settings, config_versions (29) |
| 1 | load-predefined-equals-dontupdate | `/LoadConfigFromFiles` <каталог конфигурации> `/SetPredefinedDataUpdate=DontAutoUpdate` | 0 | 2.0 | 3 Б / 0 стр. | 3ф/11873Б → 3ф/11873Б | нет | config_uuid |
| 2 | load-predefined-flag | `/LoadConfigFromFiles` <каталог конфигурации> `/SetPredefinedDataUpdate` | 0 | 2.0 | 3 Б / 0 стр. | 3ф/11873Б → 3ф/11873Б | нет | config_uuid |
| 3 | load-predefined-auto | `/LoadConfigFromFiles` <каталог конфигурации> `/SetPredefinedDataUpdate` `Auto` | 0 | 2.0 | 3 Б / 0 стр. | 3ф/11873Б → 3ф/11873Б | нет | config_uuid |
| 4 | load-predefined-autoupdate | `/LoadConfigFromFiles` <каталог конфигурации> `/SetPredefinedDataUpdate` `AutoUpdate` | 0 | 2.0 | 3 Б / 0 стр. | 3ф/11873Б → 3ф/11873Б | нет | config_uuid |
| 5 | load-predefined-dontupdate | `/LoadConfigFromFiles` <каталог конфигурации> `/SetPredefinedDataUpdate` `DontAutoUpdate` | 0 | 2.0 | 3 Б / 0 стр. | 3ф/11873Б → 3ф/11873Б | нет | config_uuid |
| 6 | load-predefined-bogus-value | `/LoadConfigFromFiles` <каталог конфигурации> `/SetPredefinedDataUpdate` `ZzzNetakogoZnacheniyaNet` | 0 | 2.0 | 3 Б / 0 стр. | 3ф/11873Б → 3ф/11873Б | нет | config_uuid |
| 7 | **восстановление** | `/LoadConfigFromFiles` <каталог конфигурации> | 0 | 2.0 | 3 Б / 0 стр. | 3ф/11873Б → 32ф/140181Б | да | bytes, config_uuid, counts, files, predefined_data, predefined_settings, config_versions (29) |

Выводы по шести формам одной и той же опции:

1. Ни один шаг с модификатором конфигурацию не загрузил: выгрузка осталась `3ф/11873Б`, `predefined_settings`
   и `predefined_data` пустые, из `ConfigDumpInfo.xml` изменён только `config_uuid`.
2. Код возврата при этом 0. Код платформы не отвечает за факт загрузки — он отвечает за дисциплину
   запуска.
3. Значение не влияет: `Auto`, `AutoUpdate`, `DontAutoUpdate`, слитная форма `/SetPredefinedDataUpdate=DontAutoUpdate`
   и заведомо постороннее `ZzzNetakogoZnacheniyaNet` дают один и тот же исход.
4. Единственная отличительная черта этих шести шагов — позиция: модификатор стоит ПОСЛЕ
   `/LoadConfigFromFiles <каталог конфигурации>`. Сравнение с формами «ПЕРЕД» — в §11.
5. `config_uuid` в `changed_by_step` у этих шагов — не следствие шага: его двигает сама выгрузка
   ИБ без конфигурации (§10). У шагов `load-ok` и восстановления к нему добавляются `files`, `counts`,
   `bytes`, `predefined_data`, `predefined_settings` и 29 `config_versions` — вот что выглядит как
   состоявшаяся загрузка.

## 4. Расширения: `-Extension`, `-AllExtensions`, `-RebuildConfigurationExtensions`

| # | вариант | хвост команды | код | сек | `/Out` | было → стало | uuid = исходник? | что изменилось |
|---|---|---|---|---|---|---|---|---|
| 0 | load-ok | `/LoadConfigFromFiles` <каталог конфигурации> | 0 | 2.0 | 3 Б / 0 стр. | 3ф/11873Б → 32ф/140181Б | да | bytes, config_uuid, counts, files, predefined_data, predefined_settings, config_versions (29) |
| 1 | load-extension-flag | `/LoadConfigFromFiles` <каталог конфигурации> `-Extension` | 1 | 2.0 | 53 Б / 1 стр. | 3ф/11873Б → 3ф/11873Б | нет | config_uuid |
| 2 | load-extension-bogus-name | `/LoadConfigFromFiles` <каталог конфигурации> `-Extension` `ZzzNetakogoRasshireniyaNet` | 1 | 2.0 | 140 Б / 1 стр. | 3ф/11873Б → 3ф/11873Б | нет | config_uuid |
| 3 | load-extension-cfgdir | `/LoadConfigFromFiles` <каталог конфигурации> `-Extension` <каталог конфигурации> | 1 | 2.0 | 71 Б / 1 стр. | 3ф/11873Б → 3ф/11873Б | нет | config_uuid |
| 4 | load-extension-baddir | `/LoadConfigFromFiles` <каталог конфигурации> `-Extension` <нет такого каталога> | 1 | 2.0 | 71 Б / 1 стр. | 3ф/11873Б → 3ф/11873Б | нет | config_uuid |
| 5 | load-allextensions-baddir | `/LoadConfigFromFiles` <каталог конфигурации> `-AllExtensions` <нет такого каталога> | 1 | 4.0 | 4463 Б / 24 стр. | 3ф/11873Б → 3ф/11873Б | нет | config_uuid |
| 6 | load-allextensions-flag | `/LoadConfigFromFiles` <каталог конфигурации> `-AllExtensions` | 1 | 4.0 | 4463 Б / 24 стр. | 3ф/11873Б → 3ф/11873Б | нет | config_uuid |
| 7 | load-rebuild-extensions | `/LoadConfigFromFiles` <каталог конфигурации> `-RebuildConfigurationExtensions` | 0 | 2.0 | 3 Б / 0 стр. | 3ф/11873Б → 32ф/140181Б | да | bytes, config_uuid, counts, files, predefined_data, predefined_settings, config_versions (29) |
| 8 | load-check-can-apply | `/LoadConfigFromFiles` <каталог конфигурации> `/CheckCanApplyConfigurationExtensions` | 0 | 2.0 | 3 Б / 0 стр. | 3ф/11873Б → 3ф/11873Б | нет | config_uuid |
| 9 | **восстановление** | `/LoadConfigFromFiles` <каталог конфигурации> | 0 | 2.0 | 3 Б / 0 стр. | 3ф/11873Б → 32ф/140181Б | да | bytes, config_uuid, counts, files, predefined_data, predefined_settings, config_versions (29) |

| # | вариант | строки `/Out` дословно |
|---|---|---|
| 1 | load-extension-flag | Не указано имя расширения. |
| 2 | load-extension-bogus-name | Загрузка не должна менять принадлежность основного объекта конфигурации |
| 3 | load-extension-cfgdir | Расширение конфигурации не найдено. |
| 4 | load-extension-baddir | Расширение конфигурации не найдено. |
| 5 | load-allextensions-baddir | Файл объекта не существует - C:/Users/goof0/Documents/REA/Platform1C/effektivnost-otdela/cfg/ЭффективностьОтдела/AccumulationRegisters/Configuration.xml <br> Файл объекта не существует - C:/Users/goof0/Documents/REA/Platform1C/effektivnost-otdela/cfg/ЭффективностьОтдела/Catalogs/Configuration.xml <br> Файл объекта не существует - C:/Users/goof0/Documents/REA/Platform1C/effektivnost-otdela/cfg/ЭффективностьОтдела/CommonModules/Configuration.xml <br> Файл объекта не существует - C:/Users/goof0/Documents/REA/Platform1C/effektivnost-otdela/cfg/ЭффективностьОтдела/Constants/Configuration.xml <br> Файл объекта не существует - C:/Users/goof0/Documents/REA/Platform1C/effektivnost-otdela/cfg/ЭффективностьОтдела/DataProcessors/Configuration.xml <br> Файл объекта не существует - C:/Users/goof0/Documents/REA/Platform1C/effektivnost-otdela/cfg/ЭффективностьОтдела/Documents/Configuration.xml <br> Файл … _(всего строк 24, неповторяющихся 12)_ |
| 6 | load-allextensions-flag | Файл объекта не существует - C:/Users/goof0/Documents/REA/Platform1C/effektivnost-otdela/cfg/ЭффективностьОтдела/AccumulationRegisters/Configuration.xml <br> Файл объекта не существует - C:/Users/goof0/Documents/REA/Platform1C/effektivnost-otdela/cfg/ЭффективностьОтдела/Catalogs/Configuration.xml <br> Файл объекта не существует - C:/Users/goof0/Documents/REA/Platform1C/effektivnost-otdela/cfg/ЭффективностьОтдела/CommonModules/Configuration.xml <br> Файл объекта не существует - C:/Users/goof0/Documents/REA/Platform1C/effektivnost-otdela/cfg/ЭффективностьОтдела/Constants/Configuration.xml <br> Файл объекта не существует - C:/Users/goof0/Documents/REA/Platform1C/effektivnost-otdela/cfg/ЭффективностьОтдела/DataProcessors/Configuration.xml <br> Файл объекта не существует - C:/Users/goof0/Documents/REA/Platform1C/effektivnost-otdela/cfg/ЭффективностьОтдела/Documents/Configuration.xml <br> Файл … _(всего строк 24, неповторяющихся 12)_ |

Выводы:

- `-Extension` без значения — отказ «Не указано имя расширения.» (53 Б, код 1).
- `-Extension <имя>`, где расширения нет, — «Расширение конфигурации не найдено.» (71 Б) и на имени
  каталога конфигурации, и на отсутствующем каталоге: сообщение не различает «такого каталога нет» и
  «расширения нет».
- `-Extension ZzzNetakogoRasshireniyaNet` даёт другое сообщение — «Загрузка не должна менять принадлежность
  основного объекта конфигурации» (140 Б). Платформа успевает усомниться в принадлежности раньше, чем
  сообщить об отсутствии расширения: форма отказа зависит от того, похож ли токен на путь.
- `-AllExtensions` даёт идентичный исход независимо от того, дописан ли после него лишний позиционный
  аргумент (имя несуществующего каталога): код 1, 4.0 с (ровно вдвое дольше остальных шагов), 4463 Б,
  24 строки вывода при 12 неповторяющихся — каждая строка продублирована ровно дважды.
- Названные каталоги в этих 12 строках — ровно каталоги объектных видов нашего исходника
  (`AccumulationRegisters`, `Catalogs`, `CommonModules`, `Constants`, `DataProcessors`, `Documents`, `Enums`,
  `InformationRegisters`, `Languages`, `Reports`, `Roles`, `Subsystems`), и путь в сообщении записан через `/`.
  То есть `-AllExtensions` перебирает подкаталоги каталога загрузки и ищет в каждом `Configuration.xml` —
  ровно так, как описано в каноническом комментарии корпусов (`docs/evidence/cli-canonical-usage.md`, §2).
- `-RebuildConfigurationExtensions` (в замере 426 имён это имя только с дефисом) — код 0 и полная загрузка
  (`32ф/140181Б`, uuid исходника).
- `/CheckCanApplyConfigurationExtensions` — код 0, `/Out` пустой, выгрузка `3ф/11873Б`: загрузка НЕ
  состоялась. Ещё один случай, когда код 0 не означает загрузки.

## 5. Опции частичной загрузки: `-files`, `-listFile`, `-Format` на пустой ИБ

| # | вариант | хвост команды | код | сек | `/Out` | было → стало | uuid = исходник? | что изменилось |
|---|---|---|---|---|---|---|---|---|
| 0 | load-ok | `/LoadConfigFromFiles` <каталог конфигурации> | 0 | 3.0 | 3 Б / 0 стр. | 3ф/11873Б → 32ф/140181Б | да | bytes, config_uuid, counts, files, predefined_data, predefined_settings, config_versions (29) |
| 1 | load-files-flag | `/LoadConfigFromFiles` <каталог конфигурации> `-files` | 0 | 2.0 | 3 Б / 0 стр. | 3ф/11873Б → 32ф/140181Б | да | bytes, config_uuid, counts, files, predefined_data, predefined_settings, config_versions (29) |
| 2 | load-files-onefile | `/LoadConfigFromFiles` <каталог конфигурации> `-files` `Configuration.xml` | 1 | 2.0 | 337 Б / 1 стр. | 3ф/11873Б → 3ф/11873Б | нет | config_uuid |
| 3 | load-listfile-onefile | `/LoadConfigFromFiles` <каталог конфигурации> `-listFile` `Configuration.xml` | 1 | 2.0 | 90 Б / 1 стр. | 3ф/11873Б → 3ф/11873Б | нет | config_uuid |
| 4 | load-listfile-ok | `/LoadConfigFromFiles` <каталог конфигурации> `-listFile` <файл-список> | 1 | 2.0 | 337 Б / 1 стр. | 3ф/11873Б → 3ф/11873Б | нет | config_uuid |
| 5 | load-format-flag | `/LoadConfigFromFiles` <каталог конфигурации> `-listFile` <файл-список> `-Format` | 1 | 2.0 | 337 Б / 1 стр. | 3ф/11873Б → 3ф/11873Б | нет | config_uuid |
| 6 | load-format-hierarchical | `/LoadConfigFromFiles` <каталог конфигурации> `-listFile` <файл-список> `-Format` `Hierarchical` | 1 | 2.0 | 337 Б / 1 стр. | 3ф/11873Б → 3ф/11873Б | нет | config_uuid |
| 7 | load-format-plain | `/LoadConfigFromFiles` <каталог конфигурации> `-listFile` <файл-список> `-Format` `Plain` | 1 | 2.0 | 337 Б / 1 стр. | 3ф/11873Б → 3ф/11873Б | нет | config_uuid |
| 8 | load-format-bogus | `/LoadConfigFromFiles` <каталог конфигурации> `-listFile` <файл-список> `-Format` `ZzzNetakogoZnacheniyaNet` | 1 | 2.0 | 337 Б / 1 стр. | 3ф/11873Б → 3ф/11873Б | нет | config_uuid |
| 9 | **восстановление** | `/LoadConfigFromFiles` <каталог конфигурации> | 0 | 2.0 | 3 Б / 0 стр. | 3ф/11873Б → 32ф/140181Б | да | bytes, config_uuid, counts, files, predefined_data, predefined_settings, config_versions (29) |

| # | вариант | строки `/Out` дословно |
|---|---|---|
| 2 | load-files-onefile | Файл - Configuration.xml: ошибка частичной загрузки - идентификатор 6b1e3a24-1c77-4c0a-90d1-0a2f4c6e8001 загружаемой конфигурации отличается от идентификатора cbb4c193-9f36-46f5-9447-4ce8fc13da63 сохраненной конфигурации |
| 3 | load-listfile-onefile | Ошибка чтения файла-списка загружаемых файлов |
| 4 | load-listfile-ok | Файл - Configuration.xml: ошибка частичной загрузки - идентификатор 6b1e3a24-1c77-4c0a-90d1-0a2f4c6e8001 загружаемой конфигурации отличается от идентификатора 5fe7800c-e501-43f8-830a-db1cf1eaaa97 сохраненной конфигурации |
| 5 | load-format-flag | Файл - Configuration.xml: ошибка частичной загрузки - идентификатор 6b1e3a24-1c77-4c0a-90d1-0a2f4c6e8001 загружаемой конфигурации отличается от идентификатора 4ff97a5c-bd8e-4873-b355-e32015968b0b сохраненной конфигурации |
| 6 | load-format-hierarchical | Файл - Configuration.xml: ошибка частичной загрузки - идентификатор 6b1e3a24-1c77-4c0a-90d1-0a2f4c6e8001 загружаемой конфигурации отличается от идентификатора aa1082c1-8e9a-49a1-af82-3bf843f3c77a сохраненной конфигурации |
| 7 | load-format-plain | Файл - Configuration.xml: ошибка частичной загрузки - идентификатор 6b1e3a24-1c77-4c0a-90d1-0a2f4c6e8001 загружаемой конфигурации отличается от идентификатора 78bad3a6-d19f-4ea4-86ed-102e7ee01052 сохраненной конфигурации |
| 8 | load-format-bogus | Файл - Configuration.xml: ошибка частичной загрузки - идентификатор 6b1e3a24-1c77-4c0a-90d1-0a2f4c6e8001 загружаемой конфигурации отличается от идентификатора 86a75318-c651-4259-875b-9bce000b4557 сохраненной конфигурации |

Выводы:

- `-files` без значения загрузку не ограничивает: полная раскладка `32ф/140181Б`. Опция работает как
  «список файлов», только когда значение дано.
- `-files Configuration.xml` на ИБ без конфигурации — отказ с сообщением об ошибке частичной загрузки
  (337 Б, §7).
- `-listFile Configuration.xml` (XML-файл вместо файла-списка) — отдельный отказ «Ошибка чтения
  файла-списка загружаемых файлов» (90 Б). Файл-список читается как список, а не как объект конфигурации.
- Файл-список из 17 абсолютных путей (2629 Б, UTF-8, переводы `\r\n`) принят как список, но загрузка
  отвергнута тем же сообщением о частичной загрузке. На пустой ИБ частичная загрузка невозможна:
  сравнивать идентификатор загружаемой конфигурации не с чем.
- `-Format` без значения, `Hierarchical`, `Plain` и постороннее значение на пустой ИБ дают одно и то же
  сообщение: до разбора формата дело не доходит. Различие форматов видно только на загруженной ИБ (§6).
- Имя опции в лестнице — `-listFile` (так она написана в замере 426 имён платформы,
  `docs/evidence/cli-flag-names.md`); живые конфигурации пишут `-listfile`. Регистр не измерен: см. §16.

## 6. Те же опции на уже загруженной ИБ

| # | вариант | хвост команды | код | сек | `/Out` | было → стало | uuid = исходник? | что изменилось |
|---|---|---|---|---|---|---|---|---|
| 0 | load-ok | `/LoadConfigFromFiles` <каталог конфигурации> | 0 | 2.0 | 3 Б / — стр. | 32ф/140181Б → 32ф/140181Б | да | config_versions (29) |
| 1 | load-files-flag | `/LoadConfigFromFiles` <каталог конфигурации> `-files` | 0 | 2.0 | 3 Б / — стр. | 32ф/140181Б → 32ф/140181Б | да | config_versions (29) |
| 2 | load-files-onefile | `/LoadConfigFromFiles` <каталог конфигурации> `-files` `Configuration.xml` | 0 | 2.0 | 3 Б / — стр. | 32ф/140181Б → 32ф/140181Б | да | config_versions (29) |
| 3 | load-listfile-onefile | `/LoadConfigFromFiles` <каталог конфигурации> `-listFile` `Configuration.xml` | 1 | 2.0 | 90 Б / — стр. | 32ф/140181Б → 32ф/140181Б | да | — |
| 4 | load-listfile-ok | `/LoadConfigFromFiles` <каталог конфигурации> `-listFile` <файл-список> | 0 | 2.0 | 3 Б / — стр. | 32ф/140181Б → 32ф/140181Б | да | config_versions (29) |
| 5 | load-format-flag | `/LoadConfigFromFiles` <каталог конфигурации> `-listFile` <файл-список> `-Format` | 0 | 2.0 | 3 Б / — стр. | 32ф/140181Б → 32ф/140181Б | да | config_versions (29) |
| 6 | load-format-hierarchical | `/LoadConfigFromFiles` <каталог конфигурации> `-listFile` <файл-список> `-Format` `Hierarchical` | 0 | 2.0 | 3 Б / — стр. | 32ф/140181Б → 32ф/140181Б | да | config_versions (29) |
| 7 | load-format-plain | `/LoadConfigFromFiles` <каталог конфигурации> `-listFile` <файл-список> `-Format` `Plain` | 1 | 2.0 | 275 Б / — стр. | 32ф/140181Б → 32ф/140181Б | да | — |
| 8 | load-format-bogus | `/LoadConfigFromFiles` <каталог конфигурации> `-listFile` <файл-список> `-Format` `ZzzNetakogoZnacheniyaNet` | 0 | 2.0 | 3 Б / — стр. | 32ф/140181Б → 32ф/140181Б | да | config_versions (29) |
| 9 | **восстановление** | `/LoadConfigFromFiles` <каталог конфигурации> | 0 | 2.0 | 3 Б / — стр. | 32ф/140181Б → 32ф/140181Б | да | config_versions (29) |

Выводы (в этом отчёте ключей `out_lines_total`/`out_lines_unique` нет — он собран до появления честных
счётчиков строк, поэтому длина вывода указана только в байтах):

- Всё, кроме `-listFile Configuration.xml` и `-Format Plain`, даёт код 0 и 29 переписанных
  `config_versions`: загрузка состоялась, хотя раскладка не изменилась (`32ф/140181Б`).
- Частичная загрузка на загруженной ИБ проходит молча: и `-files Configuration.xml`, и файл-список из 17
  путей, и `-Format` без значения, и `Hierarchical`, и постороннее значение. Никакого предупреждения о том,
  что загружены не все файлы, в `/Out` нет.
- `-Format Plain` — единственный формат, который откликнулся содержательно: код 1, 275 Б,
  «URL …/AccumulationRegisters/ЗатратыВремени.xml не может быть преобразован в полное имя объекта
  метаданных». `Plain` требует имён объектов метаданных, а файл-список построен из относительных путей
  выгрузки.
- Постороннее значение `-Format` принято без единой строки (`ZzzNetakogoZnacheniyaNet` → код 0, загрузка).
  Значения этой опции платформа не проверяет.
- Отрицательные шаги (`-listFile Configuration.xml`, `-Format Plain`) не имеют ни одной записи
  `config_versions`: отличие «загрузка была / не была» читается по `changed_by_step`, а не по коду.

## 7. Идентификаторы в сообщении о частичной загрузке: третья величина

| # | вариант | первый названный | второй названный | uuid ИБ **до** шага | uuid ИБ **после** шага | первый = uuid исходника? | второй = до? | второй = после? |
|---|---|---|---|---|---|---|---|---|
| 2 | load-files-onefile | `6b1e3a24-1c77…` | `cbb4c193-9f36…` | `9a51d3ae-f393…` | `e6ec5263-fbe3…` | да | **нет** | **нет** |
| 4 | load-listfile-ok | `6b1e3a24-1c77…` | `5fe7800c-e501…` | `5533458c-4487…` | `31920808-10b9…` | да | **нет** | **нет** |
| 5 | load-format-flag | `6b1e3a24-1c77…` | `4ff97a5c-bd8e…` | `180ce5be-087e…` | `0e9d63c4-82fb…` | да | **нет** | **нет** |
| 6 | load-format-hierarchical | `6b1e3a24-1c77…` | `aa1082c1-8e9a…` | `e3868841-45b2…` | `6dc291e6-298d…` | да | **нет** | **нет** |
| 7 | load-format-plain | `6b1e3a24-1c77…` | `78bad3a6-d19f…` | `84326fb6-bb48…` | `b6f63c73-8ff2…` | да | **нет** | **нет** |
| 8 | load-format-bogus | `6b1e3a24-1c77…` | `86a75318-c651…` | `031fadf2-b1d3…` | `d80551e5-2a4c…` | да | **нет** | **нет** |

Сообщение называет два идентификатора: загружаемой конфигурации и сохранённой конфигурации. Первый —
идентификатор исходника (`6b1e3a24-…`). Второй не совпадает ни с идентификатором ИБ, измеренным выгрузкой
ДО шага, ни с идентификатором ПОСЛЕ шага: это третья величина, которая больше нигде в замерах не
встречается. Ожидание `partial-second-identifier-is-ib-uuid-before-step`, записанное до прогона,
**опровергнуто** на шести шагах лестницы `loadopts`.

Следствие: по этому сообщению нельзя понять, какое состояние ИБ платформа сочла «сохранённым». Оно годится
только как признак отказа, но не как объяснение отказа.

## 8. `/UpdateCfg`, `/UpdateDBCfg`, режимы CONFIG/DESIGNER, повторные загрузки

| # | вариант | хвост команды | код | сек | `/Out` | было → стало | uuid = исходник? | что изменилось |
|---|---|---|---|---|---|---|---|---|
| 0 | load-ok | `/LoadConfigFromFiles` <каталог конфигурации> | 0 | 2.0 | 3 Б / 0 стр. | 3ф/11873Б → 32ф/140181Б | да | bytes, config_uuid, counts, files, predefined_data, predefined_settings, config_versions (29) |
| 1 | load-noarg | `/LoadConfigFromFiles` | 1 | 2.0 | 40 Б / 1 стр. | 3ф/11873Б → 3ф/11873Б | нет | config_uuid |
| 2 | update-cfg-noarg | `/UpdateCfg` | 1 | 2.0 | 75 Б / 1 стр. | 3ф/11873Б → 3ф/11873Б | нет | config_uuid |
| 3 | update-dbcfg | `/UpdateDBCfg` | 0 | 2.0 | 3 Б / 0 стр. | 3ф/11873Б → 3ф/11873Б | нет | config_uuid |
| 4 | update-dbcfg-server | `/UpdateDBCfg` `-Server` | 0 | 2.0 | 3 Б / 0 стр. | 3ф/11873Б → 3ф/11873Б | нет | config_uuid |
| 5 | config-update-dbcfg-server | `/UpdateDBCfg` `-Server` | 0 | 2.0 | 3 Б / 0 стр. | 3ф/11873Б → 3ф/11873Б | нет | config_uuid |
| 6 | **восстановление** | `/LoadConfigFromFiles` <каталог конфигурации> | 0 | 3.0 | 3 Б / 0 стр. | 3ф/11873Б → 32ф/140181Б | да | bytes, config_uuid, counts, files, predefined_data, predefined_settings, config_versions (29) |

| # | вариант | строки `/Out` дословно |
|---|---|---|
| 1 | load-noarg | Файл не обнаружен '' |
| 2 | update-cfg-noarg | Файл не содержит доступных обновлений |

| # | вариант | хвост команды | код | сек | `/Out` | было → стало | uuid = исходник? | что изменилось |
|---|---|---|---|---|---|---|---|---|
| 0 | load-ok | `/LoadConfigFromFiles` <каталог конфигурации> | 0 | 2.0 | 3 Б / 0 стр. | 3ф/11873Б → 32ф/140181Б | да | bytes, config_uuid, counts, files, predefined_data, predefined_settings, config_versions (29) |
| 1 | config-load-ok | `/LoadConfigFromFiles` <каталог конфигурации> | 0 | 2.0 | 3 Б / 0 стр. | 3ф/11873Б → 32ф/140181Б | да | bytes, config_uuid, counts, files, predefined_data, predefined_settings, config_versions (29) |
| 2 | **восстановление** | `/LoadConfigFromFiles` <каталог конфигурации> | 0 | 2.0 | 3 Б / 0 стр. | 3ф/11873Б → 32ф/140181Б | да | bytes, config_uuid, counts, files, predefined_data, predefined_settings, config_versions (29) |

| # | вариант | хвост команды | код | сек | `/Out` | было → стало | uuid = исходник? | что изменилось |
|---|---|---|---|---|---|---|---|---|
| 0 | load-ok | `/LoadConfigFromFiles` <каталог конфигурации> | 0 | 2.0 | 3 Б / 0 стр. | 32ф/140181Б → 32ф/140181Б | да | config_versions (29) |
| 1 | load-ok | `/LoadConfigFromFiles` <каталог конфигурации> | 0 | 2.0 | 3 Б / 0 стр. | 32ф/140181Б → 32ф/140181Б | да | config_versions (29) |
| 2 | load-ok | `/LoadConfigFromFiles` <каталог конфигурации> | 0 | 2.0 | 3 Б / 0 стр. | 32ф/140181Б → 32ф/140181Б | да | config_versions (29) |
| 3 | **восстановление** | `/LoadConfigFromFiles` <каталог конфигурации> | 0 | 2.0 | 3 Б / 0 стр. | 32ф/140181Б → 32ф/140181Б | да | config_versions (29) |

Выводы:

- `/LoadConfigFromFiles` без значения — отказ «Файл не обнаружен ''» (40 Б). Пустое имя пути — тоже путь.
- `/UpdateCfg` без значения — отказ «Файл не содержит доступных обновлений» (75 Б). Сообщение говорит о
  содержимом файла, хотя файла как такового нет: по тексту нельзя отличить «файла нет» от «файл пуст».
- `/UpdateDBCfg`, `/UpdateDBCfg -Server` (и в `DESIGNER`, и в `CONFIG`) — код 0, пустой `/Out`, состояние
  ИБ не изменилось (`3ф/11873Б`, только `config_uuid`). На ИБ без конфигурации «обновление структуры»
  проходит молча.
- `config-load-ok` (режим `CONFIG`) и `load-ok` (режим `DESIGNER`) дают побайтово одинаковый результат:
  2.0 с, `32ф/140181Б`, uuid исходника, 29 `config_versions`. Для загрузки конфигурации выбор режима не
  важен.
- `repeat`: три одинаковых шага на одной загруженной ИБ — каждый переписывает 29 атрибутов
  `configVersion`, при этом файлы, байты и идентификатор конфигурации неизменны. `configVersion` —
  не хеш содержимого; вывод «изменений нет» на нём основываться не может.
- `loadopts-shared` и `repeat` (оба на загруженной ИБ) подтверждают то же: единственный след успешной
  загрузки в `ConfigDumpInfo.xml` — 29 новых значений `configVersion`.

## 9. Ожидания, записанные до прогонов

| ожидание (записано до прогона) | predefined | extensions | loadopts | update | modes | repeat | loadopts-shared |
|---|---|---|---|---|---|---|---|
| `dump-keeps-uuid-of-loaded-config` | сбылось (2) | сбылось (3) | сбылось (3) | сбылось (2) | сбылось (3) | сбылось (4) | сбылось (10) |
| `dump-regenerates-uuid-of-empty-ib` | сбылось (6) | сбылось (7) | сбылось (7) | сбылось (5) | непроверяемо | непроверяемо | непроверяемо |
| `empty-ib-has-its-own-uuid` | сбылось (7) | сбылось (9) | сбылось (9) | сбылось (6) | сбылось (2) | непроверяемо | непроверяемо |
| `full-load-keeps-source-uuid` | сбылось (8) | сбылось (10) | сбылось (10) | сбылось (7) | сбылось (3) | сбылось (4) | сбылось (10) |
| `ib-uuid-survives-its-own-dump` | непроверяемо | непроверяемо | непроверяемо | непроверяемо | непроверяемо | сбылось (2) | сбылось (8) |
| `partial-second-identifier-is-ib-uuid-before-step` | непроверяемо | непроверяемо | **опровергнуто** (6) | непроверяемо | непроверяемо | непроверяемо | непроверяемо |
| `repeat-load-keeps-uuid` | непроверяемо | непроверяемо | непроверяемо | непроверяемо | непроверяемо | сбылось (2) | непроверяемо |

Разбор:

- `full-load-keeps-source-uuid` — сбылось во всех семи прогонах, 52 доказательства. Это опора для
  различения «полная загрузка» и «ИБ без конфигурации» по одному признаку.
- `dump-keeps-uuid-of-loaded-config` — сбылось во всех семи прогонах, 27 доказательств: выгрузка
  загруженной ИБ не двигает идентификатор конфигурации.
- `dump-regenerates-uuid-of-empty-ib` — сбылось на 25 парах выгрузок (predefined 6, extensions 7,
  loadopts 7, update 5): во всех парах файлы и байты совпали, а идентификатор различается.
- `empty-ib-has-its-own-uuid` — сбылось 33 раза там, где прогон создавал ИБ (predefined 7, extensions 9,
  loadopts 9, update 6, modes 2).
- `ib-uuid-survives-its-own-dump` (10 доказательств) и `repeat-load-keeps-uuid` (2) — сбылось только на
  прогонах без `--fresh-ib` (`repeat`, `loadopts-shared`); в остальных помечены `met: null` с причиной в
  `note`: в режиме свежей ИБ эти пары шагов не существуют.
- `partial-second-identifier-is-ib-uuid-before-step` — **опровергнуто**, 6 доказательств (§7).
- `dump-regenerates-uuid-of-empty-ib` и `empty-ib-has-its-own-uuid` непроверяемы в `repeat` и
  `loadopts-shared`, а `dump-regenerates-uuid-of-empty-ib` ещё и в `modes`: там нет шагов, идущих по
  пустой ИБ.

## 10. `dump_twice`: кто двигает идентификатор пустой ИБ

| прогон | шагов | файлы совпали | байты совпали | uuid совпал | uuid разошёлся |
|---|---|---|---|---|---|
| predefined | 7 | 7 | 7 | 1 | 6 |
| extensions | 9 | 9 | 9 | 2 | 7 |
| loadopts | 9 | 9 | 9 | 2 | 7 |
| update | 6 | 6 | 6 | 1 | 5 |
| modes | 2 | 2 | 2 | 2 | 0 |
| repeat | 3 | 3 | 3 | 3 | 0 |
| loadopts-shared | 9 | 9 | 9 | 9 | 0 |

Третья выгрузка идёт сразу за второй, без шага между ними, поэтому её разница с второй объясняется только
выгрузкой:

- На загруженной ИБ две выгрузки одного состояния совпадают по файлам, байтам и идентификатору конфигурации.
- На ИБ без конфигурации файлы и байты совпадают, а идентификатор различается: его пересоздаёт сама
  выгрузка. Отпечаток пустой ИБ непригоден для сверки состояний.

## 11. Позиция модификатора: три рукописных контроля вне лестницы

Контроли делались отдельно написанными скриптами на одноразовых ИБ (`…\p1c_effektivnost\ctrl_ib1…3`,
`ctrl2_ib1…5`, `ctrl3_ib1…3`), вне репозитория; их дословные тексты — `ctrl_predefined.txt`,
`ctrl_predefined2.txt`, `ctrl_predefined3.txt`. Команды повторяют форму контура гейта
(`1cv8.exe DESIGNER /F <иб> /Out <ф> /DisableStartupDialogs <команда> <хвост>`).

Контроль A — позиция модификатора на чистой ИБ (три ИБ, время шага загрузки — из тех же протоколов):

| кейс | команда загрузки | время шага | итог выгрузки |
|---|---|---|---|
| без модификатора | `/LoadConfigFromFiles <каталог>` | 2.0 с | 32ф/140181Б, имя `ЭффективностьОтдела`, предопределённые 1925 Б, sha1[:16] `2bdeb3270c72de76` |
| модификатор ПОСЛЕ команды | `/LoadConfigFromFiles <каталог> /SetPredefinedDataUpdate Auto` | 1.0 с | 3ф/11873Б, имя `Конфигурация`, предопределённых нет |
| модификатор ПЕРЕД командой | `/SetPredefinedDataUpdate Auto /LoadConfigFromFiles <каталог>` | 2.0 с | 32ф/140181Б, имя `ЭффективностьОтдела`, предопределённые 1925 Б, sha1[:16] `2bdeb3270c72de76` |

Тот же признак виден во времени шага: загрузка без модификатора и загрузка с модификатором ПЕРЕД команды
идут 2.0 с, шаг с модификатором ПОСЛЕ команды — 1.0 с. Ни код (0 во всех трёх случаях), ни `/Out`
(3 Б, то есть пустой, во всех трёх) различия не показывают.

Контроль B — пять форм «ПЕРЕД команды» (пять ИБ; исходник: 31 файл / 119519 Б,
uuid `6b1e3a24-1c77-4c0a-90d1-0a2f4c6e8001`, `PredefinedDataUpdate = Auto`):

| кейс | хвост ПЕРЕД командой | загрузка | uuid выгрузки | `PredefinedDataUpdate` в выгрузке |
|---|---|---|---|---|
| 1 | `/SetPredefinedDataUpdate DontAutoUpdate` | да (32ф/140181Б) | uuid исходника | `Auto` |
| 2 | `/SetPredefinedDataUpdate=DontAutoUpdate` | да (32ф/140181Б) | uuid исходника | `Auto` |
| 3 | `/SetPredefinedDataUpdate ZzzNetakogoZnacheniyaNet` | да (32ф/140181Б) | uuid исходника | `Auto` |
| 4 | `/SetPredefinedDataUpdate` (без значения) | **нет** (3ф/11873Б) | `fea7344b-deab-444d-87dd-f96098c2db4f` | тега нет вовсе |
| 5 | обычный `load`, затем повторный шаг с `/SetPredefinedDataUpdate DontAutoUpdate` | да (32ф/140181Б) | uuid исходника | `Auto` |

Контроль C — что управляется исходником, а что опцией платформы (временная копия исходника с
`<PredefinedDataUpdate>DontAutoUpdate</PredefinedDataUpdate>`, побайтовая замена, BOM и CRLF сохранены;
копия `…\p1c_effektivnost\ctrl3_cfg_dontautoupdate`):

| кейс | команда загрузки | выгрузка | `PredefinedDataUpdate` в выгрузке |
|---|---|---|---|
| копия `DontAutoUpdate`, без модификатора | `/LoadConfigFromFiles <копия>` | 32ф/140191Б | `DontAutoUpdate` |
| копия `DontAutoUpdate`, `/SetPredefinedDataUpdate Auto` ПЕРЕД загрузкой | `/SetPredefinedDataUpdate Auto /LoadConfigFromFiles <копия>` | 32ф/140191Б | `DontAutoUpdate` |
| копия `DontAutoUpdate`, посторонний голый токен `plain` перед загрузкой | `plain /LoadConfigFromFiles <копия>` | 32ф/140191Б | `DontAutoUpdate` |

Выводы:

1. Загрузку отменяет **позиция** модификатора (после команды загрузки), а не его значение — контроль A
   против §3.
2. Модификатор без значения поглощает следующий токен как своё значение: в кейсе 4 контроля B съеден сам
   `/LoadConfigFromFiles`, и загрузочной команды не осталось (выгрузка — пустая ИБ со своим uuid).
3. Опция платформы `/SetPredefinedDataUpdate` НЕ переопределяет атрибут `PredefinedDataUpdate`
   конфигурации: в выгрузке остаётся то, что написано в исходнике (контроль B — `Auto`, контроль C —
   `DontAutoUpdate`), независимо от значения опции.
4. Голый посторонний токен в начале строки платформы молча проглатывает: загрузка состоялась, `/Out` 0 Б.
   Отсутствие сообщения — не подтверждение того, что argv разобран правильно.
5. Разница `140181 Б` против `140191 Б` — только более длинный токен атриута в XML
   (`Auto` → `DontAutoUpdate`), то есть +10 Б предсказуемо; побайтово расходятся только байты этого тега.

## 12. Побайтовая сверка предопределённых данных (что именно показывает дамп)

| файл | байт | CRLF | sha1[:16] | элементов |
|---|---|---|---|---|
| `cfg/ЭффективностьОтдела/Catalogs/Сотрудники/Ext/Predefined.xml` (источник) | 1927 | 43 | `8cfdc0bb0bc67371` | 6 |
| `…/dump_gate11_backup` и выгрузки лестниц (`Catalogs/Сотрудники/Ext/Predefined.xml`) | 1925 | 42 | `2bdeb3270c72de76` | 6 |

Первое расхождение байтов отсутствует: расходятся только завершающий перевод строки источника. Строки
43 против 43, и как строки, и как мультимножества они равны, поэтому `gate.file_diff` относит файл к
классу `same` (в `reports/gate-12.json` он стоит в ключе `diff_files.same`).

Важная граница замера: дамп конфигурации показывает **описание** предопределённых данных, а не строки ИБ.
Файл `Ext/Predefined.xml` идентичен во всех случаях — 1925 Б, 6 элементов, sha1[:16] `2bdeb3270c72de76` —
и при `Auto`, и при `DontAutoUpdate`, и при `/SetPredefinedDataUpdate` любой формы. Способа прочитать
строки БД из командной строки не измерено (§16), поэтому влияние `PredefinedDataUpdate` на сами строки
предопределённых данных наблюдаемо неотличимо от его отсутствия.

## 13. Что оставляет после себя лестница: сравнение восстановления с исходником

| прогон | код | same | reordered | differ | only_source | only_dump | платформа добавила |
|---|---|---|---|---|---|---|---|
| predefined | 0 | 21 | 2 | 8 | 0 | 0 | ConfigDumpInfo.xml |
| extensions | 0 | 21 | 2 | 8 | 0 | 0 | ConfigDumpInfo.xml |
| loadopts | 0 | 21 | 2 | 8 | 0 | 0 | ConfigDumpInfo.xml |
| update | 0 | 21 | 2 | 8 | 0 | 0 | ConfigDumpInfo.xml |
| modes | 0 | 21 | 2 | 8 | 0 | 0 | ConfigDumpInfo.xml |
| repeat | 0 | 21 | 2 | 8 | 0 | 0 | ConfigDumpInfo.xml |
| loadopts-shared | 0 | 21 | 2 | 8 | 0 | 0 | ConfigDumpInfo.xml |

- `Catalogs/Сотрудники.xml`
- `Catalogs/Сотрудники/Forms/ФормаЭлемента/Ext/Form.xml`
- `Configuration.xml`
- `Constants/НормаЧасовВМесяц.xml`
- `DataProcessors/ВыгрузкаЗатратCSV/Forms/ФормаВыгрузки.xml`
- `Documents/ФактРаботы.xml`
- `InformationRegisters/ПланЗагрузки.xml`
- `Subsystems/ЭффективностьОтдела.xml`

Порядок прав в двух файлах ролей платформа переставляет (`reordered` — те же строки, другой порядок;
дефектом не считается):

- `Roles/АдминистраторСистемы/Ext/Rights.xml`
- `Roles/СотрудникОтдела/Ext/Rights.xml`

Восемь файлов класса `differ` — один и тот же набор во всех семи прогонах (списки совпадают побайтово).
Разбор (unified diff и посимвольная сверка токенов) показывает, что платформа ничего не теряет: она
дописывает значения по умолчанию и переставляет блоки.

| файл | строк ист./выгр. | что дописала платформа |
|---|---|---|
| `Catalogs/Сотрудники.xml` | 290 / 366 | `LevelCount`, `Owners`, `FillFromFillingValue`, `FillValue`, `ChoiceParameterLinks`, `ChoiceParameters` (9 строк сместились, 85 добавлены) |
| `Catalogs/Сотрудники/Forms/ФормаЭлемента/Ext/Form.xml` | 138 / 139 | `UseForFoldersAndItems = Items`; события `BeforeWrite`/`AfterWrite` в обратном порядке |
| `Configuration.xml` | 94 / 269 | `AdditionalFullTextSearchDictionaries`, `CommonSettingsStorage`, `ReportsUserSettingsStorage`, `ReportsVariantsStorage`, `FormDataSettingsStorage`, `DynamicListsUserSettingsStorage`, `URLExternalDataStorage`, `DefaultReportForm`, `Picture` |
| `Constants/НормаЧасовВМесяц.xml` | 52 / 63 | `ChoiceFoldersAndItems`, `ChoiceParameterLinks`, `ChoiceParameters`, `QuickChoice`, `ChoiceForm`, `LinkByType`, `ChoiceHistoryOnInput`, `DataLockControlMode` |
| `DataProcessors/ВыгрузкаЗатратCSV/Forms/ФормаВыгрузки.xml` | 21 / 22 | `ExtendedPresentation` |
| `Documents/ФактРаботы.xml` | 158 / 211 | `Numerator`, `InputByString` + поле `StandardAttribute.Number`, `SearchStringModeOnInputByString`, `FullTextSearchOnInputByString`, `ChoiceDataGetModeOnInputByString`, `DefaultObjectForm` |
| `InformationRegisters/ПланЗагрузки.xml` | 135 / 156 | `FillFromFillingValue`, `FillValue`, `CreateOnInput` и соседние значения по умолчанию |
| `Subsystems/ЭффективностьОтдела.xml` | 29 / 32 | `UseOneCommand`, `Explanation`, `Picture` |

Посимвольная проверка токенов (счёт вхождений в исходнике и в выгрузке) подтверждает, что «удалённые»
строки — выравнивание алгоритма diff, а не потеря: `DateFractions` 6 против 6 и `DateQualifiers` 6 против 6
в `Catalogs/Сотрудники.xml`, `DataLockControlMode` 2 против 2, `InputByString` 8 против 8,
`DefaultObjectForm` 2 против 2, `Explanation` 1 против 1. Растут только счётчики тех свойств, которые
платформа дописывает: `ChoiceFoldersAndItems` 6 → 12, `CreateOnInput` 2 → 14, `FillFromFillingValue`
0 → 6, `UseForFoldersAndItems` 0 → 2.

Следствие для проверки раскладки: исходник обязан держать только те свойства, которые он осознанно
выбрал, а сравнение с выгрузкой обязано относить дописанные значения по умолчанию к отдельному классу.
Сверка «побайтово» на этих восьми файлах невозможна в принципе.

## 14. Следствие для инструментов p1c

1. **Код возврата 0 не означает загрузки.** У 25 шагов лестниц выгрузка после шага остаётся ИБ без
   конфигурации (3 файла). Из них 10 дают код 0: шесть форм `/SetPredefinedDataUpdate` после команды
   загрузки, `/CheckCanApplyConfigurationExtensions`, и три шага `/UpdateDBCfg` (без `-Server`, с `-Server`
   в `DESIGNER` и в `CONFIG`). Остальные 15 отказов отдают код 1. Отличить «загрузилось» от «прошло молча»
   по коду невозможно в принципе. Инструмент, который после `p1c.load` смотрит только на код, молчит
   ровно там, где конфигурация не загружена.
2. **Признак состоявшейся загрузки — изменённые `config_versions` (29 пар) и полная раскладка, а не код.**
   На загруженной ИБ это 29 переписанных атрибутов при неизменных файлах; на пустой ИБ — `files`/`counts`/
   `bytes`/`predefined_*` в `changed_by_step`.
3. **Частичная загрузка не предупреждает.** На загруженной ИБ `-files <один файл>` и файл-список из 17 путей
   проходят молча. Инструмент, который загружает конфигурацию «кусками» (например, только модули или
   только один регистр), не получает от платформы никакого сигнала о неполноте.
4. **`-Format Plain` — другой язык имён.** Он требует полные имена объектов метаданных
   (`Catalog.Сотрудники`), а не относительные пути выгрузки (`Catalogs/Сотрудники.xml`). Любая попытка
   загружать по списку путей с этим форматом обречена.
5. **`-AllExtensions` — единственный измеренный случай многострочного отказа** (24 строки, 12 неповторяющихся,
   4.0 с). Кто обрезает вывод до 8 строк, теряет половину отказа и видит только половину названных каталогов.
6. **Идентификатор пустой ИБ нельзя использовать как отпечаток состояния**: его пересоздаёт сама выгрузка
   (§10). `configVersion` нельзя использовать как хеш содержимого (§8).
7. **Сообщение о частичной загрузке называет третью величину**, не совпадающую ни с состоянием до шага, ни
   после него (§7). Объяснения отказа от платформы в этом сообщении нет.

## 15. Что с этим делать (пункты плана оптимизации p1c)

- `p1c.load` и любой обёрточный шаг загрузки: после загрузки читать факт — раскладку выгрузки и
  `changed_by_step` из `ConfigDumpInfo.xml`, а не код возврата; при пустой выгрузке (наш гейт уже делает
  это через `empty_dump_detected`, `scripts/gate.py:108-125`) выдавать диагностику, а не «успех».
- Контроль порядка токенов в argv до запуска: модификатор значения (`/SetPredefinedDataUpdate`,
  `-Extension`, `-Format`, `-files`) обязан стоять после команды, значение — сразу за ним; голый
  модификатор без значения — ошибка сборки команды, а не аргумент платформы.
- Сборка argv в `p1c/src/p1c/test/run.py` и `p1c/src/p1c/debug/debug.py` (битая сборка зафиксирована в
  `docs/evidence/p1c-data-defects.md`) обязана пройти проверку на измеренных именах и на этих правилах
  порядка.
- Для частичной загрузки: строить файл-список из относительных путей выгрузки и никогда не ставить
  `-Format Plain`; при `-files` перечислять файлы явно и проверять полноту раскладки после загрузки.
- Вывод `/Out` читать полным: хранить все строки и distinct-строки (наш `out_line_stats` в
  `probe/modifier_effect.py:179`), иначе многострочные отказы (`-AllExtensions`) читаются по обрезке.
- Сверку «изменений нет» строить на файлах и байтах выгрузки, а не на `configVersion`: каждое успешное
  прохождение загрузки меняет 29 значений.

## 16. Что осталось неизмеренным

1. **Регистр имени `-listFile` против канонического `-listfile`.** В замере 426 имён платформы есть
   `-listFile`; лестница использует его. Живые конфигурации пишут `-listfile`
   (`docs/evidence/cli-canonical-usage.md`). Отличается ли поведение — не измерено: новый вариант
   упирается в тест `test_variant_flags_are_measured`, который требует опоры на замер имён.
2. **Влияние `PredefinedDataUpdate` / `/SetPredefinedDataUpdate` на строки предопределённых данных в ИБ.**
   Дамп конфигурации показывает только описание предопределённых данных (§12), а способа прочитать строки
   БД из командной строки нет: `/RunScript` даёт код 1 и пустой вывод, `/TESTCLIENT`, `/TESTMANAGER`,
   `-testFile`, `-testOut`, `-TestOnly`, `/AllowExecuteScheduledJobs` и `/EXECUTE` уходят в таймаут,
   COM-мост не зарегистрирован (`REGDB_E_CLASSNOTREG`). Это доказуемое слепое пятно инструментов, а не
   задача для доделывания — оно зафиксировано в `docs/слепые-пятна.md`.
3. **Позиция «модификатор ПЕРЕД командой» в лестницу не вводилась** сознательно (лестница меняет ровно
   один токен формы команды). Она измерена рукописными контролями (§11); в лестнице её нет.
