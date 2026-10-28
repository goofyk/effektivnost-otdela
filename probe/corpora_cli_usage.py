"""Как 1С-Софт сама вызывает имена командной строки: обход корпусов по строкам.

Зачем это нужно. `p1c/src/p1c/data/test_cli_flags.json` отвечает только на вопрос «существует такое
имя в списке параметров платформы». Он не отвечает на вопрос «как этим именем пользуются». Разница
важна: у `-listFile` в корпусе есть каноническое описание файла списка (кодировка, переносы,
состав имён), у `-Format` — канонические значения, у `/SetPredefinedDataUpdate` — нигде нет ни
одного вхождения, у `-AllExtensions` — описание, из которого следует, что «несуществующее расширение
будет создано». Поэтому перед тем как собирать лестницу модификаторов, контур читает, как команды
выглядят в исходном коде конфигураций 1С.

Что именно ищется. Строки, где имя параметра стоит в тексте программы (обычно в комментарии с
подписью команды или в `КомандаЗапуска.Добавить("...")`), плюс форма строки запуска с режимом
(`DESIGNER|CONFIG|ENTERPRISE {0} {1} /UpdateDBCfg -server ...`). Отдельно считается число вхождений
в корпус и сохраняются первые образцы с номером строки — их можно перепроверить по файлу.

Пути берутся только из `local.paths.json` (ключи `corpora_*`) через `scripts/corpora.py`: в этом
файле путей нет. Обход подписан числом прочитанных файлов на каждый корпус.

    $env:PYTHONIOENCODING="utf-8"
    python probe/corpora_cli_usage.py --json reports/corpora-cli-usage-16.json
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import corpora                                                   # noqa: E402
import paths                                                     # noqa: E402

# Имена, по которым ищем каноническое употребление: имена команд и модификаторов лестниц Task 16.
# Берутся ровно те написания, которые встречаются в каноне: в подписи команды БСП модификаторы
# записаны строчными (`[-files][-listfile][-format]`), в замере имён платформы — с большой буквы
# (`-listFile`), поэтому обе формы перечислены отдельно. Ищем ровно написания имён: поиск слова
# `Format` или `Extension` дал бы вхождения программных идентификаторов, а не вызовов команды.
NEEDLES = (
    "DumpConfigToFiles",
    "LoadConfigFromFiles",
    "UpdateDBCfg",
    "UpdateCfg",
    "LoadCfg",
    "DumpCfg",
    "DumpDBCfg",
    "RunScript",
    "SetPredefinedDataUpdate",
    "IBCheckAndRepair",
    "AllExtensions",
    "RebuildConfigurationExtensions",
    "CheckCanApplyConfigurationExtensions",
    "listFile",
    "listfile",
)

# Максимум образцов на имя: иначе вывод не читается, а число вхождений всё равно полное.
MAX_SAMPLES = 8

# Ограничения обхода, подписанные в отчёте: файлы больше 2 МБ не читаем (в корпусах это выгрузки
# форм и макетов), и не считаем вхождений в строки длиннее 400 символов (в них обычно не вызов
# команды, а склеенная одна строка данных).
MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_LINE_CHARS = 400

MODE_RE = re.compile(r"\b(ENTERPRISE|CONFIG|DESIGNER|ADMIN|COMCONNECTION|CONSOLE)\b")


def scan(roots: dict, needles: tuple = NEEDLES) -> dict:
    """Счёт вхождений и образцы строк по каждому корпусу.

    Содержимое строки в образце не правится (обрезается только хвост), чтобы номер строки
    соответствовал файлу и наблюдение можно было перепроверить вручную.
    """
    counts = {needle: {} for needle in needles}
    samples = {needle: [] for needle in needles}
    files_read = {}
    for label, root in sorted(roots.items()):
        root = pathlib.Path(root)
        seen = 0
        for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
            if not path.is_file():
                continue
            try:
                if path.stat().st_size > MAX_FILE_BYTES:
                    continue
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            seen += 1
            lines = text.splitlines()
            for needle in needles:
                hits = [index for index, line in enumerate(lines, start=1)
                        if needle in line and len(line) <= MAX_LINE_CHARS]
                if not hits:
                    continue
                counts[needle][label] = counts[needle].get(label, 0) + len(hits)
                for index in hits:
                    if len(samples[needle]) >= MAX_SAMPLES:
                        break
                    line = lines[index - 1].strip()
                    match = MODE_RE.search(line)
                    samples[needle].append({"corpus": label,
                                            "file": path.relative_to(root).as_posix(),
                                            "line": index,
                                            "mode": match.group(1) if match else "",
                                            "text": line[:220]})
        files_read[label] = seen
    return {"counts": counts, "samples": samples, "files_read": files_read}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--local", default=str(ROOT / "local.paths.json"))
    parser.add_argument("--json", default=str(ROOT / "reports" / "corpora-cli-usage-16.json"))
    args = parser.parse_args(argv)

    local = paths.load_local(args.local)
    roots = {}
    for key, value in sorted(local.items()):
        if not key.startswith(paths.KNOWN_PREFIXES[0]):
            continue
        directory = pathlib.Path(value)
        if directory.is_dir():
            roots[key.removeprefix(paths.KNOWN_PREFIXES[0])] = directory
    accepted = corpora.report(args.local)
    scan_roots = {label: path for label, path in roots.items()
                  if f"corpora_{label}" in accepted["accepted"]}
    skipped = [key for key in accepted["configured"]
               if key not in {f"corpora_{label}" for label in scan_roots}]

    result = scan(scan_roots)
    result["corpora_accepted"] = accepted["accepted"]
    result["corpora_skipped"] = skipped
    result["needles"] = list(NEEDLES)
    result["totals"] = {needle: sum(counts.values()) for needle, counts in result["counts"].items()}
    output = pathlib.Path(args.json)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    for needle in NEEDLES:
        print(f"{needle}: {result['totals'][needle]} -> "
              f"{json.dumps(result['counts'][needle], ensure_ascii=False)}")
    print(f"files_read: {json.dumps(result['files_read'], ensure_ascii=False)}")
    print(f"limits: файлы <= {MAX_FILE_BYTES} байт, строки <= {MAX_LINE_CHARS} символов")
    print(f"accepts: {', '.join(accepted['accepted'])}")
    print(f"skipped: {', '.join(skipped) or 'нет'}")
    print(f"report -> {output.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
