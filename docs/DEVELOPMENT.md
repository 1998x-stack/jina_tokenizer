# Development and review checklist

## Environment

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[api]'
python -m unittest discover -s tests -v
python -m compileall -q src tests app.py tokenizer.py jina_tokenizer.py
python benchmarks/benchmark.py
```

## Required gates

- Lossless round-trip and code-point offsets for every fixture, including CRLF and emoji.
- Max chunk size honored for arbitrary input and malformed/unclosed structures.
- Tests cover Markdown ATX/Setext heading, fences, tables, lists, quotes, references, HTML and display math.
- Error behavior explicit for invalid source types and unreadable files.
- API rejects file paths, oversized input and malformed JSON; debug mode not enabled.
- Run the benchmark on a representative corpus; compare across commits on the same machine before making speed claims.
- Keep the historical wrappers and clarify intentional compatibility changes in the PR body.

## Future work (not claimed by this PR)

- CommonMark conformance suite and tokenizer-aware budgeting.
- Incremental streaming chunking for multi-gigabyte files.
- HTML DOM parser for arbitrary nested documents.
- Fuzzing in CI and performance regression thresholds based on a stable runner.
- License verification, release automation and package publication.
