"""Тесты наблюдения исполнения BSL-программы (scripts/exec_probe.py).

Тесты не запускают платформу: они закрепляют только то, из чего состоит прогон, — форму argv,
имена флагов, тексты программы, состав лестниц и то, что прогон передаёт в argv путь
конфигурации. Само наблюдение лежит в `reports/exec-12*.json`.

Что закреплено и почему:

1. Форма команды варианта — запись таблицы `VARIANT_COMMAND` (режим запуска + команда с
   аргументами-метками) и `VARIANT_TAIL` (хвост авторизации). Ровно одна команда на вариант:
   наблюдение дефекта `p1c.test.run.command()` показало, что подстановка всех 12 имён тестовой
   группы разом (`CmdLine/...` как argv-аргументы + `/TESTCLIENT` вместе с `/TESTMANAGER`) не
   является командой платформы.
2. Каждый флаг варианта есть в измеренном списке имён платформы
   `p1c/src/p1c/data/test_cli_flags.json` (426 имён, платформа 8.3.27.1606). Имя, которого в
   замере нет, — наша выдумка: наблюдение с ним ничего не измеряет (так было с `/CmdLineParam`,
   которого в замере нет). Ключи вида `CmdLine/Имя` в argv не подставляются.
3. Текст программы не оставляет подстановочной метки и обратных слешей: в BSL обратный слеш —
   escape-символ, и путь Windows в строке BSL читается иначе, чем записан.
4. Кодирование файла программы — переменная наблюдения: `--sweep` меняет сначала её, и только
   потом режим и способ авторизации (наблюдение `runscript`: код 1 за 2.0 с при пустом выводе
   одинаково объясняется и «режим не принят», и «файл программы не прочитан»).
5. Лестница — тройка (вариант, текст программы, кодирование), и соседние шаги различаются ровно
   одной позицией: иначе прогон не отвечает ни на какой вопрос (так было у пары «режим +
   кодирование» в одном шаге). У лестниц команд (`AUTH_LADDER`, `TEST_LADDER`, лестницы
   модификаторов Task 16) дополнительно проверяется, что сдвиг варианта затрагивает ровно одну
   часть формы команды и ровно ОДИН её токен; шаг с двумя токенами допустим только если он
   зафиксирован в `TOKEN_MULTI_REASON` (смена способа входа — один измеренный способ, два ключа
   таблицы имён).
6. Контрольные прогоны (`CONTROLS`) существуют: наблюдение `runscript` неотличимо от «команда
   не принята», пока нет прогона на команде с известным исходом.
7. Лестницы модификаторов (Task 16: `PREDEFINED_LADDER`, `EXTENSION_LADDER`, `LOADOPTS_LADDER`,
   `UPDATE_LADDER`): значения модификаторов берутся из измеренных множеств (`PREDEFINED_VALUES` —
   замер свойства `PredefinedDataUpdate` в корпусах, `FORMAT_VALUES` — подписанные корпусом
   значения `-Format`), а не придумываются. Варианты, способные изменить состояние ИБ, перечислены
   в `MUTATING_VARIANTS`: они не входят в `--all` и без `--allow-mutating` не запускаются (код 2).
8. Предсказания записаны в `PREDICTIONS` до прогона и имеют проверяемый источник — файл корпуса с
   цитируемой строкой или отчёт контура с названным ключом.
"""
from __future__ import annotations

import json
import os
import pathlib
import re
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


def argv(variant: str, loadlist: str = "work/exec_loadlist.txt") -> list:
    """argv варианта с фиксированными путями (платформу не запускаем).

    `loadlist` подставлен фиксированным именем: у варианта `-listFile <файл>` аргумент обязан быть
    непустым, иначе наблюдение сравнивает «опция без значения» с «опция со значением» неверно.
    """
    out = pathlib.Path("work/exec_out.txt")
    return exec_probe.variant_argv(variant, BIN, IB, SCRIPT, out, pathlib.Path("marker.txt"),
                                   CFG, pathlib.Path("work"), loadlist)


