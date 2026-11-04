"""Backward-compatible import: ``from tokenizer import TextChunker``.

New integrations should import from ``jina_chunker`` instead.
"""

from jina_chunker.compat import TextChunker
from jina_chunker.core import TextChunk

__all__ = ["TextChunk", "TextChunker"]
