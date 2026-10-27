"""Тесты проверочного контура сборки конфигурации «Эффективность отдела».

Запускаются stdlib unittest (pytest в среде заказчика не установлен — см. журнал плана):
    python -m unittest discover -s tests -v
"""
from __future__ import annotations

import contextlib
import io
import json
import pathlib
import sys
import tempfile
import types
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import counts                                                    # noqa: E402
import gate                                                      # noqa: E402
import ib_loop                                                   # noqa: E402
import paths                                                     # noqa: E402


class IbLoopTest(unittest.TestCase):
    def test_refuses_without_bin(self):
        """Без файла платформы платформа не запускается: отказ должен назвать --bin."""
        result = ib_loop.run_step("load", {"bin": "", "ib": "x", "cfg": "y", "out": "z"})
        self.assertEqual(result["code"], 2)
        self.assertIn("--bin", result["reason"])

    def test_refuses_unknown_step(self):
        result = ib_loop.run_step("nope", {"bin": "b", "ib": "x", "cfg": "y", "out": "z"})
        self.assertEqual(result["code"], 2)
        self.assertIn("шага", result["reason"])

    def test_command_for_load_is_the_observed_shape(self):
        """Порядок флагов подтверждён наблюдением: имя режима первым, затем база, затем флаги."""
        command = ib_loop.build_command("load", {"bin": "BIN", "ib": "IB", "cfg": "CFG",
                                                 "out": "OUT"})
        self.assertEqual(command, ["BIN", "DESIGNER", "/F", "IB", "/Out", "OUT",
                                   "/DisableStartupDialogs", "/LoadConfigFromFiles", "CFG"])

    def test_check_carries_five_check_keys(self):
        command = ib_loop.build_command("check", {"bin": "BIN", "ib": "IB", "out": "OUT"})
        for key in ("-Server", "-ThinClient", "-WebClient", "-ExternalConnection",
                    "-ThickClientOrdinaryApplication"):
            self.assertIn(key, command)


class CountsTest(unittest.TestCase):
    def test_compare_detects_mismatch(self):
        diff = counts.compare_counts({"Catalog": 2}, {"Catalog": 1, "Constant": 1})
        self.assertEqual(diff["mismatch"], {"Catalog": (2, 1)})
        self.assertEqual(diff["only_source"], {})
        self.assertEqual(diff["only_dump"], {"Constant": 1})

    def test_object_counts_from_a_model(self):
        model = {"collections": {"Catalogs": {"kind": "catalog", "objects": [1, 2]},
                                "Enums": {"kind": "enum", "objects": [1]}}}
        self.assertEqual(counts.counts_from_model(model), {"catalog": 2, "enum": 1})

    def test_counts_include_what_the_reader_keeps_outside_collections(self):
        """Общие модули, общие реквизиты, формы и пропущенные файлы читатель держит в других
        ключах модели. Без них сравнение с независимым счётчиком по файлам врёт: молчание
        читателя выглядело бы как «объектов нет»."""
        model = {
            "collections": {"Справочники": {"kind": "catalog", "objects": ["А", "Б"]}},
            "objects": {"catalog.А": {"forms": [{"name": "ФормаА"}]},
                        "catalog.Б": {"forms": []}},
            "common_modules": {"М1": {}, "М2": {}},
            "common_attributes": {"Р1": {}},
            "common_forms": [{"name": "Ф1"}],
            "skipped_files": [{"path": "Модуль.bsl", "error": "не разобран"}],
        }
        got = counts.counts_from_model(model)
        self.assertEqual(got["catalog"], 2)
        self.assertEqual(got["common_module"], 2)
        self.assertEqual(got["common_attribute"], 1)
        self.assertEqual(got["form_data"], 2)
        self.assertEqual(got["skipped_module_files"], 1)

    def test_object_counts_refuses_without_reader_path(self):
        """Молчаливый «читателя не нашли» неотличим от конфигурации без объектов."""
        with self.assertRaises(RuntimeError) as caught:
            counts.object_counts(".", "")
        self.assertIn("--p1c", str(caught.exception))

    def test_object_counts_wraps_reader_refusal_as_runtime_error(self):
        """Отказ читателя («раскладку определить не удалось») гейт должен читать как причину
        отказа, а не как падение прогона: наблюдение — пустой каталог выгрузки."""
        def refusing_load(root, parallel=True):
            raise ValueError("Не удалось определить раскладку")

        fake_reader = types.SimpleNamespace(load_configuration_model=refusing_load)
        fake_package = types.SimpleNamespace(reader=fake_reader)
        saved_root = sys.modules.get("p1c")
        saved_package = sys.modules.get("p1c.load")
        sys.modules["p1c"] = types.SimpleNamespace(load=fake_package)
        sys.modules["p1c.load"] = fake_package
        with tempfile.TemporaryDirectory() as tmp:
            try:
                with self.assertRaises(RuntimeError) as caught:
                    counts.object_counts(tmp, tmp)
            finally:
                if saved_root is not None:
                    sys.modules["p1c"] = saved_root
                else:
                    sys.modules.pop("p1c", None)
                if saved_package is not None:
                    sys.modules["p1c.load"] = saved_package
                else:
                    sys.modules.pop("p1c.load", None)
        self.assertIn("читатель", str(caught.exception))


