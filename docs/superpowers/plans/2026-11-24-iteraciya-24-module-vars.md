# Итерация 24: экспортные модульные переменные — план

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Читать `Перем <имя> Экспорт;` из объектных/менеджерских модулей и регистрировать имена свойствами соответствующего типа; закрыть до 6 находок F85 и снять замер 93 без новых.

**Architecture:** Разбор рядом с `extract_exported_methods` (`load/reader.py`) пишет `module_vars` в модель; `build_type_model` добавляет их свойствами с `None` через `setdefault`. Шаблоны, каналы, фикстуры не меняются.

**Tech Stack:** Python 3.13, `p1c.bsl.exports`/`load/reader.py`, `build_type_model`, домашние тесты.

**Spec:** `docs/superpowers/specs/2026-11-24-iteraciya-24-module-vars-design.md`

## Global Constraints

Наследуются ограничения 1–26 плана итерации 18 и 1–6 итераций 19–23. Числа:

- база — замер 92 (`m92_task85b_pulsar.json`): 2 672 / 573, METHOD 1 807 | 471, why 100 %, `stats.files` 1 195, подпись `726583f1…29726`, фикстура 3 486 b / `2139fba5…49aa15` / 0 находок.
- новых троек 0; методы, шаблоны, каналы, фикстуры не меняются.
- один прогон корпуса (замер 93), предсказание до прогона.
- контуры: `<p1c>` ≥ 118 `[ok]` / 0 `[fail]`, `<docs>` Ran 305 OK, wording 0.
- коммиты: ASCII-транслит, `git commit -F`, `Co-Authored-By: Claude Code <noreply@anthropic.com>`; не пушить.

## Review Focus

1. **Только верхний уровень.** `Перем` внутри процедуры не попадает. Тест — Task 88 (в).
2. **Только `Экспорт`.** Без слова — не попадает. Тест — (г).
3. **Список имён.** `Перем А, Б Экспорт;` — оба. Тест — (б).
4. **Значение `None`, реквизит главнее.** `setdefault`; реквизит не перезаписывается. Тест — (а), (д).
5. **Сквозное обращение.** `Обработки.Тест.Таблица` молчит, чужое — находка. Тест — (е).
6. **Ноль новых троек.** Гейт 92/93.

---

### Task 88: модульные переменные, тесты, замер 93

**Files:**
- Modify: `<p1c>/src/p1c/load/reader.py` — разбор `Перем … Экспорт` рядом с `extract_exported_methods`.
- Modify: `<p1c>/src/p1c/metadata/loader.py` — свойства из `module_vars`.
- Create: `<p1c>/tests/metadata/test_module_vars.py`
- Create: `<tmp>\opencode\iter18_m93_predictions.md`, `m93_task88.py`, `m93_task88_gate.py` и артефакты.

**Interfaces:**
- Consumes: `extract_exported_methods` (`p1c.bsl.exports`), `exports_by_key`/`entry` (`reader.py:1503-1562`), `obj`/`entry` (`loader.py:165-255`), `TypeDef`.
- Produces: `entry["module_vars"]` (список имён) и свойства `object_type`/`manager_type`/`record_type` с `None`.

- [ ] **Step 0: Закоммитить дизайн и план в `<docs>`** (ASCII-тема, `git commit -F`, `Co-Authored-By`), сканер 0 новых флагов.

- [ ] **Step 1: RED-тест.** `tests/metadata/test_module_vars.py` (а–е) в стиле `tests/metadata/test_record_manager_return.py`.

- [ ] **Step 2: RED.** `python <p1c>\tests\metadata\test_module_vars.py`; ожидаем падения (а), (б), (е); число записать.

- [ ] **Step 3: Реализовать.** Разбор строк верхнего уровня `Перем <имена> Экспорт;` (мини-парсер или регэксп по тексту модуля без процедур) → `module_vars`; в `build_type_model` для каждого вида (manager/object/record) добавить `setdefault(norm(name), None)`.

- [ ] **Step 4: GREEN и контур.** Тест 0 падений; `python -B -I -X utf8 scripts/run_tests.py` ≥ 118 `[ok]` / 0 `[fail]`; wording 0.

- [ ] **Step 5: Замер 93.** Предсказание до прогона: закрытий **0…6**, формная **573**, всего **2 666…2 672**, новых троек **0**, `why` 1 807 | 471, `stats.files` 1 195, подпись, фикстура. Обёртка/гейт по образцу `m92_task85b.py`; один прогон.

- [ ] **Step 6: Коммит и отчёт.** Коммит `<p1c>`; `task-88-report.md`.

---

### Task 89: разложение остатка, §22 свидетельства, F86/M212

- [ ] **Step 1: Зонд.** По артефакту 93: остаток 13 находок (формы под объектным владельцем, менеджер-экспорты, возможные верные) с числами.
- [ ] **Step 2: §22** в `docs/evidence/tool-coverage.md`: лестница 92→93, закрытия, остаток, размер, подпись, фикстура.
- [ ] **Step 3: F86/M212** — запись F86 (§27) при реальном пробеле с ценой и путём; иначе строка M212.
- [ ] **Step 4: Сканер и коммит документов** (0 новых флагов, Ran 305 OK).

---

### Task 90: финальный обзор, лиджер, критерии

- [ ] Сверка §10 спеки; финальный обзор двумя проходами; Critical/Important — один фикс-проход; Minor — в лиджер; отчёт; ничего не пушится.

---

Замеры: 93. Дефекты: следующий F86. Миноры: следующий M212. Решения: R236. Главы: Р261.
