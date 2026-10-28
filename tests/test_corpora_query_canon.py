"""Тесты замера канона запросов (`probe/corpora_query_canon.py`).

Что этот замер обязан отвечать, и что поэтому проверяют тесты:

1. Число вхождений, а не число файлов и не число строк: в одном модуле агрегатная функция может
   встречаться несколько раз, и для вывода «платформа пишет `СУММА(`, а не `СУММ(`» нужна именно
   частота написания.
2. Имена считаются каноническими написаниями: `СУММА(` не содержит `СУММ(` как подстроку
   (после `СУММ` стоит `А`), поэтому нулевой счётчик `СУММ(` — наблюдение, а не артефакт поиска.
3. Производные меры считаются по одной строке: `ЕСТЬNULL(` и `Неопределено` на разных строках —
   это не каноническая пара, а две несвязанные строки. Поиск при этом не жадный: две пары в одной
   строке дают два вхождения, а не одно.
4. Модули форм различаются по двум раскладкам выгрузки: у формы объекта есть каталог `Forms`,
   у общей формы его нет (`CommonForms/<Форма>/Ext/Form/Module.bsl`). Проверка только по `/Forms/`
   занижает число модулей форм.
5. Ограничение по размеру файла подписано числом пропущенных файлов: без подписи пропуск крупных
   файлов выглядел бы как «такого в каноне нет».
6. В отчёте нет абсолютных путей корпусов: наблюдение должно воспроизводиться на другой машине.
7. Перекрывающий счётчик разложен своими же счётчиками: `ВЫБОР` находит и `ВЫБОРКА`, поэтому общий
   счётчик без `ВЫБОРКА`, `ВЫБОР КОГДА` и `ВЫБОР ПЕРВОЕ` нельзя читать как частоту выражения `ВЫБОР`.

Ни один тест корпуса настоящего окружения не читает и платформу не запускает: замерах участвует
только искусственная выгрузка во временном каталоге.
"""
from __future__ import annotations

import contextlib
import io
import json
import pathlib
import re
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "probe"))
sys.path.insert(0, str(ROOT / "scripts"))

import corpora_query_canon as canon                                # noqa: E402

ABSOLUTE_PATH = re.compile(r"[A-Za-z]:\\")

# Одна длинная строка запроса: в каноне текст запроса собирается вертикальной чертой, и обрезка
# такой строки по длине занизила бы счётчик агрегатных функций.
QUERY_LINE = (
    "Запрос.Текст = \"ВЫБРАТЬ\n"
    "|   СУММА(Продажи.Сумма) КАК Итог,\n"
    "|   МАКСИМУМ(Продажи.Сумма) КАК Максимум,\n"
    "|   ЕСТЬNULL(Продажи.Сумма, Неопределено) КАК Остаток,\n"
    "|   МИНИМУМ(Продажи.Сумма) КАК Минимум\n"
    "|ИЗ Продажи КАК Продажи\";\n"
    "Список = Новый Массив;\n"
    "Список.Добавить(Продажи);\n"
    "СуммаСтрокой = Формат(Продажи.Сумма, ЧДЦ=2; ЧГ=0);\n"
    "ДатаСтрокой = Формат(Продажи.Дата, ДФ=dd.MM.yyyy);\n"
)

# Разнесённые по строкам `ЕСТЬNULL(` и `Неопределено`, неканонические короткие имена агрегатных
# функций и два тернарных `?(` в одной строке.
SCATTERED_LINE = (
    "Если ЕСТЬNULL(А, Неопределено) Тогда\n"
    "    // ЕСТЬNULL(\n"
    "    //     Б, Неопределено)\n"
    "КонецЕсли;\n"
    "Итог = СУММ(А) + МАКС(А);\n"
    "Значение = ?(А > 1, А, 1) + ?(Б > 1, Б, 0);\n"
    "Текст = СтрСоединить(Формат(А, ЧДЦ=2), СтрСконать(\"А\"));\n"
)


