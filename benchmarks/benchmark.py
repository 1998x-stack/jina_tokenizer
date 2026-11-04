"""Deterministic local benchmark; run: python benchmarks/benchmark.py."""

from __future__ import annotations

import json
from time import perf_counter

from jina_chunker import TextChunker


def main():
    sentence = "# Chunking test\n\nEnglish content. 中文内容。Emoji 🙂.\n\n"
    chunker = TextChunker(max_chunk_chars=1000)
    results = []
    for characters in (10_000, 100_000, 1_000_000):
        sample = (sentence * (characters // len(sentence) + 1))[:characters]
        start = perf_counter()
        chunks = chunker.process_text(sample)
        seconds = perf_counter() - start
        assert "".join(c.content for c in chunks) == sample
        results.append({"input_chars": len(sample), "chunks": len(chunks), "elapsed_seconds": round(seconds, 6), "chars_per_second": round(len(sample) / max(seconds, 1e-9))})
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
