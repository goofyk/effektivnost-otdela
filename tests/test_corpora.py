"""Тесты выбора корпусов (scripts/corpora.py) и правила «в репозитории путей нет».

Два контракта:
1. корпуса берутся только из `local.paths.json` (ключи `corpora_*`), принимаются существующие
   каталоги, похожие на выгрузку конфигуратора, а отсутствующие и не-выгрузки сообщаются;
2. ни один код репозитория не содержит абсолютного пути окружения — иначе замер на другой машине
   не воспроизводится, и наблюдение нельзя отличить от случайного везения.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import corpora                                                   # noqa: E402

# В исходнике путь окна выглядит как буква, двоеточие и обратный слэш.
ABSOLUTE_PATH = re.compile(r"[A-Za-z]:\\")


class CorpusSelectionTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = pathlib.Path(self.tmp.name)
        self.uh = base / "UH"
        (self.uh / "Roles" / "ПолныеПрава" / "Ext").mkdir(parents=True)
        (self.uh / "Configuration.xml").write_text("x", encoding="utf-8")
        (self.uh / "Roles" / "ПолныеПрава" / "Ext" / "Rights.xml").write_text(
            "<r>1</r>", encoding="utf-8")
        (self.uh / "Roles" / "Служебная" / "Ext").mkdir(parents=True)
        (self.uh / "Roles" / "Служебная" / "Ext" / "Rights.xml").write_text(
            "<r>" + "9" * 400 + "</r>", encoding="utf-8")
        (self.uh / "Catalogs").mkdir()
        (self.uh / "Catalogs" / "Сотрудники.xml").write_text("x", encoding="utf-8")
        self.pulsar = base / "Пульсар"
        (self.pulsar / "Roles").mkdir(parents=True)
        (self.pulsar / "Roles" / "Роль.xml").write_text("x", encoding="utf-8")
        self.cf = base / "CF"
        self.cf.mkdir()
        (self.cf / "PULSAR.cf").write_text("x", encoding="utf-8")
        self.local_file = base / "local.paths.json"
        self.local_file.write_text(json.dumps({
            "corpora_uh": str(self.uh),
            "corpora_pulsar": str(self.pulsar),
            "corpora_cf": str(self.cf),
            "corpora_removed": str(base / "такого-каталога-нет"),
            "bin": str(base / "1cv8.exe"),
        }, ensure_ascii=False), encoding="utf-8")
        self.roots = corpora.dumps(str(self.local_file))
        self.addCleanup(self.tmp.cleanup)

    def test_refuses_to_read_a_corpus_path_from_anywhere_but_the_local_file(self):
        """Порядок корпусов — по имени ключа, чтобы вывод замера не зависел от файловой системы."""
        self.assertEqual([path.name for path in self.roots], ["Пульсар", "UH"],
                         [path.name for path in self.roots])

    def test_refuses_to_scan_a_directory_of_single_cf_files_as_a_corpus(self):
        """В `.cf` нет файлов метаданных и прав: замер по такому каталогу дал бы ноль находок и
        выглядел бы как «в каноне такого нет»."""
        report = corpora.report(str(self.local_file))
        self.assertIn("corpora_cf", report["not_a_dump"])
        self.assertIn("corpora_removed", report["missing"])
        self.assertEqual(report["accepted"], ["corpora_pulsar", "corpora_uh"])
        self.assertEqual(report["configured"],
                         ["corpora_cf", "corpora_pulsar", "corpora_removed", "corpora_uh"])

    def test_limit_per_root_keeps_the_measurement_repeatable(self):
        all_rights = corpora.files_named(self.roots, "Rights.xml")
        limited = corpora.files_named(self.roots, "Rights.xml", limit_per_root=1)
        self.assertEqual(len(all_rights), 2, [p.name for p in all_rights])
        self.assertEqual(len(limited), 1, [p.name for p in limited])
        self.assertEqual(corpora.relative(limited[0], self.roots),
                         "Roles/ПолныеПрава/Ext/Rights.xml")

    def test_wanted_files_takes_only_the_names_the_measurement_is_about(self):
        found = corpora.wanted_files(self.uh, ("ObjectModule.bsl", "Rights.xml"), 0)
        self.assertEqual([p.name for p in found],
                         ["Rights.xml", "Rights.xml"], [p.name for p in found])

    def test_largest_files_come_first_when_the_question_is_rights_completeness(self):
        ordered = corpora.largest(corpora.files_named(self.roots, "Rights.xml"), 1)
        self.assertEqual(ordered[0].parent.parent.name, "Служебная")


class NoEnvironmentPathsInRepositoryTest(unittest.TestCase):
    """Правило контура: путь существует как аргумент запуска или как значение local.paths.json."""

    def test_code_of_the_contour_contains_no_absolute_environment_paths(self):
        offenders = []
        for directory in ("scripts", "probe", "tests"):
            for path in sorted((ROOT / directory).rglob("*.py")):
                text = path.read_text(encoding="utf-8-sig", errors="replace")
                match = ABSOLUTE_PATH.search(text)
                if match:
                    offenders.append(path.relative_to(ROOT).as_posix())
        self.assertEqual(offenders, [],
                         "абсолютный путь в коде репозитория: " + ", ".join(offenders))

    def test_local_paths_file_is_not_tracked(self):
        ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("local.paths.json", ignore)


if __name__ == "__main__":
    unittest.main()
