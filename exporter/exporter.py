import csv, glob, gzip, json, os, time
from prometheus_client import Gauge, start_http_server

DATA = "data"
TOP_N = 15
INTERVALO = 300
PUERTO = 8000

cartas = Gauge("cardmarket_cartas", "Cartas según el cambio de precio calculado", ["direccion"])
antiguedad = Gauge("cardmarket_foto_antiguedad_segundos", "Segundos desde la última foto del price guide")
fotos = Gauge("cardmarket_fotos_total", "Número de fotos del price guide guardadas")
mercado = Gauge("cardmarket_precio_mercado_eur", "Precio de mercado (avg7) de las cartas más valiosas del stock", ["carta", "id", "foil"])

_cache = {"ruta": None, "datos": {}}

def pid(valor):
    return int("".join(c for c in valor if c.isdigit()))

def num(valor):
    return float(valor.replace(",", "."))

def leer_csv(ruta):
    with open(ruta, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f, delimiter=";"))

def cargar_ultima(ruta):
    if _cache["ruta"] != ruta:
        with gzip.open(ruta, "rt", encoding="utf-8") as f:
            _cache["datos"] = {g["idProduct"]: g for g in json.load(f)}
        _cache["ruta"] = ruta
    return _cache["datos"]

def actualizar():
    ficheros = sorted(glob.glob(f"{DATA}/history/price_guide_*.json.gz"))
    fotos.set(len(ficheros))
    if not ficheros:
        return
    ultima = ficheros[-1]
    antiguedad.set(time.time() - os.path.getmtime(ultima))
    guia = cargar_ultima(ultima)

    salida = f"{DATA}/salida_precios.csv"
    if os.path.exists(salida):
        cuenta = {"suben": 0, "bajan": 0, "igual": 0}
        for r in leer_csv(salida):
            nuevo, antes = num(r["Price_EUR"]), num(r["_OriginalPrice_EUR"])
            clave = "suben" if nuevo > antes else "bajan" if nuevo < antes else "igual"
            cuenta[clave] += 1
        for k, v in cuenta.items():
            cartas.labels(k).set(v)

    stocks = sorted(glob.glob(f"{DATA}/cardmarket-stock-*.csv"), key=os.path.getmtime)
    if stocks:
        vistas = {}
        for r in leer_csv(stocks[-1]):
            idp = pid(r["idProduct"])
            foil = r["Foil"].strip().upper() == "Y"
            precio = guia.get(idp, {}).get("avg7-foil" if foil else "avg7")
            if precio:
                vistas[(idp, foil)] = (precio, r["Name"])
        top = sorted(vistas.items(), key=lambda x: x[1][0], reverse=True)[:TOP_N]
        mercado.clear()
        for (idp, foil), (precio, nombre) in top:
            mercado.labels(nombre, str(idp), "si" if foil else "no").set(precio)

if __name__ == "__main__":
    start_http_server(PUERTO)
    print(f"Exporter escuchando en el puerto {PUERTO}", flush=True)
    while True:
        try:
            actualizar()
        except Exception as e:
            print("Error al actualizar métricas:", e, flush=True)
        time.sleep(INTERVALO)
