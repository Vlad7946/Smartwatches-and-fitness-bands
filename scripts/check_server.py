import urllib.request

html = urllib.request.urlopen("http://127.0.0.1:5050/").read().decode("utf-8")
print("taxonomy-chip count:", html.count("taxonomy-chip"))
print("14 categorii:", "14 categorii" in html)
for name in [
    "Rezistență și impermeabilitate",
    "Compatibilitate dispozitive",
    "GPS și localizare",
    "Ușurință în utilizare",
]:
    print(name, "->", name in html)
