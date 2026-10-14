/** GitHub-style year grid. Weeks start on Monday. Color follows the active metric. */

const MONTHS = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];
const DOW = ["L", "M", "X", "J", "V", "S", "D"];

export function renderCalendar(container, calendar, metric, criticalMonths, onDay) {
  container.replaceChildren();
  if (!calendar || !calendar.days) return;

  const offset = mondayOffset(calendar.year);
  const values = calendar.days.map((day) => (metric === "count" ? day.count : day.frp));
  const levels = quartileLevels(values);
  const weekCount = Math.ceil((offset + calendar.days.length) / 7);

  const root = document.createElement("div");
  root.className = "cal";

  const head = document.createElement("div");
  head.className = "cal-head";
  head.append(document.createElement("span"));
  const monthRow = document.createElement("div");
  monthRow.className = "cal-months";
  monthRow.style.gridTemplateColumns = `repeat(${weekCount}, 13px)`;
  const usedWeeks = new Set();
  calendar.days.forEach((day, index) => {
    if (!day.date.endsWith("-01") && index !== 0) return;
    const week = Math.floor((offset + index) / 7);
    if (usedWeeks.has(week)) return;
    usedWeeks.add(week);
    const label = document.createElement("span");
    label.style.gridColumn = String(week + 1);
    label.textContent = MONTHS[Number(day.date.slice(5, 7)) - 1];
    monthRow.append(label);
  });
  head.append(monthRow);

  const body = document.createElement("div");
  body.className = "cal-body";
  const dows = document.createElement("div");
  dows.className = "cal-dows";
  DOW.forEach((label) => {
    const cell = document.createElement("span");
    cell.textContent = label;
    dows.append(cell);
  });
  const weeks = document.createElement("div");
  weeks.className = "cal-weeks";
  for (let blank = 0; blank < offset; blank += 1) {
    const pad = document.createElement("span");
    pad.className = "cal-cell is-blank";
    weeks.append(pad);
  }
  calendar.days.forEach((day, index) => {
    const button = document.createElement("button");
    button.type = "button";
    const month = Number(day.date.slice(5, 7));
    button.className = `cal-cell lv-${levels[index]}${criticalMonths.has(month) ? " is-critical" : ""}`;
    button.title = `${formatDate(day.date)}: ${formatNumber(day.frp)} MW, ${day.count} detecciones`;
    button.setAttribute("aria-label", button.title);
    button.addEventListener("click", () => onDay(day));
    weeks.append(button);
  });
  body.append(dows, weeks);
  root.append(head, body);
  container.append(root);
}

function mondayOffset(year) {
  const weekday = new Date(Date.UTC(year, 0, 1)).getUTCDay();
  return (weekday + 6) % 7;
}

export function quartileLevels(values) {
  const positive = values.filter((value) => value > 0).sort((a, b) => a - b);
  if (!positive.length) return values.map(() => 0);
  const q1 = quantile(positive, 0.25);
  const q2 = quantile(positive, 0.5);
  const q3 = quantile(positive, 0.75);
  return values.map((value) => {
    if (value <= 0) return 0;
    if (value <= q1) return 1;
    if (value <= q2) return 2;
    if (value <= q3) return 3;
    return 4;
  });
}

function quantile(sorted, ratio) {
  const index = Math.min(sorted.length - 1, Math.round(ratio * (sorted.length - 1)));
  return sorted[index];
}

function formatDate(iso) {
  const [year, month, day] = iso.split("-");
  return `${Number(day)} ${MONTHS[Number(month) - 1]} ${year}`;
}

function formatNumber(value) {
  return new Intl.NumberFormat("es-ES", { maximumFractionDigits: 1 }).format(value);
}

export { formatDate, formatNumber, MONTHS };
