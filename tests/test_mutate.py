"""Тесты механизма отрицательных прогонов (scripts/mutate.py).

Отрицательный прогон нужен потому, что положительный доказывает только «инструмент молчит».
Чтобы измерить, что p1c говорит о конкретной ошибке, нужен воспроизводимый источник ошибки:
копия конфигурации ровно с одной преднамеренной поломкой.
"""
from __future__ import annotations

import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import mutate                                                    # noqa: E402


def text(path: pathlib.Path) -> str:
    return path.read_bytes().decode("utf-8-sig", "replace")


class CopyTest(unittest.TestCase):
    def test_copy_keeps_the_same_relative_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            dst = pathlib.Path(tmp) / "copy"
            n = mutate.copy_source(str(mutate.SOURCE_CFG), str(dst))
            src_files = {p.relative_to(mutate.SOURCE_CFG).as_posix()
                         for p in pathlib.Path(mutate.SOURCE_CFG).rglob("*") if p.is_file()}
            dst_files = {p.relative_to(dst).as_posix() for p in dst.rglob("*") if p.is_file()}
            self.assertEqual(n, len(src_files))
            self.assertEqual(src_files, dst_files)


class MutationTest(unittest.TestCase):
    def test_unknown_kind_is_refused_and_names_the_known_ones(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = mutate.apply_mutation("nope", tmp)
            self.assertEqual(result["code"], 2)
            self.assertIn("nope", result["reason"])
            for kind in mutate.MUTATIONS:
                self.assertIn(kind, result["reason"])

    def test_subsystem_reference_points_to_a_missing_object(self):
        with tempfile.TemporaryDirectory() as tmp:
            mutate.copy_source(str(mutate.SOURCE_CFG), tmp)
            result = mutate.apply_mutation("subsystem_bad_content", tmp)
            self.assertEqual(result["code"], 0, result.get("reason"))
            body = text(pathlib.Path(result["file"]))
            self.assertIn(mutate.MISSING_OBJECT, body)
            self.assertIn('<xr:Item xsi:type="xr:MDObjectRef">', body)
            # ломается одно содержание подсистемы, файл остаётся тем же по количеству
            self.assertEqual(len([p for p in pathlib.Path(tmp).rglob("*") if p.is_file()]),
                             len([p for p in pathlib.Path(mutate.SOURCE_CFG).rglob("*") if p.is_file()]))

    def test_form_event_handler_procedure_disappears_from_the_module(self):
        with tempfile.TemporaryDirectory() as tmp:
            mutate.copy_source(str(mutate.SOURCE_CFG), tmp)
            result = mutate.apply_mutation("form_missing_handler", tmp)
            self.assertEqual(result["code"], 0, result.get("reason"))
            handler = result["handler"]
            descriptor = text(pathlib.Path(result["descriptor"]))
            self.assertIn("<Event name=\"OnCreateAtServer\">" + handler + "</Event>", descriptor)
            self.assertNotIn("Процедура " + handler + "(", text(pathlib.Path(result["file"])))

    def test_module_calls_a_function_that_no_module_defines(self):
        with tempfile.TemporaryDirectory() as tmp:
            mutate.copy_source(str(mutate.SOURCE_CFG), tmp)
            result = mutate.apply_mutation("unknown_function_call", tmp)
            self.assertEqual(result["code"], 0, result.get("reason"))
            body = text(pathlib.Path(result["file"]))
            self.assertIn(result["call"], body)
            self.assertNotIn(result["call"], text(pathlib.Path(result["definition"])))

    def test_every_declared_mutation_has_an_implementation(self):
        for kind in mutate.MUTATIONS:
            self.assertTrue(callable(getattr(mutate, "break_" + kind)), kind)


class SourceTest(unittest.TestCase):
    def test_source_configuration_exists_and_is_green_before_mutation(self):
        """Отрицательный прогон бессмысленно делать на конфигурации, которая сама не собирается."""
        counts = mutate.source_layout_counts()
        self.assertTrue(counts.get("files"), "нет исходной конфигурации")
        self.assertEqual(mutate.shape_problems_for_source(), [], "исходник сам имеет проблемы формы")


if __name__ == "__main__":
    unittest.main()
