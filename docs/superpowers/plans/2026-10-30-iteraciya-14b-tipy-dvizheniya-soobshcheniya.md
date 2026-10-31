# План итерации 14b: канонические неявные члены, арности конструкторов и мёртвый источник `TYPE_CONSTRUCTORS`

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (нативное выполнение в этой сессии) вместе с superpowers:test-driven-development — задачи связаны одной проверкой BSL (`p1c.check.bsl`) и одной моделью типов (`p1c.metadata`), поэтому их пишет и выполняет один исполнитель. Steps use checkbox (`- [ ]`) syntax. Нумерация продолжается с `Task 34` (прежние задачи — в плане `2026-10-30-iteraciya-14a-chitatel-comands-obshchie-kollekcii.md`). В этой итерации 1С-прогонов нет: всё меряется офлайн прогонами `check.bsl`/`p1c.cli run` и тестами `p1c`.

**Goal:** убрать канонический шум проверки BSL — необъявленные неявные члены модуля владельца (`Движения`, реквизиты и табличные части объекта, `СхемаКомпоновкиДанных`) и тип `СообщениеПользователю`, который есть в модели, но без конструктора, свойств и методов; вычистить мёртвый источник арностей `TYPE_CONSTRUCTORS`, который никем не читается; снять замер по фикстуре и закрепить в evidence.

**Architecture:** правки идут в `p1c` (`src/p1c/check/bsl/semantic.py`, `src/p1c/metadata/model.py`, `src/p1c/metadata/loader.py`, `src/p1c/metadata/module_paths.py`, `src/p1c/data/platform_arities.py`, `scripts/extract_help_arities.py`) и их тесты; evidence — в контуре `effektivnost-otdela/docs/evidence/tool-coverage.md`. Источники арностей — рукописные таблицы `model.py` (`COLLECTIONS`, `EXTRA_TYPES`), а не `TYPE_CONSTRUCTORS`.

**Tech Stack:** Python 3.15; тесты `p1c` — скрипты с `check()`/`fails` под `python scripts/run_tests.py`; офлайн-замеры — `python -B -m p1c.check.bsl.cli check <корпус> --root <корпус> --format json` и `python -B -m p1c.cli run <корпус> --format json`; BSL, модель типов.

**Spec:** блок C таблицы `docs/план-оптимизации-p1c.md` (`:93-104`, C1/C2/C4) и метрика `types_without_ctor`/`types_without_properties` (`:95-98`, `:149-159`); решение исполнителя итерации 14 — в `.superpowers/sdd/effektivnost-otdela/progress.md`.

## Global Constraints

- Ответы и тексты документов — по-русски; имена флагов/команд платформы — только из `p1c/src/p1c/data/test_cli_flags.json`.
- 1С-прогонов нет; тяжёлые обходы корпусов — вне зависимости от чего-либо, по одному ключу.
- `PREDICTIONS`/`EXPECTATIONS` пишутся до прогона и не переписываются; непредсказанное — отдельным списком с причиной.
- Абсолютных путей в `scripts`/`probe`/`tests`/документах нет — только свёртки `<work>`, `<tmp>`, `<repo>`, `<dump>`, `<cfg>`, `<p1c>`.
- Перед коммитом — сканы `<tmp>\opencode\scan_texts.py`.
- Значения в модели и тестах — только из замеренных файлов корпуса.
- Методическая ловушка: `check_module_text(text, ctx, options)` (`semantic.py:869`) с ручными `options` и тот же файл через CLI (`check_options_for`) дают разные числа находок, поэтому «до/после» сравнимы только через CLI (`check.bsl.cli` или `p1c.cli run`). Все замеры — только CLI/`check_options_for`.
- `TYPE_CONSTRUCTORS` (`data/platform_arities.py:22189`) не импортируется нигде в `src/p1c/**`; его источник — генератор `scripts/extract_help_arities.py`. Реальные арности — `model.py`.

## Review Focus

- Неявные члены модуля владельца — это не «заглушить ошибку»: это добавить в разрешение имён канал «владелец модуля», который возвращает реквизиты/табличные части того объекта, чей модуль проверяется, и специальный член `Движения` у документов. Только после этого `IDS_STX_VAR_NOTDECLARED` честно исчезает.
- `Движения` — коллекция наборов записей регистров по имени регистра, поэтому `.ЗатратыВремени` должен разрешаться как произвольный член (`dynamic_members`), а не как конкретное свойство.
- `СообщениеПользователю` должен получить `ctor_arities=(0,)`, свойства и методы из замера, а не из `TYPE_CONSTRUCTORS` (там его нет). Слияние `model.py:426-428` оставляет его `ctor_arities=()` — это и есть причина `IDS_STX_CTOR_NOTFOUND`.
- Не трогать менеджерские типы без конструктора (`loader.py:116`, `:155`, `:175`, `CONSTRUCTIBLE_KINDS`) — это намеренно.
- Метрики `types_without_ctor`/`types_without_properties` в `p1c` нигде не вычисляются (только документы контура); их вычисление в эту итерацию не входит — в evidence пишутся замеренные числа из `builtin_type_model()`.

