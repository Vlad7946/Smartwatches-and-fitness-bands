"""Extragere aspecte: reguli pe lexicon + predicție ML pentru texte noi."""

from __future__ import annotations

import re
from pathlib import Path

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.multiclass import OneVsRestClassifier
from sklearn.preprocessing import MultiLabelBinarizer

from aspect_lexicon import (
    ASPECT_CATEGORIES,
    ASPECT_TONE_TO_BUCKET,
    MIXED_MARKERS,
    NEGATION_PHRASES,
    SENTIMENT_BUCKETS,
    SENTIMENT_NEGATIVE,
    SENTIMENT_NEUTRAL,
    SENTIMENT_POSITIVE,
)

MODEL_PATH = Path(__file__).resolve().parent.parent / "models" / "aspect_classifier.joblib"
BRAND_PREFIX_RE = re.compile(r"^[^:]+:\s*", re.IGNORECASE)
CONTEXT_WINDOW = 90
_SHORT_KEYWORD_MAX_LEN = 4
_WORD_CHAR = r"a-zăâîșț037"


def normalize_review_text(text: str) -> str:
    if not text or (isinstance(text, float)):
        return ""
    cleaned = str(text).strip()
    cleaned = BRAND_PREFIX_RE.sub("", cleaned)
    return cleaned.lower()


def _keyword_in_text(keyword: str, normalized: str) -> bool:
    """Evită potriviri false (ex. „dus” în „produsul”)."""
    kw = keyword.strip().lower()
    if not kw:
        return False
    if len(kw) <= _SHORT_KEYWORD_MAX_LEN:
        pattern = rf"(?<![{_WORD_CHAR}]){re.escape(kw)}(?![{_WORD_CHAR}])"
        return re.search(pattern, normalized) is not None
    return kw in normalized


def extract_aspects_rule_based(text: str) -> list[str]:
    """Identifică aspectele din text pe baza lexiconului."""
    normalized = normalize_review_text(text)
    if not normalized:
        return []

    found: list[str] = []
    for aspect, keywords in ASPECT_CATEGORIES.items():
        if any(_keyword_in_text(keyword, normalized) for keyword in keywords):
            found.append(aspect)
    return found


def format_aspects(aspects: list[str]) -> str:
    return "; ".join(aspects) if aspects else "Niciun aspect identificat"


def _count_lexicon_hits(text: str, terms: list[str]) -> int:
    return sum(1 for term in terms if _keyword_in_text(term, text))


def _sentiment_scores(text: str) -> tuple[int, int]:
    """Numără indicii pozitivi/negativi, cu tratament pentru negație (ex. „nu par premium”)."""
    pos = _count_lexicon_hits(text, SENTIMENT_POSITIVE)
    neg = _count_lexicon_hits(text, SENTIMENT_NEGATIVE)

    if any(phrase in text for phrase in NEGATION_PHRASES) and pos > 0:
        neg = max(neg, pos)
        pos = 0

    return pos, neg


def _split_review_clauses(text: str) -> list[str]:
    """Împarte review-ul în propoziții/clauze (punctuație + marcatori de contrast)."""
    normalized = normalize_review_text(text)
    if not normalized:
        return []

    markers = [m.strip() for m in MIXED_MARKERS if m.strip()]
    pattern = "|".join(re.escape(marker) for marker in markers)
    parts = re.split(pattern, normalized) if pattern else [normalized]

    clauses: list[str] = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        for sentence in re.split(r"[.!?]+\s*", part):
            sentence = re.sub(r"^[,;\s]+", "", sentence.strip())
            if sentence:
                clauses.append(sentence)

    if not clauses:
        return [normalized]

    refined: list[str] = []
    for clause in clauses:
        if "," in clause:
            for part in clause.split(","):
                part = re.sub(r"^[,;\s]+", "", part.strip())
                if part:
                    refined.append(part)
        else:
            refined.append(clause)

    with_conjunction: list[str] = []
    for part in refined:
        if " și " in part:
            for segment in part.split(" și "):
                segment = segment.strip()
                if segment:
                    with_conjunction.append(segment)
        else:
            with_conjunction.append(part)

    return with_conjunction if with_conjunction else clauses


def _segment_tones(text: str) -> set[str]:
    """Tonurile detectate pe fiecare segment semantic."""
    tones: set[str] = set()
    for clause in _split_review_clauses(text):
        tone = _clause_tone(clause)
        if tone != "neutru":
            tones.add(tone)
    return tones


def classify_review_tone(text: str) -> str:
    """Clasifică tonul general al review-ului: pozitiv, negativ, neutru sau mixt."""
    normalized = normalize_review_text(text)
    if not normalized:
        return "neutru"

    segment_tones = _segment_tones(text)
    if "pozitiv" in segment_tones and "negativ" in segment_tones:
        return "mixt"
    if "mixt" in segment_tones and len(segment_tones) > 1:
        return "mixt"
    if len(segment_tones) > 1:
        return "mixt"

    pos = _count_lexicon_hits(normalized, SENTIMENT_POSITIVE)
    neg = _count_lexicon_hits(normalized, SENTIMENT_NEGATIVE)
    neu = _count_lexicon_hits(normalized, SENTIMENT_NEUTRAL)
    has_mixed_marker = any(marker in normalized for marker in MIXED_MARKERS)

    if has_mixed_marker and (pos > 0 or neg > 0):
        return "mixt"
    if pos > 0 and neg > 0:
        return "mixt"
    if pos > neg:
        return "pozitiv"
    if neg > pos:
        return "negativ"
    if neu > 0 or (pos == 0 and neg == 0):
        return "neutru"
    return "neutru"


