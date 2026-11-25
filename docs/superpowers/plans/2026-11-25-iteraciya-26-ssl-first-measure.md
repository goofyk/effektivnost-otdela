# Итерация 26: первая мерка на SSL — план

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Снять первый артефакт проверки на невиданной конфигурации SSL (3 092 модулей), разложить профиль и сравнить с Пульсаром, назвав до пяти расхождений; без правок кода.

**Architecture:** Обёртка + гейт + один прогон CLI по `<corpora_ssl>`; зонд разложения по кодам/семействам/парам. Код не меняется.

**Tech Stack:** Python 3.13, `p1c.check.bsl.cli`, артефакт JSON, домашние обёртки/гейты.

**Spec:** `docs/superpowers/specs/2026-11-25-iteraciya-26-ssl-first-measure-design.md`

## Global Constraints

- Корпус `<corpora_ssl>` = `C:\Users\goof0\Documents\ConfigSrc1C\SRC\SSL` — только чтение; **один** прогон (замер 95); опций `--os/--formats/--dir/--context-effectives/--rule-id` не применять; команда как в замерах 80–94.
- Предсказание `iter18_m95_predictions.md` — до прогона, после не правится.
- Артефакты — только `<tmp>\opencode\`, имена `m95_*`.
- Контуры: `<p1c>` `PYTHONIOENCODING=utf-8 python -B -I -X utf8 scripts/run_tests.py` → ≥120 `[ok]` / 0 `[fail]`; `<docs>` Ran 305 OK; wording 0. Фикстура `examples/managed_app` не участвует в прогоне SSL.
- Коммиты: ASCII-транслит, `git commit -F`, `Co-Authored-By: Claude Code <noreply@anthropic.com>`; не пушить.
- `<p1c>` HEAD `befcb5e`, `<docs>` HEAD `c3dc205`; код и шаблоны/модель не менять.

## Review Focus

1. **Нет падений разбора.** 0 исключений в stderr прогона; артефакт валидный JSON.
2. **`why` 100 % на METHOD.** Объяснение не должно деградировать на чужом корпусе.
3. **Профиль по кодам.** METHOD доминирует; VAR/PROPERTY/CTOR не «взрываются».
4. **`stats.files`** равен числу прочитанных модулей SSL (сверить с числом `.bsl`).
5. **Честный интервал предсказания** (первый контакт — широкий, с оговоркой).

---

### Task 94: обёртка, гейт, прогон SSL, артефакт

**Files:**
- Create: `<tmp>\opencode\iter18_m95_predictions.md` (до прогона), `m95_task94.py`, `m95_task94_gate.py` и артефакты `m95_task94_ssl.json` / `.log` / `.err`, `m95_task94_gate.json` / `.log` / `.summary.log`, зонд `iter26_t94_profile.py` + лог.

- [ ] **Step 1: Предсказание до прогона.** `iter18_m95_predictions.md`: общее число в интервале **3 000…12 000** (первый контакт); METHOD доминирует (≥60 %); `why` 100 % на METHOD; формная строка > 0; `stats.files` = числу `.bsl` SSL (3 092); падений разбора 0; фикстура не участвует. Оговорка: числа — грубый потолок, не обещание.

- [ ] **Step 2: Обёртка и гейт.** `m95_task94.py` (образец `m94_task91.py`): `subprocess.run` команды
  `python -B -X utf8 -m p1c.check.bsl.cli check <corpora_ssl> --root <corpora_ssl> --format json --out <tmp>\opencode\m95_task94_ssl.json`, `timeout=3600`, `cwd=<p1c>`, `PYTHONPATH=<p1c>\src`. `m95_task94_gate.py` (образец `m94_task91_gate.py`): читает артефакт, считает总数/формную строку/коды/семейства/`why`-доли, пишет summary.

- [ ] **Step 3: Прогон.** Запустить обёртку один раз; зафиксировать rc/elapsed/stderr; артефакт на диске.

- [ ] **Step 4: Гейт и зонд.** Прогнать гейт (summary), затем `iter26_t94_profile.py` — разложение: коды, семейства METHOD, топ-30 пар «тип, имя», формная строка; сравнение долей с Пульсаром (2 663 / 573).

- [ ] **Step 5: Отчёт.** `task-94-report.md`: числа замера 95, расхождения с предсказанием, таблица профиля, до пяти расхождений с Пульсаром, команды и вывод. Статус DONE/BLOCKED/ПРЕРВАН.

---

### Task 95: §24, разложение профиля, очередь/дефекты

- [ ] **Step 1:** §24 в `docs/evidence/tool-coverage.md` — «Итерация 26: первая мерка SSL»: числа, таблица сравнения профилей (SSL vs Пульсар, по долям), топ расхождений, размер артефакта, подпись, отсутствие падений.
- [ ] **Step 2:** По найденным пробелам — запись дефекта **F87** (§28) при систематическом пробеле с ценой по SSL, иначе строки очереди §10.1 (M213+); никаких правок кода.
- [ ] **Step 3:** Сканер 0 новых флагов; `<docs>` Ran 305 OK; один коммит документов.

---

### Task 96: финальный обзор, лиджер, критерии

- [ ] Сверка критериев §7 спеки; финальный обзор двумя проходами; Critical/Important — один фикс-проход; Minor — в лиджер; отчёт; ничего не пушится.

---

Замеры: 95. Дефекты: следующий F87. Миноры: следующий M213. Решения: R236. Главы: Р267.