"""Тесты замера эффекта модификаторов (`probe/modifier_effect.py`).

Что наблюдено реальными прогонами (отчёты `reports/effect-16-predefined.json`,
`reports/effect-16-predefined-fresh.json`, `reports/effect-16-repeat.json`):

- `PredefinedDataUpdate` в XML выгрузки пишется **без префикса** `v8:`: поиск только с префиксом
  даёт `None` (наблюдение gate-11: `<PredefinedDataUpdate>Auto</PredefinedDataUpdate>`);
- `ConfigDumpInfo.xml` содержит `<Metadata name="..." configVersion="...">` — 29 записей при 31
  файлах выгрузки: у `Configuration` атрибута `configVersion` нет;
- три одинаковых шага `/LoadConfigFromFiles` дали **три разных набора** `configVersion`
  (`reports/effect-16-repeat.json`), а файлы, байты, числа раскладки и предопределённые данные при
  этом не изменились. Значит `configVersion` — не хеш содержимого, и «изменений нет» на него
  опираться не должно;
- на уже загруженной ИБ шаги `/SetPredefinedDataUpdate` дали шесть побайтово одинаковых выгрузок
  за 1.0 с против 2.0 с у эталонного `load-ok` — «изменений нет» неотличимо от «загрузка не
  делалась» (отсюда режим `--fresh-ib`);
- на свежей ИБ те же шаги оставили ИБ с **тремя** файлами (`ConfigDumpInfo.xml`,
  `Configuration.xml`, `Languages/Русский.xml`) вместо тридцати двух: конфигурация не загружена,
  код при этом 0, вывод пустой;
- о неполной загрузке платформа сообщает двумя идентификаторами (`6b1e3a24-1c77-4c0a-90d1-0a2f4c6e8001`
  — uuid конфигурации в исходнике), и второй идентификатор в замерах `effect-16-loadopts-fresh`,
  `effect-16-extensions-fresh`, `effect-16-update-fresh` каждый прогон новый: он не совпал ни с ним,
  ни с uuid `Configuration.xml` в выгрузке того же шага. Сверять его было не с чем — uuid ИБ ДО шага
  не снимался (отсюда выгрузка до шага `before_fingerprint` и ожидания `EXPECTATIONS`, которые
  пишутся в файле до прогона);
- в замере `reports/effect-16-loadopts-fresh2.json` uuid ИБ без конфигурации расходится между
  выгрузкой ДО шага и выгрузкой ПОСЛЕ него, хотя файлов и байтов ровно столько же (3 файла / 11873
  байта), и он же не равен второму идентификатору из вывода шага. Тогда третий снимок того же
  состояния без прогона между ними (`dump_twice`) и отделяет «шаг изменил идентификатор» от
  «выгрузка пересоздаёт идентификатор оболочки» (ожидания `dump-regenerates-uuid-of-empty-ib` и
  `dump-keeps-uuid-of-loaded-config`).

Тесты проверяют сам контур замера: что признаки снимаются, что сравнение не выдумывает изменений,
и что запрещённые прогоны отсекаются до вызова платформы. Ни один тест платформу не запускает.
"""
from __future__ import annotations

import contextlib
import io
import json
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "probe"))
sys.path.insert(0, str(ROOT / "scripts"))

import exec_probe                                              # noqa: E402
import modifier_effect                                         # noqa: E402


