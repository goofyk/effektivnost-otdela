"""Тесты наблюдения исполнения BSL-программы (scripts/exec_probe.py).

Тесты не запускают платформу: они закрепляют только то, из чего состоит прогон, — форму argv,
имена флагов, тексты программы, состав лестниц и то, что прогон передаёт в argv путь
конфигурации. Само наблюдение лежит в `reports/exec-12*.json`.

Что закреплено и почему:

1. Режим запуска стоит в argv отдельно от шаблонной части (`DESIGNER /F <иб> /Out …`), поэтому
   лестница меняет ровно одну переменную за шаг.
2. Каждый флаг варианта есть в измеренном списке имён платформы
   `p1c/src/p1c/data/test_cli_flags.json` (426 имён, платформа 8.3.27.1606). Имя, которого в
   замере нет, — наша выдумка: наблюдение с ним ничего не измеряет (так было с `/CmdLineParam`,
   которого в замере нет).
3. Текст программы не оставляет подстановочной метки и обратных слешей: в BSL обратный слеш —
   escape-символ, и путь Windows в строке BSL читается иначе, чем записан.
4. Кодирование файла программы — переменная наблюдения: `--sweep` меняет сначала её, и только
   потом режим и способ авторизации (наблюдение `runscript`: код 1 за 2.0 с при пустом выводе
   одинаково объясняется и «режим не принят», и «файл программы не прочитан»).
5. Лестница — тройка (режим, текст программы, кодирование), и соседние шаги различаются ровно
   одной позицией: иначе прогон не отвечает ни на какой вопрос (так было у пары «режим +
   кодирование» в одном шаге).
6. Контрольные прогоны (`CONTROLS`) существуют: наблюдение `runscript` неотличимо от «команда
   не принята», пока нет прогона на команде с известным исходом.
"""
from __future__ import annotations

import json
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import exec_probe                                                  # noqa: E402

# Пути здесь — условные имена, а не пути окружения: правило контура запрещает абсолютные пути
# в коде репозитория (`tests/test_corpora.py`), настоящий путь даёт `local.paths.json` или CLI.
BIN, IB, CFG = "1cv8.exe", "ib-effektivnost", "cfg-effektivnost"
SCRIPT = pathlib.Path("work/exec_program.txt")


def argv(variant: str) -> list:
    """argv варианта с фиксированными путями (платформу не запускаем)."""
    out = pathlib.Path("work/exec_out.txt")
    return exec_probe.variant_argv(variant, BIN, IB, SCRIPT, out, pathlib.Path("marker.txt"),
                                   CFG, pathlib.Path("work"))


class TestArgvShape(unittest.TestCase):
    def test_binary_comes_first(self):
        self.assertEqual(argv("runscript")[0], BIN)

    def test_designer_and_ib_are_fixed_part(self):
        head = argv("execute")
        self.assertEqual(head[1], "DESIGNER")
        self.assertEqual(head[2:4], ["/F", IB])
        self.assertEqual(head[4], "/Out")
        self.assertIn("/DisableStartupDialogs", head[:7])

    def test_program_variants_carry_exactly_one_execution_mode(self):
        """Ровно один из двух режимов исполнения, и он стоит рядом с файлом программы."""
        for variant in exec_probe.VARIANTS:
            if variant.startswith("load") or variant == "runscript-noarg":
                continue  # контрольные прогоны: команда контроля и режим без аргумента
            flags = argv(variant)
            modes = [item for item in flags if item in ("/RunScript", "/EXECUTE")]
            self.assertEqual(len(modes), 1, variant)
            script_index = flags.index(modes[0])
            self.assertEqual(flags[script_index + 1], str(SCRIPT), variant)

    def test_runscript_without_argument_has_no_script(self):
        """`runscript-noarg` — контроль «режим принят, но аргумента нет»: файл не подставляется."""
        flags = argv("runscript-noarg")
        self.assertEqual(flags[-1], "/RunScript")

    def test_control_load_variants_differ_by_their_argument(self):
        """Контроль `/LoadConfigFromFiles`: рабочий каталог, отсутствие аргумента, битый каталог."""
        ok, noarg, baddir = argv("load-ok"), argv("load-noarg"), argv("load-baddir")
        self.assertEqual(ok[ok.index("/LoadConfigFromFiles") + 1], CFG)
        self.assertEqual(noarg[-1], "/LoadConfigFromFiles")
        self.assertNotEqual(baddir[-1], CFG)
        self.assertIn("no-such-directory", baddir[-1])

    def test_runscript_and_execute_differ_only_by_mode(self):
        """Одинаковая argv, кроме имени режима: лестница меняет ровно одну переменную."""
        runscript = argv("runscript")
        execute = argv("execute")
        self.assertEqual(runscript.count("/RunScript"), 1)
        swapped = ["/EXECUTE" if item == "/RunScript" else item for item in runscript]
        self.assertEqual(swapped, execute)


