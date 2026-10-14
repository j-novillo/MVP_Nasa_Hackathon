/** Wires the calendar page: presets, drawing, sensor layer, and the three views. */

import { loadMeta, queryView } from "./api.js";
import { renderCalendar, formatDate, formatNumber } from "./calendar.js";
import { renderAnnualChart, renderMonthChart } from "./charts.js";
import { createMap, renderLegend } from "./map.js";

const MONTHS = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"];

const state = {
  regionId: "spain",
  polygon: null,
  year: 2022,
  month: 7,
  sensor: "harmonized",
  metric: "frp",
  useCaseId: "spain-summer-2022",
};

const ui = {
  banner: document.querySelector("#banner"),
  regions: document.querySelector("#regions"),
  usecases: document.querySelector("#usecases"),
  year: document.querySelector("#year"),
  hint: document.querySelector("#hint"),
  area: document.querySelector("#area-label"),
  title: document.querySelector("#summary-title"),
  stats: document.querySelector("#stats"),
  months: document.querySelector("#months"),
  critical: document.querySelector("#critical-note"),
  platforms: document.querySelector("#platforms"),
  notes: document.querySelector("#notes"),
  calendar: document.querySelector("#calendar"),
  calYear: document.querySelector("#cal-year"),
  readout: document.querySelector("#day-readout"),
  monthChart: document.querySelector("#month-chart"),
  annualChart: document.querySelector("#annual-chart"),
  assumptions: document.querySelector("#assumption-list"),
  legend: document.querySelector("#map-legend"),
  empty: document.querySelector("#map-empty"),
  draw: document.querySelector("#draw"),
  finish: document.querySelector("#draw-finish"),
  cancel: document.querySelector("#draw-cancel"),
};

const map = createMap(document.querySelector("#map"));
let catalog = null;
let requestId = 0;
let lastView = null;

document.querySelectorAll("#sensors button").forEach((button) => {
  button.addEventListener("click", () => {
    state.sensor = button.dataset.sensor;
    state.useCaseId = null;
    refresh();
  });
});
document.querySelectorAll("#metrics button").forEach((button) => {
  button.addEventListener("click", () => {
    state.metric = button.dataset.metric;
    paint(lastView);
  });
});
ui.year.addEventListener("change", () => {
  state.year = Number(ui.year.value);
  state.useCaseId = null;
  refresh();
});
document.querySelector("#year-prev").addEventListener("click", () => shiftYear(-1));
document.querySelector("#year-next").addEventListener("click", () => shiftYear(1));
ui.draw.addEventListener("click", () => {
  map.startDraw();
  ui.finish.disabled = true;
  ui.cancel.disabled = false;
  ui.hint.textContent = "Haz clic en el mapa para añadir vértices. Cierra el polígono con al menos tres.";
});
ui.finish.addEventListener("click", finishDraw);
ui.cancel.addEventListener("click", () => {
  map.cancelDraw();
  ui.finish.disabled = true;
  ui.cancel.disabled = true;
  ui.hint.textContent = "";
});
document.querySelector("#map").addEventListener("brasa-sketch", (event) => {
  ui.finish.disabled = event.detail < 3;
});
document.addEventListener("keydown", (event) => {
  if (!map.isDrawing()) return;
  if (event.key === "Enter") finishDraw();
  if (event.key === "Escape") ui.cancel.click();
});

boot();

async function boot() {
  try {
    catalog = await loadMeta();
  } catch (error) {
    ui.banner.textContent = error.message;
    return;
  }
  ui.banner.textContent = catalog.origin_note_es;
  ui.banner.classList.toggle("is-live", catalog.data_origin === "firms_api");
  fillYears();
  fillRegions();
  fillUseCases();
  fillAssumptions();
  await refresh();
  map.invalidate();
}

function fillYears() {
  ui.year.replaceChildren();
  for (let year = catalog.year_min; year <= catalog.year_max; year += 1) {
    const option = document.createElement("option");
    option.value = String(year);
    option.textContent = catalog.partial_years.includes(year) ? `${year} (parcial)` : String(year);
    ui.year.append(option);
  }
}

function fillRegions() {
  ui.regions.replaceChildren();
  catalog.regions.forEach((region) => {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = region.name;
    button.dataset.region = region.id;
    button.title = region.blurb;
    button.addEventListener("click", () => {
      state.regionId = region.id;
      state.polygon = null;
      state.useCaseId = null;
      map.cancelDraw();
      ui.finish.disabled = true;
      ui.cancel.disabled = true;
      ui.hint.textContent = region.blurb;
      refresh();
    });
    ui.regions.append(button);
  });
}

function fillUseCases() {
  ui.usecases.replaceChildren();
  catalog.use_cases.forEach((useCase) => {
    const button = document.createElement("button");
    button.type = "button";
    button.dataset.case = useCase.id;
    button.textContent = useCase.name;
    button.title = useCase.blurb;
    button.addEventListener("click", () => {
      state.regionId = useCase.region_id;
      state.polygon = null;
      state.year = useCase.year;
      state.month = useCase.month;
      state.sensor = useCase.sensor;
      state.useCaseId = useCase.id;
      map.cancelDraw();
      ui.hint.textContent = useCase.blurb;
      refresh();
    });
    ui.usecases.append(button);
  });
}

function fillAssumptions() {
  catalog.assumptions_es.forEach((text) => {
    const item = document.createElement("li");
    item.textContent = text;
    ui.assumptions.append(item);
  });
}

function finishDraw() {
  const ring = map.finishDraw();
  ui.finish.disabled = true;
  ui.cancel.disabled = true;
  if (!ring) {
    ui.hint.textContent = "Hacen falta al menos tres vértices.";
    return;
  }
  state.polygon = ring;
  state.regionId = null;
  state.useCaseId = null;
  ui.hint.textContent = "Área dibujada. Las cifras de abajo solo cuentan detecciones dentro del polígono.";
  refresh();
}

