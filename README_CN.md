# jina_tokenizer 中文快速入门

项目已经由超长正则实验脚本重构为**无损、结构感知的文本分块器**。主要说明、完整 API 契约和限制见 [README](README.md)。

```bash
python -m pip install -e .
python jina_tokenizer.py doc/Grimm.txt --json
```

```python
from jina_chunker import TextChunker
text = "# 标题\n\n这是中文。This is English!"
chunks = TextChunker(max_chunk_chars=100).process_text(text)
assert "".join(chunk.content for chunk in chunks) == text
```

- 输入原样保留：空格、换行、中文、Emoji 不会被静默删除。
- `start_pos` 和 `end_pos` 是原字符串的 Python 字符偏移，非 UTF-8 字节偏移。
- 支持标题、代码围栏、列表、表格、引文、展示数学公式等常见结构；不声称完全符合 CommonMark。
- `max_chunk_chars` 是**字符限制**，不是大模型真实 token 数。
- HTTP 仅接收字符串，不允许请求携带服务器文件路径；本地 CLI 仍支持文件输入。
- 旧 `tokenizer.py` 返回 JSON 兼容数据；新接口推荐 `from jina_chunker import TextChunker`。

测试：`PYTHONPATH=src:. python -m unittest discover -s tests -v`。
