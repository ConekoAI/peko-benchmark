"""mdstats — line/word/byte stats for text files. Stdlib only."""

from __future__ import annotations

import argparse
import sys


def count_lines(text: str) -> int:
    if not text:
        return 0
    return text.count("\n") + (0 if text.endswith("\n") else 1)


def count_words(text: str) -> int:
    return len(text.split())


def count_bytes(text: str) -> int:
    return len(text.encode("utf-8"))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="mdstats", description=__doc__)
    p.add_argument("file", nargs="?", help="input file (default: stdin)")
    p.add_argument("--lines", action="store_true", help="print line count")
    p.add_argument("--words", action="store_true", help="print word count")
    p.add_argument("--bytes", action="store_true", help="print byte count")
    return p


def read_input(path: str | None) -> str:
    if path is None:
        return sys.stdin.read()
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    text = read_input(args.file)
    show_all = not (args.lines or args.words or args.bytes)
    parts = []
    if args.lines or show_all:
        parts.append(str(count_lines(text)))
    if args.words or show_all:
        parts.append(str(count_words(text)))
    if args.bytes or show_all:
        parts.append(str(count_bytes(text)))
    label = args.file if args.file else "-"
    print("\t".join(parts) + f" {label}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
