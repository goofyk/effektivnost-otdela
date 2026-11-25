# Итерация 28: первая мерка на LSO — план

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Снять первый артефакт на второй невиданной конфигурации LSO (2 690 модулей), разложить профиль, сравнить с SSL и Пульсаром по долям, назвать до пяти расхождений; без правок кода.

**Architecture:** Обёртка + гейт + один прогон CLI по `<corpora_lso>`; зонд разложения по кодам/семействам/парам. Код не меняется.

**Tech Stack:** Python 3.13, `p1c.check.bsl.cli`, артефакт JSON, домашние обёртки/гейты/зонды.

**Spec:** `docs/superpowers/specs/2026-11-25-iteraciya-28-lso-first-measure-design.md`

## Global Constraints

- Корпус `<corpora_lso>` = `C:\Users\goof0\Documents\ConfigSrc1C\SRC\LSO` — только чтение; **один** прогон (замер 97); опций `--os/--formats/--dir/--context-effectives/--rule-id` не применять.
- Предсказание `iter18_m97_predictions.md` — до прогона, после не правится.
- Артефакты — только `<tmp>\opencode\`, имена `m97_*`.
- Контуры: `<p1c>` `PYTHONIOENCODING=utf-8 python -B -I -X utf8 scripts/run_tests.py` → ≥120 `[ok]` / 0 `[fail]`; `<docs>` Ran 305 OK; wording 0. Фикстура `examples/managed_app` не участвует в прогоне LSO (она стабильна два замера подряд).
- Коммиты: ASCII-транслит, `git commit -F`, `Co-Authored-By: Claude Code <noreply@anthropic.com>`; не пушить.
- `<p1c>` HEAD `e46890b`, `<docs>` HEAD `c88effa`; код и шаблоны/модель не менять.

## Review Focus

1. **Нет падений разбора.** 0 исключений в stderr; артефакт валидный JSON.
2. **`why` 100 % на METHOD** на чужом корпусе.
3. **Профиль по кодам.** METHOD доминирует; VAR/PROPERTY/CTOR не «взрываются».
4. **`stats.files`** = 2 690 (число `.bsl` LSO).
5. **Честный интервал предсказания** (первый контакт с LSO).

---

### Task 99: обёртка, гейт, прогон LSO, артефакт

**Files:**
- Create: `<tmp>\opencode\iter18_m97_predictions.md` (до прогона), `m97_task99.py`, `m97_task99_gate.py`, артефакты `m97_task99_lso.json` / `.log` / `.err`, `m97_task99_gate.json` / `.log` / `.summary.log`, зонд `iter28_t99_profile.py` + лог.

- [ ] **Step 1: Предсказание до прогона.** `iter18_m97_predictions.md`: общее число **2 500…11 000** (первый контакт с LSO); METHOD ≥60 %; `why` 100 % на METHOD; формная строка > 0; `stats.files` = 2 690; падений разбора 0; XDTO-домен — предсказать есть/нет и ориентир (SSL дал 12,9 % METHOD). Оговорка: грубый потолок, не обещание.

- [ ] **Step 2: Обёртка и гейт.** `m97_task99.py` (образец `m96_task97.py`): `subprocess.run`
  `python -B -X utf8 -m p1c.check.bsl.cli check <corpora_lso> --root <corpora_lso> --format json --out <tmp>\opencode\m97_task99_lso.json`, `timeout=3600`, `cwd=<p1c>`, `PYTHONPATH=<p1c>\src`. `m97_task99_gate.py`: всего/формная/коды/семейства/`why`-доли/файлы/подпись; сверка с предсказанием.

- [ ] **Step 3: Прогон.** Один раз; rc/elapsed/stderr; артефакт на диске.

- [ ] **Step 4: Гейт и зонд.** Гейт (summary), затем `iter28_t99_profile.py`: коды, семейства METHOD, топ-30 пар, XDTO-домен; сравнение долей с SSL и Пульсаром.

- [ ] **Step 5: Отчёт.** `task-99-report.md`: числа замера 97, расхождения с предсказанием, таблица профиля, до пяти расхождений, команды. Статус DONE/BLOCKED/ПРЕРВАН.

---

### Task 100: §26, разложение профиля, дефект/очередь

- [ ] **Step 1:** §26 в `docs/evidence/tool-coverage.md` — «Итерация 28: первая мерка LSO»: числа, таблица сравнения профилей (LSO vs SSL vs Пульсар, по долям), топ расхождений, размер артефакта, подпись, отсутствие падений.
- [ ] **Step 2:** По систематическому пробелу — дефект **F88** (§29) с ценой по LSO, иначе строка очереди §10.1 (M214+); никаких правок кода.
- [ ] **Step 3:** Сканер 0 новых флагов; `<docs>` Ran 305 OK; коммит документов.

---

### Task 101: финальный обзор, лиджер, критерии

- [ ] Сверка критериев §7 спеки; финальный обзор двумя проходами; Critical/Important — один фикс-проход; Minor — в лиджер; отчёт; ничего не пушится.

---

Замеры: 97. Дефекты: следующий F88. Миноры: следующий M214. Решения: R236. Главы: Р271.