class CountOccurrencesTest(unittest.TestCase):
    """Счётчик считает вхождения подстроки и не путает канонические имена с похожими."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name) / "UH"
        (self.root / "Catalogs" / "Сотрудники" / "Ext").mkdir(parents=True)
        (self.root / "Catalogs" / "Сотрудники.xml").write_text("x", encoding="utf-8")
        self.module = self.root / "Catalogs" / "Сотрудники" / "Ext" / "ObjectModule.bsl"
        self.result = self.scan_text(QUERY_LINE + SCATTERED_LINE)

    def scan_text(self, text: str) -> dict:
        """Один и тот же корпус, но с заданным содержимым единственного модуля."""
        self.module.write_text(text, encoding="utf-8")
        return canon.scan({"uh": self.root})

    def test_aggregates_of_the_canonical_spelling_are_counted(self):
        counts = self.result["counts"]
        self.assertEqual(counts["СУММА("]["uh"], 1)
        self.assertEqual(counts["МАКСИМУМ("]["uh"], 1)
        self.assertEqual(counts["МИНИМУМ("]["uh"], 1)
        self.assertEqual(sum(self.result["counts"]["СУММА("].values()), 1)

    def test_counting_one_spelling_does_not_count_the_other_one(self):
        """`СУММ(` и `МАКС(` здесь перечислены как проверка «так не пишут»: у них свои счётчики."""
        counts = self.result["counts"]
        self.assertEqual(counts["СУММ("]["uh"], 1)
        self.assertEqual(counts["МАКС("]["uh"], 1)
        self.assertEqual(counts["СУММА("]["uh"], 1, "поиск `СУММ(` не должен находить `СУММА(`")

    def test_a_needle_absent_from_the_corpus_is_reported_as_absent_not_as_zero_files(self):
        self.assertNotIn("ai_chat", self.result["counts"]["СУММА("])
        self.assertEqual(self.result["counts"]["СтрСконать"], {"uh": 1})
        self.assertEqual(self.result["modules_scanned"], {"uh": 1})

    def test_several_occurrences_in_one_file_are_all_counted(self):
        self.module.write_text("СУММА(А)\nСУММА(Б)\nСУММА(В)\n", encoding="utf-8")
        result = canon.scan({"uh": self.root})
        self.assertEqual(result["counts"]["СУММА("]["uh"], 3)
        self.assertEqual(result["modules_scanned"], {"uh": 1}, "файлов один, вхождений три")

    def test_derived_measure_needs_both_parts_in_the_same_line(self):
        scattered = self.scan_text(SCATTERED_LINE)
        self.assertEqual(scattered["counts"]["ЕСТЬNULL("]["uh"], 2)
        self.assertEqual(scattered["derived_counts"]["ЕСТЬNULL(...Неопределено)"]["uh"], 1,
                         "разнесённые по строкам `ЕСТЬNULL(` и `Неопределено` — не каноническая пара")

    def test_derived_measure_keeps_the_date_mask_inside_format(self):
        query = self.scan_text(QUERY_LINE)
        self.assertEqual(query["counts"]["ДФ=dd.MM.yyyy"]["uh"], 1)
        self.assertEqual(query["derived_counts"]["ДФ=dd.MM.yyyy внутри Формат("]["uh"], 1)

    def test_derived_measure_counts_every_pair_in_one_line(self):
        """Жадный поиск посчитал бы две пары в одной строке как одну."""
        self.module.write_text("ЕСТЬNULL(А, Неопределено) + ЕСТЬNULL(Б, Неопределено)\n",
                               encoding="utf-8")
        result = canon.scan({"uh": self.root})
        self.assertEqual(result["derived_counts"]["ЕСТЬNULL(...Неопределено)"]["uh"], 2)
        self.assertEqual(result["counts"]["ЕСТЬNULL("]["uh"], 2)

    def test_derived_measure_separates_empty_array_construction(self):
        self.module.write_text("А = Новый Массив;\nБ = Новый Массив(В);\n" * 2, encoding="utf-8")
        result = canon.scan({"uh": self.root})
        self.assertEqual(result["counts"]["Новый Массив"]["uh"], 4)
        self.assertEqual(result["derived_counts"]["Новый Массив("]["uh"], 2)

    def test_vybor_counter_is_decomposed_into_its_own_spellings(self):
        """`ВЫБОР` содержит `ВЫБОРКА`, поэтому общий счётчик нельзя читать как «платформа пишет ВЫБОР».

        Разложение обязано быть таким, чтобы из него следовало число выражений `ВЫБОР`: у общего
        счётчика отнимается число `ВЫБОРКА`, а `ВЫБОР КОГДА` и `ВЫБОР ПЕРВОЕ` считаются отдельно.
        """
        self.module.write_text(
            "Это = ВЫБОР ПЕРВОЕ А ИЗ Б;\n"
            "Текст = \"ВЫБРАТЬ А ИЗ Б\";  // ВЫБОРКА как запрос\n"
            "Итог = ВЫБОР КОГДА А > 1 ТОГДА 1 ИНАЧЕ 0 КОНЕЦ;\n",
            encoding="utf-8",
        )
        result = canon.scan({"uh": self.root})
        counts = result["counts"]
        self.assertEqual(counts["ВЫБОР"]["uh"], 3, "общий счётчик считает и `ВЫБОРКА`")
        self.assertEqual(counts["ВЫБОРКА"]["uh"], 1)
        self.assertEqual(counts["ВЫБОР КОГДА"]["uh"], 1)
        self.assertEqual(counts["ВЫБОР ПЕРВОЕ"]["uh"], 1)
        self.assertEqual(counts["ВЫБОР"]["uh"] - counts["ВЫБОРКА"]["uh"], 2,
                         "две записи выражения `ВЫБОР` без `ВЫБОРКА`")

    def test_needles_carry_the_decomposition_of_an_overlapping_needle(self):
        """Счётчик, который заведомо перекрывает другой, обязан стоять рядом с перекрываемым."""
        for overlapping in ("ВЫБОРКА", "ВЫБОР КОГДА", "ВЫБОР ПЕРВОЕ"):
            self.assertIn(overlapping, canon.NEEDLES)
            self.assertIn("ВЫБОР", canon.NEEDLES)
        self.assertGreater(canon.NEEDLES.index("ВЫБОРКА"), canon.NEEDLES.index("ВЫБОР"))

    def test_two_word_query_spelling_needs_a_text_level_measure(self):
        """В каноне `ВЫБОР` и `КОГДА` разделены переносом строки-запроса: подстрока их не считает.

        Однострочная запись считается и подстрокой, и текстовой мерой; многострочная — только
        текстовой мерой. Без текстовой меры число выражений `ВЫБОР` выглядело бы заниженным ровно
        на каноническую многострочную раскладку.
        """
        single = self.scan_text("Итог = \"ВЫБОР КОГДА А > 1 ТОГДА 1 ИНАЧЕ 0 КОНЕЦ\";\n")
        self.assertEqual(single["counts"]["ВЫБОР КОГДА"]["uh"], 1)
        self.assertEqual(single["derived_text_counts"]["ВЫБОР ... КОГДА (любой перенос)"]["uh"], 1)

        multiline = self.scan_text(
            "Запрос.Текст = \"ВЫБРАТЬ\n"
            "|   ВЫБОР\n"
            "|       КОГДА А > 1 ТОГДА 1 ИНАЧЕ 0 КОНЕЦ КАК Итог\n"
            "|ИЗ Б\";\n")
        self.assertEqual(multiline["counts"]["ВЫБОР"]["uh"], 1)
        self.assertEqual(multiline["counts"]["ВЫБОР КОГДА"], {},
                         "подстрока `ВЫБОР КОГДА` многострочную запись не находит")
        self.assertEqual(multiline["derived_text_counts"]["ВЫБОР ... КОГДА (любой перенос)"]["uh"], 1)


class FormModuleClassificationTest(unittest.TestCase):
    """Модули форм отличаются от модулей объекта и общих модулей по раскладке выгрузки."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name) / "SSL"

    def relative(self, posix: str) -> pathlib.Path:
        return self.root / posix

    def test_object_form_module_is_a_form_module(self):
        path = self.relative("Catalogs/Сотрудники/Forms/ФормаЭлемента/Ext/Form/Module.bsl")
        self.assertTrue(canon.is_form_module(path, self.root))

    def test_common_form_module_is_a_form_module_although_there_is_no_forms_directory(self):
        """В выгрузке общая форма лежит как `CommonForms/<Форма>/Ext/Form/Module.bsl`."""
        path = self.relative("CommonForms/_ДемоМоиНастройки/Ext/Form/Module.bsl")
        self.assertTrue(canon.is_form_module(path, self.root))

    def test_object_and_common_modules_are_not_form_modules(self):
        for posix in ("Catalogs/Сотрудники/Ext/ObjectModule.bsl",
                      "CommonModules/РасчётПоказателей/Module.bsl",
                      "DataProcessors/ОтчётПоЗагрузке/Ext/ObjectModule.bsl",
                      "Roles/ПолныеПрава/Ext/Rights.xml"):
            self.assertFalse(canon.is_form_module(self.relative(posix), self.root), posix)

    def test_scan_reports_form_modules_and_scanned_modules_separately(self):
        for posix in ("Catalogs/Сотрудники/Forms/ФормаЭлемента/Ext/Form/Module.bsl",
                      "CommonForms/Общая/Ext/Form/Module.bsl",
                      "Catalogs/Сотрудники/Ext/ObjectModule.bsl"):
            path = self.relative(posix)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("Процедура А() КонецПроцедуры\n", encoding="utf-8")
        result = canon.scan({"ssl": self.root})
        self.assertEqual(result["modules_scanned"], {"ssl": 3})
        self.assertEqual(result["form_modules"], {"ssl": 2})