class TestArgvShape(unittest.TestCase):
    def test_binary_comes_first(self):
        self.assertEqual(argv("runscript")[0], BIN)

    def test_designer_and_ib_are_fixed_part(self):
        head = argv("execute")
        self.assertEqual(head[1], "DESIGNER")
        self.assertEqual(head[2:4], ["/F", IB])
        self.assertEqual(head[4], "/Out")
        self.assertIn("/DisableStartupDialogs", head[:7])

    def test_every_variant_carries_exactly_one_command(self):
        """Один вариант — одно имя команды. Подстановка всех имён группы разом (как в
        `p1c.test.run.command()`) — дефект, и в этой таблице он не воспроизводится."""
        for variant in exec_probe.VARIANTS:
            signature = exec_probe.variant_signature(variant)
            self.assertIn(signature["mode"], sorted(exec_probe.LAUNCH_MODES), variant)
            self.assertLessEqual(len(signature["names"]), 1, f"{variant}: больше одной команды")

    def test_launch_modes_are_documented_by_origin(self):
        """Каждый разрешённый режим имеет источник: прогон контура или цитату корпуса. Режим,
        источник которого не записан, наблюдением не считается (`CONFIG` взят из макета
        обновления корпуса УХ, а не выдуман)."""
        for mode, origin in exec_probe.LAUNCH_MODES.items():
            self.assertTrue(origin.strip(), mode)
        for variant in exec_probe.VARIANTS:
            mode = exec_probe.variant_signature(variant)["mode"]
            self.assertIn(mode, exec_probe.LAUNCH_MODES, f"{variant}: режим {mode}")

    def test_variants_without_a_command_are_named_explicitly(self):
        """Пустая команда допустима только для названных вариантов (режим без команды)."""
        empty = [variant for variant in exec_probe.VARIANTS
                 if not exec_probe.variant_signature(variant)["names"]]
        self.assertEqual(sorted(empty), sorted(exec_probe.NO_COMMAND_VARIANTS))

    def test_launch_mode_comes_from_the_table(self):
        for variant in exec_probe.VARIANTS:
            self.assertEqual(argv(variant)[1], exec_probe.VARIANT_COMMAND[variant][0], variant)

    def test_script_file_follows_its_command(self):
        """Файл программы стоит сразу за именем команды, которое его читает."""
        for variant in exec_probe.VARIANTS:
            if not exec_probe.needs_script(variant):
                continue
            flags = argv(variant)
            name = exec_probe.variant_signature(variant)["names"][0]
            self.assertEqual(flags[flags.index(name) + 1], str(SCRIPT), variant)

    def test_variants_without_a_script_do_not_receive_it(self):
        """`-TestOnly`, `/AllowExecuteScheduledJobs` и контроли файл программы не читают."""
        for variant in exec_probe.VARIANTS:
            if exec_probe.needs_script(variant):
                continue
            self.assertNotIn(str(SCRIPT), argv(variant), variant)

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
        """Пара `-User`/`-Pwd` (оба имени есть в замере) подставлена одинаково всем вариант
        авторизации; `-PUser`/`-PPwd` не подставляются: в таблице имён они стоят в группе
        `PUser PPwd PSrv PPort NoProxy Proxy` — доступ к серверу приложений и прокси, а не к ИБ."""
        for variant in ("runscript-credentials", "load-credentials"):
            flags = argv(variant)
            self.assertIn("-User=1CTest", flags, variant)
            self.assertIn("-Pwd=1CTest", flags, variant)
            for server_only in ("-PUser", "-PPwd", "-PSrv", "-PPort"):
                self.assertNotIn(server_only, [item.split("=", 1)[0] for item in flags], variant)
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
    LADDERS = (("SWEEP", exec_probe.SWEEP),
               ("PROGRAM_LADDER", exec_probe.PROGRAM_LADDER),
               ("CONTROLS", exec_probe.CONTROLS),
               ("NEGATIVE_LADDER", exec_probe.NEGATIVE_LADDER),
               ("AUTH_LADDER", exec_probe.AUTH_LADDER),
               ("TEST_LADDER", exec_probe.TEST_LADDER))

    def test_every_step_is_a_known_triple(self):
        known = set(exec_probe.VARIANTS) | set(exec_probe.NEGATIVE_CONTROLS)
        for _name, ladder in self.LADDERS:
            for step in ladder:
                variant, kind, encoding = step
                self.assertIn(variant, known)
                self.assertIn(kind, exec_probe.PROGRAMS)
                self.assertIn(encoding, exec_probe.ENCODINGS)

    def test_consecutive_steps_change_exactly_one_variable(self):
        """Лестница наблюдения: соседние шаги различаются одной позицией тройки."""
        for name, ladder in self.LADDERS:
            for previous, current in zip(ladder, ladder[1:]):
                changed = [index for index in range(3) if previous[index] != current[index]]
                self.assertEqual(len(changed), 1,
                                 f"{name}: {previous} -> {current} меняет {changed}")

    def test_reported_diffs_agree_with_the_ladder(self):
        """Дисциплина лестницы считается по лестнице и попадает в отчёт: одиночная позиция
        тройки на шаг и одиночная часть формы команды (для лестниц команд)."""
        for name, ladder in self.LADDERS:
            diffs = exec_probe.ladder_step_diffs(ladder)
            self.assertEqual(len(diffs), len(ladder), name)
            self.assertTrue(all(step["single_variable"] for step in diffs), name)
            self.assertTrue(all(step["single_command_part"] for step in diffs), name)
            # Первая запись — эталон сравнения, сравнения с предыдущим шагом у неё нет.
            self.assertEqual(diffs[0]["from"], "", name)
            self.assertEqual(diffs[0]["changed_triple"], [], name)
            for step, (previous, current) in zip(diffs[1:], zip(ladder, ladder[1:])):
                self.assertEqual((step["from"], step["to"]), (previous[0], current[0]), name)
                self.assertEqual(len(step["changed_triple"]), 1, name)

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
        """Контроль — известные команды (`/LoadConfigFromFiles`: подтверждён гейтом код 0, без
        аргумента, с битым каталогом) рядом со спорной `/RunScript` (без аргумента и с файлом).
        Порядок фиксируется: соседние шаги различаются одной частью формы команды, поэтому исход
        спорной команды нельзя приписать сразу двум изменениям."""
        self.assertEqual([variant for variant, _, _ in exec_probe.CONTROLS],
                         ["runscript", "runscript-noarg", "load-noarg", "load-ok", "load-baddir"])
        commands = [exec_probe.variant_signature(variant)["names"][0]
                    for variant, _, _ in exec_probe.CONTROLS]
        self.assertEqual(commands,
                         ["/RunScript", "/RunScript", "/LoadConfigFromFiles",
                          "/LoadConfigFromFiles", "/LoadConfigFromFiles"])
        self.assertEqual([exec_probe.variant_signature(variant)["args"]
                          for variant, _, _ in exec_probe.CONTROLS],
                         [(exec_probe.SCRIPT_ARG,), (), (), (exec_probe.CFG_ARG,),
                          (exec_probe.BADDIR_ARG,)])

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