class TestFlagsAreMeasured(unittest.TestCase):
    """Ни одного имени, которого нет в замере имён платформы."""

    @classmethod
    def setUpClass(cls):
        flags_path = ROOT.parent / "p1c" / "src" / "p1c" / "data" / "test_cli_flags.json"
        if not flags_path.is_file():
            raise unittest.SkipTest(f"нет замера имён платформы: {flags_path.as_posix()}")
        data = json.loads(flags_path.read_text(encoding="utf-8"))
        measured = set()
        for entry in data["files"]:
            # `names` — полный список имён вида `/Имя`, `-Имя` и `CmdLine/Имя`; остальные поля
            # записи (`distinct`, `flag_like`, `keys`) — счётчики, а не списки.
            measured.update(entry["names"])
        cls.measured = measured
        cls.keys = {name for name in measured if name.startswith("CmdLine/")}

    def test_variant_flags_are_measured(self):
        for variant in exec_probe.VARIANTS:
            for item in argv(variant):
                if isinstance(item, str) and (item.startswith("/") or item.startswith("-")):
                    name = item.split("=", 1)[0]
                    self.assertIn(name, self.measured, f"{variant}: имя {name} не измерено")

    def test_control_command_is_measured(self):
        """Контроль строится на команде, имя которой подтверждено замером (как и `/RunScript`)."""
        self.assertIn("/LoadConfigFromFiles", self.measured)
        self.assertIn("/RunScript", self.measured)

    def test_credentials_use_measured_names(self):
        flags = argv("runscript-credentials")
        self.assertIn("-User=1CTest", flags)
        self.assertIn("-PUser=1CTest", flags)
        self.assertIn("CmdLine/UserName", self.keys)
        self.assertIn("CmdLine/UserPassword", self.keys)

    def test_no_invented_names_anywhere(self):
        """Имена, которые кажутся правдоподобными, но в замере отсутствуют."""
        for invented in ("/NoConfigChanges", "/NoConfigurationChanges", "/CmdLineParam"):
            self.assertNotIn(invented, self.measured)
            for variant in exec_probe.VARIANTS:
                self.assertNotIn(invented, argv(variant), variant)


class TestProgramText(unittest.TestCase):
    def test_marker_placeholder_is_replaced(self):
        text = exec_probe.program_text(exec_probe.PROGRAMS["marker"], pathlib.Path("work/m.txt"))
        self.assertNotIn("$marker$", text)
        self.assertIn("work/m.txt", text)

    def test_no_backslash_in_program(self):
        """В BSL обратный слеш — escape; путь вписывают прямыми слешами."""
        text = exec_probe.program_text(exec_probe.PROGRAMS["marker"], pathlib.Path("work/m.txt"))
        self.assertNotIn("\\", text)

    def test_program_writes_the_marker_itself(self):
        """След программы независим от /Out: файл пишет сам BSL."""
        text = exec_probe.program_text(exec_probe.PROGRAMS["marker"], pathlib.Path("work/m.txt"))
        self.assertIn("Записать", text)

    def test_program_reads_metadata_and_prints(self):
        text = exec_probe.program_text(exec_probe.PROGRAMS["marker"], pathlib.Path("work/m.txt"))
        for fragment in ("Метаданные", "Сообщить"):
            self.assertIn(fragment, text)

    def test_every_ladder_text_is_a_distinct_program(self):
        """Каждый текст лестницы различим: разный текст — разное наблюдение."""
        texts = {kind: text for kind, text in exec_probe.PROGRAMS.items() if kind != "missing"}
        self.assertEqual(len(set(texts.values())), len(texts))
        self.assertEqual(exec_probe.PROGRAMS["missing"], "")

    def test_broken_and_runtime_text_carry_their_defect(self):
        self.assertIn('("файл прочитан";', exec_probe.PROGRAMS["broken"])
        self.assertIn("ИмениКоторогоНетВПрироде", exec_probe.PROGRAMS["runtime"])

    def test_empty_text_is_only_a_comment(self):
        """Пустая программа: ни одного оператора, только комментарий — исход без вывода."""
        lines = [line.strip() for line in exec_probe.PROGRAMS["empty"].splitlines() if line.strip()]
        self.assertEqual(lines, [line for line in lines if line.startswith("//")])

    def test_ascii_program_has_no_cyrillic_bytes(self):
        """`ascii` снимает hypothesis о кодировании без её перебора: байты программы — ASCII."""
        text = exec_probe.program_text(exec_probe.PROGRAMS["ascii"], pathlib.Path("m.txt"))
        self.assertEqual(text.encode("cp1251"), text.encode("utf-8"))
        text.encode("ascii")