function shiftYear(delta) {
  const next = state.year + delta;
  if (next < catalog.year_min || next > catalog.year_max) return;
  state.year = next;
  state.useCaseId = null;
  refresh();
}

async function refresh() {
  const id = ++requestId;
  ui.year.value = String(state.year);
  press("#sensors button", "sensor", state.sensor);
  press("#metrics button", "metric", state.metric);
  document.querySelectorAll("#regions button").forEach((button) => {
    button.setAttribute("aria-pressed", String(!state.polygon && button.dataset.region === state.regionId));
  });
  document.querySelectorAll("#usecases button").forEach((button) => {
    button.setAttribute("aria-pressed", String(button.dataset.case === state.useCaseId));
  });
  try {
    const view = await queryView(state);
    if (id !== requestId) return;
    lastView = view;
    paint(view);
  } catch (error) {
    if (id !== requestId) return;
    ui.hint.textContent = error.message;
  }
}

function paint(view) {
  if (!view) return;
  ui.area.textContent = view.area.label;
  ui.title.textContent = `${MONTHS[view.month - 1]} ${view.year}`;
  ui.calYear.textContent = String(view.year);
  renderStats(view);
  renderMonths(view);
  renderPlatforms(view);
  renderNotes(view);
  const critical = new Set(view.critical_months);
  renderCalendar(ui.calendar, view.calendar, state.metric, critical, (day) => {
    ui.readout.textContent = `${formatDate(day.date)} · ${formatNumber(day.frp)} MW · ${day.count} detecciones`;
  });
  renderMonthChart(ui.monthChart, view.months, state.metric, (month) => {
    state.month = month;
    state.useCaseId = null;
    refresh();
  });
  renderAnnualChart(ui.annualChart, view.annual, state.metric, view.transition_year, view.year, (year) => {
    state.year = year;
    state.useCaseId = null;
    refresh();
  });
  const max = map.setHeat(view.heatmap, state.metric === "count" ? "count" : "frp");
  renderLegend(ui.legend, state.metric, max);
  ui.empty.hidden = view.heatmap.features.length > 0;
  map.showArea(view.area, !map.isDrawing());
  if (!ui.hint.textContent) {
    ui.hint.textContent = "El recuadro discontinuo es el área. El color del mapa es la métrica del mes elegido.";
  }
}

function renderStats(view) {
  ui.stats.replaceChildren();
  const active = view.summary.active;
  const month = view.summary.active_month;
  const metric = state.metric;
  const items = [
    ["Capa activa", sensorLabel(view.sensor)],
    [metric === "count" ? "Detecciones del mes" : "FRP del mes", metric === "count" ? String(month.count) : `${formatNumber(month.frp)} MW`],
    [metric === "count" ? "Detecciones del año" : "FRP del año", metric === "count" ? String(active.count) : `${formatNumber(active.frp)} MW`],
    ["MODIS en el año", metric === "count" ? String(view.summary.by_sensor.modis.count) : `${formatNumber(view.summary.by_sensor.modis.frp)} MW`],
    ["VIIRS en el año", metric === "count" ? String(view.summary.by_sensor.viirs.count) : `${formatNumber(view.summary.by_sensor.viirs.frp)} MW`],
  ];
  items.forEach(([label, value]) => {
    const wrap = document.createElement("div");
    const dt = document.createElement("dt");
    const dd = document.createElement("dd");
    dt.textContent = label;
    dd.textContent = value;
    wrap.append(dt, dd);
    ui.stats.append(wrap);
  });
}

function renderMonths(view) {
  ui.months.replaceChildren();
  view.months.forEach((row) => {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = MONTHS[row.month - 1].slice(0, 3);
    button.setAttribute("aria-pressed", String(row.month === view.month));
    if (row.critical) button.classList.add("is-critical");
    const value = state.metric === "count" ? row.count : row.frp;
    button.title = row.critical ? `${formatNumber(value)} · mes crítico` : formatNumber(value);
    button.addEventListener("click", () => {
      state.month = row.month;
      state.useCaseId = null;
      refresh();
    });
    ui.months.append(button);
  });
  ui.critical.textContent = view.critical_months.length
    ? `Meses críticos (1,5σ en la misma era de sensor y al menos un 25% del pico del año): ${view.critical_months.map((month) => MONTHS[month - 1]).join(", ")}.`
    : "Ningún mes de este año supera el umbral crítico con la historia disponible.";
}

function renderPlatforms(view) {
  ui.platforms.replaceChildren();
  if (!view.satellites.length) {
    const item = document.createElement("li");
    item.textContent = "No hay detecciones de esta capa en el año elegido.";
    ui.platforms.append(item);
    return;
  }
  view.satellites.forEach((sat) => {
    const item = document.createElement("li");
    item.textContent = `${sat.name} (${sat.sensor}): ${sat.pass_es}. ${sat.count} detecciones, ${sat.day} de día y ${sat.night} de noche.`;
    ui.platforms.append(item);
  });
}

function renderNotes(view) {
  ui.notes.replaceChildren();
  view.notes_es.forEach((text) => {
    const item = document.createElement("li");
    item.textContent = text;
    ui.notes.append(item);
  });
}

function press(selector, attr, value) {
  document.querySelectorAll(selector).forEach((button) => {
    button.setAttribute("aria-pressed", String(button.dataset[attr] === value));
  });
}

function sensorLabel(sensor) {
  if (sensor === "modis") return "MODIS";
  if (sensor === "viirs") return "VIIRS";
  return "Armonizada";
}
