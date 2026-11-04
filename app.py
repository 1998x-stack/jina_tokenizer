"""WSGI entry point: ``flask --app app run`` or ``gunicorn app:app``."""

from jina_chunker.api import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=False)