class TestPrepareScript(unittest.TestCase):
    def test_script_is_written_in_the_chosen_encoding(self):
        with tempfile.TemporaryDirectory() as raw:
            work = pathlib.Path(raw)
            marker = work / exec_probe.MARKER_NAME
            for encoding in sorted(exec_probe.ENCODINGS):
                script, written = exec_probe.prepare_script(work, "runscript",
                                                            f"probe_{encoding}",
                                                            exec_probe.PROGRAMS["marker"],
                                                            encoding, marker, True)
                self.assertTrue(written)
                self.assertTrue(script.is_file())
                self.assertEqual(script.read_bytes(),
                                 exec_probe.program_text(exec_probe.PROGRAMS["marker"],
                                                         marker).encode(encoding))

    def test_missing_program_does_not_create_a_file_and_removes_a_stale_one(self):
        """`missing` — отсутствие файла: прежний файл прогона удаляется, нового не появляется."""
        with tempfile.TemporaryDirectory() as raw:
            work = pathlib.Path(raw)
            marker = work / exec_probe.MARKER_NAME
            script, _ = exec_probe.prepare_script(work, "runscript", "probe_missing",
                                                  exec_probe.PROGRAMS["marker"], "cp1251", marker,
                                                  True)
            self.assertTrue(script.is_file())
            script2, written = exec_probe.prepare_script(work, "runscript", "probe_missing",
                                                         exec_probe.PROGRAMS["missing"], "cp1251",
                                                         marker, False)
            self.assertEqual(script2, script)
            self.assertFalse(written)
            self.assertFalse(script2.exists())


