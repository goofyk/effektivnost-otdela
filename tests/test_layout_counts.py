"""Тесты независимого счётчика метаданных по раскладке файлов.

Причина появления: наблюдение репозитория показало, что читатель `p1c.load` не читает папки
`Roles`, `Subsystems`, `Languages`, `SessionParameters`, `ChartsOfCharacteristicTypes`,
`CommonPictures`, `SettingsStorages` и содержимое `Templates` (COLLECTIONS_MAP в
src/p1c/load/reader.py:64-125). Гейт, построенный только на числах этой модели, не заметил бы,
что платформа выбросила все роли и подсистемы. Счётчик по раскладке файлов независим от
инструмента, и именно поэтому годится как доказательство.
"""
from __future__ import annotations

import json
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import gate                                                      # noqa: E402
import layout                                                    # noqa: E402

SAMPLE = {
    "Configuration.xml": (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<MetaDataObject xmlns="http://v8.1c.ru/8.3/MDClasses" version="2.20">\n'
        '\t<Configuration uuid="c0000000-0000-4000-8000-000000000001">\n'
        '\t\t<Properties><Name>Проба</Name></Properties>\n'
        '\t\t<ChildObjects>\n'
        '\t\t\t<Language>Русский</Language>\n'
        '\t\t\t<Subsystem>Проба</Subsystem>\n'
        '\t\t\t<Catalog>Сотрудники</Catalog>\n'
        '\t\t\t<Role>Тест</Role>\n'
        '\t\t</ChildObjects>\n'
        '\t</Configuration>\n</MetaDataObject>\n'
    ),
    "Languages/Русский.xml": '<MetaDataObject><Language/></MetaDataObject>\n',
    "Subsystems/Проба.xml": '<MetaDataObject><Subsystem/></MetaDataObject>\n',
    "Catalogs/Сотрудники.xml": '<MetaDataObject><Catalog/></MetaDataObject>\n',
    "Roles/Тест.xml": '<MetaDataObject><Role/></MetaDataObject>\n',
    "Roles/Тест/Ext/Rights.xml": '<RightsSet/>\n',
    "Catalogs/Сотрудники/Forms/ФормаЭлемента.xml": '<Form/>\n',
    "Catalogs/Сотрудники/Forms/ФормаЭлемента/Ext/Form.xml": '<Form/>\n',
    "Catalogs/Сотрудники/Forms/ФормаЭлемента/Ext/Form/Module.bsl": 'Процедура А() КонецПроцедуры\n',
    "Reports/Отчет.xml": '<MetaDataObject><Report/></MetaDataObject>\n',
    "Reports/Отчет/Templates/ОсновнаяСхемаКомпоновкиДанных.xml": '<Template/>\n',
    "Reports/Отчет/Templates/ОсновнаяСхемаКомпоновкиДанных/Ext/Template.xml": '<XDTODocument/>\n',
    "Catalogs/Сотрудники/Ext/Predefined.xml": (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<PredefinedData xmlns="http://v8.1c.ru/8.3/xcf/predef" version="2.20">\n'
        '\t<Item uuid="c0000000-0000-4000-8000-0000000000a1">\n'
        '\t\t<Name>Основной</Name>\n\t</Item>\n</PredefinedData>\n'
    ),
}


def sample_dir(root: pathlib.Path) -> None:
    for rel, text in SAMPLE.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


class LayoutCountTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.cfg = pathlib.Path(self._tmp.name)
        sample_dir(self.cfg)

    def tearDown(self):
        self._tmp.cleanup()

    def test_counts_every_kind_the_reader_does_not_read(self):
        counts = layout.layout_counts(self.cfg)
        self.assertEqual(counts["language"], 1)
        self.assertEqual(counts["subsystem"], 1)
        self.assertEqual(counts["catalog"], 1)
        self.assertEqual(counts["role"], 1)
        self.assertEqual(counts["report"], 1)

    def test_counts_form_trio_and_template_trio(self):
        counts = layout.layout_counts(self.cfg)
        self.assertEqual(counts["form_descriptor"], 1)
        self.assertEqual(counts["form_data"], 1)
        self.assertEqual(counts["form_module"], 1)
        self.assertEqual(counts["report_template"], 1)

    def test_predefined_data_is_a_class_of_its_own(self):
        """Предопределённые данные: дескриптор метаданных их не описывает (замер канона: 0 из 337
        образцов с PredefinedDataName), единственный след — сам файл Ext/Predefined.xml. Потеря
        файла не должна выглядеть как «всё в порядке с метаданными справочника»."""
        counts = layout.layout_counts(self.cfg)
        self.assertEqual(counts["predefined_data"], 1)
        self.assertEqual(counts["catalog"], 1)
        (self.cfg / "Catalogs/Сотрудники/Ext/Predefined.xml").unlink()
        self.assertNotIn("predefined_data", layout.layout_counts(self.cfg))

    def test_reads_declared_child_objects_of_configuration(self):
        declared = layout.declared_children(self.cfg)
        self.assertEqual(declared["catalog"], 1)
        self.assertEqual(declared["role"], 1)
        self.assertEqual(declared["language"], 1)

    def test_missing_role_rights_is_reported(self):
        (self.cfg / "Roles/Тест/Ext/Rights.xml").unlink()
        problems = layout.shape_problems(self.cfg, layout.layout_counts(self.cfg))
        self.assertTrue(any("Rights" in problem for problem in problems), problems)

    def test_expected_numbers_mismatch_is_a_finding(self):
        expected = {"catalog": 1, "role": 2}
        diff = layout.compare_expected(layout.layout_counts(self.cfg), expected)
        self.assertEqual(diff["role"], (1, 2))


class GateLayoutTest(unittest.TestCase):
    def test_gate_uses_layout_counts_not_only_tool_model(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = pathlib.Path(tmp) / "cfg"
            cfg.mkdir()
            sample_dir(cfg)
            expected = cfg / "expected.json"
            expected.write_text(json.dumps({"expected": {"catalog": 1, "role": 1, "language": 1}}),
                                encoding="utf-8")
            code, report = gate.check_metadata(cfg, expected)
            self.assertEqual(code, 0, report)
            self.assertEqual(report["layout"]["role"], 1)

    def test_gate_reports_the_case_the_reader_is_blind_to(self):
        """Все роли выброшены: модель p1c об этом молчит, гейт обязан сказать «расхождение»."""
        with tempfile.TemporaryDirectory() as tmp:
            cfg = pathlib.Path(tmp) / "cfg"
            cfg.mkdir()
            sample_dir(cfg)
            for path in (cfg / "Roles").rglob("*"):
                if path.is_file():
                    path.unlink()
            (cfg / "expected.json").write_text(json.dumps(
                {"expected": {"role": 1, "catalog": 1}}), encoding="utf-8")
            code, report = gate.check_metadata(cfg, cfg / "expected.json")
            self.assertEqual(code, 1)
            self.assertIn("role", report["layout_mismatch"])

    def test_incomplete_expected_numbers_are_not_a_hard_problem(self):
        """Промежуточная итерация сборки: эталон описывает всю итерацию, а объект ещё не
        дописан. Парность файлов не нарушена — цикл платформы обязан выполниться, иначе
        итерационная сборка не получит коды платформы на каждом шаге."""
        with tempfile.TemporaryDirectory() as tmp:
            cfg = pathlib.Path(tmp) / "cfg"
            cfg.mkdir()
            sample_dir(cfg)
            (cfg / "expected.json").write_text(json.dumps(
                {"expected": {"catalog": 1, "role": 5}}), encoding="utf-8")
            code, report = gate.check_metadata(cfg, cfg / "expected.json")
            self.assertEqual(code, 0, report)
            self.assertEqual(report["expected_mismatch"], {"role": (1, 5)})
            self.assertEqual(report["hard_problems"], [])


if __name__ == "__main__":
    unittest.main()
