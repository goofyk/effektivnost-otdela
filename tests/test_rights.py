"""Тесты статической проверки прав ролей (scripts/rights.py).

Главная проверка — регрессия на найденном отказе загрузки: блок `<object>` с правами на
перечисление (`Enum.ГрейдыСпециалистов`) `/LoadConfigFromFiles` не договорала до конца (30–45 с,
0 байт вывода, кода нет), а p1c прав роли не читает вовсе. Контур обязан находить эту поломку
статически, до запуска платформы, и по измеренному канону, а не по догадке.
"""
from __future__ import annotations

import pathlib
import shutil
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import rights                                                    # noqa: E402

SOURCE = ROOT / "cfg" / "ЭффективностьОтдела"

# Канон как его измерил probe/corpora_rights_probe.py: видов объектов в правах много,
# а `Enum.` — нет ни одного блока.
CANON = {"rights_files": 1672, "object_blocks": 103686,
         "object_kinds": {"Catalog": 33843, "Document": 30510, "InformationRegister": 15660,
                          "Constant": 5347, "Report": 3731, "AccumulationRegister": 2097,
                          "Configuration": 1360, "SessionParameter": 812},
         "right_names": {"Read": 21132, "View": 53476, "Update": 11986, "Set": 640,
                         "Use": 5770, "TotalsControl": 2027}}

CANONICAL_RIGHTS = """<Rights>
\t<object>
\t\t<name>Catalog.Сотрудники</name>
\t\t<right>
\t\t\t<name>Read</name>
\t\t\t<value>true</value>
\t\t</right>
\t\t<right>
\t\t\t<name>View</name>
\t\t\t<value>true</value>
\t\t</right>
\t</object>
</Rights>
"""


class ParseRightsTest(unittest.TestCase):
    def test_parses_blocks_rights_and_top_flags(self):
        text = ('<Rights><setForNewObjects>false</setForNewObjects>'
                '<setForAttributesByDefault>true</setForAttributesByDefault>'
                '<independentRightsOfChildObjects>false</independentRightsOfChildObjects>'
                + CANONICAL_RIGHTS + "</Rights>")
        parsed = rights.parse_rights(text)
        self.assertEqual([obj["name"] for obj in parsed["objects"]], ["Catalog.Сотрудники"])
        self.assertEqual(parsed["objects"][0]["rights"], {"Read": "true", "View": "true"})
        self.assertEqual(parsed["flags"], {"setForNewObjects": "false",
                                           "setForAttributesByDefault": "true",
                                           "independentRightsOfChildObjects": "false"})

    def test_owner_of_a_nested_rights_name_is_the_object_that_must_exist(self):
        """В каноне права описывают и вложенные объекты (`…Command.Отчёт`): висячей считается ссылка,
        у которой нет владельца — вида и имени самого объекта."""
        self.assertEqual(rights.owner("Catalog.Сотрудники.Command.ОтчётПоСотрудникам"),
                         "Catalog.Сотрудники")
        self.assertEqual(rights.owner("Configuration.ЭффективностьОтдела"),
                         "Configuration.ЭффективностьОтдела")


