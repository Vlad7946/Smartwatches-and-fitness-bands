# Aspect Analyzer — Fitness Trackers

Aplicație web Flask pentru analiza review-urilor de fitness trackers în limba română: detectare aspecte (lexicon + ML) și clasificare pe ton (pozitiv / negativ / neutru / mixt).

## Rulare locală

```powershell
pip install -r requirements.txt
python scripts/label_reviews.py   # opțional — antrenează modelul ML
python app.py
```

Deschideți http://127.0.0.1:5050/ — verificare API: http://127.0.0.1:5050/health

## Deploy (GitHub → Railway)

Codul este pe GitHub; producția folosește **Railway** (vezi `Procfile`, `railway.toml`).

1. [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub repo**
2. Selectați `Vlad7946/Smartwatches-and-fitness-bands`
3. Railway detectează Python și pornește: `gunicorn app:app --bind 0.0.0.0:$PORT`
4. **Settings** → **Networking** → **Generate Domain** (URL public)
5. La fiecare `git push` pe `main`, Railway redeployează automat

Health check: `https://<domeniul-tau>.up.railway.app/health`

## Repository

https://github.com/Vlad7946/Smartwatches-and-fitness-bands

## Structură

| Cale | Rol |
|------|-----|
| `app.py` | Server Flask, API `/api/analyze` |
| `src/aspect_lexicon.py` | Categorii aspecte + lexicoane sentiment |
| `src/aspect_extractor.py` | Extragere + clasificare |
| `models/aspect_classifier.joblib` | Model ML (după `label_reviews.py`) |
| `static/`, `templates/` | Interfață web |