class TestCommandLadders(unittest.TestCase):
    """Лестницы команд (`--auth`, `--test`): меняется ровно одна часть формы команды."""

    def test_auth_ladder_keeps_the_working_command(self):
        """Команда остаётся заведомо рабочей (`/LoadConfigFromFiles` с каталогом конфигурации)."""
        for variant, _kind, _encoding in exec_probe.AUTH_LADDER:
            signature = exec_probe.variant_signature(variant)
            self.assertEqual(signature["mode"], "DESIGNER", variant)
            self.assertEqual(signature["names"], ("/LoadConfigFromFiles",), variant)
            self.assertEqual(signature["args"], (exec_probe.CFG_ARG,), variant)

    def test_auth_ladder_starts_from_the_reference_and_changes_only_the_tail(self):
        self.assertEqual(exec_probe.AUTH_LADDER[0][0], "load-ok")
        diffs = exec_probe.ladder_step_diffs(exec_probe.AUTH_LADDER)
        for step in diffs[1:]:
            self.assertEqual(step["changed_command"], ["tail"],
                             f"{step['from']} -> {step['to']}")

    def test_auth_ladder_covers_the_measured_authorization_names(self):
        tails = [exec_probe.variant_signature(variant)["tail"]
                 for variant, _kind, _encoding in exec_probe.AUTH_LADDER]
        flat = {item.split("=", 1)[0] for tail in tails for item in tail}
        self.assertEqual(flat, {"/authoff", "-AllUsers", "-CurrentUser", "-User", "-Pwd"})
        self.assertEqual(tails[0], (), "эталонный шаг идёт без хвоста авторизации")

    def test_test_ladder_opens_with_the_launch_mode_pair(self):
        """Первый шаг сравнивает `DESIGNER` и `ENTERPRISE` как единственную часть команды."""
        variants = [variant for variant, _kind, _encoding in exec_probe.TEST_LADDER]
        self.assertEqual(variants[:3], ["runscript", "enterprise-runscript", "runscript"])
        diffs = exec_probe.ladder_step_diffs(exec_probe.TEST_LADDER)
        self.assertEqual(diffs[1]["changed_command"], ["mode"])
        self.assertEqual(diffs[2]["changed_command"], ["mode"])

    def test_test_ladder_carries_the_measured_test_group_names(self):
        """Имена группы `test` замера, которые подставляют в argv как флаги."""
        names = {name for variant, _kind, _encoding in exec_probe.TEST_LADDER
                 for name in exec_probe.variant_signature(variant)["names"]}
        for expected in ("/TESTCLIENT", "/TESTMANAGER", "-testFile", "-testOut", "-TestOnly"):
            self.assertIn(expected, names)
        self.assertIn("/RunScript", names, "лестница обязана включать базовую сигнатуру")

    def test_command_keys_never_enter_argv(self):
        """`CmdLine/Имя` — ключи конфигурации командной строки, а не argv-аргументы.
        Наблюдение `p1c.test.run.command()` показало: 10 таких ключей в argv дают код 1."""
        for variant in tuple(exec_probe.VARIANT_COMMAND) + tuple(exec_probe.NEGATIVE_CONTROLS):
            for item in exec_probe.variant_argv(variant, BIN, IB, SCRIPT,
                                                pathlib.Path("w/o.txt"), pathlib.Path("w/m.txt"),
                                                CFG, pathlib.Path("work")):
                self.assertFalse(str(item).startswith("CmdLine/"), variant)

    def test_main_refuses_auth_ladder_without_configuration_directory(self):
        """Как и `--controls`: без каталога конфигурации эталонной команды нет.
        (`--test` не проверяют: его лестница не содержит команды загрузки, и отказ тут же
        означал бы, что тест запустил бы платформу.)"""
        missing = ROOT / "tests" / "_no-such-local-paths.json"
        self.assertEqual(exec_probe.main(["--local", str(missing), "--work", "work",
                                          "--bin", BIN, "--ib", IB, "--auth"]), 2)


