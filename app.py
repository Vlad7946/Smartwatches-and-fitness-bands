"""Aplicație Flask – analiză aspecte din review-uri fitness trackers."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from flask import Flask, jsonify, render_template, request

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from aspect_extractor import identify_aspects, load_classifier

app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False


def get_aspect_categories() -> list[str]:
    """Reîncarcă lexiconul în development; în producție folosește modulul încărcat."""
    import importlib

    import aspect_lexicon

    if os.environ.get("FLASK_DEBUG", "").lower() in ("1", "true"):
        importlib.reload(aspect_lexicon)
    return list(aspect_lexicon.ASPECT_CATEGORIES.keys())


@app.route("/")
def index():
    model_ready = load_classifier() is not None
    categories = get_aspect_categories()
    return render_template(
        "index.html",
        aspect_categories=categories,
        aspect_count=len(categories),
        model_ready=model_ready,
    )


@app.route("/health")
def health():
    return jsonify({"status": "ok", "model_loaded": load_classifier() is not None})


@app.route("/api/analyze", methods=["POST"])
def analyze():
    payload = request.get_json(silent=True) or {}
    review_text = (payload.get("review") or request.form.get("review") or "").strip()

    if not review_text:
        return jsonify({"error": "Introduceți textul review-ului."}), 400

    result = identify_aspects(review_text, use_ml=True)
    details = [
        {
            "aspect": aspect,
            "sursa": info["sursa"],
            "scor": round(info["scor"], 3),
        }
        for aspect, info in result["detalii"].items()
    ]

    return jsonify(
        {
            "review": review_text,
            "aspecte": result["aspecte"],
            "aspecte_formatate": result["aspecte_formatate"],
            "detalii": details,
        }
    )


if __name__ == "__main__":
    on_railway = bool(os.environ.get("RAILWAY_ENVIRONMENT"))
    port = int(os.environ.get("PORT", 8080 if on_railway else 5050))
    host = "0.0.0.0" if on_railway or os.environ.get("BIND_ALL") else "127.0.0.1"
    debug = not on_railway and os.environ.get("FLASK_DEBUG", "1").lower() in ("1", "true")

    print(f"Server: http://{host}:{port}")
    app.run(debug=debug, host=host, port=port, use_reloader=False)
