# API

FastAPI sirve JSON en `/api` y la documentación interactiva en `/docs`. No hay autenticación: es un servidor local de hackathon.

## `GET /api/health`

```json
{"status": "ok"}
```

## `GET /api/meta`

Ficha del dataset cargado: origen, nota en español, rango de fechas, años parciales, tamaño de celda, año de corte, filas conservadas y descartadas, supuestos, regiones y casos de uso.

El campo `data_origin` vale `synthetic_demo`, `local_csv`, `firms_api` o `mixed`.

## `GET /api/query`

Parámetros:

| Parámetro | Default | Notas |
| --- | --- | --- |
| `region` | — | `spain`, `california` o `australia` |
| `bbox` | — | `oeste,sur,este,norte` en grados. Si viene, gana a la región. |
| `year` | 2022 | |
| `month` | 7 | 1-12. Solo afecta al heatmap y al resumen del mes. |
| `sensor` | `harmonized` | `harmonized`, `modis` o `viirs` |

Ejemplo:

```bash
curl -s "http://localhost:8000/api/query?region=spain&year=2022&month=7&sensor=harmonized"
```

## `POST /api/query`

Cuerpo JSON para un polígono. Si `polygon` viene informado, se ignora la región.

```json
{
  "polygon": [[-4.2, 40.0], [-3.2, 40.0], [-3.2, 40.8], [-4.2, 40.8]],
  "year": 2022,
  "month": 7,
  "sensor": "harmonized"
}
```

Cada vértice es `[longitud, latitud]`. Hacen falta entre 3 y 200. También acepta `region_id` o `bbox` en el mismo esquema, sin polígono.

Un área imposible, una región desconocida o un sensor distinto responden 400 con `detail` en español.

## Cuerpo de la respuesta

| Campo | Contenido |
| --- | --- |
| `area` | `kind`, `label`, `bbox` y, si existe, `polygon` |
| `sensor`, `year`, `month`, `transition_year`, `partial_year` | Lo que se pidió y el contexto |
| `summary.active` | Conteo y FRP de la capa en el año |
| `summary.active_month` | Lo mismo, solo el mes del mapa |
| `summary.by_sensor` | MODIS y VIIRS del año, sin la regla de corte, para comparar |
| `summary.detections_in_area` | Filas limpias de todos los años dentro del área, los dos sensores |
| `calendar.days` | Un objeto por día: `date`, `count`, `frp`, `level` (0-4 según cuantiles de FRP) |
| `calendar.week_starts` | Siempre `monday` |
| `months` | Doce meses con FRP y conteo de las tres capas, más `critical` de la capa activa |
| `annual` | Un objeto por año del catálogo, con FRP y conteo de MODIS, VIIRS y la serie armonizada |
| `heatmap` | `FeatureCollection` de celdas del mes. Propiedades: `sensor`, `count`, `frp`, `cell_lat`, `cell_lon` |
| `critical_months` | Números de mes marcados |
| `satellites` | Plataformas de la capa en ese año, con hora nominal y conteo día/noche |
| `notes_es` | Frases sobre el corte de 2012, el año parcial y el origen de los datos |

`level` del calendario está calculado con FRP. Si la interfaz enseña conteos, recalcula los cuantiles en el navegador a partir de `count`.

## Ficheros que no pasan por la consulta

`data/processed/monthly_grid.geojson` es el producto estático de todo el catálogo, no el recorte del área. La API no lo reenvía entero. Se puede abrir con cualquier visor GeoJSON para revisar la rejilla sin el servidor.