class PathsTest(unittest.TestCase):
    def test_local_paths_drops_unknown_key_and_says_so(self):
        """Опечатка в имени пути не должна превращаться в необъяснимый отказ запуска."""
        with tempfile.TemporaryDirectory() as tmp:
            local = pathlib.Path(tmp) / "local.paths.json"
            local.write_text(json.dumps({"bin": "B", "binn": " typo"}), encoding="utf-8")
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                values = paths.load_local(local)
        self.assertEqual(values, {"bin": "B"})
        self.assertIn("неизвестный ключ", stderr.getvalue())

    def test_local_paths_keeps_corpora_group(self):
        with tempfile.TemporaryDirectory() as tmp:
            local = pathlib.Path(tmp) / "local.paths.json"
            local.write_text(json.dumps({"corpora_erp": "E", "corpora_uh": "U"}), encoding="utf-8")
            values = paths.load_local(local)
        self.assertEqual(values, {"corpora_erp": "E", "corpora_uh": "U"})

    def test_refuse_missing_bin_names_the_flag(self):
        self.assertIn("--bin", paths.refuse_missing_bin(""))
        self.assertEqual(paths.refuse_missing_bin(sys.executable), "")


class GateTest(unittest.TestCase):
    def test_refuses_without_cfg(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, report = gate.run(str(pathlib.Path(tmp) / "нет-такого-каталога"),
                                    str(pathlib.Path(tmp) / "gate.json"))
        self.assertEqual(code, 2)
        self.assertIn("конфигураци", report["reason"])

    def test_flags_empty_dump_when_source_has_objects(self):
        """Неудачная загрузка: источник с объектами, выгрузка — пустая конфигурация платформы."""
        self.assertTrue(gate.empty_dump_detected({"catalog": 7, "enum": 8}, {}))

    def test_does_not_flag_empty_when_both_sides_empty(self):
        """Обе стороны пусты — это не провал загрузки, это пустая конфигурация."""
        self.assertFalse(gate.empty_dump_detected({}, {}))

    def test_dump_named_konfiguratciya_against_named_source_is_a_failure(self):
        """Наблюдение B2: после отменённой загрузки платформа выгружает пустую конфигурацию
        поверх старого дампа и не затирает прежние файлы (239 файлов, свежих 3). Дамп выглядит
        полным, поэтому расхождение имени корневого объекта с исходником — признак провала."""
        self.assertTrue(gate.empty_dump_detected(
            {"catalog": 7, "enum": 8}, {"catalog": 10, "enum": 10},
            dump_name="Конфигурация", source_name="ЭффективностьОтдела"))

    def test_matching_names_are_not_a_failure(self):
        self.assertFalse(gate.empty_dump_detected(
            {"catalog": 7}, {"catalog": 7},
            dump_name="ЭффективностьОтдела", source_name="ЭффективностьОтдела"))

    def test_source_named_konfiguratciya_is_not_a_failure(self):
        """Наблюдение D: реальная конфигурация корпуса «ИИ Чат 1С/Project» сама называется
        «Конфигурация». Проверять имя по константе нельзя — это давало бы ложный провал
        зелёной сборки; сравнивать надо имя выгрузки с именем исходника."""
        counts = {"catalog": 10, "enum": 10, "role": 3}
        self.assertFalse(gate.empty_dump_detected(
            counts, dict(counts), dump_name="Конфигурация", source_name="Конфигурация"))


if __name__ == "__main__":
    unittest.main()
