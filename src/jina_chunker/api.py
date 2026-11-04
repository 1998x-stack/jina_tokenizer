"""Optional Flask HTTP interface. It never reads client-provided server paths."""

from __future__ import annotations

from .compat import TextChunker


def create_app(*, max_text_chars: int = 200_000):
    from flask import Flask, jsonify, request
    from werkzeug.exceptions import BadRequest, RequestEntityTooLarge

    if isinstance(max_text_chars, bool) or not isinstance(max_text_chars, int) or max_text_chars < 1:
        raise ValueError("max_text_chars must be a positive integer")
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = max_text_chars * 4 + 8192
    processor = TextChunker()

    @app.get("/healthz")
    def health():
        return jsonify({"status": "ok"})

    @app.post("/tokenizer")
    def tokenize():
        if not request.is_json:
            return jsonify({"error": "Content-Type must be application/json"}), 415
        try:
            data = request.get_json()
        except BadRequest:
            return jsonify({"error": "Invalid JSON"}), 400
        if not isinstance(data, dict):
            return jsonify({"error": "Expected a JSON object"}), 400
        input_type = data.get("input_type", "string")
        if input_type != "string":
            return jsonify({"error": "HTTP input_type must be 'string'; file paths are not accepted"}), 400
        value = data.get("text", data.get("input_data"))
        if not isinstance(value, str):
            return jsonify({"error": "text or input_data must be a string"}), 400
        if len(value) > max_text_chars:
            return jsonify({"error": "Input exceeds maximum length"}), 413
        return jsonify(processor.process_str(value))

    @app.errorhandler(RequestEntityTooLarge)
    def too_large(_error):
        return jsonify({"error": "Request body too large"}), 413

    return app
