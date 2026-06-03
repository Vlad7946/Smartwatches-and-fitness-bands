"""Extragere aspecte: reguli pe lexicon + predicție ML pentru texte noi."""

from __future__ import annotations

import re
from pathlib import Path

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.multiclass import OneVsRestClassifier
from sklearn.preprocessing import MultiLabelBinarizer

from aspect_lexicon import ASPECT_CATEGORIES

MODEL_PATH = Path(__file__).resolve().parent.parent / "models" / "aspect_classifier.joblib"
BRAND_PREFIX_RE = re.compile(r"^[^:]+:\s*", re.IGNORECASE)


def normalize_review_text(text: str) -> str:
    if not text or (isinstance(text, float)):
        return ""
    cleaned = str(text).strip()
    cleaned = BRAND_PREFIX_RE.sub("", cleaned)
    return cleaned.lower()


def extract_aspects_rule_based(text: str) -> list[str]:
    """Identifică aspectele din text pe baza lexiconului."""
    normalized = normalize_review_text(text)
    if not normalized:
        return []

    found: list[str] = []
    for aspect, keywords in ASPECT_CATEGORIES.items():
        if any(keyword in normalized for keyword in keywords):
            found.append(aspect)
    return found


def format_aspects(aspects: list[str]) -> str:
    return "; ".join(aspects) if aspects else "Niciun aspect identificat"


def _prepare_training_samples(df) -> tuple[list[str], list[list[str]]]:
    from aspect_lexicon import REVIEW_COLUMNS

    texts: list[str] = []
    labels: list[list[str]] = []

    for col in REVIEW_COLUMNS:
        for raw in df[col].astype(str):
            text = normalize_review_text(raw)
            if not text:
                continue
            texts.append(text)
            labels.append(extract_aspects_rule_based(raw))

    return texts, labels


def train_classifier(df) -> dict:
    """Antrenează clasificator multi-label pe etichete generate cu reguli."""
    texts, label_lists = _prepare_training_samples(df)

    mlb = MultiLabelBinarizer()
    y = mlb.fit_transform(label_lists)

    vectorizer = TfidfVectorizer(
        ngram_range=(1, 2),
        min_df=2,
        max_features=8000,
        sublinear_tf=True,
    )
    X = vectorizer.fit_transform(texts)

    classifier = OneVsRestClassifier(
        LogisticRegression(max_iter=1000, class_weight="balanced")
    )
    classifier.fit(X, y)

    bundle = {
        "vectorizer": vectorizer,
        "classifier": classifier,
        "mlb": mlb,
        "aspect_names": list(mlb.classes_),
    }
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, MODEL_PATH)
    return bundle


def load_classifier():
    if not MODEL_PATH.exists():
        return None
    return joblib.load(MODEL_PATH)


def predict_aspects_ml(text: str, threshold: float = 0.35) -> list[tuple[str, float]]:
    bundle = load_classifier()
    if bundle is None:
        return []

    normalized = normalize_review_text(text)
    if not normalized:
        return []

    X = bundle["vectorizer"].transform([normalized])
    probas = bundle["classifier"].predict_proba(X)[0]
    aspects = bundle["aspect_names"]

    results: list[tuple[str, float]] = []
    for aspect, score in zip(aspects, probas):
        if score >= threshold:
            results.append((aspect, float(score)))
    results.sort(key=lambda x: x[1], reverse=True)
    return results


def identify_aspects(text: str, use_ml: bool = True) -> dict:
    """
    Identifică aspectele pentru o instanță nouă.
    Combină regulile (bază) cu modelul antrenat pe date existente.
    """
    rule_aspects = extract_aspects_rule_based(text)
    ml_hits = predict_aspects_ml(text) if use_ml else []

    combined: dict[str, dict] = {}
    for aspect in rule_aspects:
        combined[aspect] = {"sursa": "lexicon", "scor": 1.0}

    for aspect, score in ml_hits:
        if aspect in combined:
            combined[aspect]["sursa"] = "lexicon+ml"
            combined[aspect]["scor"] = max(combined[aspect]["scor"], score)
        else:
            combined[aspect] = {"sursa": "ml", "scor": score}

    aspect_list = list(combined.keys())
    return {
        "aspecte": aspect_list,
        "aspecte_formatate": format_aspects(aspect_list),
        "detalii": combined,
    }