---

### Task 34: неявные реквизиты и табличные части владельца модуля

**Files:**
- Modify: `p1c/src/p1c/check/bsl/semantic.py` (`resolve_varref` `598-619` — вставить канал «владелец модуля» перед `global_properties`; `self.options` уже в объекте)
- Modify: `p1c/src/p1c/metadata/module_paths.py` (`check_options_for` `106-121` — добавить `owner`; новый помощник `module_owner` рядом с `common_module_name` `80-86`)
- Create: `p1c/tests/check_bsl/test_module_owner.py`

**Interfaces:**
- Produces: в объектном модуле ссылка на собственный реквизит/табличную часть владельца разрешается без `IDS_STX_VAR_NOTDECLARED`. Канал строится так: `module_owner(path)` возвращает имя владельца по раскладке (`Catalogs/<Имя>/Ext/ObjectModule.bsl` → `catalog.<Имя>`; `Documents/…` → `document.<Имя>`; регистры — по имени файла модуля), `check_options_for` кладёт `opts["owner"]`, а `resolve_varref` проверяет `self.ctx.objects[owner]` (реквизиты и табличные части уже в модели читателя) до `global_properties`.
- Consumes: модель `ctx.objects` (`metadata/model.py` `TypeModel`), построенная `build_type_model` из читателя; фикстуры `examples/designer_dump` (`Catalogs/Номенклатура/Ext/ObjectModule.bsl:3` `Цены.Итог("Цена")`, `Documents/ЗаказПокупателя/Ext/ObjectModule.bsl:3` `Товары.Итог("Цена")`) и `examples/managed_app`.

- [ ] **Step 1: Write the failing test** `tests/check_bsl/test_module_owner.py` (форма `check()`/`fails`): текст

  ```bsl
  Процедура П()
      Сообщить(Цены.Итог("Цена"));
  КонецПроцедуры
  ```

  с `options={"module_kind": "object", "owner": "catalog.Номенклатура"}` и моделью, где `catalog.Номенклатура` имеет табличную часть `Цены`, — ожидается 0 находок `IDS_STX_VAR_NOTDECLARED` (сейчас 1); плюс кейс, где владельца нет или реквизит не найден — ошибка остаётся. Ожидается отказ.
- [ ] **Step 2: Run to verify the reason** — тест падает на `IDS_STX_VAR_NOTDECLARED` для `Цены` (канал отсутствует), причина — `resolve_varref` не знает владельца.
- [ ] **Step 3: Implement минимально** — `module_owner` в `module_paths.py` (по пути, в том же стиле, что `common_module_name`), `opts["owner"]` в `check_options_for`, и в `resolve_varref` после `collections`/`common_modules`/…/`global_enums` вставка: если `owner` задан и `self.ctx.objects.get(owner)` имеет реквизит/ТЧ с этим именем — вернуть его тип. Глобальные имена (`global_properties`) остаются последними.
- [ ] **Step 4: Run tests to verify they pass** — новый тест зелёный; `python scripts/run_tests.py` (0 неудач). Проверить пины, которые мог задеть канал: `tests/check_bsl/test_scope.py`, `tests/check_bsl/test_semantic.py`.
- [ ] **Step 5: Офлайн-замер** — `python -B -m p1c.check.bsl.cli check examples/designer_dump --root examples/designer_dump --format json`: шум `Цены`/`Товары` (2 находки `IDS_STX_VAR_NOTDECLARED` по фикстуре) должен уйти. Числа «до» зафиксировать до правки. Записать в журнал.
- [ ] **Step 6: Commit** в `p1c`.

### Task 35: канонический член `Движения` у документов

**Files:**
- Modify: `p1c/src/p1c/check/bsl/semantic.py` (канал владельца из Task 34 — добавить специальный член `Движения` для `kind == "document"`)
- Modify: `p1c/src/p1c/metadata/model.py` или `loader.py` (если `Движения` вешается как свойство типа объекта документа — иначе псевдо-тип с `dynamic_members` в канале)
- Create: `p1c/tests/check_bsl/test_dvizheniya.py`