class TestModifierLadders(unittest.TestCase):
    """Лестницы Task 16 (`--predefined`, `--extensions`, `--loadopts`, `--update`, `--modes`).
    Отвечают за то, что шаг приписывается ровно одному изменённому токену команды."""

    LADDERS = (("PREDEFINED_LADDER", exec_probe.PREDEFINED_LADDER),
               ("EXTENSION_LADDER", exec_probe.EXTENSION_LADDER),
               ("LOADOPTS_LADDER", exec_probe.LOADOPTS_LADDER),
               ("UPDATE_LADDER", exec_probe.UPDATE_LADDER),
               ("MODE_LADDER", exec_probe.MODE_LADDER))

    def test_every_ladder_starts_from_the_reference_with_a_known_outcome(self):
        """Эталонный шаг — `load-ok`: его код 0 подтверждён прогонами гейта, поэтому дальше
        сравнение идёт с известным исходом, а не с первым попавшимся прогоном."""
        for name, ladder in self.LADDERS:
            self.assertEqual(ladder[0][0], "load-ok", name)
            diffs = exec_probe.ladder_step_diffs(ladder)
            self.assertEqual(diffs[0]["from"], "", name)
            self.assertEqual(diffs[0]["command_tokens"], [], name)

    def test_every_step_changes_exactly_one_command_token(self):
        for name, ladder in self.LADDERS:
            for step in exec_probe.ladder_step_diffs(ladder)[1:]:
                tokens = step["command_tokens"]
                self.assertEqual(len(tokens), 1,
                                 f"{name}: {step['from']} -> {step['to']} меняет {tokens}")
                # Изменённая часть формы команды — ровно одна, и она же стоит в токене.
                self.assertEqual(step["changed_command"], [tokens[0]["part"]],
                                 f"{name}: {step['from']} -> {step['to']}")

    def test_ladder_steps_change_exactly_one_triple_position(self):
        for name, ladder in self.LADDERS:
            for previous, current in zip(ladder, ladder[1:]):
                changed = [index for index in range(3) if previous[index] != current[index]]
                self.assertEqual(len(changed), 1, f"{name}: {previous} -> {current}")

    def test_modifier_ladders_have_no_multi_token_step(self):
        """Исключения `TOKEN_MULTI_REASON` (смена способа входа) в этих лестницах не нужны: там
        меняется одно имя флага или одно его значение."""
        for name, ladder in self.LADDERS:
            pairs = {(step["from"], step["to"])
                     for step in exec_probe.ladder_step_diffs(ladder)[1:]}
            self.assertFalse(pairs & set(exec_probe.TOKEN_MULTI_REASON), name)

    def test_multi_token_steps_of_every_ladder_are_documented(self):
        """Ни необъяснённого шага с двумя токенами, ни устаревшей записи исключения."""
        all_ladders = (exec_probe.SWEEP, exec_probe.PROGRAM_LADDER, exec_probe.CONTROLS,
                       exec_probe.NEGATIVE_LADDER, exec_probe.AUTH_LADDER, exec_probe.TEST_LADDER,
                       *(ladder for _name, ladder in self.LADDERS))
        used = set()
        for ladder in all_ladders:
            for step in exec_probe.ladder_step_diffs(ladder)[1:]:
                if len(step["command_tokens"]) > 1:
                    pair = (step["from"], step["to"])
                    self.assertIn(pair, exec_probe.TOKEN_MULTI_REASON,
                                  f"{pair}: {step['command_tokens']}")
                    used.add(pair)
        self.assertEqual(used, set(exec_probe.TOKEN_MULTI_REASON),
                         "запись `TOKEN_MULTI_REASON` не встречается ни в одной лестнице")

    def test_mode_ladder_changes_only_the_launch_mode(self):
        """`load-ok` -> `config-load-ok`: команда и аргументы те же, сдвигается только режим.
        Без этой лестницы вариант `config-load-ok` не доставался бы ни одним прогоном."""
        step = exec_probe.ladder_step_diffs(exec_probe.MODE_LADDER)[1]
        self.assertEqual(step["changed_command"], ["mode"])
        self.assertEqual(step["command_tokens"],
                         [{"part": "mode", "position": 0, "from": "DESIGNER", "to": "CONFIG"}])
        reference = exec_probe.variant_signature("load-ok")
        config = exec_probe.variant_signature("config-load-ok")
        self.assertEqual(config["mode"], "CONFIG")
        for part in ("names", "args", "tail"):
            self.assertEqual(config[part], reference[part], part)

    def test_update_ladder_ends_on_the_canonical_config_form(self):
        """Канон макета обновления корпуса: `/UpdateDBCfg -server`, CONFIG-форма — в УХ-версии."""
        signatures = [exec_probe.variant_signature(variant)
                      for variant, _kind, _encoding in exec_probe.UPDATE_LADDER]
        self.assertEqual([item["mode"] for item in signatures],
                         ["DESIGNER"] * (len(signatures) - 1) + ["CONFIG"])
        self.assertEqual(signatures[-1]["names"], ("/UpdateDBCfg",))
        self.assertEqual(signatures[-1]["tail"], ("-Server",))
        self.assertIn("CONFIG", exec_probe.LAUNCH_MODES)

    def test_each_ladder_is_named_by_its_own_option(self):
        """Наблюдение вызывают опцией, а не «как-нибудь»: иначе лестницу нельзя повторить."""
        text = (ROOT / "scripts" / "exec_probe.py").read_text(encoding="utf-8")
        for option in ("--predefined", "--extensions", "--loadopts", "--update", "--modes"):
            self.assertIn(f'"{option}"', text, option)

    def test_ladder_ok_answers_for_the_discipline_only(self):
        """Код ломает только необъяснённый шаг с двумя токенами; состав исходов — в отчёте."""
        base = {"ladder_single_variable": True, "ladder_single_command_part": True}
        self.assertTrue(exec_probe.ladder_ok(dict(base, ladder_multi_token_documented=True)))
        self.assertFalse(exec_probe.ladder_ok(dict(base, ladder_multi_token_documented=False)))


