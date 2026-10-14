/** Leaflet map: preset rectangle or a polygon drawn by clicks, plus the monthly grid. */

const HEAT = ["#3a241c", "#8a3b16", "#e85d04", "#ffb703", "#fff1d6"];

export function createMap(element) {
  const map = L.map(element, { zoomControl: true, minZoom: 2 });
  // OSM standard tiles need no key. Carto's dark basemap now watermarks
  // requests that do not carry an API key, which hid the geography.
  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "&copy; OpenStreetMap",
    maxZoom: 18,
  }).addTo(map);
  L.control.scale({ imperial: false, metric: true }).addTo(map);

  const heat = L.geoJSON(null, { style: () => ({ weight: 0.4, color: "#1a100c", fillOpacity: 0.78 }) }).addTo(map);
  const area = L.layerGroup().addTo(map);
  const sketch = L.layerGroup().addTo(map);

  let drawing = false;
  let points = [];
  let areaKey = "";

  map.on("click", (event) => {
    if (!drawing) return;
    points.push(event.latlng);
    drawSketch();
    element.dispatchEvent(new CustomEvent("brasa-sketch", { detail: points.length }));
  });

  function drawSketch() {
    sketch.clearLayers();
    points.forEach((point) => {
      L.circleMarker(point, { radius: 4, color: "#ffd7a8", weight: 2, fillOpacity: 1 }).addTo(sketch);
    });
    if (points.length >= 2) {
      L.polyline(points, { color: "#ff6a2c", weight: 2, dashArray: "4 4" }).addTo(sketch);
    }
  }

  function styleFor(features, metric) {
    const values = features.map((feature) => Number(feature.properties[metric] || 0));
    const max = Math.max(0, ...values);
    return (feature) => {
      const value = Number(feature.properties[metric] || 0);
      const rank = max <= 0 || value <= 0 ? 0 : Math.min(HEAT.length - 1, Math.ceil((Math.log1p(value) / Math.log1p(max)) * (HEAT.length - 1)));
      return { weight: 0.5, color: "#1a100c", fillColor: HEAT[rank], fillOpacity: value > 0 ? 0.82 : 0 };
    };
  }

  return {
    isDrawing: () => drawing,
    startDraw() {
      drawing = true;
      points = [];
      sketch.clearLayers();
      map.getContainer().style.cursor = "crosshair";
    },
    cancelDraw() {
      drawing = false;
      points = [];
      sketch.clearLayers();
      map.getContainer().style.cursor = "";
    },
    finishDraw() {
      if (points.length < 3) return null;
      const ring = points.map((point) => [round(point.lng), round(point.lat)]);
      drawing = false;
      points = [];
      sketch.clearLayers();
      map.getContainer().style.cursor = "";
      return ring;
    },
    setHeat(collection, metric) {
      const features = collection.features || [];
      heat.clearLayers();
      heat.options.style = styleFor(features, metric);
      if (features.length) heat.addData(collection);
      return maxOf(features, metric);
    },
    showArea(areaShape, fit) {
      const key = JSON.stringify(areaShape.bbox) + (areaShape.polygon ? "p" : "b");
      area.clearLayers();
      if (areaShape.polygon) {
        const latlngs = areaShape.polygon.map(([lon, lat]) => [lat, lon]);
        L.polygon(latlngs, { color: "#f4efe6", weight: 1.5, dashArray: "5 4", fillOpacity: 0.04 }).addTo(area);
      } else if (areaShape.bbox) {
        const [west, south, east, north] = areaShape.bbox;
        L.rectangle([[south, west], [north, east]], {
          color: "#f4efe6",
          weight: 1,
          dashArray: "5 4",
          fill: false,
        }).addTo(area);
      }
      if (fit && key !== areaKey && areaShape.bbox) {
        areaKey = key;
        const [west, south, east, north] = areaShape.bbox;
        map.fitBounds([[south, west], [north, east]], { padding: [20, 20] });
      }
    },
    invalidate() {
      map.invalidateSize();
    },
  };
}

function round(value) {
  return Math.round(value * 1e5) / 1e5;
}

function maxOf(features, metric) {
  return features.reduce((max, feature) => Math.max(max, Number(feature.properties[metric] || 0)), 0);
}

export function renderLegend(element, metric, max) {
  const label = metric === "count" ? "conteo" : "FRP";
  element.replaceChildren();
  const caption = document.createElement("span");
  caption.textContent = max > 0 ? `${label} 0–${formatCompact(max)}` : label;
  element.append(caption);
  ["#3a241c", "#8a3b16", "#e85d04", "#ffb703", "#fff1d6"].forEach((color) => {
    const swatch = document.createElement("i");
    swatch.style.background = color;
    element.append(swatch);
  });
}

function formatCompact(value) {
  return new Intl.NumberFormat("es-ES", { maximumFractionDigits: value >= 100 ? 0 : 1 }).format(value);
}
