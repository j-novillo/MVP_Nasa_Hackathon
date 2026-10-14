# Preprocesado

El preprocesado es la pieza 1 del MVP: Python y pandas, sin base de datos, pensado para correr antes de la demo y no en cada clic. Geopandas no hace falta porque la entrada es CSV de puntos y la rejilla es regular. Un archivo shapefile de FIRMS habría que pasarlo a CSV antes, o añadir GDAL más adelante.

## Orden real del código

`build_dataset()` en `brasa/pipeline/build.py` hace esto:

1. `discover_inputs()` mira `data/raw`. Si hay CSV, esos son la entrada y la muestra no se mezcla. Si `data/raw/ORIGIN` contiene `firms_api`, el origen queda etiquetado como descarga FIRMS. Si no hay nada en `raw`, entran `data/samples/*.csv` y el origen es `synthetic_demo`.
2. `clean_paths()` lee cada CSV, detecta el sensor y anota un motivo de descarte por fila.
3. `monthly_aggregate()` asigna celdas y suma.
4. Se escriben `detections.csv`, `monthly_grid.csv`, `monthly_grid.geojson` y `meta.json`.

El comando es:

```bash
python -m brasa.pipeline.build
python -m brasa.pipeline.build --data-dir /ruta/alternativa
```

`--include-samples` fuerza la mezcla y debe usarse solo para depurar.

## Generador de la muestra

`scripts/generate_sample_data.py` no llama a NASA. Escribe dos CSV con las cabeceras reales de FIRMS.

Cada foco sintético sale de un punto caliente (Galicia, Valencia, Sierra Nevada de California, Nueva Gales del Sur, norte de Australia, etc.) con una curva estacional. MODIS existe desde 2000; Aqua se añade en 2002, así que 2000 y 2001 solo llevan Terra. VIIRS empieza en 2012 con S-NPP (`N`), suma NOAA-20 (`N20`) en 2018 y NOAA-21 (`N21`) en 2023. Esa suma de plataformas es deliberada: el conteo VIIRS puede subir aunque el fuego no, y la interfaz lo enseña si se cambia la métrica a conteo.

Un 18 % de las filas MODIS y un 20 % de las VIIRS nacen con confianza baja para que el filtro tenga algo que quitar.

Los casos de uso no dependen solo del azar de Poisson. Hay eventos extra, con FRP más alto, en julio y agosto de 2022 en España, en agosto-octubre de 2020 en California y en diciembre de 2019 y enero-febrero de 2020 en el sureste australiano.

El archivo de la muestra termina el 23 de septiembre de 2026 como máximo. 2026 queda en `partial_years` y no entra en la climatología ni se marca como crítico.

## Descarga FIRMS

`scripts/fetch_firms.py` es el único sitio que habla con NASA.

| `FIRMS_MAP_KEY` | Comportamiento |
| --- | --- |
| Vacía o ausente | No hay petición. Código de salida 0. Sigue la muestra. |
| `DEMO_KEY` | Intenta la petición. Si falla, avisa y sale con 0. La muestra sigue. |
| Una clave real | Escribe los CSV que respondan bien. Si no escribe ninguno, sale con 1. |

Los ficheros buenos sustituyen a otros `firms_*.csv` anteriores. Un CSV tuyo con otro nombre, dentro de `data/raw`, también entra en el build. Después hay que lanzar `python -m brasa.pipeline.build`, o simplemente reiniciar: el arranque reconstruye si el hash no coincide.

La ventana máxima de la API de área en este cliente es de 5 días. No descarga el archivo histórico 2000-2026. Ese archivo, si se consigue en la web de FIRMS, se copia a `data/raw` a mano.