**Interfaces:**
- Produces: в модуле документа ссылка `Движения.<Регистр>.<Поле>` разрешается: `Движения` — псевдо-тип с `dynamic_members=True` (имя регистра — произвольный член), возвращающий тип, у которого дальше допустимы члены набора записей. Живой пример: `examples/managed_app/Documents/ФактРаботы/Ext/ObjectModule.bsl:18-21` (`Движения.ЗатратыВремени…`) даёт сейчас 7×`IDS_STX_VAR_NOTDECLARED`, после — 0 (или только реальные ошибки, если есть).
- Consumes: Task 34; `resolve_member` (`semantic.py:621-664`) для разрешения `.ЗатратыВремени` и `.Поле`.

- [ ] **Step 1: Write the failing test** `tests/check_bsl/test_dvizheniya.py`: текст `Движения.ЗатратыВремени.Количество = 1;` в контексте `{"module_kind": "object", "owner": "document.ФактРаботы"}` — ожидается 0 находок (сейчас 2: `Движения` и, следом, `ЗатратыВремени`). Плюс проверка, что `Движения` не разрешается в модуле не-документа. Ожидается отказ.
- [ ] **Step 2: Run to verify the reason** — тест падает на `IDS_STX_VAR_NOTDECLARED` для `Движения`; канала владельца нет до Task 34, а `Движения` отсутствует в `check/bsl/**` вовсе (замер: только мёртвое `data/platform_vocab.py:1587`, файл никем не импортируется).
- [ ] **Step 3: Implement минимально** — в канале владельца для `kind == "document"` добавить `Движения` как тип с `dynamic_members=True` (и, при необходимости, типом набора записей регистра); `Движения` не трогать в `GLOBAL_PROPERTIES` (`model.py:481-526`) — он не глобален.
- [ ] **Step 4: Run tests to verify they pass** — новый тест зелёный; `python scripts/run_tests.py` (0 неудач); перепроверить пины `tests/check_bsl/test_declarations.py`, `tests/check_bsl/test_scope.py`.
- [ ] **Step 5: Офлайн-замер** — `check.bsl` по `examples/managed_app`: 7 находок `Движения` должны уйти (11 scope → 4 scope в этом файле). Записать в журнал.
- [ ] **Step 6: Commit** в `p1c`.

### Task 36: тип `СообщениеПользователю` — конструктор, свойства, методы

**Files:**
- Modify: `p1c/src/p1c/metadata/model.py` (`EXTRA_TYPES` `186-262` — добавить `СообщениеПользователю` с `ctor`, свойствами и методами; слияние `426-431` и consumed `339-343` остаются как есть)
- Create: `p1c/tests/check_bsl/test_soobshchenie.py`

**Interfaces:**
- Produces: `Новый СообщениеПользователю` больше не даёт `IDS_STX_CTOR_NOTFOUND` (`semantic.py:739-741`); члены `Текст`, `Поле`, `Сообщить` разрешаются как свойство/метод. Тип регистрируется в `EXTRA_TYPES` с `ctor=(0,)` и измеренными членами (метод `Сообщить`, свойства `Текст`/`Поле` — замерить по справке `data/platform_arities.py:18739-18743` и/или фикстуре; без выдумывания).
- Consumes: `check_new` `semantic.py:724-749`, `resolve_member` `621-664`; фикстура `examples/managed_app` (4 находки `names` = CTOR на строке 25 + методы `СообщениеПользователю.Текст/Поле/Сообщить`).

- [ ] **Step 1: Write the failing test** `tests/check_bsl/test_soobshchenie.py`: `М = Новый СообщениеПользователю; М.Текст = "x"; М.Сообщить();` в общем контексте — ожидается 0 находок (сейчас: `IDS_STX_CTOR_NOTFOUND` на `Новый`, плюс `Текст`/`Сообщить` не определены). Ожидается отказ.
- [ ] **Step 2: Run to verify the reason** — тест падает на `IDS_STX_CTOR_NOTFOUND` (`t.ctor_arities` пуст) и далее на членах; причина — тип в модели как `kind="collection"` без конструктора (`model.py:426-428`), и в `TYPE_CONSTRUCTORS` его нет (замер: 22 записи, все имена событий/методов).
- [ ] **Step 3: Implement минимально** — запись `СообщениеПользователю` в `EXTRA_TYPES` с `ctor=(0,)`, `properties` и `methods` из замера; `resolve_type`/слияние не меняется. Не трогать соседние пробелы той же природы (`ДиалогВыбораФайла`, `ЗаписьТекста`, `ТекстовыйДокумент`, `ОписаниеОповещения` из `SCALARS:126`) — они фиксируются в журнале как отдельный замер, не в этой задаче.
- [ ] **Step 4: Run tests to verify they pass** — новый тест зелёный; `python scripts/run_tests.py` (0 неудач). Проверить пины `tests/metadata/test_loader.py:68-73`, `tests/check_bsl/test_declarations.py`.
- [ ] **Step 5: Офлайн-замер** — `check.bsl` по `examples/managed_app`: 4 находки `names` должны уйти (15 → 11 total). Записать в журнал.
- [ ] **Step 6: Commit** в `p1c`.

