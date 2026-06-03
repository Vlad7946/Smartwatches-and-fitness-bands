"""
Parcurge fiecare review din dataset și adaugă coloane cu aspecte clar identificate.
Rulează: python scripts/label_reviews.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from aspect_extractor import extract_aspects_rule_based, format_aspects, train_classifier
from aspect_lexicon import ASPECT_OUTPUT_COLUMNS, REVIEW_COLUMNS

INPUT_FILE = ROOT / "Fitness_trackers_1000_records_reviews_split.xlsx"
OUTPUT_FILE = ROOT / "Fitness_trackers_1000_records_reviews_split.xlsx"
BACKUP_FILE = ROOT / "data" / "Fitness_trackers_reviews_cu_aspecte.xlsx"


def label_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    mapping = {
        "Reviewuri Pozitive": "Aspecte_Pozitive",
        "Reviewuri Negative": "Aspecte_Negative",
        "Reviewuri Neutre": "Aspecte_Neutre",
        "Reviewuri Mixte": "Aspecte_Mixte",
    }

    for review_col, aspect_col in mapping.items():
        df[aspect_col] = df[review_col].apply(
            lambda text: format_aspects(extract_aspects_rule_based(str(text)))
        )

    def merge_row_aspects(row) -> str:
        all_aspects: list[str] = []
        for col in mapping.values():
            raw = row[col]
            if raw and raw != "Niciun aspect identificat":
                all_aspects.extend([a.strip() for a in str(raw).split(";")])
        unique = sorted(set(all_aspects))
        return format_aspects(unique)

    df["Aspecte_Identificate"] = df.apply(merge_row_aspects, axis=1)
    return df


def main() -> None:
    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Lipsește fișierul: {INPUT_FILE}")

    df = pd.read_excel(INPUT_FILE)
    df = label_dataframe(df)

    BACKUP_FILE.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(OUTPUT_FILE, index=False)
    df.to_excel(BACKUP_FILE, index=False)

    print(f"Procesate {len(df)} înregistrări.")
    print(f"Coloane noi: {', '.join(ASPECT_OUTPUT_COLUMNS)}")
    print(f"Actualizat: {OUTPUT_FILE}")
    print(f"Copie backup: {BACKUP_FILE}")

    print("\nAntrenare model ML pentru instanțe noi...")
    train_classifier(df)
    print("Model salvat în models/aspect_classifier.joblib")


if __name__ == "__main__":
    main()
