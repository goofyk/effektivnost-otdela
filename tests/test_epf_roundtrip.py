"""Тесты плана наблюдения выгрузки/загрузки внешней обработки (probe/epf_roundtrip.py).

Платформу тесты не запускают: они закрепляют форму наблюдения и дисциплину лестницы. Сами замеры
лежат в `reports/epf-15-roundtrip.json`.

Что закреплено и почему:

1. Имена команд (`/DumpExternalDataProcessorOrReportToFiles`,
   `/LoadExternalDataProcessorOrReportFromFiles`) есть в измеренном списке имён платформы
   `p1c/src/p1c/data/test_cli_flags.json` — иначе наблюдение измеряет выдуманную команду.
2. Лестница из шести шагов: соседние шаги различаются ровно одной частью формы команды — именем
   команды, первым аргументом или вторым аргументом. Иначе отказ нельзя приписать одному
   изменению (так было в Task 12, когда один шаг менял сразу «режим + кодирование»).
3. Каждая часть формы команды проверена изолированно: имя команды меняется один раз, каждая из
    двух позиций аргументов — по два раза (по одному разу у выгрузки и у загрузки). Прямой порядок
    аргументов подтверждается шагом 1, отказ на перестановке — шагами 2 и 3.
4. Корневым файлом выгрузки считается только XML в корне каталога выгрузки: файлы форм лежат глубже
    (`<Имя>/Forms/...`) и загрузке не подаются. Метка `root` появляется только в шагах загрузки,
    после шага выгрузки с каталогом в arg1.
5. Относительный путь внутри выгрузки — с прямыми слешами (`as_posix`), чтобы его можно было
    сравнивать с раскладкой файловой конфигурации (`scripts/layout.py`).
"""
from __future__ import annotations

import json
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "probe"))

import epf_roundtrip                                                 # noqa: E402

FLAGS_FILE = ROOT.parent / "p1c" / "src" / "p1c" / "data" / "test_cli_flags.json"


def measured_names() -> set:
    data = json.loads(FLAGS_FILE.read_text(encoding="utf-8"))
    names = set()
    for entry in data["files"]:
        names.update(entry["names"])
    return names


class TestPlanDiscipline(unittest.TestCase):
    def test_command_names_are_measured(self):
        names = measured_names()
        for _, command, _ in epf_roundtrip.STEP_PLAN:
            self.assertIn(command, names, command)

    def test_each_step_changes_one_command_part(self):
        diffs = epf_roundtrip.plan_diffs()
        self.assertEqual(len(diffs), len(epf_roundtrip.STEP_PLAN) - 1)
        for step in diffs:
            self.assertEqual(len(step["changed"]), 1, step)
            self.assertTrue(step["single_command_part"], step)

    def test_every_part_of_the_command_form_is_isolated(self):
        """Имя команды проверено одним изменением, каждая позиция аргументов — двумя."""
        counts = {}
        for step in epf_roundtrip.plan_diffs():
            for part in step["changed"]:
                counts[part] = counts.get(part, 0) + 1
        self.assertEqual(counts, {"arg1": 2, "arg2": 2, "command": 1}, counts)

    def test_argument_order_is_proved_by_a_rejected_swap(self):
        """Подтверждённый порядок (каталог, файл) идёт первым, перестановки — следующими шагами."""
        plan = epf_roundtrip.STEP_PLAN
        self.assertEqual(plan[0][0], "dump-dir-epf")
        self.assertEqual(plan[0][2], ("outdir", "epf"))
        swapped = [step[2] for step in plan if step[1] == epf_roundtrip.DUMP]
        self.assertIn(("epf", "epf"), swapped)
        self.assertIn(("epf", "outdir"), swapped)

    def test_command_name_change_keeps_arguments(self):
        """Шаг, где меняется только имя команды, сохраняет обе позиции аргументов."""
        for step in epf_roundtrip.plan_diffs():
            if step["changed"] == ["command"]:
                left = next(item for item in epf_roundtrip.STEP_PLAN if item[0] == step["from"])
                right = next(item for item in epf_roundtrip.STEP_PLAN if item[0] == step["to"])
                self.assertEqual(left[2], right[2], step)

    def test_root_file_follows_the_dump(self):
        """Метка `root` (корневой XML выгрузки) появляется только после шага выгрузки в каталог."""
        seen_dump = False
        for name, command, labels in epf_roundtrip.STEP_PLAN:
            if "root" in labels:
                self.assertTrue(seen_dump, name)
                self.assertEqual(command, epf_roundtrip.LOAD, name)
            if command == epf_roundtrip.DUMP and labels[0] == "outdir":
                seen_dump = True

    def test_confirming_steps_are_first_and_last(self):
        names = [step[0] for step in epf_roundtrip.STEP_PLAN]
        self.assertEqual(names[0], "dump-dir-epf")
        self.assertEqual(names[-1], "load-root-target")
        last = epf_roundtrip.STEP_PLAN[-1]
        self.assertEqual(last[1], epf_roundtrip.LOAD)
        self.assertEqual(last[2], ("root", "targetdir"))


class TestHelpers(unittest.TestCase):
    def test_decode_out_prefers_utf8_with_bom(self):
        raw = "Выгрузка завершена.".encode("utf-8")
        self.assertEqual(epf_roundtrip.decode_out(b"\xef\xbb\xbf" + raw), ["Выгрузка завершена."])

    def test_root_candidates_takes_only_top_level_xml(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / "Обработка.xml").write_text("<xml/>", encoding="utf-8")
            deep = root / "Обработка" / "Forms"
            deep.mkdir(parents=True)
            (deep / "Form.xml").write_text("<xml/>", encoding="utf-8")
            (root / "note.txt").write_text("текст", encoding="utf-8")
            self.assertEqual(epf_roundtrip.root_candidates(root), ["Обработка.xml"])

    def test_tree_files_uses_forward_slashes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            deep = root / "Обработка" / "Forms"
            deep.mkdir(parents=True)
            (deep / "Module.bsl").write_text("Процедура(); КонецПроцедуры;", encoding="utf-8")
            items = epf_roundtrip.tree_files(root)
            self.assertEqual([item["path"] for item in items], ["Обработка/Forms/Module.bsl"])

    def test_missing_epf_is_a_usage_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            local = pathlib.Path(tmp) / "local.paths.json"
            local.write_text(json.dumps({"bin": "1cv8.exe", "ib": "ib", "work": tmp}),
                             encoding="utf-8")
            self.assertEqual(epf_roundtrip.main(["--local", str(local)]), 2)


if __name__ == "__main__":
    unittest.main()