class FingerprintTest(unittest.TestCase):
    """Признаки выгрузки снимаются по фактическому написанию тегов, а не по ожиданию."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dump = pathlib.Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def write(self, relative: str, text: str) -> pathlib.Path:
        path = self.dump / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"\xef\xbb\xbf" + text.replace("\n", "\r\n").encode("utf-8"))
        return path

    def test_predefined_tag_is_found_without_prefix_and_with_it(self):
        self.write("Catalogs/Сотрудники.xml",
                   "<a><PredefinedDataUpdate>Auto</PredefinedDataUpdate></a>")
        self.write("Documents/ФактРаботы.xml",
                   "<a><v8:PredefinedDataUpdate>DontAutoUpdate</v8:PredefinedDataUpdate></a>")
        self.write("Enums/ГрейдыСпециалистов.xml", "<a>TagaNet</a>")
        found = modifier_effect.predefined_settings(self.dump)
        self.assertEqual(found, {"Catalogs/Сотрудники.xml": "Auto",
                                 "Documents/ФактРаботы.xml": "DontAutoUpdate"}, found)

    def test_predefined_data_counts_items_bytes_and_fingerprint(self):
        self.write("Catalogs/Сотрудники/Ext/Predefined.xml",
                   '<Predefined><Item id="1"/><Item id="2"/></Predefined>')
        self.write("Catalogs/Сотрудники/Ext/ObjectModule.bsl", "Сообщить(1);")
        found = modifier_effect.predefined_data(self.dump)
        rel = "Catalogs/Сотрудники/Ext/Predefined.xml"
        self.assertEqual(list(found), [rel], found)
        self.assertEqual(found[rel]["items"], 2, found)
        self.assertEqual(found[rel]["bytes"], (self.dump / rel).read_bytes().__len__(), found)
        self.assertEqual(len(found[rel]["sha1"]), 16, found)

    def test_predefined_data_fingerprint_differs_for_different_records(self):
        rel = "Catalogs/Сотрудники/Ext/Predefined.xml"
        self.write(rel, '<Predefined><Item id="1"/></Predefined>')
        first = modifier_effect.predefined_data(self.dump)[rel]["sha1"]
        self.write(rel, '<Predefined><Item id="2"/></Predefined>')
        second = modifier_effect.predefined_data(self.dump)[rel]["sha1"]
        self.assertNotEqual(first, second, (first, second))

    def test_config_versions_skips_metadata_without_version(self):
        # Замер gate-11: 29 записей `configVersion` при 31 файле выгрузки — у `Configuration`
        # атрибута `configVersion` нет, и он в отпечаток не попадает.
        self.write("ConfigDumpInfo.xml",
                   '<Metadata name="Configuration" uuid="x"/>\n'
                   '<Metadata name="Catalog.Сотрудники" id="y" configVersion="AB12"/>\n')
        self.assertEqual(modifier_effect.config_versions(self.dump),
                         {"Catalog.Сотрудники": "AB12"})

    def test_fingerprint_holds_every_compared_sign_and_ignores_platform_file(self):
        self.write("Catalogs/Сотрудники.xml", "<a/>")
        self.write("ConfigDumpInfo.xml", '<Metadata name="Catalog.Сотрудники" configVersion="1"/>')
        fp = modifier_effect.fingerprint(self.dump)
        self.assertEqual(set(fp), {"files", "bytes", "counts", "predefined_settings",
                                   "predefined_data", "config_versions", "config_uuid"}, fp)
        self.assertEqual(fp["files"], 2, fp)
        # `ConfigDumpInfo.xml` — файл платформы: в числах раскладки его быть не должно, иначе
        # выгрузка всегда оказывается «длиннее» исходника (наблюдение гейта).
        self.assertNotIn("ConfigDumpInfo.xml", json.dumps(fp["counts"], ensure_ascii=False), fp)

    def test_map_keys_are_signs_of_the_fingerprint(self):
        fp = modifier_effect.fingerprint(self.dump)
        for key in modifier_effect.MAP_KEYS:
            self.assertIn(key, fp, key)

    def test_config_uuid_is_read_from_the_root_tag_and_lowercased(self):
        # Наблюдение gate-11: `<Configuration uuid="6b1e3a24-1c77-4c0a-90d1-0a2f4c6e8001">`.
        self.write("Configuration.xml",
                   '<MetaDataObject><Configuration uuid="6B1E3A24-1C77-4C0A-90D1-0A2F4C6E8001">'
                   '</Configuration></MetaDataObject>')
        self.assertEqual(modifier_effect.config_uuid(self.dump),
                         "6b1e3a24-1c77-4c0a-90d1-0a2f4c6e8001")
        self.assertEqual(modifier_effect.source_config_uuid(self.dump),
                         "6b1e3a24-1c77-4c0a-90d1-0a2f4c6e8001")

    def test_config_uuid_is_empty_when_the_tag_or_file_is_missing(self):
        self.assertEqual(modifier_effect.config_uuid(self.dump), "", "нет файла вовсе")
        self.write("Configuration.xml", '<MetaDataObject><Configuration></Configuration>')
        self.assertEqual(modifier_effect.config_uuid(self.dump), "", "тега без атрибута uuid")
        self.write("Configuration.xml",
                   '<MetaDataObject><Catalogs uuid="6b1e3a24-1c77-4c0a-90d1-0a2f4c6e8001"/>'
                   '<Configuration/></MetaDataObject>')
        # Ищется именно корневой тег: uuid дочернего объекта идентификатором конфигурации не делается.
        self.assertEqual(modifier_effect.config_uuid(self.dump), "", "uuid не у Configuration")


class FingerprintDiffTest(unittest.TestCase):
    """Сравнение выгрузок не выдумывает изменений и не молчит, когда изменение есть."""

    def test_base_step_has_nothing_to_compare_against(self):
        # Базовый шаг лестницы (`load-ok`) сравнивать не с чем: без этого шага замер падал.
        self.assertEqual(modifier_effect.fingerprint_diff(None, {"files": 3}), {})

    def test_identical_dumps_give_no_changes(self):
        fp = {"files": 32, "bytes": 100, "counts": {"catalog": 1},
              "predefined_settings": {"Catalogs/Сотрудники.xml": "Auto"},
              "predefined_data": {}, "config_versions": {"Catalog.Сотрудники": "1"}}
        self.assertEqual(modifier_effect.fingerprint_diff(fp, dict(fp)), {})

    def test_changed_value_appears_with_old_and_new(self):
        before = {"predefined_settings": {"Catalogs/Сотрудники.xml": "Auto"}}
        after = {"predefined_settings": {"Catalogs/Сотрудники.xml": "DontAutoUpdate"}}
        self.assertEqual(modifier_effect.fingerprint_diff(before, after),
                         {"predefined_settings": {"Catalogs/Сотрудники.xml":
                                                  ["Auto", "DontAutoUpdate"]}})

    def test_appearing_file_appears_as_change_with_none_before(self):
        # Наблюдение `--fresh-ib`: после шага с `/SetPredefinedDataUpdate` предопределённых данных
        # в выгрузке нет вовсе — изменение видно как `[старое, null]`, а не как «изменений нет».
        before = {"predefined_data": {"Catalogs/Сотрудники/Ext/Predefined.xml": {"items": 6}}}
        changed = modifier_effect.fingerprint_diff(before, {"predefined_data": {}})
        self.assertEqual(changed["predefined_data"]["Catalogs/Сотрудники/Ext/Predefined.xml"][-1],
                         None, changed)

    def test_version_changes_reports_only_changed_names(self):
        self.assertEqual(
            modifier_effect.version_changes({"A": "1", "B": "2"}, {"A": "1", "B": "3"}),
            {"B": ["2", "3"]})

    def test_config_versions_change_is_reported_as_its_own_key(self):
        # Наблюдение `repeat`: версии расходятся при неизменном остальном содержимом выгрузки.
        before = {"config_versions": {"Catalog.Сотрудники": "1"}}
        after = {"config_versions": {"Catalog.Сотрудники": "2"}}
        self.assertEqual(modifier_effect.fingerprint_diff(before, after),
                         {"config_versions": {"Catalog.Сотрудники": ["1", "2"]}})

    def test_config_uuid_change_is_reported_as_its_own_key(self):
        # Наблюдение `effect-16-*`: uuid `Configuration.xml` в выгрузке меняется от выгрузки к
        # выгрузке, и это отдельный признак сравнения, а не частность `config_versions`.
        before = {"config_uuid": "6b1e3a24-1c77-4c0a-90d1-0a2f4c6e8001"}
        after = {"config_uuid": "8f78a7d3-5166-494a-bd7a-05cf57f53b3b"}
        self.assertEqual(modifier_effect.fingerprint_diff(before, after),
                         {"config_uuid": ["6b1e3a24-1c77-4c0a-90d1-0a2f4c6e8001",
                                          "8f78a7d3-5166-494a-bd7a-05cf57f53b3b"]})

    def test_same_config_uuid_gives_no_change(self):
        uuid = "6b1e3a24-1c77-4c0a-90d1-0a2f4c6e8001"
        self.assertEqual(modifier_effect.fingerprint_diff({"config_uuid": uuid},
                                                          {"config_uuid": uuid}), {})


class LadderTableTest(unittest.TestCase):
    """Замер берёт лестницы и варианты из `scripts/exec_probe.py`, а не сочиняет их заново."""

    def test_every_ladder_variant_is_a_known_variant(self):
        for name, (_, ladder) in modifier_effect.LADDERS.items():
            for variant, kind, encoding in ladder:
                self.assertIn(variant, exec_probe.VARIANTS, f"{name}: {variant}")
                self.assertIn(kind, exec_probe.PROGRAMS, f"{name}: {kind}")
                self.assertIn(encoding, exec_probe.ENCODINGS, f"{name}: {encoding}")

    def test_repeat_control_is_three_identical_load_steps(self):
        # Контроль, который измеряет сам признак `configVersion`: три шага с одной командой.
        ladder = modifier_effect.LADDERS["repeat"][1]
        self.assertEqual([variant for variant, _, _ in ladder], ["load-ok"] * 3, ladder)

    def test_every_named_ladder_of_exec_probe_is_measurable(self):
        for ladder_name in ("PREDEFINED_LADDER", "EXTENSION_LADDER", "LOADOPTS_LADDER",
                            "UPDATE_LADDER", "MODE_LADDER"):
            self.assertIn(ladder_name, [name for name, _ in modifier_effect.LADDERS.values()],
                          ladder_name)


SOURCE_UUID = "6b1e3a24-1c77-4c0a-90d1-0a2f4c6e8001"
FOREIGN_UUID = "8f78a7d3-5166-494a-bd7a-05cf57f53b3b"
OTHER_UUID = "d7499c9b-a5a2-4752-ba6b-026efaf566d7"
FULL_FILES, EMPTY_FILES = 32, 3
# Побайтовые наблюдения выгрузок тех же состояний: ИБ без конфигурации и загруженная конфигурация
# (`reports/effect-16-loadopts-fresh2.json`, `reports/gate-11.json`).
FULL_BYTES, EMPTY_BYTES = 140181, 11873
# Дословная строка наблюдения (`reports/effect-16-loadopts-fresh.json`, шаг `load-files-onefile`).
PARTIAL_LOAD_LINE = ("Файл - Configuration.xml: ошибка частичной загрузки - идентификатор "
                     "6b1e3a24-1c77-4c0a-90d1-0a2f4c6e8001 загружаемой конфигурации отличается "
                     "от идентификатора d7499c9b-a5a2-4752-ba6b-026efaf566d7")


class IdentifierTest(unittest.TestCase):
    """Идентификаторы из вывода шага читаются списком в порядке появления."""

    def test_both_identifiers_of_the_partial_load_line_are_read(self):
        self.assertEqual(modifier_effect.identifiers_in([PARTIAL_LOAD_LINE]),
                         [SOURCE_UUID, OTHER_UUID])

    def test_repeated_identifier_is_listed_once_and_case_is_normalized(self):
        self.assertEqual(modifier_effect.identifiers_in([PARTIAL_LOAD_LINE,
                                                         PARTIAL_LOAD_LINE.upper()]),
                         [SOURCE_UUID, OTHER_UUID])

    def test_config_version_is_not_an_identifier(self):
        # `configVersion` в `ConfigDumpInfo.xml` — 40 шестнадцатеричных символов без тире: его
        # нельзя принимать за идентификатор конфигурации.
        self.assertEqual(modifier_effect.identifiers_in(
            ['<Metadata name="Catalog.Сотрудники" configVersion="1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b"/>']),
            [])

    def test_no_lines_no_identifiers(self):
        self.assertEqual(modifier_effect.identifiers_in([]), [])
        self.assertEqual(modifier_effect.identifiers_in(None), [])


# Дословная строка многострочного отказа (`reports/effect-16-extensions-fresh.json`, шаги
# `load-allextensions-baddir` и `load-allextensions-flag`).
ALL_EXTENSIONS_LINE = ("Файл объекта не существует - C:/Users/goof0/Documents/REA/Platform1C/"
                       "effektivnost-otdela/cfg/ЭффективностьОтдела/Catalogs/Configuration.xml")
ALL_EXTENSIONS_CATALOGS = ("AccumulationRegisters", "Catalogs", "CommonModules", "Constants",
                           "DataProcessors", "Documents", "Enums", "InformationRegisters",
                           "Languages", "Reports", "Roles", "Subsystems")


def all_extensions_lines() -> list:
    """тот же отказ, повторённый дважды: в выводе шага каждая строка стоит дважды."""
    lines = [ALL_EXTENSIONS_LINE.replace("/Catalogs/", "/" + catalog + "/")
             for catalog in ALL_EXTENSIONS_CATALOGS]
    return lines + lines


class OutputLineStatsTest(unittest.TestCase):
    """Полный вывод шага считается ДО обрезки `lines`: обрезка длиной вывода не является."""

    def test_empty_lines_are_dropped_and_edges_are_stripped(self):
        rows, unique = modifier_effect.out_line_stats(["", "  а  ", "б", "\t", ""])
        self.assertEqual(rows, ["а", "б"])
        self.assertEqual(unique, ["а", "б"])

    def test_no_lines_no_counts(self):
        self.assertEqual(modifier_effect.out_line_stats([]), ([], []))
        self.assertEqual(modifier_effect.out_line_stats(None), ([], []))

    def test_unique_rows_are_sorted_without_duplicates(self):
        rows, unique = modifier_effect.out_line_stats(all_extensions_lines())
        self.assertEqual(len(rows), 24)
        self.assertEqual(unique, sorted(set(all_extensions_lines())))
        self.assertEqual(len(unique), len(ALL_EXTENSIONS_CATALOGS))

    def test_the_counted_lines_are_more_than_the_reported_window(self):
        # В отчёт попадает 8 строк (`lines`); у этого отказа их 24, и неповторяющихся 12. Счётчик
        # обязан показывать настоящее число: по одному окну видно только 4 каталога из 12.
        rows, unique = modifier_effect.out_line_stats(all_extensions_lines())
        self.assertGreater(len(rows), 8)
        self.assertGreater(len(unique), 4)
        self.assertEqual(len(rows[:8]), 8)


def make_step(index: int, variant: str, *, uuid: str, files: int = FULL_FILES,
              before_uuid: str = "", before_files: int = EMPTY_FILES,
              identifiers: tuple = (), dump_twice: dict | None = None) -> dict:
    """Шаг отчёта такой формы, какую даёт `run_and_dump` (только нужные ожиданиям ключи)."""
    step = {"index": index, "variant": variant, "identifiers": list(identifiers),
            "before_fingerprint": {"config_uuid": before_uuid, "files": before_files},
            "fingerprint": {"config_uuid": uuid, "files": files}}
    if dump_twice is not None:
        step["dump_twice"] = dump_twice
    return step


def make_twice(files: tuple, bytes_: tuple, uuids: tuple) -> dict:
    """Пара «выгрузка ПОСЛЕ шага -> вторая выгрузка того же состояния» в форме ключа `dump_twice`.

    Признаки равенства вычисляются из пар, а не подставляются: так helper не может сообщить «равно»
    там, где значения расходятся (в контуре их вычисляет `fingerprint_diff`).
    """
    return {"files": list(files), "bytes": list(bytes_), "config_uuid": list(uuids),
            "same_files": files[0] == files[1], "same_bytes": bytes_[0] == bytes_[1],
            "same_uuid": uuids[0] == uuids[1]}


def make_report(steps: list, restore: dict, fresh: bool) -> dict:
    return {"source_uuid": SOURCE_UUID, "ib_fresh_each_step": fresh, "steps": steps,
            "restore": restore}


class ExpectationTest(unittest.TestCase):
    """Ожидания `EXPECTATIONS` проверяются по факту выгрузок, а непроверенное ожидание не считается
    сбывшимся."""

    def test_every_expectation_has_a_check_and_a_claim(self):
        self.assertEqual(set(modifier_effect.EXPECTATIONS), set(modifier_effect.EXPECTATION_CHECKS))
        for name, claim in modifier_effect.EXPECTATIONS.items():
            self.assertTrue(claim.strip(), name)

    def test_partial_identifier_expectation_met_and_missed(self):
        met = make_report([make_step(0, "load-ok", uuid=SOURCE_UUID),
                           make_step(1, "load-format-flag", uuid=OTHER_UUID, files=EMPTY_FILES,
                                     before_uuid=FOREIGN_UUID,
                                     identifiers=(SOURCE_UUID, FOREIGN_UUID))],
                          make_step(2, "load-ok", uuid=SOURCE_UUID), fresh=True)
        result = modifier_effect.check_partial_identifier(met)
        self.assertTrue(result["met"], result)
        self.assertTrue(result["evidence"][0]["first_is_source_uuid"], result)
        missed = make_report([make_step(1, "load-format-flag", uuid=OTHER_UUID, files=EMPTY_FILES,
                                        before_uuid=FOREIGN_UUID,
                                        identifiers=(SOURCE_UUID, OTHER_UUID))],
                             make_step(2, "load-ok", uuid=SOURCE_UUID), fresh=True)
        self.assertFalse(modifier_effect.check_partial_identifier(missed)["met"], missed)

    def test_full_load_agreement_met_and_missed(self):
        met = make_report([make_step(0, "load-ok", uuid=SOURCE_UUID),
                           make_step(1, "load-format-flag", uuid=OTHER_UUID, files=EMPTY_FILES)],
                          make_step(2, "load-ok", uuid=SOURCE_UUID), fresh=True)
        self.assertTrue(modifier_effect.check_full_load_keeps_source_uuid(met)["met"], met)
        # Чужой uuid при полной раскладке (или свой uuid при трёх файлах) — ожидание не сбывается:
        # именно такая нестыковка и запрещает вывод «код 0, значит конфигурация на месте».
        missed = make_report([make_step(1, "load-format-flag", uuid=SOURCE_UUID,
                                        files=EMPTY_FILES)],
                             make_step(2, "load-ok", uuid=SOURCE_UUID), fresh=True)
        self.assertFalse(modifier_effect.check_full_load_keeps_source_uuid(missed)["met"], missed)

    def test_empty_ib_uuid_expectation_met_and_missed(self):
        met = make_report([make_step(0, "load-ok", uuid=SOURCE_UUID, before_uuid=FOREIGN_UUID),
                           make_step(1, "load-format-flag", uuid=OTHER_UUID, files=EMPTY_FILES,
                                     before_uuid=OTHER_UUID)],
                          make_step(2, "load-ok", uuid=SOURCE_UUID), fresh=True)
        result = modifier_effect.check_empty_ib_has_own_uuid(met)
        self.assertTrue(result["met"], result)
        # uuid пустой ИБ назначается при создании ИБ, а не берётся из исходника: два шага на двух
        # свежих ИБ дают два разных идентификатора.
        self.assertEqual(result["distinct_uuids"], sorted({FOREIGN_UUID, OTHER_UUID}), result)
        missed = make_report([make_step(0, "load-ok", uuid=OTHER_UUID, files=EMPTY_FILES,
                                        before_uuid=SOURCE_UUID)],
                             make_step(1, "load-ok", uuid=SOURCE_UUID), fresh=True)
        self.assertFalse(modifier_effect.check_empty_ib_has_own_uuid(missed)["met"], missed)

    def test_dump_and_repeat_checks_need_a_shared_ib(self):
        # В режиме `--fresh-ib` между выгрузками стоит `reset_ib`: сверка идентификаторов этих
        # выгрузок ничего про выгрузку или повтор загрузки не сообщает, и проверка отвечает
        # `met: null`.
        fresh = make_report([make_step(0, "load-ok", uuid=FOREIGN_UUID, before_uuid=FOREIGN_UUID),
                             make_step(1, "load-ok", uuid=OTHER_UUID, before_uuid=OTHER_UUID)],
                            make_step(2, "load-ok", uuid=SOURCE_UUID), fresh=True)
        for name in ("ib-uuid-survives-its-own-dump", "repeat-load-keeps-uuid"):
            check = modifier_effect.EXPECTATION_CHECKS[name](fresh)
            self.assertIsNone(check["met"], name)
            self.assertTrue(check["note"].strip(), name)
        shared = make_report([make_step(0, "load-ok", uuid=SOURCE_UUID, before_uuid=FOREIGN_UUID),
                              make_step(1, "load-ok", uuid=SOURCE_UUID, before_uuid=SOURCE_UUID)],
                             make_step(2, "load-ok", uuid=SOURCE_UUID), fresh=False)
        self.assertTrue(modifier_effect.check_uuid_survives_dump(shared)["met"], shared)
        self.assertTrue(modifier_effect.check_repeat_load_keeps_uuid(shared)["met"], shared)

    def test_repeat_check_misses_when_the_uuid_moves_between_identical_loads(self):
        shared = make_report([make_step(0, "load-ok", uuid=SOURCE_UUID),
                              make_step(1, "load-ok", uuid=OTHER_UUID, before_uuid=SOURCE_UUID)],
                             make_step(2, "load-ok", uuid=SOURCE_UUID), fresh=False)
        self.assertFalse(modifier_effect.check_repeat_load_keeps_uuid(shared)["met"], shared)

    def test_dump_pair_checks_separate_the_two_ib_states(self):
        # Разделительный контроль: между двумя выгрузками одной пары прогона нет, поэтому у ИБ без
        # конфигурации остаётся только одна причина расхождения uuid — сама выгрузка.
        empty = make_step(1, "load-format-flag", uuid=OTHER_UUID, files=EMPTY_FILES,
                          before_uuid=FOREIGN_UUID,
                          dump_twice=make_twice((EMPTY_FILES, EMPTY_FILES),
                                                (EMPTY_BYTES, EMPTY_BYTES), (OTHER_UUID, FOREIGN_UUID)))
        loaded = make_step(0, "load-ok", uuid=SOURCE_UUID,
                           dump_twice=make_twice((FULL_FILES, FULL_FILES), (FULL_BYTES, FULL_BYTES),
                                                 (SOURCE_UUID, SOURCE_UUID)))
        restore = make_step(2, "load-ok", uuid=SOURCE_UUID,
                            dump_twice=make_twice((FULL_FILES, FULL_FILES), (FULL_BYTES, FULL_BYTES),
                                                  (SOURCE_UUID, SOURCE_UUID)))
        report = make_report([loaded, empty], restore, fresh=True)
        regenerates = modifier_effect.check_dump_regenerates_empty_ib_uuid(report)
        keeps = modifier_effect.check_dump_keeps_loaded_uuid(report)
        self.assertTrue(regenerates["met"], regenerates)
        self.assertTrue(keeps["met"], keeps)
        # Строки разделены по состоянию ИБ: пустая ИБ попадает только в первую проверку, загруженная
        # (шаг и восстановление) — только во вторую.
        self.assertEqual([row["index"] for row in regenerates["evidence"]], [1], regenerates)
        self.assertEqual([row["index"] for row in keeps["evidence"]], [0, 2], keeps)
        row = regenerates["evidence"][0]
        self.assertTrue(row["same_files"] and row["same_bytes"], row)
        self.assertFalse(row["same_uuid"], row)

    def test_dump_pair_checks_miss_when_the_uuid_behaves_the_other_way(self):
        # ИБ без конфигурации, где вторая выгрузка даёт тот же uuid, и загруженная ИБ, где uuid
        # расходится: обе проверки обязаны ответить «не сбылось», а не промолчать.
        empty = make_step(0, "load-format-flag", uuid=OTHER_UUID, files=EMPTY_FILES,
                          dump_twice=make_twice((EMPTY_FILES, EMPTY_FILES),
                                                (EMPTY_BYTES, EMPTY_BYTES), (OTHER_UUID, OTHER_UUID)))
        loaded = make_step(1, "load-ok", uuid=SOURCE_UUID,
                           dump_twice=make_twice((FULL_FILES, FULL_FILES), (FULL_BYTES, FULL_BYTES),
                                                 (SOURCE_UUID, FOREIGN_UUID)))
        restore = make_step(2, "load-ok", uuid=SOURCE_UUID)
        report = make_report([empty, loaded], restore, fresh=True)
        self.assertFalse(modifier_effect.check_dump_regenerates_empty_ib_uuid(report)["met"], report)
        self.assertFalse(modifier_effect.check_dump_keeps_loaded_uuid(report)["met"], report)

    def test_dump_pair_with_other_changed_sign_is_not_read_as_uuid_regeneration(self):
        # Файлы второй выгрузки уже не те: расхождение идентификатора в такой паре не является
        # «выгрузка пересоздала uuid при том же содержимом».
        empty = make_step(0, "load-format-flag", uuid=OTHER_UUID, files=EMPTY_FILES,
                          dump_twice=make_twice((EMPTY_FILES, EMPTY_FILES + 1),
                                                (EMPTY_BYTES, EMPTY_BYTES + 7), (OTHER_UUID, FOREIGN_UUID)))
        report = make_report([empty], make_step(1, "load-ok", uuid=SOURCE_UUID), fresh=True)
        self.assertFalse(modifier_effect.check_dump_regenerates_empty_ib_uuid(report)["met"], report)

    def test_uncheckable_expectation_is_reported_as_unchecked_not_as_met(self):
        # Общий ИБ, ни один шаг не назвал идентификаторов, выгрузки до шага полные, ключа `dump_twice`
        # нет: шесть ожиданий из семи остаются без проверки.
        report = make_report([make_step(0, "load-ok", uuid=SOURCE_UUID, before_uuid=SOURCE_UUID,
                                        before_files=FULL_FILES),
                              make_step(1, "load-ok", uuid=SOURCE_UUID, before_uuid=SOURCE_UUID,
                                        before_files=FULL_FILES)],
                             make_step(2, "load-ok", uuid=SOURCE_UUID), fresh=True)
        checks = modifier_effect.check_expectations(report)
        self.assertEqual(set(checks), set(modifier_effect.EXPECTATIONS), checks)
        uncheckable = [name for name, check in checks.items() if check["met"] is None]
        # Проверемой остаётся одна сверка: «свой uuid <=> полная раскладка». Остальные шесть
        # требуют либо названных идентификаторов, либо общей ИБ, либо пустой ИБ до шага, либо пар
        # выгрузок одного состояния.
        self.assertEqual(sorted(uncheckable),
                         ["dump-keeps-uuid-of-loaded-config", "dump-regenerates-uuid-of-empty-ib",
                          "empty-ib-has-its-own-uuid", "ib-uuid-survives-its-own-dump",
                          "partial-second-identifier-is-ib-uuid-before-step",
                          "repeat-load-keeps-uuid"], uncheckable)
        for name in uncheckable:
            self.assertTrue(checks[name]["note"].strip(), name)
            self.assertEqual(checks[name]["evidence"], [], name)


class GuardTest(unittest.TestCase):
    """Запрещённые прогоны отсекаются до вызова платформы (код 2)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = pathlib.Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)
        self.local = self.base / "local.paths.json"
        self.local.write_text(json.dumps({"bin": str(self.base / "1cv8.exe"),
                                          "ib": str(self.base / "ib"),
                                          "cfg": str(self.base / "cfg")}), encoding="utf-8")
        self.probe_ib = self.base / "probe_ib"

    def run_main(self, argv: list) -> tuple:
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code = modifier_effect.main(["--local", str(self.local)] + argv)
        return code, err.getvalue()

    def test_gate_ib_is_refused_as_a_polygon(self):
        # ИБ гейта (ключ `ib`) — боевая ИБ конфигурации: mutating-лестница на ней не запускается.
        code, err = self.run_main(["--ladder", "predefined", "--allow-mutating",
                                   "--ib", str(self.base / "ib")])
        self.assertEqual(code, 2, err)
        self.assertIn("ИБ гейта", err, err)

    def test_mutating_ladder_without_flag_is_refused(self):
        code, err = self.run_main(["--ladder", "predefined", "--ib", str(self.probe_ib)])
        self.assertEqual(code, 2, err)
        self.assertIn("--allow-mutating", err, err)

    def test_fresh_ib_outside_the_gate_ib_directory_is_refused(self):
        # `--fresh-ib` удаляет каталог ИБ: чужой каталог под этот режим не подставляется.
        code, err = self.run_main(["--ladder", "predefined", "--allow-mutating", "--fresh-ib",
                                   "--ib", str(self.base / "elsewhere" / "probe_ib")])
        self.assertEqual(code, 2, err)
        self.assertIn("--fresh-ib", err, err)

    def test_missing_ib_is_refused(self):
        code, err = self.run_main(["--ladder", "predefined", "--allow-mutating", "--ib", ""])
        self.assertEqual(code, 2, err)
        self.assertIn("--ib", err, err)

    def test_uncreated_ib_is_refused(self):
        # Общий режим требует уже созданной ИБ: на пустом каталоге замер смысла не имеет.
        code, err = self.run_main(["--ladder", "predefined", "--allow-mutating",
                                   "--ib", str(self.probe_ib)])
        self.assertEqual(code, 2, err)
        self.assertIn("не создана", err, err)


