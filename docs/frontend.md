# Interfaz

Una sola página, sin empaquetador. FastAPI sirve `frontend/index.html`, `frontend/css/app.css`, `frontend/js/` y Leaflet 1.9.4 desde `frontend/vendor/leaflet/`. Leaflet está copiado en el repositorio (licencia BSD de 2 cláusulas, fichero `LICENSE` junto al código) para que el calendario no dependa de un CDN. Las teselas del mapa base sí salen a la red.

Textos de la página en español. Los nombres de funciones y de campos JSON siguen en inglés.

## Módulos

| Fichero | Qué hace |
| --- | --- |
| `js/app.js` | Estado (región o polígono, año, mes, capa, métrica) y repintado |
| `js/api.js` | `GET /api/meta`, `GET /api/query` para regiones y `POST /api/query` para el polígono |
| `js/map.js` | Mapa, rectángulo del área, polígono por clics y celdas coloreadas |
| `js/calendar.js` | Rejilla de semanas que empiezan en lunes y cuantiles locales si la métrica es el conteo |
| `js/charts.js` | SVG del año (barras MODIS y VIIRS) y de la serie 2000-2026 |

`app.js` guarda un número de petición. Si se cambia el año mientras la anterior no ha vuelto, la respuesta vieja se tira.

## Mapa

El fondo es el estilo oscuro de CARTO. La escala es métrica. El área preparada se dibuja como rectángulo discontinuo; el polígono, como línea sobre los vértices clicados.

Las celdas usan cinco tonos, del marrón apagado al crema, según el logaritmo del FRP o del conteo dentro del mes que se está viendo. Un mes con poco fuego usa igual toda la rampa: el color dice contraste interno, no un umbral absoluto de megavatios.

El mapa vacío enseña un aviso. No es un error de red.

## Calendario

Cada día es un botón con fecha, FRP y conteo en el `title` y en la etiqueta accesible. El día pulsado se escribe también en el texto de encima, para quien no use el tooltip.

Los días de un mes crítico llevan un borde rosa. El nivel 0 es un día sin detecciones de la capa activa, que puede esconder detecciones del otro sensor. En 2022, un día solo con MODIS aparece vacío en la capa armonizada y visible si se cambia a MODIS.

## Gráficos

El de la izquierda son doce grupos de dos barras: verde agua para MODIS, ámbar para VIIRS. Un punto rosa marca el mes crítico de la capa activa, no de cada barra por separado. Pulsar una barra cambia el mes del mapa.

El de la derecha son tres líneas: MODIS, VIIRS y la armonizada, que coincide con MODIS hasta 2011 y con VIIRS desde 2012. La línea vertical naranja marca ese corte. Pulsar un año lo selecciona. 2026 en la muestra es un año corto; la línea baja por eso, no porque el fuego se apague.

## Origen de los datos en pantalla

El banner sale de `origin_note_es`. Con la muestra es un aviso de que los datos no son reales. Si el origen es `firms_api`, el banner cambia de color, pero el texto sigue diciendo que la descarga es una ventana corta de tiempo casi real.

Los supuestos largos están en el desplegable del pie y llegan desde `/api/meta`, así que coinciden con `meta.json` del build.
