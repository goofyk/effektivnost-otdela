"""Тесты правил вырезания объекта метаданных (scripts/bisect_cfg.py) для биновидного замера.

Контракт: вырезание разрешено, только когда все ссылки на объект снимаются правилами
(файл объекта и его поддерево, декларация у родителя, пункты Content, блоки прав,
свойство-ссылка). Ссылки, которые снять нечем (типы `cfg:CatalogRef.…`, стандартные атрибуты
`Catalog.…StandardAttribute.…`), обязаны дать отказ: иначе замер путает «объект дорогой» с
«конфигурация битая после вырезания».
"""
from __future__ import annotations

import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import bisect_cfg                                                # noqa: E402

SOURCE = ROOT / "cfg" / "ЭффективностьОтдела"

# Объекты, на которые никто не ссылается типом: вырезать можно, ссылка снимается правилом.
SELF_CONTAINED = ("Report.ОтчётЗагрузки", "Document.ФактРаботы",
                  "AccumulationRegister.ЗатратыВремени", "InformationRegister.ПланЗагрузки",
                  "CommonModule.РасчётПоказателей", "Constant.НормаЧасовВМесяц")
# Объекты, на которые ссылается тип другого объекта: вырезать нельзя, пока не вырезан зависимый.
REFERENCED = ("Catalog.Сотрудники", "Enum.ГрейдыСпециалистов")


def copy_into(tmp: str) -> pathlib.Path:
    return bisect_cfg.copy_source(str(SOURCE), str(pathlib.Path(tmp) / "variant"))


def read(cfg: pathlib.Path, relative: str) -> str:
    return (cfg / relative).read_bytes().decode("utf-8-sig", "replace")


def all_text(cfg: pathlib.Path, suffixes=(".xml",)) -> str:
    return "\n".join(p.read_bytes().decode("utf-8-sig", "replace")
                     for p in cfg.rglob("*") if p.is_file() and p.suffix in suffixes)