class TestModifierValuesAreMeasured(unittest.TestCase):
    """Значения модификаторов взяты из измеренных множеств: корпусных значений свойства
    `PredefinedDataUpdate` и подписанного корпусом БСП описания опций `-Format`/`-Extension`."""

    def test_predefined_values_come_from_the_corpora_measurement(self):
        allowed = set(exec_probe.PREDEFINED_VALUES) | {exec_probe.BOGUS_VALUE}
        variants = [item for item in exec_probe.VARIANTS if item.startswith("load-predefined")]
        self.assertTrue(variants)
        for variant in variants:
            tail = exec_probe.variant_signature(variant)["tail"]
            self.assertTrue(tail, variant)
            self.assertEqual(tail[0].split("=", 1)[0], "/SetPredefinedDataUpdate", variant)
            values = ([tail[0].split("=", 1)[1]] if "=" in tail[0] else list(tail[1:]))
            for value in values:
                self.assertIn(value, allowed, f"{variant}: значение {value} не измерено")

    def test_format_values_come_from_the_canonical_description(self):
        """Каждое измеренное значение (`Hierarchical`, `Plain`) и вымышленное прогоняются,
        `-Format` при этом стоит после `-listFile`: канон связывает формат с частичной загрузкой."""
        allowed = set(exec_probe.FORMAT_VALUES) | {exec_probe.BOGUS_VALUE}
        seen = set()
        variants = [item for item in exec_probe.VARIANTS if item.startswith("load-format")]
        self.assertTrue(variants)
        for variant in variants:
            tail = list(exec_probe.variant_signature(variant)["tail"])
            self.assertEqual(tail[0], "-listFile", variant)
            self.assertLess(tail.index("-Format"), len(tail), variant)
            if len(tail) > tail.index("-Format") + 1:
                value = tail[tail.index("-Format") + 1]
                self.assertIn(value, allowed, f"{variant}: значение {value} не измерено")
                seen.add(value)
        self.assertEqual(seen, allowed, "лестница обязана прогнать каждое измеренное значение")

    def test_extension_argument_is_a_placeholder_or_the_bogus_name(self):
        for variant in ("load-extension-flag", "load-extension-bogus-name", "load-extension-cfgdir",
                        "load-extension-baddir", "load-allextensions-flag",
                        "load-allextensions-baddir"):
            tail = list(exec_probe.variant_signature(variant)["tail"])
            self.assertIn(tail[0], ("-Extension", "-AllExtensions"), variant)
            for value in tail[1:]:
                self.assertIn(value, (exec_probe.CFG_ARG, exec_probe.BADDIR_ARG,
                                      exec_probe.BOGUS_EXTENSION_NAME),
                              f"{variant}: значение {value} не измерено")

    def test_files_value_is_a_measured_root_file_name(self):
        """`Configuration.xml` — имя корневого файла выгрузки (замер раскладки), а не придуманное."""
        self.assertEqual(exec_probe.LOAD_FILE_ARG, "Configuration.xml")
        for variant in ("load-files-onefile", "load-listfile-onefile"):
            self.assertIn(exec_probe.LOAD_FILE_ARG,
                          exec_probe.variant_signature(variant)["tail"], variant)

    def test_bogus_values_are_absent_from_the_measured_sets(self):
        """Вымышленное значение обязано быть вымышленным: иначе отрицательный контроль внутри
        лестницы совпадает с настоящим значением и ничего не различает."""
        self.assertNotIn(exec_probe.BOGUS_VALUE, exec_probe.PREDEFINED_VALUES)
        self.assertNotIn(exec_probe.BOGUS_VALUE, exec_probe.FORMAT_VALUES)
        self.assertNotIn(exec_probe.BOGUS_EXTENSION_NAME, exec_probe.PREDEFINED_VALUES)
        self.assertNotIn(exec_probe.BOGUS_EXTENSION_NAME, exec_probe.PLACEHOLDER_ARGS)

    def test_measured_sets_are_non_empty_and_without_duplicates(self):
        for values in (exec_probe.PREDEFINED_VALUES, exec_probe.FORMAT_VALUES):
            self.assertTrue(values)
            self.assertEqual(len(values), len(set(values)))

    def test_tail_placeholders_are_substituted_too(self):
        """Метки подставляют и в хвост, а не только в шаблон команды: иначе модификатор нельзя
        передать вовсе (`-Extension cfg`, `-listFile listfile`, `-Format` без значения)."""
        flags = argv("load-extension-cfgdir")
        self.assertIn(CFG, flags)
        self.assertNotIn(exec_probe.CFG_ARG, flags)
        flags = argv("load-listfile-ok")
        self.assertNotIn(exec_probe.LIST_ARG, flags)
        self.assertIn("work/exec_loadlist.txt", flags)


