"""Regression tests emphasizing lossless content, offsets and bounded chunks."""

import random
import tempfile
import unittest
from pathlib import Path

from jina_chunker import TextChunker
from jina_chunker.compat import TextChunker as LegacyChunker


SAMPLE = """# 标题 Title\n\n中文第一句。English second sentence! 😄\n- [x] 任务一\n- 任务二\n\n```python\nprint('hello')\n```\n\n| A | B |\n| --- | --- |\n| 1 | 2 |\n\n$$\nx^2+y^2=z^2\n$$\n"""


class CoreTest(unittest.TestCase):
    def assert_lossless(self, text, cap):
        chunks = TextChunker(cap).process_text(text)
        self.assertEqual("".join(c.content for c in chunks), text)
        self.assertTrue(all(0 < len(c.content) <= cap for c in chunks))
        last = 0
        for chunk in chunks:
            self.assertEqual(chunk.start_pos, last)
            self.assertEqual(chunk.end_pos, last + len(chunk.content))
            self.assertEqual(text[chunk.start_pos:chunk.end_pos], chunk.content)
            last = chunk.end_pos
        self.assertEqual(last, len(text))
        return chunks

    def test_unicode_and_structure(self):
        chunks = self.assert_lossless(SAMPLE, 1000)
        self.assertIn("heading", [c.chunk_type for c in chunks])
        self.assertIn("list", [c.chunk_type for c in chunks])
        self.assertIn("code", [c.chunk_type for c in chunks])
        self.assertIn("table", [c.chunk_type for c in chunks])
        self.assertIn("math", [c.chunk_type for c in chunks])
        self.assertTrue(any("print('hello')" in c.content for c in chunks if c.chunk_type == "code"))

    def test_fences_must_match_and_unclosed_is_preserved(self):
        for source in ["````py\nx\n```\ny\n````\n", "~~~\na\n~~~\n", "```\nnever closed"]:
            chunks = self.assert_lossless(source, 1000)
            self.assertEqual([c.chunk_type for c in chunks], ["code"])

    def test_setext_and_thematic_break(self):
        text = "Title\n---\n\n***\n"
        kinds = [c.chunk_type for c in self.assert_lossless(text, 1000)]
        self.assertIn("heading", kinds)
        self.assertIn("thematic_break", kinds)

    def test_hard_caps_and_complex_unicode(self):
        for limit in (1, 2, 7, 35, 100, 1000):
            self.assert_lossless(SAMPLE * 3, limit)
            self.assert_lossless("汉" * 513 + "a" * 513, limit)

    def test_crlf_newlines_and_whitespace(self):
        self.assert_lossless("  \r\n# H\r\n\r\n\tcode\r\n\u2028foo\n", 12)

    def test_empty(self):
        self.assertEqual(TextChunker().process_text(""), [])

    def test_random_losslessness(self):
        rng = random.Random(1337)
        alphabet = "ab中🙂。!?\n\r |`~-[]()  \t\u0301"
        for _ in range(100):
            text = "".join(rng.choice(alphabet) for _ in range(rng.randrange(200)))
            self.assert_lossless(text, rng.randint(1, 60))

    def test_errors(self):
        for size in (0, -1, 1_000_001, 1.5, True):
            with self.assertRaises(ValueError):
                TextChunker(size)
        with self.assertRaises(TypeError):
            TextChunker().process_text(None)

    def test_local_file_and_legacy_json(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "unicode.txt"
            path.write_text("你好。Hello!", encoding="utf-8")
            self.assertEqual("".join(c.content for c in TextChunker().process_file(path)), "你好。Hello!")
            legacy = LegacyChunker().process("你好。Hello!", "string")
            self.assertTrue(legacy["info"]["coverage_complete"])
            self.assertEqual(legacy["info"]["chunk_count"], len(legacy["chunks"]))
            self.assertTrue(LegacyChunker().process(str(path), "file")["chunks"])
            self.assertIn("error", LegacyChunker().process(str(path) + ".absent", "file")["info"])


if __name__ == "__main__":
    unittest.main()
