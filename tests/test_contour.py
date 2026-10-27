"""Тесты проверочного контура сборки конфигурации «Эффективность отдела».

Запускаются stdlib unittest (pytest в среде заказчика не установлен — см. журнал плана):
    python -m unittest discover -s tests -v
"""
from __future__ import annotations

import contextlib
import io
import json
import pathlib
import re
import shutil
import sys
import tempfile
import time
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

    def test_ib_exists_reads_the_file_base_markers(self):
        """Признак файловой базы — маркеры каталога. По ним решаем, нужен ли create.

        Наблюдение 8.3.27: база, созданная CREATEINFOBASE File=…, содержит 1Cv8.1CD (и
        1Cv8.1CL.cfl), а не «классические» 1Cv8.8cd. Без базы /LoadConfigFromFiles даёт
        «Информационная база не обнаружена!» и код 1 — то же самое, что дал бы битый каталог
        конфигурации, поэтому различать «базы нет» и «конфигурация не читается» надо до запуска.
        """
        with tempfile.TemporaryDirectory() as tmp:
            self.assertFalse(ib_loop.ib_exists(tmp))
            (pathlib.Path(tmp) / "1Cv8.8cd").write_bytes(b"x")
            self.assertTrue(ib_loop.ib_exists(tmp))
        with tempfile.TemporaryDirectory() as tmp:
            (pathlib.Path(tmp) / "1Cv8.1CD").write_bytes(b"x")
            self.assertTrue(ib_loop.ib_exists(tmp), "наблюдённый маркер 8.3.27")
        self.assertFalse(ib_loop.ib_exists(""))

    def test_create_command_is_the_observed_shape(self):
        command = ib_loop.build_command("create", {"bin": "BIN", "ib": "IB", "out": "OUT"})
        self.assertEqual(command, ["BIN", "CREATEINFOBASE", "File=IB", "/Out", "OUT",
                                   "/DisableStartupDialogs"])


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
    def test_missing_ib_adds_the_create_step(self):
        """Цикл без базы начинался бы с загрузки и дал бы «Информационная база не обнаружена!»
        — тот же код 1, что и битый каталог конфигурации. Различать эти два случая должен
        контур, а не человек, читающий вывод."""
        self.assertEqual(gate.loop_steps(ib_ready=False), ("create", "load", "check", "dump"))
        self.assertEqual(gate.loop_steps(ib_ready=True), ("load", "check", "dump"))

    def test_each_step_writes_its_own_output_file(self):
        """Наблюдение gate-03: один файл вывода на весь цикл — диагностика загрузки исчезает,
        потому что её перезаписывает следующий шаг (у загрузки было 0 байт, и в отчёте остались
        только строки /CheckModules)."""
        outs = [gate.loop_out_path("OUT/out.txt", step) for step in gate.loop_steps(True)]
        self.assertEqual(len(set(outs)), len(outs), outs)
        for step, path in zip(gate.loop_steps(True), outs):
            self.assertIn(step, pathlib.Path(path).name)

    def test_diagnostics_keep_which_step_said_what(self):
        report = {"diagnostics": [], "diagnostics_by_step": {}}
        gate.record_diagnostics(report, "load", ["Отсутствует внутренняя информация"])
        gate.record_diagnostics(report, "check", ["Синтаксических ошибок не обнаружено!"])
        self.assertEqual(report["diagnostics_by_step"]["load"],
                         ["Отсутствует внутренняя информация"])
        self.assertEqual(report["diagnostics"],
                         ["Отсутствует внутренняя информация",
                          "Синтаксических ошибок не обнаружено!"])

    def test_timeout_is_named_as_a_step_problem_not_as_a_empty_dump(self):
        """gate-03: /LoadConfigFromFiles не завершился за 600 с и не вывел ни байта. Отчёт обязан
        назвать этот шаг, а не прятать его за «составом выгрузки»."""
        timed_out = gate.step_problem("load", {"code": 1, "timed_out": True, "seconds": 600,
                                               "bytes": 0})
        self.assertIn("load", timed_out)
        self.assertIn("ожидани", timed_out)
        self.assertIn("600", timed_out)
        self.assertIn("0 байт", timed_out)
        self.assertEqual(gate.step_problem("check", {"code": 0, "timed_out": False,
                                                     "seconds": 2, "bytes": 73}), "")
        self.assertIn("код 1", gate.step_problem("dump", {"code": 1, "timed_out": False,
                                                          "seconds": 2, "bytes": 0}))

    def test_load_timeout_stops_the_cycle_but_a_finished_load_does_not(self):
        """После убитого по ожиданию процесса база недописана: /CheckModules на такой базе в
        gate-03 дал код 0 и «Синтаксических ошибок не обнаружено!», то есть показания дальнейших
        шагов нельзя читать как доказательство. Отказ загрузки, который платформа договорала до
        конца (ненулевой код, вывод есть), наоборот, обязан дойти до выгрузки: она показывает,
        что именно осталось в базе."""
        self.assertFalse(gate.cycle_continues("load", {"code": 1, "timed_out": True}))
        self.assertFalse(gate.cycle_continues("create", {"code": 1, "timed_out": False}))
        self.assertTrue(gate.cycle_continues("load", {"code": 1, "timed_out": False}))
        self.assertTrue(gate.cycle_continues("load", {"code": 0, "timed_out": False}))
        self.assertTrue(gate.cycle_continues("check", {"code": 1, "timed_out": False}))
        self.assertTrue(gate.cycle_continues("dump", {"code": 0, "timed_out": False}))

    def test_success_lines_of_the_platform_are_not_findings(self):
        """Наблюдённые строки успешного вывода (create, check). Если считать их находками,
        зелёной итерации не будет никогда: /CheckModules печатает свою строку всегда."""
        lines = ['Создание информационной базы ("File=...") успешно завершено',
                 "Синтаксических ошибок не обнаружено!", "", "   "]
        self.assertEqual(gate.diagnostic_findings(lines), [])

    def test_platform_error_lines_are_findings(self):
        """Тексты отказов, полученные в gate-01 и gate-02, обязаны оставаться находками."""
        lines = ["Ошибка XDTO в файле - ЭффективностьОтдела.xml, при чтении свойства: Content",
                 "Отсутствует внутренняя информация (узел InternalInfo) для объекта Report.",
                 "Неверное значение перечисления - Turnover",
                 "Информационная база не обнаружена!",
                 "Синтаксических ошибок не обнаружено!"]
        findings = gate.diagnostic_findings(lines)
        self.assertEqual(len(findings), 4, findings)
        self.assertIn("Информационная база не обнаружена!", findings)

    def test_gate_refuses_a_non_canonical_rights_block_before_touching_the_platform(self):
        """Найденная причина зависания (права на перечисление) обязана находиться статическим шагом
        гейта: цикл платформы на такой конфигурации только отнимает время и молчит."""
        with tempfile.TemporaryDirectory() as tmp:
            copy = pathlib.Path(tmp) / "cfg"
            shutil.copytree(ROOT / "cfg" / "ЭффективностьОтдела", copy)
            path = copy / "Roles" / "СотрудникОтдела" / "Ext" / "Rights.xml"
            text = path.read_bytes().decode("utf-8-sig").replace("\r\n", "\n")
            marker = "\t<object>\n\t\t<name>Constant.НормаЧасовВМесяц</name>"
            self.assertIn(marker, text)
            injected = ("\t<object>\n\t\t<name>Enum.ГрейдыСпециалистов</name>\n\t\t<right>\n"
                        "\t\t\t<name>Read</name>\n\t\t\t<value>true</value>\n\t\t</right>\n"
                        "\t</object>\n" + marker)
            path.write_bytes(injected.replace("\n", "\r\n").encode("utf-8"))
            code, report = gate.run(str(copy), str(pathlib.Path(tmp) / "gate.json"),
                                    {"cfg": str(copy), "local": str(pathlib.Path(tmp) / "нет.json")})
            self.assertEqual(code, 1, report.get("reason"))
            self.assertIn("Enum", report["reason"])
            self.assertEqual(report["steps"], [], "платформу за этот отказ запускать нельзя")

    def test_the_clean_configuration_passes_the_rights_stage(self):
        """Права исправленной конфигурации чисты по измеренному канону; без `--bin` гейт обязан
        остановиться уже после этого шага, а не до него."""
        with tempfile.TemporaryDirectory() as tmp:
            source = str(ROOT / "cfg" / "ЭффективностьОтдела")
            code, report = gate.run(source, str(pathlib.Path(tmp) / "gate.json"),
                                    {"cfg": source, "local": str(pathlib.Path(tmp) / "нет.json")})
            self.assertEqual(report["rights"]["code"], 0, report["rights"]["problems"])
            self.assertEqual(code, 2, report.get("reason"))
            self.assertIn("платформ", report["reason"])

    def test_gate_refuses_when_the_dump_rights_are_not_the_source_rights(self):
        """Наблюдение gate-05: платформа выбрасывает права, равные значению по умолчанию роли, —
        в исходнике 8 блоков / 43 права, в выгрузке 6 блоков / 19 прав. Пока составы не совпадают,
        намерение роли не зафиксировано, и гейт обязан отказать даже при нулевых кодах платформы:
        коды платформы о правах молчат."""
        pattern = re.compile(r"[ \t]*<right>\s*<name>[^<]+</name>\s*<value>[^<]*</value>\s*"
                             r"</right>[ \t]*\r?\n", re.S)
        with tempfile.TemporaryDirectory() as tmp:
            source = pathlib.Path(tmp) / "cfg"
            dump = pathlib.Path(tmp) / "dump"
            shutil.copytree(ROOT / "cfg" / "ЭффективностьОтдела", source)
            shutil.copytree(source, dump)
            path = dump / "Roles" / "СотрудникОтдела" / "Ext" / "Rights.xml"
            text = path.read_bytes().decode("utf-8-sig")
            dropped, removed = pattern.subn("", text, count=1)
            self.assertEqual(removed, 1, "право в файле прав должно найтись")
            path.write_bytes(dropped.encode("utf-8"))
            local = pathlib.Path(tmp) / "local.paths.json"
            local.write_text(json.dumps({"bin": sys.executable, "ib": str(pathlib.Path(tmp) / "ib"),
                                         "dump": str(dump)}), encoding="utf-8")
            exists = ib_loop.ib_exists
            step = ib_loop.run_step
            ib_loop.ib_exists = lambda ib: True
            ib_loop.run_step = lambda name, opts: {"step": name, "code": 0, "timed_out": False,
                                                   "seconds": 1.0, "bytes": 3,
                                                   "started": time.time(), "lines": []}
            try:
                code, report = gate.run(str(source), str(pathlib.Path(tmp) / "gate.json"),
                                        {"cfg": str(source), "local": str(local)})
            finally:
                ib_loop.ib_exists = exists
                ib_loop.run_step = step
        self.assertEqual(code, 1, report.get("reason"))
        self.assertIn("прав выгрузки", report["reason"])
        immobility = report["rights_immobility"]
        self.assertEqual(immobility["code"], 1)
        self.assertEqual(len(immobility["dropped"]), 1, immobility["problems"])
        self.assertEqual(immobility["counts"]["source_rights"],
                         immobility["counts"]["dump_rights"] + 1)

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