class TestLadders(unittest.TestCase):
    def test_every_step_is_a_known_triple(self):
        known = set(exec_probe.VARIANTS) | set(exec_probe.NEGATIVE_CONTROLS)
        for ladder in (exec_probe.SWEEP, exec_probe.PROGRAM_LADDER, exec_probe.CONTROLS,
                       exec_probe.NEGATIVE_LADDER):
            for step in ladder:
                variant, kind, encoding = step
                self.assertIn(variant, known)
                self.assertIn(kind, exec_probe.PROGRAMS)
                self.assertIn(encoding, exec_probe.ENCODINGS)

    def test_consecutive_steps_change_exactly_one_variable(self):
        """Лестница наблюдения: соседние шаги различаются одной позицией тройки."""
        for name, ladder in (("SWEEP", exec_probe.SWEEP),
                             ("PROGRAM_LADDER", exec_probe.PROGRAM_LADDER)):
            for previous, current in zip(ladder, ladder[1:]):
                changed = [index for index in range(3) if previous[index] != current[index]]
                self.assertEqual(len(changed), 1,
                                 f"{name}: {previous} -> {current} меняет {changed}")

    def test_sweep_changes_encoding_before_mode(self):
        """Первые три шага — одно имя режима при разных кодированиях."""
        variants = [variant for variant, _, _ in exec_probe.SWEEP]
        self.assertEqual(variants[:3], ["runscript"] * 3)
        encodings = [encoding for _, _, encoding in exec_probe.SWEEP[:3]]
        self.assertEqual(len(set(encodings)), 3)

    def test_program_ladder_keeps_one_mode_and_one_encoding(self):
        """Вся лестница текстов идёт при одном режиме и одном кодировании."""
        self.assertEqual({variant for variant, _, _ in exec_probe.PROGRAM_LADDER}, {"runscript"})
        self.assertEqual({encoding for _, _, encoding in exec_probe.PROGRAM_LADDER}, {"cp1251"})

    def test_controls_are_command_with_a_known_outcome(self):
        """Контроль — известные команды: `/LoadConfigFromFiles` (подтверждён гейтом) и `/RunScript`
        без аргумента."""
        self.assertEqual([variant for variant, _, _ in exec_probe.CONTROLS],
                         ["load-ok", "load-noarg", "load-baddir", "runscript-noarg"])

    def test_encoding_labels_are_distinct(self):
        labels = list(exec_probe.ENCODINGS.values())
        self.assertEqual(len(labels), len(set(labels)))
        for label in labels:
            self.assertNotIn("-", label)

    def test_program_encodes_in_every_swept_encoding(self):
        """Ни один шаг лестницы не падает на кодировании: кириллица влезает во все три."""
        text = exec_probe.program_text(exec_probe.PROGRAMS["marker"], pathlib.Path("m.txt"))
        ascii_bytes = len(text.encode("ascii", "ignore"))
        for encoding in sorted({encoding for _, _, encoding in exec_probe.SWEEP}):
            self.assertGreater(len(text.encode(encoding)), ascii_bytes)

    def test_cp1251_and_utf8_bytes_differ_for_cyrillic(self):
        """Кодирование — наблюдаемая переменная: байты файла программы разные."""
        text = exec_probe.program_text(exec_probe.PROGRAMS["marker"], pathlib.Path("m.txt"))
        self.assertNotEqual(text.encode("cp1251"), text.encode("utf-8"))
        self.assertNotEqual(text.encode("utf-8-sig"), text.encode("utf-8"))


class TestNegativeControls(unittest.TestCase):
    """Отрицательный контроль: имя команды, которого нет в замере имён платформы."""

    @classmethod
    def setUpClass(cls):
        flags_path = ROOT.parent / "p1c" / "src" / "p1c" / "data" / "test_cli_flags.json"
        if not flags_path.is_file():
            raise unittest.SkipTest(f"нет замера имён платформы: {flags_path.as_posix()}")
        data = json.loads(flags_path.read_text(encoding="utf-8"))
        measured = set()
        for entry in data["files"]:
            measured.update(entry["names"])
        cls.measured = measured

    def test_negative_names_are_absent_from_measurement(self):
        for name in exec_probe.NEGATIVE_CONTROLS.values():
            self.assertNotIn(name, self.measured, f"{name} всё-таки измерено")

    def test_negative_variants_are_not_launch_variants(self):
        """Отрицательные контроли не смешиваются с вариантами наблюдения (`--variant`)."""
        self.assertFalse(set(exec_probe.NEGATIVE_CONTROLS) & set(exec_probe.VARIANTS))

    def test_negative_argv_carries_only_the_unrecognized_name(self):
        out_file = pathlib.Path("w/o.txt")
        for variant, name in exec_probe.NEGATIVE_CONTROLS.items():
            flags = exec_probe.variant_argv(variant, "1cv8.exe", "ib", pathlib.Path("w/p.txt"),
                                            out_file, pathlib.Path("w/m.txt"))
            self.assertEqual(flags[:7], ["1cv8.exe", "DESIGNER", "/F", "ib", "/Out",
                                         str(out_file), "/DisableStartupDialogs"], variant)
            self.assertEqual(flags[7:], [name], variant)

    def test_negative_ladder_compares_against_runscript_in_one_measurement(self):
        """`runscript` и нераспознанные имена прогоняются одним замером, одной переменой за шаг."""
        self.assertEqual([variant for variant, _, _ in exec_probe.NEGATIVE_LADDER],
                         ["runscript"] + list(exec_probe.NEGATIVE_CONTROLS))
        for previous, current in zip(exec_probe.NEGATIVE_LADDER,
                                     exec_probe.NEGATIVE_LADDER[1:]):
            changed = [index for index in range(3) if previous[index] != current[index]]
            self.assertEqual(len(changed), 1, f"{previous} -> {current}")

    def test_negative_ladder_writes_no_program_file(self):
        """Команда с нераспознанным именем не читает файл программы: лишний файл — шум."""
        for variant, _, _ in exec_probe.NEGATIVE_LADDER[1:]:
            self.assertIn(variant, exec_probe.NEGATIVE_CONTROLS)