def _clause_tone(clause: str) -> str:
    pos, neg = _sentiment_scores(clause)
    neu = _count_lexicon_hits(clause, SENTIMENT_NEUTRAL)

    if pos > 0 and neg > 0:
        return "mixt"
    if pos > neg:
        return "pozitiv"
    if neg > pos:
        return "negativ"
    if neu > 0:
        return "neutru"
    return "neutru"


def _aspect_context_fragment(text: str, aspect: str) -> str:
    """Context local în jurul cuvântului-cheie al aspectului (nu întreaga propoziție lungă)."""
    normalized = normalize_review_text(text)
    keywords = ASPECT_CATEGORIES.get(aspect, [])
    best_pos = -1
    best_len = 0
    for keyword in keywords:
        if not _keyword_in_text(keyword, normalized):
            continue
        pos = normalized.find(keyword) if len(keyword) > _SHORT_KEYWORD_MAX_LEN else None
        if pos is None:
            match = re.search(
                rf"(?<![{_WORD_CHAR}]){re.escape(keyword.strip())}(?![{_WORD_CHAR}])",
                normalized,
            )
            pos = match.start() if match else -1
        if pos != -1 and (best_pos == -1 or pos < best_pos):
            best_pos = pos
            best_len = len(keyword.strip())

    if best_pos != -1:
        prefix = normalized[:best_pos]
        start = max(0, best_pos - CONTEXT_WINDOW)
        dar_idx = prefix.rfind("dar ")
        if dar_idx != -1:
            start = max(start, dar_idx + 4)
        last_comma = prefix.rfind(",")
        if last_comma != -1:
            start = max(start, last_comma + 1)

        end = min(len(normalized), best_pos + best_len + CONTEXT_WINDOW)
        chunk = normalized[start:end]
        rel = best_pos - start
        comma_right = chunk.find(",", rel)
        if comma_right != -1:
            chunk = chunk[:comma_right]
        return chunk.strip() or normalized[start:end]

    clauses = _split_review_clauses(text)
    matching = [c for c in clauses if _aspect_in_clause(c, aspect)]
    return matching[0] if matching else normalized


def _aspect_in_clause(clause: str, aspect: str) -> bool:
    keywords = ASPECT_CATEGORIES.get(aspect, [])
    return any(_keyword_in_text(keyword, clause) for keyword in keywords)


def _resolve_aspect_tone(raw_tone: str, context: str) -> str:
    """Transformă ton ambiguu într-unul clar: pozitiv, negativ sau neutru."""
    if raw_tone in ASPECT_TONE_TO_BUCKET:
        return raw_tone

    pos, neg = _sentiment_scores(context)
    if pos > neg:
        return "pozitiv"
    if neg > pos:
        return "negativ"
    return "neutru"


def classify_aspect_tone(text: str, aspect: str) -> str:
    """Tonul mențiunii unui aspect — întotdeauna pozitiv, negativ sau neutru."""
    clauses = _split_review_clauses(text)
    matching = sorted(
        [c for c in clauses if _aspect_in_clause(c, aspect)],
        key=len,
    )

    for clause in matching:
        pos, neg = _sentiment_scores(clause)
        if pos == neg:
            continue
        return _resolve_aspect_tone(_clause_tone(clause), clause)

    fragment = _aspect_context_fragment(text, aspect)
    return _resolve_aspect_tone(_clause_tone(fragment), fragment)


def group_aspects_by_sentiment(
    text: str, combined: dict[str, dict]
) -> tuple[str, dict[str, list[str]]]:
    """
    Grupează aspectele în pozitive / negative / neutre.
    Tonul „mixt” se folosește doar la nivel de review, nu per aspect.
    """
    review_tone = classify_review_tone(text)
    segments = _split_review_clauses(text)
    use_per_aspect = review_tone == "mixt" or len(segments) >= 2
    groups: dict[str, list[str]] = {bucket: [] for bucket in SENTIMENT_BUCKETS}

    for aspect in combined:
        if use_per_aspect or review_tone == "mixt":
            aspect_tone = classify_aspect_tone(text, aspect)
        elif review_tone in ASPECT_TONE_TO_BUCKET:
            aspect_tone = review_tone
        else:
            aspect_tone = classify_aspect_tone(text, aspect)

        if aspect_tone not in ASPECT_TONE_TO_BUCKET:
            aspect_tone = _resolve_aspect_tone(
                aspect_tone, _aspect_context_fragment(text, aspect)
            )
        bucket = ASPECT_TONE_TO_BUCKET[aspect_tone]
        combined[aspect]["sentiment"] = aspect_tone
        groups[bucket].append(aspect)

    groups["mixte"] = []
    for bucket in SENTIMENT_BUCKETS:
        groups[bucket].sort()

    return review_tone, groups


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

    normalized = normalize_review_text(text)
    for aspect, score in ml_hits:
        if not _aspect_in_clause(normalized, aspect):
            continue
        if aspect in combined:
            combined[aspect]["sursa"] = "lexicon+ml"
            combined[aspect]["scor"] = max(combined[aspect]["scor"], score)
        else:
            combined[aspect] = {"sursa": "ml", "scor": score}

    aspect_list = list(combined.keys())
    review_tone, aspecte_pe_sentiment = group_aspects_by_sentiment(text, combined)

    return {
        "aspecte": aspect_list,
        "aspecte_formatate": format_aspects(aspect_list),
        "ton_review": review_tone,
        "aspecte_pe_sentiment": aspecte_pe_sentiment,
        "detalii": combined,
    }
