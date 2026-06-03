"""Aplicație Flask – analiză aspecte din review-uri fitness trackers."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from flask import Flask, jsonify, render_template, request

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False
API_VERSION = "2.2"


@app.context_processor
def inject_template_globals():
    import aspect_lexicon

    return {
        "aspect_keywords": dict(aspect_lexicon.ASPECT_CATEGORIES),
    }


def _reload_analysis_modules():
    import importlib

    import aspect_extractor
    import aspect_lexicon

    importlib.reload(aspect_lexicon)
    importlib.reload(aspect_extractor)
    return aspect_extractor


def _identify_aspects(review_text: str, use_ml: bool = True):
    """Reîncarcă modulele de analiză ca modificările să fie active fără repornire manuală."""
    aspect_extractor = _reload_analysis_modules()
    return aspect_extractor.identify_aspects(review_text, use_ml=use_ml)


def _load_classifier():
    import aspect_extractor

    if os.environ.get("FLASK_DEBUG", "").lower() in ("1", "true"):
        aspect_extractor = _reload_analysis_modules()
    return aspect_extractor.load_classifier()


def get_aspect_categories() -> list[str]:
    """Reîncarcă lexiconul în development; în producție folosește modulul încărcat."""
    import importlib

    import aspect_lexicon

    if os.environ.get("FLASK_DEBUG", "").lower() in ("1", "true"):
        importlib.reload(aspect_lexicon)
    return list(aspect_lexicon.ASPECT_CATEGORIES.keys())


@app.route("/")
def index():
    model_ready = _load_classifier() is not None
    categories = get_aspect_categories()
    return render_template(
        "index.html",
        aspect_categories=categories,
        aspect_count=len(categories),
        model_ready=model_ready,
    )


@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "api_version": API_VERSION,
        "model_loaded": _load_classifier() is not None,
        "sentiment_api": True,
    })


@app.route("/api/analyze", methods=["POST"])
def analyze():
    payload = request.get_json(silent=True) or {}
    review_text = (payload.get("review") or request.form.get("review") or "").strip()

    if not review_text:
        return jsonify({"error": "Introduceți textul review-ului."}), 400

    result = _identify_aspects(review_text, use_ml=True)
    details = [
        {
            "aspect": aspect,
            "sursa": info["sursa"],
            "scor": round(info["scor"], 3),
            "sentiment": info.get("sentiment", "neutru"),
        }
        for aspect, info in result["detalii"].items()
    ]

    return jsonify(
        {
            "api_version": API_VERSION,
            "review": review_text,
            "ton_review": result.get("ton_review", "neutru"),
            "aspecte_pe_sentiment": result.get("aspecte_pe_sentiment", {}),
            "aspecte": result.get("aspecte", []),
            "aspecte_formatate": result.get("aspecte_formatate", ""),
            "detalii": details,
        }
    )


if __name__ == "__main__":
    on_railway = bool(os.environ.get("RAILWAY_ENVIRONMENT"))
    port = int(os.environ.get("PORT", 8080 if on_railway else 5050))
    host = "0.0.0.0" if on_railway or os.environ.get("BIND_ALL") else "127.0.0.1"
    debug = not on_railway and os.environ.get("FLASK_DEBUG", "1").lower() in ("1", "true")

    print(f"Server v{API_VERSION}: http://{host}:{port}")
    print("Verificare: http://127.0.0.1:{0}/health trebuie sa contina api_version".format(port))
    # Fara reloader: un singur proces, evita serverul „fantoma” cu cod vechi
    app.run(debug=debug, host=host, port=port, use_reloader=False)