class TestMutatingVariants(unittest.TestCase):
    """Варианты, способные изменить состояние ИБ: названы, отделены от `--all`, достигаются
    названной лестницей и без `--allow-mutating` не запускаются."""

    NAMED_LADDERS = (exec_probe.PREDEFINED_LADDER, exec_probe.EXTENSION_LADDER,
                     exec_probe.LOADOPTS_LADDER, exec_probe.UPDATE_LADDER, exec_probe.MODE_LADDER)

    def test_mutating_variants_are_launch_variants(self):
        self.assertTrue(set(exec_probe.MUTATING_VARIANTS) <= set(exec_probe.VARIANTS))
        self.assertEqual(len(exec_probe.MUTATING_VARIANTS), len(set(exec_probe.MUTATING_VARIANTS)))
        for variant in exec_probe.MUTATING_VARIANTS:
            self.assertTrue(exec_probe.variant_signature(variant)["names"], variant)

    def test_observation_variants_exclude_them(self):
        observation = set(exec_probe.all_observation_variants())
        self.assertFalse(observation & set(exec_probe.MUTATING_VARIANTS))
        self.assertEqual(observation | set(exec_probe.MUTATING_VARIANTS), set(exec_probe.VARIANTS))
        self.assertEqual(len(observation),
                         len(exec_probe.VARIANTS) - len(exec_probe.MUTATING_VARIANTS))

    def test_every_mutating_variant_is_reachable_by_a_named_ladder(self):
        """mutating-вариант вне названной лестницы — наблюдение, которое нельзя вызвать: он обязан
        быть достижим явной опцией (так появился `MODE_LADDER` для `config-load-ok`)."""
        reachable = {variant for ladder in self.NAMED_LADDERS for variant, _k, _e in ladder}
        self.assertEqual(set(exec_probe.MUTATING_VARIANTS) - reachable, set(),
                         "есть mutating-вариант, который ни одна лестница не прогоняет")

    def test_load_variants_outside_the_set_have_a_written_reason(self):
        loads = {variant for variant in exec_probe.VARIANTS
                 if variant.startswith("load") and variant not in exec_probe.MUTATING_VARIANTS}
        self.assertTrue(loads)
        unreasoned = loads - set(exec_probe.NON_MUTATING_LOAD_REASONS)
        self.assertEqual(unreasoned, set(),
                         "утверждение «состояние не меняется» нигде не записано")
        for variant in sorted(loads):
            self.assertTrue(exec_probe.NON_MUTATING_LOAD_REASONS[variant].strip(), variant)

    def test_written_reasons_do_not_cover_mutating_variants(self):
        self.assertFalse(set(exec_probe.NON_MUTATING_LOAD_REASONS) & set(exec_probe.MUTATING_VARIANTS))

    def test_reasons_are_distinct_from_the_variants_they_explain(self):
        """Причина — предложение, а не пересказ имени варианта: иначе запись ничего не добавляет."""
        for variant, reason in exec_probe.NON_MUTATING_LOAD_REASONS.items():
            self.assertGreater(len(reason), len(variant), variant)

    def test_main_refuses_mutating_ladders_without_the_allow_flag(self):
        missing = ROOT / "tests" / "_no-such-local-paths.json"
        calls = []

        def stub(argv_line, **kwargs):
            calls.append(list(argv_line))
            raise AssertionError("без --allow-mutating платформу запускать нельзя")

        original = exec_probe.subprocess.Popen
        exec_probe.subprocess.Popen = stub
        try:
            for option in ("--predefined", "--extensions", "--loadopts", "--update", "--modes"):
                code = exec_probe.main(["--local", str(missing), "--work", "work", "--bin", BIN,
                                        "--ib", IB, "--cfg", CFG, option])
                self.assertEqual(code, 2, option)
            code = exec_probe.main(["--local", str(missing), "--work", "work", "--bin", BIN,
                                    "--ib", IB, "--cfg", CFG, "--variant", "config-load-ok"])
            self.assertEqual(code, 2, "--variant config-load-ok")
        finally:
            exec_probe.subprocess.Popen = original
        self.assertEqual(calls, [], "отказ обязан предшествовать запуску платформы")

    def test_refusal_writes_nothing_into_the_work_directory(self):
        """Отказ предшествует и записи файла списка: иначе отказавший прогон оставляет файлы."""
        missing = ROOT / "tests" / "_no-such-local-paths.json"
        with tempfile.TemporaryDirectory() as raw:
            work = pathlib.Path(raw) / "work"
            code = exec_probe.main(["--local", str(missing), "--work", str(work), "--bin", BIN,
                                    "--ib", IB, "--cfg", CFG, "--loadopts"])
            self.assertEqual(code, 2)
            self.assertFalse((work / exec_probe.LOADLIST_NAME).exists())
            self.assertFalse(work.exists() and any(work.iterdir()), "рабочий каталог остался пуст")

    def test_mutating_ladders_are_named_as_mutating_in_the_cli_help(self):
        text = (ROOT / "scripts" / "exec_probe.py").read_text(encoding="utf-8")
        self.assertIn("--allow-mutating", text)
        self.assertIn("MUTATING_VARIANTS", text)


