# План итерации 14c: CLI — `--root` против позиционного, argv тестового runner и код `check.sdbl fields`; закрытие итерации

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (нативное выполнение в этой сессии) вместе с superpowers:test-driven-development — задачи связаны контрактом выходных кодов CLI и одним слоем `p1c.core.contracts`, поэтому их пишет и выполняет один исполнитель. Steps use checkbox (`- [ ]`) syntax. Нумерация продолжается с `Task 39` (прежние задачи — в планах `2026-10-30-iteraciya-14a-…` и `…-14b-…`). В этой итерации 1С-прогонов нет: всё меряется офлайн прогонами CLI и тестами `p1c`.

**Goal:** починить три разломанных места блока B — флаг `--root` бегуна, который затирается позиционным аргументом и падает traceback'ом на нераспознанной раскладке (B4), ручной разбор argv в тестовом runner с `IndexError` на голом флаге и потерей stdout/stderr (B5), и `check.sdbl fields`, который не различает «нет корня выгрузки» и `--no-model` (B6); затем закрыть итерацию 14 в роадмапе и журнале.

**Architecture:** правки идут в `p1c` (`src/p1c/cli/runner.py`, `src/p1c/test/run.py`, `src/p1c/check/sdbl/cli.py`) и их тесты; документы и журнал — в контуре `effektivnost-otdela`. Образец дружелюбного отказа — `load/cli.py:50-62` (`W.error` → код 2 через `core/writers.py`).

**Tech Stack:** Python 3.15; тесты `p1c` — скрипты с `check()`/`fails` под `python scripts/run_tests.py`; офлайн-прогоны — `python -B -m p1c.cli.runner …`, `python -B -m p1c.test.run …`, `python -B -m p1c.check.sdbl.cli fields …`; argparse, контракт `p1c.core.contracts`.

**Spec:** блок B таблицы `docs/план-оптимизации-p1c.md` (`:78-80`, B4–B6); решение исполнителя итерации 14 — в `.superpowers/sdd/effektivnost-otdela/progress.md`.

## Global Constraints

- Ответы и тексты документов — по-русски; имена флагов/команд платформы — только из `p1c/src/p1c/data/test_cli_flags.json` (в нём нет `--root`/`--out`/`--format` — это собственные флаги `p1c`; фиксировать как факт, не выдумывать).
- 1С-прогонов нет; гейт-ИБ не трогается.
- `PREDICTIONS`/`EXPECTATIONS` — до прогона, не переписываются.
- Абсолютных путей в коде/тестах/документах нет — только свёртки.
- Перед коммитом — сканы `<tmp>\opencode\scan_texts.py`.
- Контракт кодов: `0` — есть результат без ошибок, `1` — есть находки (для бегуна), `2` — исполнение невозможно (ошибка аргумента/контекста). `core/context.py` не имеет класса ошибки для отсутствующего `config.root` (`"root": None` `:43-47`, `build:211-226`) — новые ошибки оформляются через `W.error`, а не через контекст.

## Review Focus

- B4 не ломает контракт «1 = есть находки» (`runner.py:14-18`): нераспознанная раскладка — это ошибка аргумента (код 2), а не пустой источник (код 1). Путь `--root` нормализуется один раз и показывается как есть.
- B5: тесты `tests/test_run/test_run.py:142-149` ждут **возвращаемое** значение 2 от `main`, а `argparse` при ошибке бросает `SystemExit(2)` — нужен перехват/шина, иначе тест станет красным не по дефекту, а по форме. Слойный страж `tests/core/test_layers.py:45,52-53` запрещает `run.py` импортировать лишнее — argparse встроенный, импорт допустим.
- B6: `fields` возвращает 0 на успехе (`:313`), а не «всегда 2» — это запись прежнего замера роадмапа, которую правит Task 42. Различаются три случая: нет корня выгрузки (код 2, текст «Нужен корень…»), `--no-model` (код 2, текст «поля недоступны без модели»), объект не найден (код 2, уже есть).
- `load/scan.py` и `core/rules.py`/`core/rules.json` не трогаются.

---

### Task 39 (B4): `--root` бегуна против позиционного; дружелюбный отказ на нераспознанной раскладке

**Files:**
- Modify: `p1c/src/p1c/cli/runner.py` (argparse `279-310` — `--root` `:286`; подстановка позиционного `args.root = args.rest[0]` `:298`; `cmd_run` `107-120` — вызов `load_configuration_model` `118-119` без перехвата)
- Modify: `p1c/tests/cli/test_runner.py` (пины `74-85`, `98`, `131-136`, `147`, `154`, `167`, `198`, `230-231`, `242-243` — проверить и пополнить)
- Create: `p1c/tests/cli/test_runner_root.py`

