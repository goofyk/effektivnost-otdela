"""Чем именно файлы выгрузки отличаются от исходника после нормализации BOM и переводов строк.

Наблюдение гейта gate-04: загрузка `код 0` (3 с), выгрузка `код 0` (2 с), но пофайловое сравнение
источника и выгрузки дало `same 5`, `differ 19`, `only_dump: ["ConfigDumpInfo.xml"]`, хотя `fc.exe`
по одному из «отличающихся» файлов (`Enums/ГрейдыСпециалистов.xml`) говорит «no differences
encountered». Этот замер показал три разных события:

1. 8 файлов отличались только завершающим переводом строки (мы его пишем, платформа нет);
2. `ConfigDumpInfo.xml` добавляет в выгрузку платформа (он есть во всех канонических корпусах);
3. остальные отличия — платформенная канонизация состава: платформа дописывает свойства, которые
   мы не написали, и переписывает узлы, которые мы написали неканонически (например наши
   `<v8:DecimalQualifiers><v8:Precision>2` она превратила в `<v8:NumberQualifiers>` с нулями).

После того как контур научился различать 1 и 2 (`gate.file_diff`, `gate.PLATFORM_ADDED_FILES`),
этот замер показывает содержимое только настоящих отличий. Классификацию файлов он берёт из
`gate.file_diff`, чтобы числа замера и гейта не расходились.

Пути берутся из `local.paths.json` (`cfg`, `dump`). Платформу замер не запускает, ничего не пишет.
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import gate                                                      # noqa: E402
import paths                                                     # noqa: E402

CONTEXT = 110


def normalized(path: pathlib.Path) -> str:
    """Как контур: BOM и переводы строк нормализуются, завершающие переводы строки не считаются."""
    data = path.read_bytes()
    if data[:3] == b"\xef\xbb\xbf":
        data = data[3:]
    return data.decode("utf-8", "replace").replace("\r\n", "\n").rstrip("\r\n")


def first_difference(a: str, b: str) -> int:
    limit = min(len(a), len(b))
    for index in range(limit):
        if a[index] != b[index]:
            return index
    return limit


def main(argv: list | None = None) -> int:
    local = paths.load_local(str(ROOT / "local.paths.json"))
    source_dir = pathlib.Path(argv[0]) if argv else pathlib.Path(local["cfg"])
    dump_dir = pathlib.Path(local["dump"])
    diff = gate.file_diff(source_dir, dump_dir)
    print("одинаковых:", len(diff["same"]), "| отличающихся:", len(diff["differ"]),
          "| только в источнике:", diff["only_source"],
          "| файлов платформы в выгрузке:", diff["platform_added"],
          "| только в выгрузке:", diff["only_dump"])
    source_files = {path.relative_to(source_dir).as_posix(): path
                    for path in source_dir.rglob("*") if path.is_file()}
    dump_files = {path.relative_to(dump_dir).as_posix(): path
                  for path in dump_dir.rglob("*") if path.is_file()}
    for relative in diff["differ"]:
        left, right = normalized(source_files[relative]), normalized(dump_files[relative])
        position = first_difference(left, right)
        print("\n---", relative, "| источника", len(left), "символов",
              "| выгрузки", len(right), "символов", "| первое различие в", position)
        print("   источник:", repr(left[position:position + CONTEXT]))
        print("   выгрузка:", repr(right[position:position + CONTEXT]))
    return 1 if diff["differ"] or diff["only_source"] or diff["only_dump"] else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
