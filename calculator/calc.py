import csv, glob, gzip, json
from datetime import date

STOCK = "data/cardmarket-stock-2026-11-17-es-Magic-v2.4.4.csv"
SALIDA = "data/salida_precios.csv"
DIAS = 14
PRECIO_MIN = 0.50
hoy = date.today()

def pid(r):
    return int("".join(c for c in r["idProduct"] if c.isdigit()))

def num(s):
    return float(s.replace(",", "."))

snapshots = []
for ruta in sorted(glob.glob("data/history/price_guide_*.json.gz")):
    dia = date.fromisoformat(ruta.split("price_guide_")[1][:10])
    if (hoy - dia).days <= DIAS:
        with gzip.open(ruta, "rt", encoding="utf-8") as f:
            snapshots.append({g["idProduct"]: g for g in json.load(f)})
print("Snapshots usados:", len(snapshots), "(ideal: 14)")

def referencia(idp, foil):
    suf = "-foil" if foil else ""
    vals = [s[idp].get("avg7" + suf) for s in snapshots if idp in s]
    vals = [v for v in vals if v]
    return max(vals) if vals else None

with open(STOCK, newline="", encoding="utf-8-sig") as f:
    lector = csv.DictReader(f, delimiter=";")
    campos = lector.fieldnames
    rows = list(lector)

suben = bajan = igual = sin_dato = 0
for r in rows:
    foil = r["Foil"].strip().upper() == "Y"
    ref = referencia(pid(r), foil)
    if ref is None:
        sin_dato += 1
        continue
    nuevo = max(round(ref, 2), PRECIO_MIN)
    actual = num(r["Price_EUR"])
    if nuevo > actual: suben += 1
    elif nuevo < actual: bajan += 1
    else: igual += 1
    r["Price_EUR"] = f"{nuevo:.2f}".replace(".", ",")

with open(SALIDA, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=campos, delimiter=";")
    w.writeheader()
    w.writerows(rows)

print(f"Suben: {suben} | Bajan: {bajan} | Igual: {igual} | Sin dato: {sin_dato}")
print("Escrito", SALIDA)