class TestLoadListFile(unittest.TestCase):
    """Форма файла `-listFile` — канон БСП (стр. 485-488): UTF-8 без BOM, переносы `\r\n`,
    без пустых строк, абсолютные имена корневых XML-файлов через обратный слеш."""

    ROOT_FILES = ("Configuration.xml", "Catalogs/Сотрудники.xml")
    OTHER_FILES = ("Catalogs/Сотрудники/Ext/Predefined.xml",
                   "Catalogs/Сотрудники/Forms/ФормаСписка/Ext/Form.xml",
                   "Catalogs/Сотрудники/Forms/ФормаСписка/Ext/Form/Module.bsl",
                   "Ext/SessionModule.bsl")

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.cfg = pathlib.Path(self._tmp.name) / "cfg"
        for name in self.ROOT_FILES + self.OTHER_FILES:
            file = self.cfg / name
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text("x", encoding="utf-8")
        self.work = pathlib.Path(self._tmp.name) / "work"

    def test_only_root_xml_files_are_listed(self):
        """Файлы каталога `Ext/` в списке не перечисляют: их подтягивает иерархический формат
        вместе с корневым файлом объекта (стр. 843-844 канона)."""
        names = exec_probe.loadlist_paths(self.cfg)
        relative = sorted(pathlib.Path(name).relative_to(self.cfg).as_posix() for name in names)
        self.assertEqual(relative, sorted(self.ROOT_FILES))
        for name in names:
            self.assertTrue(pathlib.Path(name).is_absolute(), name)
            self.assertTrue(name.endswith(".xml"), name)
            self.assertNotIn("Ext", pathlib.Path(name).relative_to(self.cfg).parts, name)

    def test_names_use_the_windows_separator(self):
        if os.sep != "\\":
            raise unittest.SkipTest("разделитель путей не Windows: форма имён не наблюдаема здесь")
        for name in exec_probe.loadlist_paths(self.cfg):
            self.assertIn("\\", name, name)
            self.assertNotIn("/", name, name)

    def test_write_loadlist_bytes_match_the_canonical_form(self):
        path, names = exec_probe.write_loadlist(self.cfg, self.work)
        self.assertEqual(path.name, exec_probe.LOADLIST_NAME)
        self.assertEqual(path.parent, self.work)
        raw = path.read_bytes()
        self.assertFalse(raw.startswith(b"\xef\xbb\xbf"), "BOM в списке не каноничен")
        self.assertIn(b"\r\n", raw)
        # Одиночный `\n` в перечислении поддерживаемых переносов отсутствует.
        lone = [index for index, byte in enumerate(raw)
                if byte == 0x0A and (index == 0 or raw[index - 1] != 0x0D)]
        self.assertEqual(lone, [], "одиночный перевод строки не поддерживается списком")
        self.assertNotIn(b"\r\r", raw, "пустая строка между именами")
        self.assertFalse(raw.startswith(b"\r") or raw.endswith(b"\r\n"), "пустой строки нет")
        self.assertEqual(raw.decode("utf-8").split("\r\n"), names)

    def test_needs_loadlist_marks_exactly_the_listfile_variants(self):
        expected = {"load-listfile-ok", "load-format-flag", "load-format-hierarchical",
                    "load-format-plain", "load-format-bogus"}
        marked = {variant for variant in exec_probe.VARIANTS if exec_probe.needs_loadlist(variant)}
        self.assertEqual(marked, expected)

    def test_listfile_variants_carry_the_list_file_in_argv(self):
        for variant in ("load-listfile-ok", "load-format-plain", "load-format-bogus"):
            flags = argv(variant)
            index = flags.index("-listFile")
            self.assertEqual(flags[index + 1], "work/exec_loadlist.txt", variant)