**Interfaces:**
- Produces: явно заданный `--root` не подменяется позиционным `rest[0]`; если `--root` задан и `rest` тоже задан, они должны совпадать или `--root` побеждает (зафиксировать решением и тестом). `cmd_run` перехватывает `ValueError` от `detect_layout` (`load/reader.py:835`) и отдаёт `W.error(str(exc))` → код 2 по образцу `load/cli.py:50-62`, а не traceback с кодом 1.
- Consumes: `load/reader.py::detect_layout` `828-837`; `core/writers.py::W.error` (`:51-59`, `SystemExit(2)`).

- [ ] **Step 1: Write the failing test** `tests/cli/test_runner_root.py`: (1) `main(["run", "examples/managed_app", "--root", "examples/designer_dump"])` использует корень `examples/designer_dump` (проверить по выводу/находкам), а не позиционный; (2) `main(["run", "--root", "<несуществующий каталог без признаков>"])` даёт код 2 и сообщение «Не удалось определить раскладку…», без `Traceback`. Ожидается отказ (сейчас корень затирается, а `ValueError` уходит в трейсбек).
- [ ] **Step 2: Run to verify the reason** — тест падает на подмене корня и на `Traceback` (`ValueError`) с кодом 1.
- [ ] **Step 3: Implement минимально** — в `main` после `parse_args` сделать `args.root` приоритетным над `rest[0]` (и, если оба заданы и различаются, сообщить противоречие — по образцу `cannot_execute` в `test/run.py:71-88`); в `cmd_run` обернуть `load_configuration_model`/`build_type_model`/`Schema.from_model` в `try/except ValueError` → `W.error(str(exc))`. Не добавлять `--root`-веток в `load/cli.py` (у load корень позиционный, `load/cli.py:152-175`).
- [ ] **Step 4: Run tests to verify they pass** — новый тест зелёный; `python scripts/run_tests.py` (0 неудач); проверить пины `tests/cli/test_runner.py` (живые прогоны: `p1c-run run --root examples/managed_app` → «Нужен корень выгрузки или config.root», код 2 — это прежнее поведение, не менять).
- [ ] **Step 5: Commit** в `p1c`.

### Task 40 (B5): argparse в тестовом runner, обязательный `--bin`/база, отказ `IndexError`, захват вывода

**Files:**
- Modify: `p1c/src/p1c/test/run.py` (ручной разбор `144-167` → argparse; `main:144`, `argv = argv or sys.argv[1:]` `:147`, `IndexError` в `:156`, имя теста `files[0]` `:161`, `subprocess.run(...).returncode` без захвата вывода `:165`)
- Modify: `p1c/tests/test_run/test_run.py` (пины `58-61`, `65`, `96-99`, `103`, `107`, `118-121`, `126-132`, `142-149`, `156-157`, `161`)
- Create: нет (регресс — существующие тесты + новые проверки в том же файле)

**Interfaces:**
- Produces: `main` парсит argv через `argparse` (позиционные файлы, `--bin`/`--ib`/`--connection-string`/`--file`); голый флаг без значения даёт понятное сообщение и код 2 (а не `IndexError`); `--root`-подобные неизвестные флаги отклоняются argparse с сообщением; stdout/stderr подпроцесса платформы сохраняются в результат (поле `diagnostics` или новое поле), а не выбрасываются.
- Consumes: `ARGUMENT_TO_FLAG:39`, `STATUS:44`, `flags():47`, `cannot_execute:71-88` (логика сохранена); `tests/test_run/test_run.py`.

- [ ] **Step 1: Write the failing test** (в `tests/test_run/test_run.py`, добавить кейсы): (1) `main(["--root"])` возвращает 2 и не бросает `IndexError` (ожидается отказ — сейчас `IndexError` в `:156`); (2) `main(["--bin", "x", "--ib", "y", "файл"])` строит команду и возвращает код из `STATUS`; (3) неизвестный флаг `--bogus` даёт код 2 с сообщением. Существующие пины `:142-149` (ожидание возвращаемой 2) сохранить — их защищает шина перехвата `SystemExit`.
- [ ] **Step 2: Run to verify the reason** — тест падает на `IndexError` (`:156`) и на отсутствии отклонения неизвестного флага; причина — ручной разбор, а не argparse.
- [ ] **Step 3: Implement минимально** — заменить ручной цикл `154-158` на `argparse.ArgumentParser` (позиционные `files` через `nargs="*"`, опции `--bin/--ib/--connection-string/--file`); `argparse` при ошибке бросает `SystemExit(2)` — в `main` перехватывать его в шине, возвращающей 2, чтобы тесты ждали значение, а не исключение; захватить `stdout`/`stderr` подпроцесса (`subprocess.run(..., capture_output=True)`) и положить их в результат. Логику `cannot_execute`/`command` не переписывать.
- [ ] **Step 4: Run tests to verify they pass** — `python scripts/run_tests.py` (0 неудач); слойный страж `tests/core/test_layers.py:45,52-53` зелёный.
- [ ] **Step 5: Commit** в `p1c`.