class ReportShapeTest(unittest.TestCase):
    """Отчёт подписывает, что именно считалось, и не выдаёт путей окружения."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = pathlib.Path(self.tmp.name)
        self.uh = self.base / "UH"
        (self.uh / "Catalogs" / "Сотрудники" / "Ext").mkdir(parents=True)
        (self.uh / "Configuration.xml").write_text("x", encoding="utf-8")
        (self.uh / "Catalogs" / "Сотрудники" / "Ext" / "ObjectModule.bsl").write_text(
            QUERY_LINE, encoding="utf-8")
        self.not_a_dump = self.base / "CF"
        self.not_a_dump.mkdir()
        (self.not_a_dump / "UH.cf").write_text("x", encoding="utf-8")
        self.local_file = self.base / "local.paths.json"
        self.local_file.write_text(json.dumps(
            {"corpora_uh": str(self.uh), "corpora_cf": str(self.not_a_dump),
             "corpora_removed": str(self.base / "такого-корпуса-нет")}, ensure_ascii=False),
            encoding="utf-8")
        self.json_file = self.base / "reports" / "corpora-query-canon.json"

    def run_main(self) -> dict:
        arguments = ["--local", str(self.local_file), "--json", str(self.json_file)]
        with contextlib.redirect_stdout(io.StringIO()) as out:
            code = canon.main(arguments)
        self.assertEqual(code, 0, out.getvalue())
        return json.loads(self.json_file.read_text(encoding="utf-8"))

    def test_report_signs_what_the_numbers_count(self):
        report = self.run_main()
        self.assertIn("counting", report)
        self.assertIn("вхождений", report["counting"])
        self.assertEqual(report["limits"], {"max_file_bytes": canon.MAX_FILE_BYTES})
        self.assertEqual(report["needles"], list(canon.NEEDLES))
        self.assertEqual(sorted(report["derived"]), sorted(canon.DERIVED))
        self.assertEqual(sorted(report["derived_text"]), sorted(canon.DERIVED_TEXT))
        self.assertEqual(report["modules_scanned"], {"uh": 1})
        self.assertEqual(report["corpora_skipped"], ["corpora_cf", "corpora_removed"])

    def test_report_totals_are_the_sum_of_the_per_corpus_counts(self):
        report = self.run_main()
        for needle in canon.NEEDLES:
            self.assertEqual(report["totals"][needle], sum(report["counts"][needle].values()),
                             needle)
        for name in canon.DERIVED:
            self.assertEqual(report["derived_totals"][name],
                             sum(report["derived_counts"][name].values()), name)
        for name in canon.DERIVED_TEXT:
            self.assertEqual(report["derived_text_totals"][name],
                             sum(report["derived_text_counts"][name].values()), name)
        self.assertEqual(report["totals"]["СУММ("], 0, "в каноне `СУММ(` нет")

    def test_report_contains_no_absolute_environment_paths(self):
        """Наблюдение должно воспроизводиться на другой машине: корпус подписан именем ключа."""
        text = json.dumps(self.run_main(), ensure_ascii=False)
        match = ABSOLUTE_PATH.search(text)
        self.assertIsNone(match, "в отчёте появился абсолютный путь: " + (match.group(0)
                                                                          if match else ""))

    def test_oversized_files_are_skipped_and_the_skip_is_signed(self):
        """Без подписи пропуск крупных файлов выглядел бы как «такого в каноне нет»."""
        big = self.uh / "Catalogs" / "Сотрудники" / "Ext" / "FormModule.bsl"
        big.write_text("СУММА(" + "А" * 4000 + ")\n", encoding="utf-8")
        original = canon.MAX_FILE_BYTES
        canon.MAX_FILE_BYTES = 1000
        try:
            report = self.run_main()
        finally:
            canon.MAX_FILE_BYTES = original
        self.assertEqual(report["modules_scanned"], {"uh": 1})
        self.assertEqual(report["skipped_large_files"], {"uh": 1})
        self.assertEqual(report["totals"]["СУММА("], 1, "крупный файл в счётчик не вошёл")


if __name__ == "__main__":
    unittest.main()