class TestOutcomeKey(unittest.TestCase):
    """Класс исхода — то, чем контроль различает прогоны."""

    @staticmethod
    def step(code=0, timed_out=False, out_bytes=3):
        return {"code": code, "timed_out": timed_out, "bytes": out_bytes}

    def test_seconds_do_not_change_the_class(self):
        self.assertEqual(exec_probe.outcome_key(self.step()),
                         exec_probe.outcome_key(self.step()))

    def test_hang_is_a_distinct_class(self):
        self.assertNotEqual(exec_probe.outcome_key(self.step()),
                            exec_probe.outcome_key(self.step(timed_out=True)))

    def test_empty_and_non_empty_output_are_distinct(self):
        self.assertNotEqual(exec_probe.outcome_key(self.step()),
                            exec_probe.outcome_key(self.step(out_bytes=40)))

    def test_code_is_part_of_the_class(self):
        self.assertNotEqual(exec_probe.outcome_key(self.step(code=0)),
                            exec_probe.outcome_key(self.step(code=1)))


class TestMainGuards(unittest.TestCase):
    def test_main_refuses_without_bin_and_ib(self):
        missing = ROOT / "tests" / "_no-such-local-paths.json"
        self.assertEqual(exec_probe.main(["--local", str(missing), "--work", "work"]), 2)

    def test_main_refuses_controls_without_configuration_directory(self):
        """Без каталога конфигурации контроль не является контролем: известной команды нет."""
        missing = ROOT / "tests" / "_no-such-local-paths.json"
        self.assertEqual(exec_probe.main(["--local", str(missing), "--work", "work",
                                         "--bin", BIN, "--ib", IB, "--controls"]), 2)

    def test_ladders_are_distinct_from_the_variant_list(self):
        """`--all` — варианты при одном кодировании; лестницы — свои наборы шагов."""
        self.assertNotEqual(exec_probe.SWEEP, exec_probe.PROGRAM_LADDER)
        self.assertTrue(all(variant not in {v for v, _, _ in exec_probe.CONTROLS}
                            for variant, _, _ in exec_probe.SWEEP))


class TestRunPassesPathsToArgv(unittest.TestCase):
    """`run` обязан передавать каталог конфигурации и рабочий каталог в argv (иначе контроль
    строит команду с пустым аргументом)."""

    class StubProcess:
        def __init__(self, argv, **kwargs):
            self.returncode = 7

        def poll(self):
            return 7

        def terminate(self):
            pass

        def wait(self, timeout=None):
            return 7

    def test_control_variant_argv_carries_the_configuration_directory(self):
        recorded = []

        def stub(argv, **kwargs):
            recorded.append(list(argv))
            return self.StubProcess(argv, **kwargs)

        original = exec_probe.subprocess.Popen
        exec_probe.subprocess.Popen = stub
        try:
            with tempfile.TemporaryDirectory() as raw:
                result = exec_probe.run(BIN, IB, exec_probe.PROGRAMS["marker"], "load-ok",
                                        pathlib.Path(raw), timeout=1, encoding="cp1251",
                                        program_kind="marker", write_script=False, cfg=CFG)
        finally:
            exec_probe.subprocess.Popen = original
        self.assertEqual(recorded[0][recorded[0].index("/LoadConfigFromFiles") + 1], CFG)
        self.assertEqual(result["code"], 7)
        self.assertFalse(result["script_written"], "контрольный прогон не пишет файл программы")


if __name__ == "__main__":
    unittest.main()
