# Итерация 27: объяснение XDTO-находок и вердикт F87 — план

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Дать XDTO-находкам замера 95 честное `why` (схема пакета), зафиксировать вердикт F87 как предел выгрузки, снять замер 96 на SSL с нулевыми закрытиями/открытиями.

**Architecture:** Ветвь `_explain_member` в `semantic.py` для пяти XDTO-видов; решения и тройки не меняются.

**Tech Stack:** Python 3.13, `p1c`, артефакт JSON, домашние обёртки/гейты.

**Spec:** `docs/superpowers/specs/2026-11-25-iteraciya-27-xdto-explanation-design.md`

## Global Constraints

- Корпус `<corpora_ssl>` = `C:\Users\goof0\Documents\ConfigSrc1C\SRC\SSL` — только чтение; **один** прогон (замер 96); опций `--os/--formats/--dir/--context-effectives/--rule-id` не применять.
- Предсказание — до прогона, после не правится.
- Нулевые закрытия и нулевые открытия: объяснение не меняет решений, кодов, текстов, координат, троек.
- Контуры: `<p1c>` `PYTHONIOENCODING=utf-8 python -B -I -X utf8 scripts/run_tests.py` → ≥120 `[ok]` / 0 `[fail]`; `<docs>` Ran 305 OK; wording 0.
- Коммиты: ASCII-транслит, `git commit -F`, `Co-Authored-By: Claude Code <noreply@anthropic.com>`; не пушить.
- База `<p1c>` HEAD `befcb5e`, `<docs>` HEAD `5d7af1a`.

## Review Focus

1. **Тройки не сдвинулись.** Сравнение 95/96: `(code, file, line)` идентичны, только `why`/`hint` XDTO-находок изменились.
2. **`why` 100 % на METHOD** остался.
3. **«Пакет» только у XDTO** — тест (г) держит прежнее модельное объяснение у обычных типов.
4. **0 закрытий / 0 открытий** — лестница не сдвинулась, подпись та же.

---

### Task 97: XDTO-семейство объяснения, тесты, замер 96

**Files:**
- Edit: `src/p1c/check/bsl/semantic.py` (константа `XDTO_TYPES`, ветвь в `_explain_member`).
- Create: `tests/check_bsl/test_xdto_explanation.py`, `<tmp>\opencode\iter18_m96_predictions.md`, `m96_task97.py`, `m96_task97_gate.py`, артефакты `m96_task97_ssl.json`/`.log`/`.err`, `m96_task97_gate.json`/`.log`/`.summary.log`.

- [ ] **Step 1: Предсказание до прогона** (`iter18_m96_predictions.md`): закрытий 0, открытий 0, всего 6 415, формная 1 209, METHOD 4 059 | 760, `why` 100 %, `stats.files` 3 092, подпись та же, артефакт > 5 147 175 b.

- [ ] **Step 2: Реализация.** В `semantic.py` найти `_explain_member` и `ROW_TYPE_MARK`; добавить `XDTO_TYPES = frozenset({"значениеxdto","объектxdto","типзначенияxdto","пакетxdto","фабрикаxdto"})`; в модельной ветви при `norm(t.name) in XDTO_TYPES` писать `why` про схему пакета и `hint`. Остальные ветви не трогать.

- [ ] **Step 3: Тесты** `tests/check_bsl/test_xdto_explanation.py` (а)–(д) по дизайну §7; прогон `python -B -I -X utf8 scripts/run_tests.py` → ≥120 `[ok]` / 0 `[fail]`.

- [ ] **Step 4: Прогон SSL** через `m96_task97.py` (один раз, timeout 3600).

- [ ] **Step 5: Гейт** `m96_task97_gate.py`: сравнение троек 95/96 (должно быть пусто), число/формная/коды/`why`/файлы/подпись; расхождение размера артефакта — строкой.

- [ ] **Step 6: Отчёт** `task-97-report.md` в каталоге плана итерации 27.

---

### Task 98: §25 свидетельства, вердикт F87, M213; коммит документов

- [ ] **Step 1:** §25 в `docs/evidence/tool-coverage.md`: что изменено в объяснении, замер 96 (0/0, `why` 100 %, размер вырос, подпись та же).
- [ ] **Step 2:** F87 (§28) дописывающей строкой — вердикт «предел выгрузки», путь XSD/платформа, решение владельца; M213 уточнён (объяснение есть, закрытие требует схем).
- [ ] **Step 3:** Сканер 0 новых флагов; `<docs>` Ran 305 OK; коммит `<docs>`.

---

### Task 99: финальный обзор, лиджер, критерии

- [ ] Сверка критериев §10 спеки; финальный обзор двумя проходами; Critical/Important — один фикс-проход; Minor — в лиджер; отчёт; ничего не пушится.

---

Замеры: 96. Дефекты: следующий F88. Миноры: следующий M214. Решения: R236. Главы: Р269.
