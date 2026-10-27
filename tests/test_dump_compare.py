"""Тесты сравнения исходника и выгрузки гейта (по замеру real-прогона gate-04).

Что наблюдено реальным прогоном (`reports/gate-04.json`, `probe/dump_vs_source.py`):

- загрузка `код 0` (3 с), выгрузка `код 0` (2 с), но сравнение файлов дало `same 5`, `differ 19`,
  `only_dump: ["ConfigDumpInfo.xml"]`;
- из 19 «отличающихся» файлов 8 отличались **только завершающим переводом строки**: мы его пишем,
  платформа — нет (замер: первое различие стоит ровно на позиции, равной длине файла выгрузки);
- `ConfigDumpInfo.xml` есть во всех шести канонических выгрузках корпусов (`corpora_*`, замер
  `Test-Path` по каждому `corpora_*`), то есть это файл платформы, а не лишняя метаданная нашей
  рукописной сборки;
- остальные отличия вносит сама платформа: она дописывает свойства и переписывает состав
  (`DecimalQualifiers/Precision` -> `NumberQualifiers/Digits/FractionDigits`). Поэтому «байты не
  совпали» не является доказательством дефекта и не может быть критерием провала само по себе;
- замер gate-07: оба файла прав совпадают по длине и по составу прав, но блоки в выгрузке идут в
  другом порядке — контур называет такие файлы `reordered` отдельно от `differ`.

Контракт, который закрепляют эти тесты: различия, которые вносит платформа, контур называет
отдельно от файлов, которых не хватает.
"""
from __future__ import annotations

import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import gate                                                      # noqa: E402
import layout                                                    # noqa: E402


class DumpCompareTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = pathlib.Path(self.tmp.name)
        self.source = self.base / "cfg"
        self.dump = self.base / "dump"
        (self.source / "Catalogs").mkdir(parents=True)
        (self.dump / "Catalogs").mkdir(parents=True)
        self.addCleanup(self.tmp.cleanup)

    def write(self, root: pathlib.Path, relative: str, text: str) -> pathlib.Path:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"\xef\xbb\xbf" + text.replace("\n", "\r\n").encode("utf-8"))
        return path

    def test_trailing_newline_alone_is_not_a_difference(self):
        self.write(self.source, "Catalogs/Сотрудники.xml", "<a>1</a>\n")
        self.write(self.dump, "Catalogs/Сотрудники.xml", "<a>1</a>")
        diff = gate.file_diff(self.source, self.dump)
        self.assertEqual(diff["same"], ["Catalogs/Сотрудники.xml"], diff)
        self.assertEqual(diff["differ"], [], diff)

    def test_a_real_content_difference_is_still_reported_as_a_difference(self):
        self.write(self.source, "Catalogs/Сотрудники.xml", "<a>1</a>\n")
        self.write(self.dump, "Catalogs/Сотрудники.xml", "<a>2</a>")
        diff = gate.file_diff(self.source, self.dump)
        self.assertEqual(diff["differ"], ["Catalogs/Сотрудники.xml"], diff)
        self.assertEqual(diff["same"], [], diff)

    def test_the_file_the_platform_adds_is_named_separately_from_extra_files(self):
        self.write(self.source, "Catalogs/Сотрудники.xml", "<a>1</a>\n")
        self.write(self.dump, "Catalogs/Сотрудники.xml", "<a>1</a>\n")
        self.write(self.dump, "ConfigDumpInfo.xml", "<d>1</d>\n")
        diff = gate.file_diff(self.source, self.dump)
        self.assertEqual(diff["only_dump"], [], diff)
        self.assertEqual(diff["platform_added"], ["ConfigDumpInfo.xml"], diff)
        self.assertEqual(diff["only_source"], [], diff)

    def test_a_file_absent_from_the_dump_is_still_a_failure(self):
        self.write(self.source, "Catalogs/Сотрудники.xml", "<a>1</a>\n")
        self.write(self.source, "Catalogs/Заказы.xml", "<a>2</a>\n")
        self.write(self.dump, "Catalogs/Сотрудники.xml", "<a>1</a>\n")
        diff = gate.file_diff(self.source, self.dump)
        self.assertEqual(diff["only_source"], ["Catalogs/Заказы.xml"], diff)

    def test_blocks_the_platform_reorders_are_named_apart_from_rewritten_content(self):
        """Замер gate-07 на файлах прав: длина совпадает (4951 и 4951, 2201 и 2201), состав прав
        совпадает (`rights.immobile`: dropped [], added []), но блоки стоят в другом порядке.
        «Переписано» и «переставлено» — разные утверждения: второе дефектом не является, и путать их
        нельзя."""
        self.write(self.source, "Roles/СотрудникОтдела/Ext/Rights.xml",
                   "<object>\n\t<name>Catalog.Сотрудники</name>\n</object>\n"
                   "<object>\n\t<name>Constant.НормаЧасовВМесяц</name>\n</object>\n")
        self.write(self.dump, "Roles/СотрудникОтдела/Ext/Rights.xml",
                   "<object>\n\t<name>Constant.НормаЧасовВМесяц</name>\n</object>\n"
                   "<object>\n\t<name>Catalog.Сотрудники</name>\n</object>\n")
        diff = gate.file_diff(self.source, self.dump)
        self.assertEqual(diff["reordered"], ["Roles/СотрудникОтдела/Ext/Rights.xml"], diff)
        self.assertEqual(diff["differ"], [], diff)

    def test_reordering_plus_an_extra_line_is_a_difference_not_a_reordering(self):
        """Перестановка не должна маскировать потерянное право: если строк стало меньше — это differ."""
        self.write(self.source, "Roles/СотрудникОтдела/Ext/Rights.xml",
                   "<object>\n\t<name>Catalog.Сотрудники</name>\n\t<value>true</value>\n</object>\n"
                   "<object>\n\t<name>Constant.НормаЧасовВМесяц</name>\n</object>\n")
        self.write(self.dump, "Roles/СотрудникОтдела/Ext/Rights.xml",
                   "<object>\n\t<name>Constant.НормаЧасовВМесяц</name>\n</object>\n"
                   "<object>\n\t<name>Catalog.Сотрудники</name>\n</object>\n")
        diff = gate.file_diff(self.source, self.dump)
        self.assertEqual(diff["differ"], ["Roles/СотрудникОтдела/Ext/Rights.xml"], diff)
        self.assertEqual(diff["reordered"], [], diff)


class PlatformAddedFilesCountTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dump = pathlib.Path(self.tmp.name) / "dump"
        (self.dump / "Catalogs").mkdir(parents=True)
        (self.dump / "Catalogs" / "Сотрудники.xml").write_text("<a/>", encoding="utf-8")
        (self.dump / "ConfigDumpInfo.xml").write_text("<d/>", encoding="utf-8")
        self.addCleanup(self.tmp.cleanup)

    def test_layout_counts_can_ignore_the_files_the_platform_adds(self):
        """Иначе выгрузка всегда будет на один файл «длиннее» исходника, и гейт будет падать на
        файле, которого в конфигурации быть не может."""
        plain = layout.layout_counts(self.dump)
        ignored = layout.layout_counts(self.dump, ignore=gate.PLATFORM_ADDED_FILES)
        self.assertEqual(plain["files"], 2, plain)
        self.assertEqual(ignored["files"], 1, ignored)
        self.assertEqual(ignored["catalog"], plain["catalog"])

    def test_the_measured_name_of_the_platform_file_is_the_one_the_dumps_contain(self):
        self.assertEqual(gate.PLATFORM_ADDED_FILES, ("ConfigDumpInfo.xml",))


if __name__ == "__main__":
    unittest.main()
