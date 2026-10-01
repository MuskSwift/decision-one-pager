"""argparse CLI for Decision One-Pager Engine v0."""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

from .generate import generate, strip_leading_preamble, strip_wrapping_fences
from .validate import missing_headings


def slugify(topic: str, max_len: int = 48) -> str:
    """ASCII-ish slug: keep letters, digits, CJK; spaces become hyphens."""
    text = topic.strip().lower()
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"[^\w\u4e00-\u9fff\-]+", "", text, flags=re.UNICODE)
    text = re.sub(r"-{2,}", "-", text).strip("-._")
    if not text:
        text = hashlib.sha1(topic.encode("utf-8")).hexdigest()[:10]
    return text[:max_len]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="decision-one-pager",
        description="Decision One-Pager Engine v0 — generate a 6-heading Chinese decision memo.",
    )
    parser.add_argument(
        "topic_pos",
        nargs="?",
        help="Decision topic (positional alternative to --topic)",
    )
    parser.add_argument("--topic", help="Decision topic")
    parser.add_argument("--materials", help="Background materials as a string")
    parser.add_argument(
        "--materials-file",
        metavar="PATH",
        help="Path to a file containing background materials",
    )
    parser.add_argument("--taboo", help="Taboo / forbidden content as a string")
    parser.add_argument(
        "--taboo-file",
        metavar="PATH",
        help="Path to a file containing taboo / forbidden content",
    )
    parser.add_argument(
        "--out",
        help="Output markdown path (default: ./out/<slug>-one-pager.md)",
    )
    return parser.parse_args(argv)


def _read_text(path: str) -> str:
    file_path = Path(path)
    if not file_path.is_file():
        raise FileNotFoundError(f"file not found: {path}")
    return file_path.read_text(encoding="utf-8")


def _join_sources(inline: str | None, file_path: str | None) -> str:
    parts: list[str] = []
    if inline and inline.strip():
        parts.append(inline.strip())
    if file_path:
        parts.append(_read_text(file_path).strip())
    return "\n\n".join(p for p in parts if p)


def resolve_inputs(args: argparse.Namespace) -> tuple[str, str, str]:
    topic = (args.topic or args.topic_pos or "").strip()
    if not topic:
        raise ValueError("topic is required (positional or --topic)")

    materials = _join_sources(args.materials, args.materials_file)
    if not materials:
        raise ValueError("at least one of --materials or --materials-file is required")

    taboo = _join_sources(args.taboo, args.taboo_file)
    return topic, materials, taboo


def resolve_out(out_arg: str | None, topic: str) -> Path:
    if out_arg:
        return Path(out_arg)
    return Path("out") / f"{slugify(topic)}-one-pager.md"


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    out_path: Path | None = None
    try:
        topic, materials, taboo = resolve_inputs(args)
        markdown = strip_wrapping_fences(generate(topic, materials, taboo))
        markdown = strip_leading_preamble(markdown)
        if not markdown.strip():
            raise RuntimeError("generation produced empty markdown")

        out_path = resolve_out(args.out, topic)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(markdown.rstrip() + "\n", encoding="utf-8")

        missing = missing_headings(markdown)
        if missing:
            try:
                out_path.unlink()
            except OSError:
                pass
            print("validation failed; missing headings:", file=sys.stderr)
            for heading in missing:
                print(f"  {heading}", file=sys.stderr)
            return 1

        print(str(out_path))
        return 0
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