class RightsProblemsTest(unittest.TestCase):
    def test_finds_rights_on_a_kind_that_never_appears_in_the_canon(self):
        """Найденный отказ загрузки: права на перечисление вешают `/LoadConfigFromFiles`."""
        files = {"Roles/СотрудникОтдела/Ext/Rights.xml": rights.parse_rights(
            '<object><name>Enum.ГрейдыСпециалистов</name>'
            '<right><name>Read</name><value>true</value></right></object>')}
        known = {"Enum.ГрейдыСпециалистов": "Enums/ГрейдыСпециалистов.xml"}
        found = rights.problems_of(files, known, CANON)
        self.assertEqual(len(found), 1, found)
        self.assertIn("Enum", found[0])
        self.assertIn("ни одного", found[0])

    def test_finds_rights_that_reference_an_object_the_configuration_does_not_have(self):
        files = {"Roles/СотрудникОтдела/Ext/Rights.xml": rights.parse_rights(
            '<object><name>Catalog.ТакогоНет</name>'
            '<right><name>Read</name><value>true</value></right></object>')}
        found = rights.problems_of(files, {"Catalog.Сотрудники": "Catalogs/Сотрудники.xml"}, CANON)
        self.assertEqual(len(found), 1, found)
        self.assertIn("ТакогоНет", found[0])
        self.assertIn("молчит", found[0])

    def test_finds_an_invented_right_name(self):
        files = {"Roles/СотрудникОтдела/Ext/Rights.xml": rights.parse_rights(
            '<object><name>Catalog.Сотрудники</name>'
            '<right><name>ЧиститьПамять</name><value>true</value></right></object>')}
        found = rights.problems_of(files, {"Catalog.Сотрудники": "Catalogs/Сотрудники.xml"}, CANON)
        self.assertEqual(len(found), 1, found)
        self.assertIn("ЧиститьПамять", found[0])

    def test_accepts_a_canonical_rights_block(self):
        files = {"Roles/СотрудникОтдела/Ext/Rights.xml": rights.parse_rights(CANONICAL_RIGHTS)}
        self.assertEqual(rights.problems_of(files, {"Catalog.Сотрудники": "x"}, CANON), [])

    def test_refuses_to_claim_absence_of_something_without_a_measured_canon(self):
        files = {"Roles/Роль/Ext/Rights.xml": rights.parse_rights(
            '<object><name>Enum.ГрейдыСпециалистов</name>'
            '<right><name>Read</name><value>true</value></right></object>')}
        found = rights.problems_of(files, {}, {})
        self.assertEqual(len(found), 1, found)
        self.assertIn("не измерен", found[0])


class ConfigurationRightsTest(unittest.TestCase):
    def test_lists_metadata_names_in_the_form_rights_use(self):
        names = rights.metadata_names(SOURCE)
        for expected in ("Configuration.ЭффективностьОтдела", "Catalog.Сотрудники",
                         "Document.ФактРаботы", "InformationRegister.ПланЗагрузки",
                         "AccumulationRegister.ЗатратыВремени", "Report.ОтчётЗагрузки",
                         "Constant.НормаЧасовВМесяц", "Enum.ГрейдыСпециалистов",
                         "CommonModule.РасчётПоказателей", "Role.СотрудникОтдела",
                         "Subsystem.ЭффективностьОтдела"):
            self.assertIn(expected, names, "нет " + expected + " из " + str(sorted(names))[:200])

    def test_the_fixed_configuration_passes_the_rights_check(self):
        """Регрессия: после того как блок прав на перечисление убран, права нашей конфигурации чисты
        по измеренному канону (`docs/canonical-rights.json`)."""
        canon = rights.load_canon()
        if not canon:
            self.skipTest("канон прав не измерен (нет docs/canonical-rights.json)")
        result = rights.check(SOURCE, canon)
        self.assertEqual(result["code"], 0, result["problems"])
        self.assertEqual(result["counts"]["rights_files"], 2, result["counts"])
        self.assertGreaterEqual(result["counts"]["rights"], 20, result["counts"])

    def test_adding_the_enum_rights_block_back_reproduces_the_load_failure_signal(self):
        """Тот самый дефект обязан находиться статически: без 30–600 с ожидания платформы."""
        with tempfile.TemporaryDirectory() as tmp:
            copy = pathlib.Path(tmp) / "cfg"
            shutil.copytree(SOURCE, copy)
            path = copy / "Roles" / "СотрудникОтдела" / "Ext" / "Rights.xml"
            text = path.read_bytes().decode("utf-8-sig").replace("\r\n", "\n")
            injected = ('\t<object>\n\t\t<name>Enum.ГрейдыСпециалистов</name>\n\t\t<right>\n'
                        '\t\t\t<name>Read</name>\n\t\t\t<value>true</value>\n\t\t</right>\n\t</object>\n'
                        + "\t<object>\n\t\t<name>Constant.НормаЧасовВМесяц</name>")
            self.assertIn("\t<object>\n\t\t<name>Constant.НормаЧасовВМесяц</name>", text)
            path.write_bytes(injected.replace("\n", "\r\n").encode("utf-8"))
            result = rights.check(copy, rights.load_canon())
            self.assertEqual(result["code"], 1, result["problems"])
            self.assertTrue(any("Enum.ГрейдыСпециалистов" in problem
                                for problem in result["problems"]), result["problems"])


if __name__ == "__main__":
    unittest.main()
