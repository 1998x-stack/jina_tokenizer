"""HTTP safety and backwards-compatible request/response tests."""

import unittest

try:
    from flask import Flask
except ImportError:
    Flask = None

from jina_chunker.api import create_app


@unittest.skipIf(Flask is None, "install the optional Flask API extra")
class ApiTest(unittest.TestCase):
    def setUp(self):
        self.client = create_app(max_text_chars=20).test_client()

    def test_legacy_payload(self):
        response = self.client.post("/tokenizer", json={"input_data": "你好！", "input_type": "string"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json["info"]["coverage_complete"])

    def test_modern_payload(self):
        response = self.client.post("/tokenizer", json={"text": "Hello"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["chunks"][0]["content"], "Hello")

    def test_server_path_rejected(self):
        response = self.client.post("/tokenizer", json={"input_data": "/etc/passwd", "input_type": "file"})
        self.assertEqual(response.status_code, 400)
        self.assertNotIn("root:", response.get_data(as_text=True))

    def test_invalid(self):
        self.assertEqual(self.client.post("/tokenizer", data="x").status_code, 415)
        self.assertEqual(self.client.post("/tokenizer", data="{", content_type="application/json").status_code, 400)
        self.assertEqual(self.client.post("/tokenizer", json=[1]).status_code, 400)
        self.assertEqual(self.client.post("/tokenizer", json={"text": 3}).status_code, 400)
        self.assertEqual(self.client.post("/tokenizer", json={"text": "x" * 21}).status_code, 413)
        self.assertEqual(self.client.get("/healthz").json, {"status": "ok"})


if __name__ == "__main__":
    unittest.main()