class AllowedDropTest(unittest.TestCase):
    def test_report_files_declaration_content_and_rights_all_disappear(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = copy_into(tmp)
            result = bisect_cfg.drop_metadata(cfg, "Report.ОтчётЗагрузки")
            self.assertEqual(result["code"], 0, result.get("reason"))
            self.assertFalse((cfg / "Reports" / "ОтчётЗагрузки.xml").exists())
            self.assertFalse((cfg / "Reports" / "ОтчётЗагрузки").exists())
            configuration = read(cfg, "Configuration.xml")
            self.assertNotIn("<Report>ОтчётЗагрузки</Report>", configuration)
            self.assertIn("<Catalog>Сотрудники</Catalog>", configuration)
            self.assertNotIn("Report.ОтчётЗагрузки", all_text(cfg))

    def test_no_dangling_reference_for_every_self_contained_object(self):
        for name in SELF_CONTAINED:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                cfg = copy_into(tmp)
                result = bisect_cfg.drop_metadata(cfg, name)
                self.assertEqual(result["code"], 0, result.get("reason"))
                self.assertNotIn(name, all_text(cfg))
                kind, short = name.split(".")
                self.assertFalse((cfg / bisect_cfg.KIND_DIRECTORY[kind] / (short + ".xml")).exists())

    def test_dropping_a_register_empties_the_document_register_records(self):
        """Платформа при удалении регистра снимает его и из записей регистров документа."""
        with tempfile.TemporaryDirectory() as tmp:
            cfg = copy_into(tmp)
            result = bisect_cfg.drop_metadata(cfg, "AccumulationRegister.ЗатратыВремени")
            self.assertEqual(result["code"], 0, result.get("reason"))
            self.assertIn("<RegisterRecords/>", read(cfg, "Documents/ФактРаботы.xml"))

    def test_dropping_a_role_empties_default_roles(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = copy_into(tmp)
            result = bisect_cfg.drop_metadata(cfg, "Role.АдминистраторСистемы")
            self.assertEqual(result["code"], 0, result.get("reason"))
            self.assertIn("<DefaultRoles/>", read(cfg, "Configuration.xml"))
            self.assertNotIn("Role.АдминистраторСистемы", all_text(cfg))

    def test_form_trio_drop_empties_the_default_form_property(self):
        """Форма снимается вместе со ссылкой на неё, как это делает конфигуратор: иначе замер
        дал бы конфигурацию со ссылкой на несуществующую форму."""
        with tempfile.TemporaryDirectory() as tmp:
            cfg = copy_into(tmp)
            result = bisect_cfg.drop_metadata(cfg, "Catalog.Сотрудники.Form.ФормаЭлемента")
            self.assertEqual(result["code"], 0, result.get("reason"))
            self.assertFalse((cfg / "Catalogs" / "Сотрудники" / "Forms").exists())
            self.assertTrue((cfg / "Catalogs" / "Сотрудники" / "Ext" / "ObjectModule.bsl").is_file())
            catalog = read(cfg, "Catalogs/Сотрудники.xml")
            self.assertIn("<DefaultObjectForm/>", catalog)
            self.assertNotIn("<Form>ФормаЭлемента</Form>", catalog)
            self.assertNotIn("ФормаЭлемента", all_text(cfg))

    def test_template_drop_empties_the_main_data_composition_schema(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = copy_into(tmp)
            result = bisect_cfg.drop_metadata(cfg, "Report.ОтчётЗагрузки.Template."
                                                  "ОсновнаяСхемаКомпоновкиДанных")
            self.assertEqual(result["code"], 0, result.get("reason"))
            self.assertFalse((cfg / "Reports" / "ОтчётЗагрузки" / "Templates").exists())
            report = read(cfg, "Reports/ОтчётЗагрузки.xml")
            self.assertIn("<MainDataCompositionSchema/>", report)
            self.assertNotIn("<Template>ОсновнаяСхемаКомпоновкиДанных</Template>", report)


class RefusedDropTest(unittest.TestCase):
    def test_drop_is_refused_when_a_type_reference_survives(self):
        for name in REFERENCED:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                cfg = copy_into(tmp)
                before = all_text(cfg)
                result = bisect_cfg.drop_metadata(cfg, name)
                self.assertEqual(result["code"], 2, "вырезание должно быть отказом")
                self.assertIn(name, result["reason"])
                self.assertIn("cfg:", result["reason"])
                self.assertEqual(all_text(cfg), before, "отказ ничего не меняет в копии")
                self.assertFalse(result.get("changed", False))

    def test_unknown_object_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = copy_into(tmp)
            result = bisect_cfg.drop_metadata(cfg, "Catalog.ТакогоНет")
            self.assertEqual(result["code"], 2)
            self.assertIn("ТакогоНет", result["reason"])


class MeasurementHelperTest(unittest.TestCase):
    def test_variant_applies_every_drop_in_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            variant = bisect_cfg.build_variant(SOURCE, str(pathlib.Path(tmp) / "v"),
                                               ["Report.ОтчётЗагрузки", "Document.ФактРаботы"])
            self.assertEqual(variant["code"], 0, variant.get("reason"))
            cfg = pathlib.Path(variant["cfg"])
            self.assertNotIn("Report.ОтчётЗагрузки", all_text(cfg))
            self.assertNotIn("Document.ФактРаботы", all_text(cfg))
            self.assertIn("<Catalog>Сотрудники</Catalog>", read(cfg, "Configuration.xml"))

    def test_variant_refuses_a_bad_drop_and_names_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            variant = bisect_cfg.build_variant(SOURCE, str(pathlib.Path(tmp) / "v"),
                                               ["Catalog.Сотрудники"])
            self.assertEqual(variant["code"], 2)
            self.assertIn("Catalog.Сотрудники", variant["reason"])

    def test_file_drop_removes_exactly_one_file_and_keeps_the_rest(self):
        """`file:<путь>` нужен, чтобы различить дескриптор объекта и его Ext-файл: роль остаётся,
        прав у неё нет — и по результату замера видно, кто из них ломает загрузку."""
        with tempfile.TemporaryDirectory() as tmp:
            variant = bisect_cfg.build_variant(SOURCE, str(pathlib.Path(tmp) / "v"),
                                               ["file:Roles/СотрудникОтдела/Ext/Rights.xml"])
            self.assertEqual(variant["code"], 0, variant.get("reason"))
            cfg = pathlib.Path(variant["cfg"])
            self.assertFalse((cfg / "Roles" / "СотрудникОтдела" / "Ext"
                              / "Rights.xml").exists())
            self.assertTrue((cfg / "Roles" / "СотрудникОтдела.xml").is_file())
            self.assertTrue((cfg / "Roles" / "АдминистраторСистемы" / "Ext"
                             / "Rights.xml").is_file())

    def test_file_drop_refuses_a_missing_file_and_names_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            variant = bisect_cfg.build_variant(SOURCE, str(pathlib.Path(tmp) / "v"),
                                               ["file:Roles/ТакогоНет/Ext/Rights.xml"])
            self.assertEqual(variant["code"], 2)
            self.assertIn("ТакогоНет", variant["reason"])

    def test_module_references_are_reported_not_hidden(self):
        """Вырезание общего модуля оставляет вызовы в BSL: замер обязан это показать."""
        with tempfile.TemporaryDirectory() as tmp:
            cfg = copy_into(tmp)
            result = bisect_cfg.drop_metadata(cfg, "CommonModule.РасчётПоказателей")
            self.assertEqual(result["code"], 0, result.get("reason"))
            self.assertTrue(result["module_references_left"], "должно быть видно, кто ссылается")
            self.assertIn("РасчётПоказателей", all_text(cfg, (".bsl",)))


if __name__ == "__main__":
    unittest.main()
