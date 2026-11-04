"""Lossless, deterministic, structure-aware text chunking.

Offsets are Python Unicode code-point offsets into the unmodified input string.
This module does not compute model token IDs or semantic embeddings.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import re
from typing import Iterator


_ATX = re.compile(r"^ {0,3}#{1,6}(?:[ \t]+|$)")
_SETEXT = re.compile(r"^ {0,3}(?:=+|-+)[ \t]*$")
_FENCE = re.compile(r"^ {0,3}(?P<mark>`{3,}|~{3,})(?P<info>[^\r\n]*)$")
_LIST = re.compile(r"^ {0,3}(?:[-+*•]|[0-9]{1,9}[.)])(?:[ \t]+|$)")
_QUOTE = re.compile(r"^ {0,3}>[ \t]?")
_HRULE = re.compile(r"^ {0,3}(?:(?:\*[ \t]*){3,}|(?:-[ \t]*){3,}|(?:_[ \t]*){3,})$")
_REFERENCE = re.compile(r"^ {0,3}\[[0-9]+\][ \t]+")
_HTML_OPEN = re.compile(r"^ {0,3}<(?P<tag>pre|table|h[1-6])(?:\s[^>]*)?>", re.IGNORECASE)
_MATH_OPEN = re.compile(r"^ {0,3}(?:\$\$|\\\[)[ \t]*$")
_TABLE_SEPARATOR = re.compile(r"^:?-{3,}:?$")
_SENTENCE_END = set("。！？!?；;…")


@dataclass(frozen=True, slots=True)
class TextChunk:
    content: str
    chunk_type: str
    start_pos: int
    end_pos: int

    def to_dict(self) -> dict[str, str | int]:
        return asdict(self)


def _without_eol(line: str) -> str:
    return line.rstrip("\r\n")


def _table_rule(line: str) -> bool:
    cells = _without_eol(line).strip().strip("|").split("|")
    return len(cells) >= 2 and all(_TABLE_SEPARATOR.fullmatch(c.strip()) for c in cells)


def _is_table(lines: list[str], i: int) -> bool:
    return (
        i + 1 < len(lines)
        and "|" in lines[i]
        and _table_rule(lines[i + 1])
        and len(_without_eol(lines[i]).strip("|").split("|"))
        == len(_without_eol(lines[i + 1]).strip("|").split("|"))
    )


def _structural_line(lines: list[str], i: int) -> bool:
    line = _without_eol(lines[i])
    return bool(
        not line.strip()
        or _ATX.match(line)
        or _FENCE.match(line)
        or _LIST.match(line)
        or _QUOTE.match(line)
        or _HRULE.match(line)
        or _REFERENCE.match(line)
        or _HTML_OPEN.match(line)
        or _MATH_OPEN.match(line)
        or _is_table(lines, i)
    )


def _blocks(text: str) -> Iterator[tuple[str, int, int]]:
    """Yield contiguous (type, start, end) spans covering every input character."""
    lines = text.splitlines(keepends=True)
    # splitlines treats Unicode paragraph separators as line boundaries too; preserve
    # them verbatim in the returned spans.
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))

    i = 0
    while i < len(lines):
        line = _without_eol(lines[i])
        j = i + 1
        kind = "paragraph"
        fence = _FENCE.match(line)
        html = _HTML_OPEN.match(line)
        if not line.strip():
            kind = "whitespace"
            while j < len(lines) and not lines[j].strip():
                j += 1
        elif fence:
            kind = "code"
            marker = fence.group("mark")
            # A closing fence must use the same character, with at least the
            # opening length, and contain nothing after it but whitespace.
            closer = re.compile(r"^ {0,3}" + re.escape(marker[0]) +
                                "{" + str(len(marker)) + r",}[ \t]*$")
            while j < len(lines):
                if closer.fullmatch(_without_eol(lines[j])):
                    j += 1
                    break
                j += 1
        elif _MATH_OPEN.match(line):
            kind = "math"
            closer = "$$" if line.lstrip().startswith("$$") else r"\]"
            while j < len(lines):
                if _without_eol(lines[j]).strip() == closer:
                    j += 1
                    break
                j += 1
        elif html:
            tag = html.group("tag").lower()
            kind = "heading" if tag.startswith("h") else ("code" if tag == "pre" else "table")
            closing = re.compile(r"</" + tag + r"\s*>", re.IGNORECASE)
            if not closing.search(line):
                while j < len(lines):
                    if closing.search(lines[j]):
                        j += 1
                        break
                    j += 1
        elif _ATX.match(line):
            kind = "heading"
        elif _is_table(lines, i):
            kind = "table"
            j = i + 2
            while j < len(lines) and "|" in lines[j] and lines[j].strip():
                j += 1
        elif _HRULE.match(line):
            kind = "thematic_break"
        elif i + 1 < len(lines) and line.strip() and _SETEXT.match(_without_eol(lines[i + 1])):
            kind = "heading"
            j = i + 2
        elif _QUOTE.match(line):
            kind = "blockquote"
            while j < len(lines) and _QUOTE.match(_without_eol(lines[j])):
                j += 1
        elif _LIST.match(line):
            kind = "list"
            while j < len(lines):
                next_line = _without_eol(lines[j])
                if _LIST.match(next_line) or (next_line.startswith(("    ", "\t")) and next_line.strip()):
                    j += 1
                else:
                    break
        elif _REFERENCE.match(line):
            kind = "reference"
        elif line.startswith(("    ", "\t")):
            kind = "code"
            while j < len(lines) and lines[j].startswith(("    ", "\t")):
                j += 1
        else:
            while j < len(lines) and not _structural_line(lines, j):
                # Keep a Setext underline attached to its preceding paragraph.
                if j + 1 < len(lines) and _SETEXT.match(_without_eol(lines[j + 1])):
                    break
                j += 1
        yield kind, offsets[i], offsets[j]
        i = j


def _soft_boundary(text: str, start: int, limit: int) -> int:
    """Select a boundary within a strict character budget, never dropping data."""
    minimum = start + max(1, (limit - start) // 2)
    for at in range(limit - 1, minimum - 1, -1):
        current = text[at]
        following = text[at + 1] if at + 1 < len(text) else ""
        if current in _SENTENCE_END:
            return at + 1
        if current == "." and (not following or following.isspace()):
            return at + 1
        if current in "\n\r" or current.isspace():
            return at + 1
    # Prefer not to begin a piece with a combining mark or emoji modifier.
    try:
        import unicodedata
        while limit > start + 1 and (
            unicodedata.combining(text[limit])
            or text[limit] in "\ufe0e\ufe0f\u200d"
            or "\U0001f3fb" <= text[limit] <= "\U0001f3ff"
        ):
            limit -= 1
    except IndexError:
        pass
    return limit


class TextChunker:
    """Deterministic chunker with a strict maximum number of characters.

    Structural blocks are preserved as a unit when within the configured limit.
    Oversized blocks are split, retain their type, and may span multiple chunks.
    """

    def __init__(self, max_chunk_chars: int = 1000) -> None:
        if isinstance(max_chunk_chars, bool) or not isinstance(max_chunk_chars, int) or not 1 <= max_chunk_chars <= 1_000_000:
            raise ValueError("max_chunk_chars must be an integer between 1 and 1,000,000")
        self.max_chunk_chars = max_chunk_chars

    def process_text(self, text: str) -> list[TextChunk]:
        if not isinstance(text, str):
            raise TypeError("text must be a string")
        chunks: list[TextChunk] = []
        for kind, start, end in _blocks(text):
            pos = start
            while pos < end:
                limit = min(pos + self.max_chunk_chars, end)
                cut = _soft_boundary(text, pos, limit) if limit < end else end
                if cut <= pos:
                    cut = limit
                chunks.append(TextChunk(text[pos:cut], kind, pos, cut))
                pos = cut
        return chunks

    def chunk(self, text: str) -> list[TextChunk]:
        return self.process_text(text)

    def process_file(self, filepath: str | Path, *, encoding: str = "utf-8") -> list[TextChunk]:
        return self.process_text(Path(filepath).read_text(encoding=encoding))