### Task 37: мёртвый источник `TYPE_CONSTRUCTORS` — переименовать/удалить

**Files:**
- Modify: `p1c/src/p1c/data/platform_arities.py` (`TYPE_CONSTRUCTORS` `22189` — удалить или переименовать с пометкой «не используется»)
- Modify: `p1c/scripts/extract_help_arities.py` (генератор `252` — перестать генерировать `TYPE_CONSTRUCTORS`; `--out` `146` указывает на устаревший путь)
- Create: нет (регресс — существующие тесты)

**Interfaces:**
- Produces: `TYPE_CONSTRUCTORS` исчезает из `data/platform_arities.py` (или переименовывается так, чтобы имя больше не обещало «конструкторы»); `extract_help_arities.py` его не генерирует. Никакой импорт не ломается (замер: 0 вхождений в `src/p1c/**`).
- Consumes: замер — 22 записи, все имена событий/методов (`AfterWrite`, `BeforeWrite`, `ВыборЗначения`, `Записать`…), `СообщениеПользователю`/`Массив`/`ТекстовыйДокумент` отсутствуют; причина — `extract_help_arities.py:55-75` (страница без `ru_owner` → `{"ctor": (min,max)}`) и `:163-167` (`continue`).

- [ ] **Step 1: Write the failing test** — регрессный тест (или проверка): `python -c`-скриптом во временном каталоге подтвердить, что `TYPE_CONSTRUCTORS` не импортируется (`grep -R TYPE_CONSTRUCTORS src/p1c` пуст), и что `extract_help_arities.py` после правки не пишет его в выход. Ожидается: сейчас имя есть, после — нет.
- [ ] **Step 2: Run to verify the reason** — `TYPE_CONSTRUCTORS` определён в `:22189`, генератор пишет в `:252`; импортов нет.
- [ ] **Step 3: Implement минимально** — удалить `TYPE_CONSTRUCTORS` (или переименовать в `LEGACY_*` с комментарием «не источник арностей»), поправить генератор, чтобы он его не эмитил.
- [ ] **Step 4: Run tests to verify they pass** — `python scripts/run_tests.py` (0 неудач); ни один тест не ссылается на `TYPE_CONSTRUCTORS` (замер: 0).
- [ ] **Step 5: Commit** в `p1c`.

### Task 38: офлайн-замер `check.bsl` по фикстуре и evidence

**Files:**
- Modify: `effektivnost-otdela/docs/evidence/tool-coverage.md` (новый раздел итерации 14 — числа C1/C2/C4)
- Modify: `.superpowers/sdd/effektivnost-otdela/progress.md` (журнал — отдельный коммит)

**Interfaces:**
- Produces: раздел evidence с числом находок `check.bsl` по `examples/managed_app` до (15: `scope 11` + `names 4`) и после правок Tasks 34–36, и замером `builtin_type_model()` (1913 типов, 1869 без `ctor_arities`, 44 с, 1891 без `properties`, 5 `dynamic_members`; `TYPE_SIGNATURES` 1885, `GLOBAL_CONTEXT_SIGNATURES` 987, `EVENT_SIGNATURES` 135) — числа переснять после правок.
- Consumes: Tasks 34–36.

- [ ] **Step 1: Записать `PREDICTIONS` до прогона** — ожидается: `check examples/managed_app` даёт `count < 15` (11 scope шума и 4 names уходят: 7×`Движения` + 2×`Цены/Товары` + 4×`СообщениеПользователю`), и `python -B -m p1c.cli run examples/designer_dump --format json` остаётся `bsl {"count": 6, "files": 7}` (фикстура designer_dump не менялась). Записать в журнал.
- [ ] **Step 2: Прогнать CLI-замеры** — `check.bsl` и `p1c.cli run` до и после (до — зафиксировать до начала правок Tasks 34–36), сравнить, непредсказанное — отдельным списком.
- [ ] **Step 3: Переснять `builtin_type_model()`** — скриптом во временном каталоге (не однострочником) посчитать типы без `ctor_arities`/`properties` до и после Task 36.
- [ ] **Step 4: Поправить документы** — раздел в `docs/evidence/tool-coverage.md`; прежние числа (15, 20→12 in-memory) остаются записью прежних замеров, новые — только из этого прогона.
- [ ] **Step 5: Сканы текстов** `<tmp>\opencode\scan_texts.py` по изменённым файлам.
- [ ] **Step 6: Коммиты** — код и тесты `p1c` (Tasks 34–37), затем документы контура, затем `progress.md` отдельно; финал — `git status --porcelain` пуст в обоих репозиториях.