### Task 41 (B6): `check.sdbl fields` различает «нет корня» и `--no-model`

**Files:**
- Modify: `p1c/src/p1c/check/sdbl/cli.py` (`cmd_fields` `290-313`; `_schema` `134-142`; `_root` `83-90`; тексты `W.error` `:293`, `:297`)
- Modify: `p1c/tests/check_sdbl/test_cli.py` (пины `104-110`, `163-164`, `182-185`, `189-191`, `199-202`, `204-205`, `302-304`, `307-308`, `312-314`; заголовок кэша `--no-model` `249-250`)

**Interfaces:**
- Produces: `cmd_fields` при `schema is None` различает причину: `--no-model` → `W.error("поля недоступны без модели (--no-model)")` (код 2); нет `config.root` → прежний текст «Нужен корень выгрузки или config.root…» (код 2); успешный путь по-прежнему `return 0` (`:313`) с полями, стандартными полями, разрезами и общими реквизитами.
- Consumes: `_schema` `134-142`, `_root` `83-90`, `core/writers.py::W.error`.

- [ ] **Step 1: Write the failing test** (в `tests/check_sdbl/test_cli.py`): `fields --no-model <ключ>` даёт код 2 и текст про `--no-model` (сейчас — текст «Нужен корень…», неотличимый от отсутствия корня); `fields <ключ>` без корня даёт код 2 и текст «Нужен корень…»; `fields <существующий ключ>` с корнем даёт код 0 и непустые `fields` (пины `:163-164`, `:307-308` не меняются). Ожидается отказ на первом кейсе.
- [ ] **Step 2: Run to verify the reason** — тест падает на неотличимости текста (`_schema` возвращает `None` и для `--no-model`, и для отсутствия корня).
- [ ] **Step 3: Implement минимально** — в `cmd_fields` перед вызовом `_schema` проверить `args.no_model` и выдать свой текст; иначе — прежний путь. `_schema` не менять (он намеренно возвращает `None` для `--no-model`, `:137-138`).
- [ ] **Step 4: Run tests to verify they pass** — новый тест зелёный; `python scripts/run_tests.py` (0 неудач); пины кода 0 (`:163-164`, `:307-308`) и кода 2 (`:182-185`, `:302-304`) сохранены.
- [ ] **Step 5: Commit** в `p1c`.

### Task 42: закрытие итерации 14 — статусы блоков A/C/B, метрика G и журнал

**Files:**
- Modify: `effektivnost-otdela/docs/план-оптимизации-p1c.md` (таблица A `:21-28` и статус `:48-69` — обновить на «к итерации 14»; блок C `:93-104` — статус C1/C2/C4; блок B `:78-80` — правка формулировки B6 про «fields всегда код 2» на фактические якоря `check/sdbl/cli.py:293` и `:313`; метрика G `:149-159` и `:161-164`)
- Modify: `effektivnost-otdela/docs/evidence/tool-coverage.md` (сводка замеров 14a/14b)
- Modify: `.superpowers/sdd/effektivnost-otdela/progress.md` (журнал итерации 14 — отдельный коммит)

**Interfaces:**
- Produces: статусы A (остаток закрыт: командные модули, общие коллекции, одиночные макеты, `SettingsStorages`/`FilterCriteria`, диагноз разбора XML), C1/C2/C4 и B4/B5/B6 — с пометкой «к итерации 14», со ссылками на закоммиченные артефакты и числа замеров этой итерации; метрика G пересчитана по новым числам (метрики `types_without_ctor`/`types_without_properties` — только в evidence, они в `p1c` не вычисляются).
- Consumes: планы 14a/14b/14c и их замеры.

- [ ] **Step 1: Поправить документы** — таблицу A и статус (командные модули и декларации, общие коллекции, одиночные макеты, коллекции вне `COLLECTIONS_MAP`, диагноз разбора), блок C (C1/C2/C4 с замеренными числами «до/после»), блок B (B4/B5/B6; правка формулировки B6: `fields` возвращает 0 на успехе, якоря `:293`/`:313`), метрику G.
- [ ] **Step 2: Сводка в evidence** — раздел итерации 14 в `docs/evidence/tool-coverage.md`.
- [ ] **Step 3: Сканы текстов** `<tmp>\opencode\scan_texts.py` по всем изменённым файлам обоих репозиториев.
- [ ] **Step 4: Коммиты** — код и тесты `p1c` (Tasks 39–41 уже закоммичены по задачам); документы контура одним коммитом; `progress.md` отдельным коммитом; финал — `git status --porcelain` пуст в обоих репозиториях.
