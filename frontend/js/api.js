/** Talks to the FastAPI routes. Polygon queries use POST; presets use GET. */

export async function loadMeta() {
  const response = await fetch("/api/meta");
  if (!response.ok) {
    throw new Error("No se pudo leer la ficha de datos.");
  }
  return response.json();
}

export async function queryView(state) {
  let response;
  if (state.polygon) {
    response = await fetch("/api/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        polygon: state.polygon,
        year: state.year,
        month: state.month,
        sensor: state.sensor,
      }),
    });
  } else {
    const params = new URLSearchParams({
      region: state.regionId,
      year: String(state.year),
      month: String(state.month),
      sensor: state.sensor,
    });
    response = await fetch(`/api/query?${params}`);
  }
  const payload = await response.json();
  if (!response.ok) {
    const detail = payload.detail || "La consulta no se pudo completar.";
    throw new Error(typeof detail === "string" ? detail : "La consulta no se pudo completar.");
  }
  return payload;
}
