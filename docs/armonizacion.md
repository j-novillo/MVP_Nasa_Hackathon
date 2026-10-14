# Armonización

La propuesta del hackathon fija la armonización mínima: no calibrar radiancias, agregar en el tiempo y en una rejilla, sumar FRP además de contar puntos, enseñar MODIS y VIIRS por separado, y en el solape quedarse con VIIRS para la serie única. Esta página es esa regla, tal como está en el código.

## Qué se considera la serie armonizada

Para un área ya recortada:

- si el año es anterior a 2012, entran solo las detecciones `modis`;
- si el año es 2012 o posterior, entran solo las detecciones `viirs`.

MODIS de 2012 en adelante no se borra. Sigue en la capa MODIS y en las barras del gráfico. No se suma a VIIRS en el mismo mes de la serie armonizada. VIIRS anterior a 2012, si un CSV lo trajera, tampoco entra en la serie armonizada. En la muestra no existe.

El corte es por año de calendario, no por el día exacto del primer granulo de S-NPP. Enero de 2012 ya cuenta como era VIIRS. Es una simplificación: el archivo real de VIIRS 375 m no cubre todo enero de 2012 con la misma densidad.

La función está en `brasa/pipeline/harmonize.py` (`select_sensor`) y se usa tanto al etiquetar `in_harmonized_series` en la rejilla como al responder una consulta.

## Métrica

Dentro de la selección de sensor se suman dos cosas:

- **FRP acumulado**, en MW, suma de la columna `frp` de las filas que quedan. Es la métrica por defecto del calendario, del mapa y de los gráficos.
- **Conteo**, número de filas. Sirve para ver el efecto del sensor y de las plataformas de más. No es un número de incendios.

No hay peso por confianza dentro de las clases que se conservan (nominal y high cuentan igual). No hay peso por tamaño de píxel. Un MW de MODIS (píxel de 1 km) y un MW de VIIRS (píxel de 375 m) se tratan como la misma unidad, que es precisamente lo que una calibración futura tendría que revisar.

## Rejilla

La agregación espacial de referencia es una celda de 0,25°. El heatmap del mes elegido vuelve a hacer esa suma solo con los puntos del área, así que una celda cortada por el polígono aporta únicamente los puntos interiores, no el total de la celda precalculada. El GeoJSON global, en cambio, suma la celda entera. Las dos cifras pueden diferir en el borde de un polígono. El mapa de la aplicación usa el recorte por puntos.

## Calendario diario

El reto se llama calendario de actividad de quema y la pieza visible es una rejilla de días por semanas, al estilo de las contribuciones de GitHub. La armonización sigue siendo la misma selección de sensor. Cada día es la suma de FRP (o el conteo) de las detecciones de ese día dentro del área. La semana empieza en lunes.

El color de 0 a 4 sale de los cuantiles de los días con valor positivo de ese año y esa métrica. Un año flojo y un año extremo usan toda la escala cada uno. El color no se compara entre años; para eso está el gráfico anual.

## Meses críticos

Para el año y la capa que se están viendo:

1. Se elige la era de referencia.
   - Capa armonizada en 2012 o después, o capa VIIRS: años VIIRS desde 2012, sin el año consultado y sin años parciales.
   - Capa armonizada antes de 2012: solo los años MODIS anteriores a 2012.
   - Capa MODIS: todos los años MODIS disponibles, sin mezclarla con VIIRS.
2. Hacen falta al menos tres años de referencia. Si no, no hay marca.
3. Para cada mes se calcula la media y la desviación típica poblacional del FRP de ese mes en los años de referencia. Un año sin detecciones cuenta como cero.
4. El mes es crítico si su FRP es mayor que media + 1,5 desviaciones, es mayor que cero, y además es al menos el 25 % del mes más alto de ese mismo año.

El último corte evita marcar un febrero diminuto solo porque los otros febreros están a cero. El año consultado no entra en la media, para que un pico no ensanche su propio umbral. 2026, en la muestra, es parcial y no se evalúa.

Es una heurística de boceto. No es el detector de anomalías de X sigma sobre una climatología observada de verdad, que la propuesta dejaba como ampliación. Compara la muestra consigo misma.

## Lo que la regla no corrige

- El mismo fuego visto por Terra y por Aqua, o por S-NPP, NOAA-20 y NOAA-21, se cuenta varias veces.
- No se divide por el número de órbitas ni por los píxeles observados. Un día sin focos puede ser un día nublado o un día sin pasada. No lo distinguimos.
- No se corrige que Terra pasa por la mañana (~10:30) y Aqua y VIIRS por la tarde (~13:30), cuando la quema suele ser más intensa. La interfaz lista la hora nominal de cada plataforma presente en el año, para que ese sesgo se vea, no para quitarlo.
- No hay factores de simultaneous nadir overpass ni regresión MODIS-VIIRS.

Esas tres omisiones son el núcleo de lo que el MVP decidió no hacer en el tiempo del hackathon. Conviene decirlas en la presentación.
