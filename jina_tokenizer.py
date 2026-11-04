"""Legacy CLI script and library import shim."""

from jina_chunker import TextChunk, TextChunker
from jina_chunker.cli import main

__all__ = ["TextChunk", "TextChunker", "main"]

if __name__ == "__main__":
    raise SystemExit(main())
