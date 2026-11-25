# Итерация 30: первая мерка на ERP — план

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Снять первый артефакт на крупнейшем корпусе ERP (25 118 модулей), разложить профиль, сравнить с четырьмя другими корпусами по долям, подтвердить F87 и повторить F88; без правок кода.

**Architecture:** Обёртка + гейт + один прогон CLI по corpora_erp + зонд. Код не меняется.

**Spec:** docs/superpowers/specs/2026-11-26-iteraciya-30-erp-first-measure-design.md

## Global Constraints

- Корпус corpora_erp — C:/Users/goof0/Documents/ConfigSrc1C/SRC/ERP — только чтение; один прогон (замер 99); опции --os/--formats/--dir/--context-effectives/--rule-id не применять.
- Предсказание iter18_m99_predictions.md — до прогона.
- Артефакты — только в tmp/opencode, имена m99_*.
- Контуры: p1c >=120 ok / 0 fail; docs Ran 305 OK; wording 0.
- Коммиты ASCII-транслит, git commit -F, Co-Authored-By; не пушить.
- p1c HEAD e46890b, docs HEAD f8bbb25.

## Review Focus

1. Нет падений разбора на 25 тыс. модулей.
2. why 100 % на METHOD.
3. stats.files = 25 118.
4. XDTO-домен без корреляции с 423 пакетами.
5. F88 повторяется (Форма.* неверный владелец) или нет.

---

### Task 105: обёртка, гейт, прогон ERP, артефакт

- [ ] Step 1: Предсказание до прогона: всего 55 000…95 000; METHOD >=60 %; why 100 %; формная >0; files=25118; падений 0; XDTO 3–27 % METHOD.
- [ ] Step 2: Обёртка m99_task105.py (timeout=10800) и гейт m99_task105_gate.py.
- [ ] Step 3: Прогон; rc/elapsed/stderr.
- [ ] Step 4: Гейт и зонд iter30_t105_profile.py (XDTO, Форма.*, топ-30 пар).
- [ ] Step 5: Отчёт task-105-report.md.

---

### Task 106: §28, разложение профиля, дефект/очередь

- [ ] Step 1: §28 в docs/evidence/tool-coverage.md.
- [ ] Step 2: Дефект F89 (§30) или строка M216; сверка F87/F88.
- [ ] Step 3: Сканер 0 новых флагов; docs Ran 305 OK; CRLF; коммит.

---

### Task 107: финальный обзор, лиджер, критерии

- [ ] Сверка критериев; финальный обзор; фикс-проход; Minor в лиджер.

---

Замеры: 99. Дефекты: следующий F89. Миноры: следующий M216. Решения: R236. Главы: Р275.
