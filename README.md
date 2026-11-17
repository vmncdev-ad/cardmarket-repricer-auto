# Cardmarket Repricer

Pipeline para revisar los precios de cartas de Magic en Cardmarket a partir de los datos públicos del mercado, con histórico propio y métricas y dashboards.

> **Estado:** en desarrollo. Ver [Roadmap](#roadmap).

## Qué problema resuelve

Mantener precios competitivos a mano en cientos de cartas es lento. Este proyecto calcula un precio de referencia para cada carta de mi stock y genera un CSV listo para reimportar, sin depender de la API de Cardmarket.

## Decisión de diseño importante: sin API de Cardmarket

El plan inicial era usar la API oficial (OAuth 1.0). Al investigarlo descubrí que **actualmente no se aceptan solicitudes de acceso y que la API está restringida a vendedores profesionales**, así que rediseñé el flujo:

| Necesidad | Solución |
|---|---|
| Datos de mercado | Price guide público de Cardmarket (fichero JSON estático, sin credenciales) |
| Mi inventario | Exportación CSV del stock con una extensión de navegador |
| Aplicar precios nuevos | CSV generado por el pipeline, importado en bloque |

## Lógica de precios

La estrategia ha cambiado respecto a la idea inicial (mínimo del mercado + margen):

- **Precio de referencia:** el máximo de la media a 7 días (`avg7`) durante los últimos 14 días, usando la columna foil o no foil según la carta. Se usa `avg7` y no `avg1` porque `avg1` es la media de un solo día y una venta aislada dispara el valor.
- **Histórico propio:** el price guide solo trae el momento actual, así que se guarda una foto diaria comprimida y el máximo se calcula sobre esas fotos. Mientras no haya 14 días acumulados, el resultado es una aproximación.
- **Precio mínimo:** 0,50 €.
- **Techo opcional (pendiente):** limitar el precio a un 5 % por debajo de la oferta más cara de otros vendedores de la misma carta. Ese dato no está en el price guide, así que de momento no se aplica.

Limitaciones conocidas: el price guide no distingue el estado de la carta, y precios cercanos al máximo reciente pueden dejar cartas sin vender si hay copias más baratas.

## Formato del CSV de stock

Detalles que hay que respetar al procesarlo y al generar la salida:

- Separador `;` y codificación UTF-8 con BOM.
- Los identificadores vienen como `="20895"` (formato texto estilo Excel). Para cruzar con el guide se extraen los dígitos, pero en el CSV de salida se conserva el valor original.
- `Foil` es `Y` / `N`.
- Los precios usan coma decimal (`0,50`).
- `_OriginalPrice_EUR` y `_OriginalComments` no se modifican: la extensión las usa para detectar qué ha cambiado al reimportar.

## Scripts

| Script | Qué hace |
|---|---|
| `calculator/snapshot.py` | Descarga el price guide y guarda una foto diaria comprimida en `data/history/` |
| `calculator/calc.py` | Cruza el stock con las fotos, calcula los precios nuevos y escribe `data/salida_precios.csv` |

La ruta del CSV de stock está al principio de `calc.py` y hay que ajustarla al nombre del archivo exportado.

La foto diaria se programa con `cron`.

## Estructura del proyecto

```
cardmarket-repricer/
├── calculator/
│   ├── snapshot.py
│   └── calc.py
├── data/              # stock, histórico y salida (ignorado por git)
├── .gitignore
└── README.md
```

## Uso

```bash
git clone https://github.com/vmncdev-ad/cardmarket-repricer-auto.git
cd cardmarket-repricer-auto
mkdir -p data
/calc.py
python3 calculator/snapshot.py
python3 calculator/calc.py
```

## Roadmap

- [x] Diseño de arquitectura
- [x] Investigación de acceso a datos (API vs. ficheros públicos)
- [x] Exportar stock a CSV
- [x] Descarga del price guide y foto diaria
- [x] Cálculo de precios y generación del CSV de salida
- [x] Foto diaria programada con cron
- [ ] Acumular 14 días de histórico y revisar los resultados
- [ ] Evaluar umbral mínimo de cambio y ajuste por estado de la carta
- [ ] Techo respecto a la oferta más cara de otros vendedores
- [ ] Docker Compose
- [ ] Exporter de métricas + Prometheus
- [ ] Dashboards en Grafana

## Aviso

Proyecto personal, no afiliado a Cardmarket.
