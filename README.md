# jina_tokenizer — Lossless Structure-Aware Text Chunker

[![CI](https://github.com/1998x-stack/jina_tokenizer/actions/workflows/ci.yml/badge.svg)](https://github.com/1998x-stack/jina_tokenizer/actions/workflows/ci.yml)

A small, deterministic Python library for splitting Markdown, HTML snippets, Chinese and English text into **lossless, position-aware chunks**. Designed as a preprocessing building block for RAG and document indexing. No cloud service, model download, or API key is required.

> **Naming:** This is a *text chunker*, not a model tokenizer. It does not encode text as model token IDs or measure model context-window tokens. The historical repository name and CLI filename are retained for compatibility.

## Guarantees

- **Lossless:** `''.join(chunk.content for chunk in chunks) == original_text`.
- **Exact offsets:** `original_text[chunk.start_pos:chunk.end_pos] == chunk.content`; offsets count Python Unicode code points (not UTF-8 bytes).
- **Strict character cap:** each output chunk contains at most `max_chunk_chars` code points (default **1000**). Oversized structural blocks are divided and retain the same type; no promise of syntactic completeness across such splits.
- **Deterministic:** same input and configuration produce the same chunks; no inference calls.
- **Structured boundaries:** ATX/Setext headings, Markdown lists, blockquotes, fenced and indented code, tables, thematic breaks, reference entries, `<pre>`/`<table>`/heading HTML blocks, and display math (`$$`/`\[...\]`). Unmatched fences and math delimiters extend to the end of the document instead of silently losing content.
- **Safe HTTP boundary:** local file paths are accepted by trusted local CLI/Python code, **not** by the HTTP endpoint.

This is a practical, heuristic parser, not a complete CommonMark/HTML/LaTeX implementation. It does not guarantee semantic equivalence, full Markdown nesting, language-specific sentence interpretation, grapheme-preserving splits at very small limits, or embedding-model token budgets.

## Install

Python **3.10+**:

```bash
python -m pip install -e .           # core: standard library only
python -m pip install -e '.[api]'   # optional Flask HTTP service
```

## Python API

```python
from jina_chunker import TextChunker

source = '# 标题\n\n中文第一句。English second sentence!\n'
chunks = TextChunker(max_chunk_chars=120).process_text(source)

assert ''.join(item.content for item in chunks) == source
for chunk in chunks:
    print(chunk.chunk_type, chunk.start_pos, chunk.end_pos, repr(chunk.content))
```

`TextChunk` contains `content`, `chunk_type`, `start_pos`, `end_pos`, and `to_dict()`. The modern `process_file(path)` returns `list[TextChunk]` and raises ordinary file errors.

### CLI

```bash
jina-chunker doc/Grimm.txt --max-chars 1000
jina-chunker --text '# Hello\n\n你好。' --json
cat README.md | jina-chunker --stdin --json
# original script is still a valid CLI entry point:
python jina_tokenizer.py doc/Grimm.txt --json
```

### HTTP API (optional)

```bash
python -m pip install -e '.[api]'
flask --app app run --host 127.0.0.1 --port 5000
curl -sS http://127.0.0.1:5000/tokenizer \
  -H 'Content-Type: application/json' \
  -d '{"text":"Hello! 你好。"}'
```

`POST /tokenizer` accepts `{"text":"..."}` or the legacy payload `{"input_data":"...","input_type":"string"}`. Response includes `chunks` and `info`; `GET /healthz` is available. File paths sent by HTTP are rejected with HTTP 400. Invalid JSON and types return 400, non-JSON requests 415, excessive bodies/text 413. The default maximum text length is 200,000 characters; customize through `create_app(max_text_chars=...)` in a deployment wrapper. The built-in development server is not a production deployment choice.

### Historical compatibility

- `from tokenizer import TextChunker` preserves the **JSON-returning** `process_str`, `process_file`, and `process(input_data, input_type)` interface; the legacy `process_file` returns an error payload for file read failures.
- `from jina_tokenizer import TextChunker` preserves the original **list-returning** local `process_file` interface and exposes `process_text`.
- New code should import from `jina_chunker` and use `process_text` / `process_file`.
- `chunk_type` now uses meaningful names (`heading`, `paragraph`, `list`, `code`, `table`, `blockquote`, `math`, `reference`, `thematic_break`, `whitespace`) rather than unstable `Type_N` group indexes. If you rely on old labels, migrate explicitly.

## Validate and benchmark

```bash
PYTHONPATH=src:. python -m unittest discover -s tests -v
PYTHONPATH=src python benchmarks/benchmark.py
```

CI runs Python 3.10 and 3.13 with the API extra. The benchmark prints local time and throughput; it is not a claim of performance relative to Jina's hosted Segmenter.

## Background and sources

The earlier README documented a single large regex inspired by structural text splitting. The present implementation uses an **independent line scanner plus bounded character splitting** to make coverage and offset invariants testable, rather than copying the linked regex.

- [Jina Segmenter — official overview](https://jina.ai/segmenter): comparison point for chunking and model tokenizer functionality; this project does not call the API.
- [Jina late chunking explainer](https://jina.ai/news/late-chunking-in-long-context-embedding-models/): downstream embedding technique distinct from our local chunker.
- [Jina-inspired regex example (third-party Gist)](https://gist.github.com/Josephrp/880181141c76259c4eda1fab247fe4ae): historical background only, **not** copied into this source.
- [regex101](https://regex101.com/): useful to explore individual rules, but its engine is not identical to Python `re`.
- [Original Han Xiao Gist](https://gist.github.com/hanxiao/3f60354cf6dc5ac698bc9154163b4e6a) and [original WeChat article](https://mp.weixin.qq.com/s/HsyEgqbhO2iqdJAGVs3pdA): retained for provenance; unavailable to verify in the November 2026 review. Do not treat them as verified API or license documentation.

Further details: [Architecture](docs/ARCHITECTURE.md), [Reference audit](docs/REFERENCE_REVIEW.md), [Development](docs/DEVELOPMENT.md).

## License

**The original repository does not currently contain a LICENSE file.** Redistribution terms must be confirmed with the repository owner before publication as a reusable licensed package. This PR deliberately does not invent a license or assume that the upstream Jina/Gist license covers this implementation.