class ResetIbTest(unittest.TestCase):
    """Режим `--fresh-ib`: каталог ИБ удаляется, а шаг `create` без файла платформы не запускается."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = pathlib.Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)
        self.ib = self.base / "probe_ib"
        (self.ib / "sub").mkdir(parents=True)
        (self.ib / "1Cv8.1CD").write_bytes(b"x")
        (self.ib / "sub" / "1Cv8.8cd").write_bytes(b"y")

    def test_reset_removes_the_ib_directory_and_reports_it(self):
        import ib_loop
        result = modifier_effect.reset_ib(str(self.ib), str(self.base / "netakogo.exe"),
                                          self.base / "work", 0, 30)
        self.assertTrue(result["removed"], result)
        self.assertFalse(self.ib.exists(), sorted(p.as_posix() for p in self.base.rglob("*")))
        # Платформы нет: шаг `create` обязан быть отсеян, а не запущен (иначе тест гоняет 1С).
        self.assertTrue(ib_loop.refusal("create", {"bin": str(self.base / "netakogo.exe"),
                                                   "ib": str(self.ib), "out": "x"}), result)
        # Отказ шага `ib_loop.run_step` отвечает кодом 2 (код 1 у прогона, который платформа
        # завершила с ошибкой) и называет причину, поэтому лестница не продолжает вслепую.
        self.assertEqual(result["code"], 2, result)
        self.assertIn("платформ", result["reason"], result)


if __name__ == "__main__":
    unittest.main()
