# Cardmarket Repricer

Pipeline contenerizado para revisar los precios de mis cartas de Magic en Cardmarket a partir de los datos públicos del mercado, con histórico propio, métricas en Prometheus y un dashboard en Grafana.

> **Estado:** en desarrollo. Ver [Roadmap](#roadmap).

## Qué problema resuelve

Mantener precios competitivos a mano en cientos de cartas es lento. Este proyecto calcula un precio de referencia para cada carta de mi stock, genera un CSV listo para reimportar y deja visibles en un dashboard los cambios, la salud del pipeline y la evolución de precio de las cartas más valiosas, sin depender de la API de Cardmarket.

## Decisión de diseño importante: sin API de Cardmarket

El plan inicial era usar la API oficial (OAuth 1.0). Al investigarlo descubrí que **actualmente no se aceptan solicitudes de acceso y que la API está restringida a vendedores profesionales**, así que rediseñé el flujo:

| Necesidad | Solución |
|---|---|
| Datos de mercado | Price guide público de Cardmarket (fichero JSON estático, sin credenciales) |
| Mi inventario | Exportación CSV del stock con una extensión de navegador |
| Aplicar precios nuevos | CSV generado por el pipeline, importado en bloque |

## Arquitectura

```
Price guide público ──▶ snapshot ──▶ data/history/ (una foto al día)
                                          │
Stock (CSV) ───────────────────────────▶ calc ──▶ data/salida_precios.csv
                                          │
                                          ▼
                                      exporter (:8000/metrics)
                                          │
                                          ▼
                                     Prometheus (:9090) ──▶ Grafana (:3000)
```

Todo orquestado con Docker Compose. `snapshot` y `calc` son tareas que corren y terminan; `exporter`, `prometheus` y `grafana` son servicios que se quedan encendidos.

## Lógica de precios

- **Precio de referencia:** el máximo de la media a 7 días (`avg7`) durante los últimos 14 días, usando la columna foil o no foil según la carta. Se usa `avg7` y no `avg1` porque `avg1` es la media de un solo día y una venta aislada dispara el valor.
- **Histórico propio:** el price guide solo trae el momento actual, así que se guarda una foto diaria comprimida y el máximo se calcula sobre esas fotos. Mientras no haya 14 días acumulados, el resultado es una aproximación.
- **Precio mínimo:** 0,50 €.
- **Techo opcional (pendiente):** limitar el precio a un 5 % por debajo de la oferta más cara de otros vendedores de la misma carta. Ese dato no está en el price guide (solo en la web o en la API), así que de momento no se aplica.

Limitaciones conocidas: el price guide no distingue el estado de la carta, y precios cercanos al máximo reciente pueden dejar cartas sin vender si hay copias más baratas.

## Foto diaria idempotente

`snapshot.py` solo descarga si todavía no existe la foto de hoy y la escribe de forma atómica (archivo temporal y renombrado), de modo que una descarga cortada nunca deja una foto a medias. Como la máquina no siempre está encendida a la misma hora, se lanza con `cron` cada hora: la primera ejecución de cada día guarda la foto y el resto termina enseguida.

## Observabilidad

El exporter publica estas métricas en `/metrics`:

| Métrica | Qué mide |
|---|---|
| `cardmarket_cartas{direccion}` | Cartas que suben, bajan o se quedan igual según el CSV de salida |
| `cardmarket_foto_antiguedad_segundos` | Antigüedad de la última foto del price guide |
| `cardmarket_fotos_total` | Número de fotos acumuladas |
| `cardmarket_precio_mercado_eur{carta,id,foil}` | Precio de mercado (`avg7`) de las 15 cartas más valiosas del stock |

Configuración actual: recogida cada 5 minutos, histórico de 15 días en Prometheus, y dashboard de Grafana provisionado desde código (rango por defecto de 24 horas y panel de antigüedad en rojo pasadas 24 horas sin foto nueva). El datasource y el dashboard viven en `grafana/provisioning/`, así que el entorno se reconstruye idéntico con un `docker compose up`.

## Buenas prácticas aplicadas

- Contenedores sin root: se ejecutan con mi UID y GID para que los archivos de `data/` sigan siendo míos.
- Principio de mínimo privilegio: el exporter monta `data/` en solo lectura.
- Puertos publicados solo en `127.0.0.1`.
- Imágenes con versión fija (Python 3.12, Prometheus 3.1.0, Grafana 11.4.0).
- Secretos fuera del repositorio: la configuración variable va en `.env` (ignorado por git) y `.dockerignore` evita que el stock acabe dentro de una imagen.
- La contraseña de Grafana se genera aleatoria; no se usa `admin/admin`.

## Formato del CSV de stock

- Separador `;` y codificación UTF-8 con BOM.
- Los identificadores vienen como `="20895"` (formato texto estilo Excel). Para cruzar con el guide se extraen los dígitos, pero en el CSV de salida se conserva el valor original.
- `Foil` es `Y` / `N`.
- Los precios usan coma decimal (`0,50`).
- `_OriginalPrice_EUR` y `_OriginalComments` no se modifican: la extensión las usa para detectar qué ha cambiado al reimportar.

## Estructura del proyecto

```
cardmarket-repricer/
├── calculator/
│   ├── snapshot.py
│   └── calc.py
├── exporter/
│   ├── Dockerfile
│   ├── exporter.py
│   └── requirements.txt
├── prometheus/
│   └── prometheus.yml
├── grafana/
│   └── provisioning/
│       ├── datasources/prometheus.yml
│       └── dashboards/
│           ├── dashboards.yml
│           └── cardmarket.json
├── data/              # stock, histórico y salida (ignorado por git)
├── Dockerfile
├── docker-compose.yml
├── .dockerignore
├── .gitignore
└── README.md
```

## Uso

Requisitos: Docker y Docker Compose.

```bash
git clone https://github.com/vmncdev-ad/cardmarket-repricer-auto.git
cd cardmarket-repricer-auto
mkdir -p data

# Variables locales (el archivo .env no se sube a git)
echo "DOCKER_USER=$(id -u):$(id -g "$USER")" > .env
echo "GRAFANA_PASSWORD=$(openssl rand -base64 18 | tr -d '/+=')" >> .env

# Copia tu CSV de stock a data/ y ajusta su nombre en calculator/calc.py
docker compose run --rm snapshot
docker compose run --rm calc
docker compose up -d exporter prometheus grafana
```

Grafana queda en `http://localhost:3000` (usuario `admin`; la contraseña está en `.env`) y Prometheus en `http://localhost:9090`.

Para programar la foto diaria, una línea de `cron` que se ejecute cada hora:

```
0 * * * * cd /ruta/al/proyecto && python3 calculator/snapshot.py >> data/snapshot.log 2>&1
```

## Roadmap

- [x] Diseño de arquitectura
- [x] Investigación de acceso a datos (API vs. ficheros públicos)
- [x] Exportar stock a CSV
- [x] Foto diaria idempotente, programada con cron cada hora
- [x] Cálculo de precios y generación del CSV de salida
- [x] Docker Compose (snapshot y calc)
- [x] Exporter de métricas
- [x] Prometheus
- [x] Dashboard de Grafana provisionado desde código
- [ ] Acumular 14 días de histórico y revisar los resultados
- [ ] Evaluar umbral mínimo de cambio y ajuste por estado de la carta
- [ ] Techo respecto a la oferta más cara de otros vendedores
- [ ] Sustituir el cron del host por ejecución desde Compose
- [ ] Evaluar alertas (por ejemplo, foto atrasada)

## Aviso

Proyecto personal, no afiliado a Cardmarket. No subas nunca tu stock ni credenciales al repositorio.
