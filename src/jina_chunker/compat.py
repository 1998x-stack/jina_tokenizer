"""Compatibility layer for the legacy tokenizer.py JSON API."""

from __future__ import annotations

from pathlib import Path
from time import perf_counter

from .core import TextChunker as CoreTextChunker


class TextChunker(CoreTextChunker):
    def _response(self, text: str) -> dict:
        start = perf_counter()
        chunks = self.process_text(text)
        elapsed = perf_counter() - start
        return {
            "chunks": [chunk.to_dict() for chunk in chunks],
            "info": {
                "chunk_count": len(chunks),
                "input_chars": len(text),
                "execution_time_sec": round(elapsed, 6),
                "execution_time": f"{elapsed:.3f} seconds",
                "coverage_complete": "".join(c.content for c in chunks) == text,
            },
        }

    def process_str(self, content: str) -> dict:
        return self._response(content)

    def process_file(self, filepath: str | Path, *, encoding: str = "utf-8") -> dict:
        try:
            return self._response(Path(filepath).read_text(encoding=encoding))
        except (OSError, UnicodeError) as exc:
            return {"chunks": [], "info": {"error": f"Cannot read input file: {type(exc).__name__}"}}

    def process(self, input_data: str, input_type: str) -> dict:
        if input_type == "string":
            return self.process_str(input_data)
        if input_type == "file":
            return self.process_file(input_data)
        return {"chunks": [], "info": {"error": "input_type must be 'file' or 'string'"}}
