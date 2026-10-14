# Decisiones a revisar

El MVP sigue la propuesta escrita. Donde esa propuesta dejaba una opción abierta, se eligió lo de abajo. Cualquiera de estos puntos se puede cambiar sin rehacer la página.

1. **Rejilla de 0,25°.** La propuesta decía «por ejemplo 0,25°». Está en `GRID_DEGREES`. Bajarla a 0,1° acerca el mapa al fuego y multiplica las celdas.

2. **VIIRS gana desde el año 2012 inclusive, no desde una fecha de granulo.** MODIS queda como capa. No hay clustering a 1 km y unas horas, que la propuesta marcaba como la primera trampa de tiempo.

3. **FRP sumado, no Fire Radiative Energy.** No hay duración por detección. El eje dice MW de suma de filas.

4. **Confianza MODIS baja por debajo de 30.** Es el corte low/nominal de FIRMS. VIIRS se filtra por la etiqueta `low`.

5. **Calendario diario además de la agregación mensual.** La armonización de referencia es el mes. El calendario existe porque el reto se llama así y la propuesta lo pedía como pieza visible. Usa la misma regla de sensor.

6. **Semana que empieza en lunes.** La metáfora es la de GitHub; el inicio de semana es el de un calendario en español.

7. **Mes crítico = 1,5σ del mismo mes y misma era, más un 25 % del pico del año.** La propuesta dejaba la anomalía como ampliación. Entra una versión pequeña para que «periodo crítico» se vea en los casos de uso. El 1,5 y el 25 % son arbitrarios (`CRITICAL_SIGMA` en `brasa/config.py` y el `0.25` en `services/query.py`).

8. **Pandas en vez de geopandas.** La entrada del MVP es CSV de puntos y la geometría es una rejilla regular más un punto-en-polígono. Evita GDAL en la instalación del hackathon. Un shapefile de archivo no se lee todavía.

9. **FastAPI en vez de un JSON estático puro.** La propuesta aceptaba las dos cosas. El polígono dibujado obliga a filtrar en el servidor. El GeoJSON mensual sigue existiendo como artefacto estático.

10. **Muestra sintética versionada, y la API de FIRMS solo como opción.** La propuesta decía predescargar archivos y no consultar FIRMS en la demo. Sin un `MAP_KEY` ni un archivo histórico en el repo, la alternativa que arranca sola es la muestra, con el aviso en pantalla. `DEMO_KEY` no se envía como si fuera una clave válida de FIRMS: se intenta y, si falla, se sigue con la muestra.

11. **Tres regiones y tres casos.** España, California y Australia, como ejemplos de la propuesta. Los picos de la muestra no deben presentarse como el verano real de 2022.

12. **VIIRS 375 m, no el producto de banda M a 750 m.** La propuesta decía investigar cuál salta menos respecto a MODIS. Para el boceto se usó 375 m, que es el que la propia propuesta prioriza en el solape por resolución. El 750 m no está modelado.

13. **Hora local solo documentada.** Terra ~10:30, Aqua y VIIRS ~13:30. No hay corrección.

14. **Leaflet vendido en el repo, teselas de OpenStreetMap por red.** El estilo oscuro se hace con un filtro CSS. CARTO pedía clave y marcaba el mapa. El calendario funciona sin teselas. El dibujo es propio, sin el plugin Leaflet.draw.

15. **2026 parcial hasta septiembre en el generador.** El año no se marca como crítico. Si entra un CSV real de 2026 completo, hay que quitar 2026 de `PARTIAL_YEARS` o la marca seguirá apagada.

16. **El resumen numérico grande es el año, y el mapa es el mes.** Mezclarlos en un solo total confundía la lectura. Si se prefiere un único número, el del mes está en `summary.active_month`.
