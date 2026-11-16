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
import paths                                                     # noqa: E402

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


# Ожидание записано ДО правки счётчика (мера Task 64: `t17_layout_counts.py` ->
# `iter17_t17_layout.log`, снята 2026-11-16 по фикстуре `p1c/examples/reader_gaps`,
# 35 файлов / 48 каталогов / 4 429 b; фикстура этим раундом не тронута).
# Что обязано появиться: девять классов манифеста читателя, у которых величины счётчика
# не было вовсе — `common_command_module`, `common_picture_content`, `common_picture_data`,
# `common_template_data`, `help`, `style`, `style_data`, `style_item`, `style_item_data`.
# Дескрипторы `StyleItems` и `Styles` ложатся в словарь папок; остальные семь — классы
# содержимого, у которых своей папки нет, и они задаются отдельными чертежами.
# Что не двинется: восемнадцать совпавших классов и две величины счётчика, которых манифест
# фикстуры не называет (`bsl_module` 8 и `files` 35). Расхождение `object_module` (счётчик 6
# против манифеста 4) — свойство чертежа `Ext/*.bsl` и остаётся названным.
# Нулевые величины: счётчик печатает только ненулевые, поэтому класс без файлов на диске
# обязан отсутствовать в словаре, а не выглядеть нулём — на фикстуре таких четырёх классов
# манифеста нет, но четыре GAP-класса без файлов (`command_descriptor`, `form_descriptor`,
# `report_template_data`, `common_attribute`) отсутствуют в счётчике именно так.
FIXTURE_KINDS_AFTER = {
    "bsl_module": 8, "catalog": 1, "command_group": 1, "command_module": 1,
    "common_command": 1, "common_command_module": 1, "common_form": 1, "common_module": 1,
    "common_picture": 1, "common_picture_content": 1, "common_picture_data": 1,
    "common_template": 1, "common_template_data": 1, "files": 35, "filter_criteria": 1,
    "form_data": 3, "form_module": 2, "help": 1, "language": 1, "object_module": 6,
    "report_template": 1, "role": 1, "role_rights": 1, "settings_storage": 1, "style": 1,
    "style_data": 1, "style_item": 2, "style_item_data": 1, "subsystem": 1,
}
FIXTURE_KINDS_ADDED = ("common_command_module", "common_picture_content", "common_picture_data",
                       "common_template_data", "help", "style", "style_data", "style_item",
                       "style_item_data")


class FixtureLayoutExpectationTest(unittest.TestCase):
    """Ожидание счётчика по фикстуре `p1c/examples/reader_gaps` — спецификация до правки.

    Фикстура выбрана потому, что на ней манифест читателя уже называет все девять классов,
    у которых у счётчика не было величины: сверка двух независимых раскладок на ней мерима
    без добавления файлов. Ожидание записано до правки `scripts/layout.py` и не подгоняется
    под неё: после правки проверяется весь словарь целиком, а не только добавленные классы.
    """

    def _fixture(self):
        local = ROOT / "local.paths.json"
        src = paths.load_local(local).get("p1c") if local.is_file() else None
        if not src:
            self.skipTest("нет пути читателя (local.paths.json)")
        base = pathlib.Path(src).parent / "examples" / "reader_gaps"
        if not base.is_dir():
            self.skipTest("фикстуры reader_gaps нет")
        return base

    def test_fixture_counter_names_every_manifest_class(self):
        base = self._fixture()
        counts = layout.layout_counts(base)
        self.assertEqual(layout.compare_expected(counts, FIXTURE_KINDS_AFTER), {}, counts)
        self.assertEqual(len(counts), len(FIXTURE_KINDS_AFTER))
        missing = [kind for kind in FIXTURE_KINDS_ADDED if kind not in counts]
        self.assertEqual(missing, [], counts)

    def test_descriptor_folders_of_the_fixture_are_named_by_the_folder_dict(self):
        """`StyleItems` (3 файла на диске: 2 дескриптора плюс `Ext/StyleItem.xml`) и `Styles`
        (2 файла: 1 дескриптор плюс `Ext/Style.xml`) входят в словарь папок, и по ним
        считаются ровно дескрипторы: 2 и 1."""
        self.assertEqual(layout.KIND_FOLDERS.get("StyleItems"), "style_item")
        self.assertEqual(layout.KIND_FOLDERS.get("Styles"), "style")
        base = self._fixture()
        self.assertEqual(len(layout._object_files(base, base / "StyleItems")), 2)
        self.assertEqual(len(layout._object_files(base, base / "Styles")), 1)


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
