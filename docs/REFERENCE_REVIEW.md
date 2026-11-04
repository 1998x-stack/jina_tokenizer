# README source review — 2026-11-04

The legacy README referenced regex101, a Han Xiao Gist, and a WeChat article. This document separates verified observations from unavailable sources.

| Source | Observation | Implementation decision |
|---|---|---|
| https://regex101.com/ | Regex testing playground; Python runtime regex behavior may differ by engine. | Unit tests on the Python runtime are authoritative. |
| https://gist.github.com/hanxiao/3f60354cf6dc5ac698bc9154163b4e6a | Original link was not accessible (HTTP 404) when reviewed. | Keep a provenance link but do not infer current source, contents or license. |
| https://mp.weixin.qq.com/s/HsyEgqbhO2iqdJAGVs3pdA | Article could not be retrieved by automated review. | Keep as unverified background, not a specification. |
| https://jina.ai/segmenter | Official Jina Segmenter product page describes tokenization and structure-aware chunking. | Clearly distinguish this local chunker from model tokenization and from the hosted API. |
| https://jina.ai/news/late-chunking-in-long-context-embedding-models/ | Jina discusses late chunking for embedding models. | Document late chunking as downstream context, not a feature of this repository. |
| https://gist.github.com/Josephrp/880181141c76259c4eda1fab247fe4ae | Accessible third-party illustration of the older all-in-one regex approach. | Historical explanation only; no source copied. |

## Corrections to the old README

- The example `from text_chunker import TextChunker` did not match repository files.
- It described fourteen regex types, while runtime classification depended on capture-group indices rather than stable semantic identifiers.
- It contained a nested fenced-code example that did not render reliably and left types 7–14 as placeholders.
- It did not explain that a model token is not a character or a regex chunk.
- It did not specify a no-loss coverage guarantee or offsets, nor did it warn that exposing local `file` inputs over HTTP permits reading server-side files.

## Licensing caveat

The original repository contains no LICENSE file. Jina's API and third-party Gists may have separate terms. New code is written independently; distribution rights should be clarified by the repository owner before release.
