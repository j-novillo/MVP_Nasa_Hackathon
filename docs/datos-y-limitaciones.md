# Datos, supuestos y limitaciones

## Qué hay ahora mismo en el disco

| Pieza | Hecho |
| --- | --- |
| Filas de entrada | 11396 en los dos CSV de muestra |
| Conservadas | 9238 (5248 MODIS, 3990 VIIRS) |
| Tiradas por confianza baja | 2158 |
| Tiradas por inválidas | 0 |
| Fechas | 2000-01-07 a 2026-09-23 |
| Origen | `synthetic_demo` |

Esas cifras cambian si regeneras la muestra o si pones CSV propios en `data/raw`. `data/processed/meta.json` es la fuente después de cada build.

## Supuestos con los que se puede leer un número

1. Una fila es una detección de un píxel, no un incendio ni una parcela quemada.
2. Sumar FRP aproxima mejor la actividad que contar puntos, pero sigue sin ser energía ni potencia de un único fuego.
3. A partir de 2012 la comparación justa, dentro de este MVP, es VIIRS contra otros años VIIRS, y MODIS contra otros años MODIS. La línea armonizada no es una serie homogénea 2000-2026.
4. La confianza baja no aporta. El resto de confianzas pesan igual.
5. El área dibujada solo ve los focos que caen dentro. No hay un modelo que reparta una celda a medias.
6. Los meses sin filas son ceros en la climatología. No sabemos si el satélite miró.
7. 2026 en la muestra acaba en septiembre y no se juzga como año completo.

## Limitaciones que un jurado debería oír

- **No son datos FIRMS** mientras el banner lo diga. Los picos de los casos de uso están construidos en el generador para probar la pantalla. Con un CSV real, la misma regla puede no marcar esos meses, y debe poder no marcarlos.
- **Doble conteo.** No hay agrupación espacio-temporal. Tres satélites VIIRS inflan conteo y FRP frente a la época de un solo S-NPP.
- **Sin normalizar por observación.** El salto de plataformas en 2018 y 2023 puede parecer más fuego.
- **Sin corrección diurna.** La tarde (Aqua, VIIRS) no se ha bajado al nivel de la mañana (Terra).
- **Sin calibración cruzada.** Un FRP de VIIRS y uno de MODIS se dibujan en el mismo eje a propósito, para que el desacuerdo se vea, no porque sean intercambiables.
- **Rejilla grosera.** 0,25° es una celda de decenas de kilómetros. No localiza un incendio.
- **API de FIRMS corta.** La clave, si se usa, trae como mucho cinco días NRT por petición de este cliente, no el archivo.
- **Cobertura de la muestra.** Fuera de las tres regiones no hay puntos. Un polígono en el Amazonas sale a cero y eso no significa que no hubiera fuego.
- **España sin Canarias.** Baleares queda en el borde oriental de la caja y casi fuera.
- **Años parciales y huecos.** Un archivo real con meses ausentes se leerá como cero y puede fabricar meses críticos falsos. Conviene mirar `date_min` y `date_max` antes de creerse una marca rosa.
- **Volumen.** El diseño en memoria vale para esta muestra y para un archivo regional moderado. Un CSV global de dos décadas no debería cargarse entero en el proceso del mapa.

## Qué sería el siguiente incremento, en el orden de la propuesta

1. Normalizar por número de observaciones o de órbitas del sensor ese día.
2. Sustituir la heurística de 1,5σ por una climatología calculada solo con días observados, y enseñar una banda, no solo un punto rosa.
3. Comparar dos periodos o dos áreas a la vez.
4. Animar el heatmap con un deslizador de año.

Y, ya fuera del MVP, la opción C: factores empíricos en el solape usando pasos nadir casi simultáneos de Aqua y S-NPP.
