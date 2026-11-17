import gzip, json, os, urllib.request
from datetime import date

URL = "https://downloads.s3.cardmarket.com/productCatalog/priceGuide/price_guide_1.json"
CAMPOS = ["idProduct", "low", "low-foil", "avg1", "avg1-foil",
          "avg7", "avg7-foil", "avg30", "avg30-foil", "trend", "trend-foil"]

os.makedirs("data/history", exist_ok=True)
with urllib.request.urlopen(URL) as r:
    guia = json.load(r)["priceGuides"]

compacto = [{c: g.get(c) for c in CAMPOS} for g in guia]
ruta = f"data/history/price_guide_{date.today()}.json.gz"
with gzip.open(ruta, "wt", encoding="utf-8") as f:
    json.dump(compacto, f)

print(f"Guardado {ruta} con {len(compacto)} productos")