class TestPredictions(unittest.TestCase):
    """Предсказания живут в таблице, записаны до прогона и имеют проверяемый источник."""

    LADDER_VARIANTS = {variant for ladder in (exec_probe.PREDEFINED_LADDER,
                                              exec_probe.EXTENSION_LADDER,
                                              exec_probe.LOADOPTS_LADDER,
                                              exec_probe.UPDATE_LADDER,
                                              exec_probe.MODE_LADDER)
                       for variant, _kind, _encoding in ladder}

    def test_prediction_keys_are_steps_of_the_task16_ladders(self):
        self.assertTrue(exec_probe.PREDICTIONS)
        for variant in exec_probe.PREDICTIONS:
            self.assertIn(variant, self.LADDER_VARIANTS,
                          f"{variant}: предсказание стоит не на шаге лестницы")

    def test_prediction_records_use_allowed_kinds_and_outcomes(self):
        for variant, record in exec_probe.PREDICTIONS.items():
            self.assertIn(record["kind"], exec_probe.PREDICTION_KINDS, variant)
            self.assertIn(record["predicts"], exec_probe.PREDICTION_OUTCOMES, variant)
            self.assertTrue(record["quote"].strip(), variant)
            self.assertTrue(record["note"].strip(), variant)
            if record["kind"] == "corpora":
                self.assertTrue(record["needle"].strip(), variant)
            else:
                self.assertTrue(record["source"].startswith("reports/"), variant)
                self.assertTrue(record["source_key"].strip(), variant)

    def test_reference_prediction_comes_from_a_gate_report(self):
        """Эталонный шаг предсказан отчётом контура: `load_code` = 0 (гейт итерации 5)."""
        record = exec_probe.PREDICTIONS["load-ok"]
        self.assertEqual(record["kind"], "kontur")
        self.assertEqual(record["predicts"], "code0")
        self.assertEqual(record["source_key"], "load_code")

    def test_corpora_source_is_a_corpus_key_and_a_relative_path(self):
        key, relative = exec_probe.PREDICTION_SOURCE
        self.assertTrue(key.startswith("corpora_"), key)
        self.assertFalse(pathlib.PurePosixPath(relative).is_absolute(), relative)
        self.assertTrue(relative.endswith(".bsl"), relative)

    def test_predictions_are_not_written_during_the_run(self):
        """Предсказание, дописанное после прогона, предсказанием не считается."""
        text = (ROOT / "scripts" / "exec_probe.py").read_text(encoding="utf-8")
        self.assertIsNone(re.search(r"PREDICTIONS\[[^\]]+\]\s*=[^=]", text))
        self.assertNotIn("PREDICTIONS.update(", text)
        self.assertNotIn("PREDICTIONS.setdefault(", text)

    def test_missing_corpus_source_is_reported_as_unreadable(self):
        with tempfile.TemporaryDirectory() as raw:
            local = pathlib.Path(raw) / "local.paths.json"
            local.write_text(json.dumps({"bin": BIN, "ib": IB, "cfg": CFG}), encoding="utf-8")
            sources = exec_probe.verify_prediction_sources(str(local), pathlib.Path(raw))
        self.assertEqual(set(sources), set(exec_probe.PREDICTIONS))
        for variant, record in exec_probe.PREDICTIONS.items():
            if record["kind"] == "corpora":
                self.assertFalse(sources[variant]["file_found"], variant)
                self.assertFalse(sources[variant]["needle_found"], variant)

    def test_prediction_sources_in_this_environment_are_cited_from_readable_files(self):
        """Источник предсказания в этом окружении — читаемый файл с цитируемым именем.

        Отчёт контура (`reports/gate-11.json`) в репозиторий не попадает: его отсутствие означает
        отсутствие прогона в этом окружении, а не отсутствие источника.
        """
        local = ROOT / "local.paths.json"
        if not local.is_file():
            raise unittest.SkipTest("нет local.paths.json: корпуса и отчёты контура недоступны")
        sources = exec_probe.verify_prediction_sources(str(local), ROOT)
        for variant, value in sorted(sources.items()):
            record = exec_probe.PREDICTIONS[variant]
            if record["kind"] == "kontur":
                if not value["file_found"]:
                    continue
                self.assertTrue(value["needle_found"],
                                f"{variant}: ключ {record['source_key']} не равен 0 в "
                                f"{value['source']}")
            else:
                self.assertTrue(value["file_found"],
                                f"{variant}: файл корпуса {value['source']} не читается")
                self.assertTrue(value["needle_found"],
                                f"{variant}: цитируемое имя {record['needle']} не найдено в "
                                f"{value['source']}")


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
                         ["runscript", "runscript-noarg"] + list(exec_probe.NEGATIVE_CONTROLS))
        for previous, current in zip(exec_probe.NEGATIVE_LADDER,
                                     exec_probe.NEGATIVE_LADDER[1:]):
            changed = [index for index in range(3) if previous[index] != current[index]]
            self.assertEqual(len(changed), 1, f"{previous} -> {current}")
        for step in exec_probe.ladder_step_diffs(exec_probe.NEGATIVE_LADDER)[1:]:
            self.assertEqual(len(step["changed_command"]), 1,
                             f"{step['from']} -> {step['to']}: {step['changed_command']}")

    def test_negative_ladder_writes_no_program_file(self):
        """Ни один шаг после базового не читает файл программы: лишний файл — шум."""
        for variant, _kind, _encoding in exec_probe.NEGATIVE_LADDER[1:]:
            self.assertFalse(exec_probe.needs_script(variant), variant)
        self.assertTrue(set(variant for variant, _, _ in exec_probe.NEGATIVE_LADDER[2:])
                        <= set(exec_probe.NEGATIVE_CONTROLS))


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
        """`--all` — варианты при одном кодировании; лестницы — свои наборы шагов.
        Контроль загрузки (`load-*`) входит только в `CONTROLS` и `AUTH_LADDER`: лестницы
        исполнения BSL (Sweep, тексты программ, отрицательная, тестовая) его не содержат."""
        self.assertNotEqual(exec_probe.SWEEP, exec_probe.PROGRAM_LADDER)
        load_variants = {variant for variant, _, _ in exec_probe.CONTROLS
                         if variant.startswith("load")}
        self.assertTrue(load_variants)
        for name, ladder in (("SWEEP", exec_probe.SWEEP),
                             ("PROGRAM_LADDER", exec_probe.PROGRAM_LADDER),
                             ("NEGATIVE_LADDER", exec_probe.NEGATIVE_LADDER),
                             ("TEST_LADDER", exec_probe.TEST_LADDER)):
            self.assertFalse({variant for variant, _, _ in ladder} & load_variants, name)
        self.assertTrue(all(variant.startswith("load") for variant, _, _ in exec_probe.AUTH_LADDER),
                        "лестница авторизации идёт на рабочей команде загрузки")


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
