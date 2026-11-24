# Итерация 22: предопределённые элементы как свойства менеджера — план

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Перенести верхнеуровневые предопределённые элементы из загруженной модели в свойства типа менеджера, закрыть до 73 находок F83 и снять замер 91 без единой новой находки.

**Architecture:** Одна правка в `metadata/loader.py` (`build_type_model`): свойства менеджера дополняются именами из `model["predefined_data"]` со значением `ref_type`. Каналы, шаблоны, данные книги и фикстуры не меняются.

**Tech Stack:** Python 3.13, `TypeDef`/`build_type_model` (`metadata/loader.py`), `load/reader.py` (`predefined_data`), домашние тесты.

**Spec:** `docs/superpowers/specs/2026-11-24-iteraciya-22-predefined-manager-design.md`

## Global Constraints

Наследуются ограничения 1–26 плана итерации 18 и 1–6 итераций 19–21. Числа:

- база — замер 90 (`m90_task79_pulsar.json`): 2 784 / 616, METHOD 1 919 | 514, why 100 %, `stats.files` 1 195, подпись `726583f1…29726`, фикстура 3 486 b / `2139fba5…49aa15` / 0 находок.
- новых троек 0; `semantic.py`, каналы, решения `resolve_member`, шаблоны, данные книги и фикстуры не меняются.
- один прогон корпуса (замер 91), предсказание до прогона.
- контуры: `<p1c>` ≥ 116 `[ok]` / 0 `[fail]`, `<docs>` Ran 305 OK, wording 0.
- коммиты: ASCII-транслит, `git commit -F`, `Co-Authored-By: Claude Code <noreply@anthropic.com>`; не пушить.

## Review Focus

1. **Верхний уровень.** На менеджер попадают только элементы с `parent == ""`; вложенный не попадает. Тест — Task 82 (б).
2. **Ссылочный тип.** Значение свойства — `ref_type` объекта; если ссылок нет — `None`. Тест — (а).
3. **Ключ вида.** `predefined_data` находится по `kind.obj`, `spec.kind.obj` или суффиксу `.{obj}`; объект без файла — без свойств. Тест — (в).
4. **Обращение молчит, чужое имя — находка.** Сквозной модуль: предопределённое имя закрыто, несуществующее остаётся. Тест — (г)–(д).
5. **Шаблоны и каналы целы.** Шаблонные члены и `dynamic_members` не тронуты. Тест — (е).
6. **Ноль новых троек.** Гейт 90/91; любое появление — откат.

---

### Task 82: предопределённые имена в менеджере, тесты, замер 91

**Files:**
- Modify: `<p1c>/src/p1c/metadata/loader.py` — `build_type_model`, свойства менеджера.
- Create: `<p1c>/tests/metadata/test_predefined_manager.py`
- Create: `<tmp>\opencode\iter18_m91_predictions.md`, `m91_task82.py`, `m91_task82_gate.py` и артефакты `m91_task82_pulsar.json` / `.log` / `.err`, `m91_task82_gate.json` / `.log` / `.summary.log`.

**Interfaces:**
- Consumes: `build_type_model(model: dict, base: TypeModel | None = None) -> TypeModel` (`loader.py:146`), `model["predefined_data"]: dict[str, {"items": list[dict]}]` (`load/reader.py:1174`), поля элемента `name`, `parent`, `is_folder`; `ref_type`; `TypeDef`.
- Produces: менеджер с `properties`, где верхнеуровневые предопределённые имена → `ref_type` (или `None`), `methods`/`kind`/`ctor_arities` прежние.

- [ ] **Step 0: Закоммитить дизайн и план в `<docs>`** (один коммит, ASCII-тема, `git commit -F`, `Co-Authored-By`), сканер 0 новых флагов.

- [ ] **Step 1: RED-тест.** `tests/metadata/test_predefined_manager.py` в стиле соседей (`test_loader.py`):
  - (а) минимальная модель: коллекция `catalogs` с объектом `Тест`, `predefined_data["Catalog.Тест"]` = `{"items": [{"name": "Первый", "parent": "", "is_folder": False}]}`; `build_type_model(model).resolve_type("СправочникМенеджер.Тест").properties["первый"] == "СправочникСсылка.Тест"`;
  - (б) элемент `{"name": "Вложенный", "parent": "Первый"}` в свойства не попадает;
  - (в) объект без `predefined_data` — свойств нет, тип регистрируется;
  - (г) сквозной модуль с `Справочники.Тест.Первый` (или метаданные фикстуры) — обращения к члену нет находки;
  - (д) `Справочники.Тест.Несуществующее` — находка остаётся;
  - (е) шаблонные члены (`НайтиПоКоду`) и `dynamic_members` не тронуты.

- [ ] **Step 2: RED.** `python <p1c>\tests\metadata\test_predefined_manager.py`; ожидаем падения (а), (г); число записать.

- [ ] **Step 3: Реализовать.** В `build_type_model` после `ref_type`:
  - `pre = model.get("predefined_data", {})`; ключи-кандидаты: `f"{kind}.{obj_name}"`, `f"{spec.get('kind')}.{obj_name}"`, любой ключ, оканчивающийся `.{obj_name}`;
  - `props = {norm(i["name"]): (ref_type or None) for i in pre.get("items", []) if not i.get("parent")}`;
  - передать `properties=props` в `TypeDef(name=manager_type, ...)`.

- [ ] **Step 4: GREEN и контур.** Тест 0 падений; `python -B -I -X utf8 scripts/run_tests.py` ≥ 116 `[ok]` / 0 `[fail]`; `test_wording.py` 0.

- [ ] **Step 5: Замер 91.** Предсказание до прогона: закрытий **0…73**, формная **586…616**, всего **2 711…2 784**, новых троек **0**, `why` 1 919 | 514, `stats.files` 1 195, подпись, фикстура. Обёртка/гейт по образцу `m90_task79.py`; один прогон; сравнение 90/91; если `ref_type` открыл новые тройки — значение свойства `None` и повторный замер с записью решения (второй прогон только по этому решению).

- [ ] **Step 6: Коммит и отчёт.** Коммит `<p1c>` (loader + тест); `task-82-report.md` с RED/GREEN, замером, тройками, расхождениями.

---

### Task 83: остаток M209, §20 свидетельства, F84/M210

- [ ] **Step 1: Зонд.** По артефакту 91: остаток соседних шаблонов (`РегистрСведенийЗапись.<…>.Выбран`, `.Удалить`) и прочих; числа, форма/корпус.
- [ ] **Step 2: §20** в `docs/evidence/tool-coverage.md`: лестница 90→91, закрытия, остаток, размер, подпись, фикстура.
- [ ] **Step 3: F84/M210** — если остаток M209 требует нового знания (соседний шаблон), запись F84 (§25) с ценой и путём; иначе строка M210.
- [ ] **Step 4: Сканер и коммит документов** (0 новых флагов, Ran 305 OK).

---

### Task 84: финальный обзор, лиджер, критерии

- [ ] Сверка §10 спеки; финальный обзор двумя проходами; Critical/Important — один фикс-проход; Minor — в лиджер; отчёт; ничего не пушится.

---

Замеры: 91. Дефекты: следующий F84. Миноры: следующий M210. Решения: R236. Главы: Р255.
