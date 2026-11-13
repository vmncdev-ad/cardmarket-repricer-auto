# Cardmarket Repricer

Pipeline automatizado para revisar cada semana los precios de mis cartas de Magic en Cardmarket a partir de los datos públicos del mercado, con métricas y dashboards.

> **Estado:** en desarrollo. Ver [Roadmap](#roadmap).

## Qué problema resuelve

Mantener precios competitivos a mano en cientos de cartas es lento. Este proyecto calcula el precio objetivo de cada carta (mínimo del mercado + margen) y genera el fichero para aplicarlo en bloque, además de medir cómo evolucionan los precios.

## Decisión de diseño importante: sin API de Cardmarket

El plan inicial era usar la API oficial de Cardmarket (OAuth 1.0) para leer y actualizar los listings. Al investigarlo descubrí que **actualmente no se aceptan solicitudes de acceso y que la API está restringida a vendedores profesionales**. Así que rediseñé el flujo para no depender de ella:

| Necesidad | Solución |
|---|---|
| Datos de mercado | Price guide público de Cardmarket (ficheros estáticos, sin credenciales) |
| Mi inventario | Exportación CSV de mi stock (extensión de navegador) |
| Aplicar precios nuevos | CSV generado por el pipeline + importación en bloque |

## Arquitectura

```
Price guide público ──▶ Calculator (Python) ◀── CSV de mi stock
                              │
                 ┌────────────┴────────────┐
                 ▼                         ▼
        CSV con precios nuevos        Exporter /metrics
                                           │
                                           ▼
                                      Prometheus ──▶ Grafana
```

Todo orquestado con **Docker Compose**.

## Stack

- Python (descarga del price guide y cálculo de precios)
- Docker / Docker Compose
- Prometheus (métricas)
- Grafana (dashboards)

## Lógica de precios

```
precio_nuevo = precio_mínimo_mercado × (1 + margen)
```

El margen es configurable. Estrategia elegida: ligeramente por encima del mínimo para ganar margen sin perder visibilidad.

## Estructura del proyecto

```
cardmarket-repricer/
├── docker-compose.yml
├── calculator/        # descarga price guide + calcula precios
├── exporter/          # expone métricas para Prometheus
├── prometheus/
│   └── prometheus.yml
├── grafana/
│   └── provisioning/
├── data/              # CSV de stock y salida (no se sube a git)
└── README.md
```

## Uso

```bash
git clone https://github.com/vmncdev-ad/cardmarket-repricer.git
cd cardmarket-repricer
docker compose up -d
```

(Ajusta la URL si el repositorio tiene otro nombre.)

## Roadmap

- [x] Diseño de arquitectura
- [x] Investigación de acceso a datos (API vs. ficheros públicos)
- [ ] Exportar stock a CSV
- [ ] Descarga y parseo del price guide
- [ ] Cálculo de precios con margen configurable
- [ ] Generación del CSV de salida
- [ ] Exporter de métricas + Prometheus
- [ ] Dashboards en Grafana
- [ ] Ejecución programada semanal

## Aviso

Proyecto personal. No afiliado a Cardmarket. No incluyas nunca tu stock ni credenciales en el repositorio.
