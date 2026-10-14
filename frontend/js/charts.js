/** Two inline SVG charts: the selected year by sensor, and the annual series. */

const NS = "http://www.w3.org/2000/svg";
const MONTHS = ["E", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"];

export function renderMonthChart(container, months, metric, onMonth) {
  container.replaceChildren();
  const svg = svgEl("svg", { class: "chart", viewBox: "0 0 640 220", role: "img" });
  svg.append(svgEl("title", {}, "FRP y conteo mensuales de MODIS y VIIRS"));
  const width = 640;
  const height = 220;
  const pad = { l: 44, r: 12, t: 16, b: 28 };
  const key = metric === "count" ? "count" : "frp";
  const max = Math.max(1, ...months.flatMap((row) => [row[`modis_${key}`], row[`viirs_${key}`]]));
  const innerW = width - pad.l - pad.r;
  const innerH = height - pad.t - pad.b;
  const slot = innerW / 12;
  months.forEach((row, index) => {
    const x = pad.l + index * slot;
    bar(svg, x + 4, pad.t, slot * 0.38, innerH, row[`modis_${key}`], max, "#2ec4b6", () => onMonth(row.month));
    bar(svg, x + slot * 0.46, pad.t, slot * 0.38, innerH, row[`viirs_${key}`], max, "#ffb703", () => onMonth(row.month));
    if (row.critical) {
      svg.append(svgEl("circle", {
        cx: x + slot / 2,
        cy: pad.t + 6,
        r: 3.5,
        fill: "#ff5d73",
      }));
    }
    const label = svgEl("text", { x: x + slot / 2, y: height - 8, "text-anchor": "middle" });
    label.textContent = MONTHS[index];
    svg.append(label);
  });
  axisLabel(svg, pad.l - 6, pad.t + 8, formatTick(max));
  axisLabel(svg, pad.l - 6, height - pad.b, "0");
  container.append(svg);
}

export function renderAnnualChart(container, annual, metric, transitionYear, selectedYear, onYear) {
  container.replaceChildren();
  const svg = svgEl("svg", { class: "chart", viewBox: "0 0 640 220", role: "img" });
  svg.append(svgEl("title", {}, "Serie anual MODIS, VIIRS y armonizada"));
  if (!annual.length) {
    container.append(svg);
    return;
  }
  const width = 640;
  const height = 220;
  const pad = { l: 48, r: 12, t: 18, b: 28 };
  const key = metric === "count" ? "count" : "frp";
  const max = Math.max(
    1,
    ...annual.flatMap((row) => [row[`modis_${key}`], row[`viirs_${key}`], row[`harmonized_${key}`]]),
  );
  const innerW = width - pad.l - pad.r;
  const innerH = height - pad.t - pad.b;
  const xOf = (index) => pad.l + (annual.length === 1 ? innerW / 2 : (index / (annual.length - 1)) * innerW);
  const yOf = (value) => pad.t + innerH - (value / max) * innerH;

  const transitionIndex = annual.findIndex((row) => row.year >= transitionYear);
  if (transitionIndex >= 0) {
    const x = xOf(transitionIndex);
    svg.append(svgEl("line", { x1: x, x2: x, y1: pad.t, y2: height - pad.b, stroke: "#ff6a2c", "stroke-dasharray": "3 3" }));
    const tag = svgEl("text", { x: x + 4, y: pad.t + 12 });
    tag.textContent = "VIIRS";
    svg.append(tag);
  }

  line(svg, annual.map((row, index) => [xOf(index), yOf(row[`modis_${key}`])]), "#2ec4b6");
  line(svg, annual.map((row, index) => [xOf(index), yOf(row[`viirs_${key}`])]), "#ffb703");
  line(svg, annual.map((row, index) => [xOf(index), yOf(row[`harmonized_${key}`])]), "#ff6a2c");

  annual.forEach((row, index) => {
    const showLabel = row.year % 2 === 0 || row.year === selectedYear || row.year === transitionYear;
    if (showLabel) {
      const label = svgEl("text", { x: xOf(index), y: height - 8, "text-anchor": "middle" });
      label.textContent = String(row.year).slice(2);
      if (row.year === selectedYear) label.setAttribute("fill", "#f4efe6");
      svg.append(label);
    }
    const hit = svgEl("rect", {
      x: xOf(index) - innerW / annual.length / 2,
      y: pad.t,
      width: innerW / annual.length,
      height: innerH,
      fill: "transparent",
    });
    hit.style.cursor = "pointer";
    hit.addEventListener("click", () => onYear(row.year));
    svg.append(hit);
  });
  axisLabel(svg, 4, pad.t + 10, formatTick(max));
  container.append(svg);
}

function bar(svg, x, top, width, innerH, value, max, color, onClick) {
  const height = (value / max) * innerH;
  const rect = svgEl("rect", {
    x,
    y: top + innerH - height,
    width,
    height: Math.max(height, value > 0 ? 1 : 0),
    rx: 2,
    fill: color,
  });
  rect.style.cursor = "pointer";
  rect.addEventListener("click", onClick);
  svg.append(rect);
}

function line(svg, points, color) {
  if (!points.length) return;
  const path = svgEl("path", {
    d: points.map((point, index) => `${index === 0 ? "M" : "L"}${point[0].toFixed(1)},${point[1].toFixed(1)}`).join(" "),
    fill: "none",
    stroke: color,
    "stroke-width": 2,
    "stroke-linejoin": "round",
  });
  svg.append(path);
}

function axisLabel(svg, x, y, text) {
  const node = svgEl("text", { x, y });
  node.textContent = text;
  svg.append(node);
}

function svgEl(name, attrs, text) {
  const node = document.createElementNS(NS, name);
  Object.entries(attrs).forEach(([key, value]) => node.setAttribute(key, value));
  if (text) node.textContent = text;
  return node;
}

function formatTick(value) {
  return new Intl.NumberFormat("es-ES", { notation: "compact", maximumFractionDigits: 1 }).format(value);
}
