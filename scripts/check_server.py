import json
import sys
import urllib.request

BASE = "http://127.0.0.1:5050"
health = json.loads(urllib.request.urlopen(f"{BASE}/health").read().decode())
print("health:", health)

ok = (
    health.get("api_version") == "2.4"
    and health.get("aspect_count") == 16
    and health.get("lexicon_version") == "2026.06.03"
)
if not ok:
    print("FAIL: server vechi sau mai multe procese pe 5050. Opriți toate python app.py și reporniți.")
    sys.exit(1)

html = urllib.request.urlopen(f"{BASE}/").read().decode("utf-8")
print("taxonomy-chip count:", html.count("taxonomy-chip"))
for name in ["Livrare și logistică", "Calitate construcție și materiale"]:
    print(name, "->", name in html)
print("OK")
