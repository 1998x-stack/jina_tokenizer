"""Command line interface for standalone local text chunking."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .core import TextChunker


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Lossless structural text chunker (not an LLM token counter)")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("path", nargs="?", help="UTF-8 text file")
    source.add_argument("--text", help="Literal text to chunk")
    source.add_argument("--stdin", action="store_true", help="Read UTF-8 from standard input")
    parser.add_argument("--max-chars", type=int, default=1000, help="Maximum code points per chunk")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable UTF-8 JSON")
    args = parser.parse_args(argv)
    try:
        text = args.text if args.text is not None else (sys.stdin.read() if args.stdin else Path(args.path).read_text(encoding="utf-8"))
        chunks = TextChunker(args.max_chars).process_text(text)
    except (ValueError, OSError, UnicodeError) as exc:
        parser.exit(2, f"error: {exc}\n")
    result = {"chunks": [chunk.to_dict() for chunk in chunks], "info": {"chunk_count": len(chunks), "input_chars": len(text), "coverage_complete": "".join(c.content for c in chunks) == text}}
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"chunks={len(chunks)} chars={len(text)} coverage={result['info']['coverage_complete']}")
        for chunk in chunks[:10]:
            print(f"[{chunk.chunk_type} {chunk.start_pos}:{chunk.end_pos}] {chunk.content[:70]!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
