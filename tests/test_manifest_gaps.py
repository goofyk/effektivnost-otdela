"""Паритет манифеста читателя и раскладки на фикстуре `p1c/examples/reader_gaps`.

Фикстура — минимальная выгрузка, покрывающая классы, которые читатель обязан
открывать (каталог с модулями и командой, общие коллекции, хранилище настроек,
критерий отбора, одиночный макет). Читатель должен назвать каждый файл, кроме
корневого `Configuration.xml` (его читатель не открывает — это граница паритета).

Запуск:  python -m unittest tests.test_manifest_gaps -v
"""
from __future__ import annotations

import collections
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import manifest_gaps                                                # noqa: E402
import paths                                                         # noqa: E402


class ManifestGapsTest(unittest.TestCase):
    def _fixture(self):
        local = ROOT / "local.paths.json"
        src = paths.load_local(local).get("p1c") if local.is_file() else None
        if not src:
            self.skipTest("нет пути читателя (local.paths.json)")
        base = pathlib.Path(src).parent / "examples" / "reader_gaps"
        if not base.is_dir():
            self.skipTest("фикстуры reader_gaps нет")
        sys.path.insert(0, str(src))
        from p1c.load import reader                                     # noqa: E402
        return base, reader.load_configuration_model(str(base), parallel=False)

    def test_manifest_covers_every_file_except_configuration(self):
        base, model = self._fixture()
        disk = {p.relative_to(base).as_posix() for p in base.rglob("*") if p.is_file()}
        man = {e["path"] for e in model.get("read_files", [])}
        self.assertEqual(sorted(disk - man), ["Configuration.xml"])

    def test_gaps_are_empty(self):
        base, model = self._fixture()
        self.assertEqual(manifest_gaps.gaps(base, model), {})

    def test_new_classes_present(self):
        _, model = self._fixture()
        kinds = collections.Counter(e["kind"] for e in model.get("read_files", []))
        for kind in ("common_command", "command_group", "common_picture",
                     "common_template", "common_form", "settings_storage",
                     "filter_criteria", "command_module", "common_command_module",
                     "report_template", "common_picture_data",
                     "common_picture_content", "common_template_data", "help"):
            self.assertEqual(kinds.get(kind, 0), 1, kind)


if __name__ == "__main__":
    unittest.main()
