# Architecture and invariants

## Pipeline

```text
Input (Python str, unchanged)
  -> splitlines(keepends=True) and absolute offset index
  -> priority-ordered block scanner
      fence / display math / HTML / heading / table / rule / quote / list / reference / indented code / paragraph
  -> bounded soft-boundary splitter (max_chunk_chars)
  -> frozen TextChunk(content, type, start_pos, end_pos)
  -> Python list, CLI JSON or optional Flask response
```

No external model, remote API or embedding computation is involved. The block scanner recognizes a deliberately limited subset of Markdown/HTML. It is deterministic and bounded by document size. Broad HTML correctness (attributes containing `>`, nesting and mixed-case elements) is outside the supported subset.

## Safety properties

1. **Coverage:** block spans are contiguous and cover the entire string, including CRLF, blank lines and whitespace. The secondary splitter partitions each span, never filters it.
2. **Offsets:** `start_pos` is inclusive, `end_pos` is exclusive and is measured in Unicode code points of the *original* Python string.
3. **Limit:** a chunk never exceeds the configured code-point budget. A code fence may be split when the complete block is larger than the budget; consumers should use `chunk_type=code` and offsets to reassemble it when needed.
4. **Boundaries:** paragraph segmentation prefers punctuation and whitespace but falls back to a hard character cut. Extremely small budgets may split a grapheme/ZWJ emoji sequence.
5. **Error boundary:** file read failures are raised by the new API and represented as an `info.error` in the legacy JSON API; the Flask endpoint never opens caller-provided paths.

## Trade-offs

- Compared to one composite regex: straightforward traceability, no nested backtracking across entire document, explicit named types and exact coverage.
- Compared to CommonMark parsers: lower dependency footprint and preservation of original positions without AST reconstruction; not a fully conformant parser.
- Compared to model tokenizers: character length can differ widely from token counts. For real token budgets, compose with the tokenizer of the target model.
- Compared to Jina Segmenter: this is an independent local heuristic implementation. Do not expect matching segmentation or hosted API behavior.

## Compatibility contract

| Entry point | Return type | Notes |
|---|---|---|
| `jina_chunker.TextChunker.process_text(text)` | `list[TextChunk]` | Recommended |
| `jina_chunker.TextChunker.process_file(path)` | `list[TextChunk]` | Raises on file errors |
| `jina_tokenizer.TextChunker` | `list[TextChunk]` | Legacy import shim |
| `tokenizer.TextChunker.process_str(text)` | JSON-like `dict` | Historical Flask interface |
| `tokenizer.TextChunker.process_file(path)` | JSON-like `dict` | Historical JSON file interface |
| `POST /tokenizer` | JSON | String input only, never file paths |

The former `Type_1` etc. are replaced by stable descriptive type names. This is a documented migration, not bit-for-bit output compatibility. Avoid using chunk types as positional regex group IDs.
