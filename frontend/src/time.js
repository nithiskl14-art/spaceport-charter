export const TZ = "America/Chicago";

function centralDateString(value) {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: TZ,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(value);
  const fields = Object.fromEntries(
    parts.map((part) => [part.type, part.value]),
  );
  return `${fields.year}-${fields.month}-${fields.day}`;
}

export function todayInCentral() {
  return centralDateString(new Date());
}

function centralDateTimeParts(value) {
  return new Intl.DateTimeFormat("en-US", {
    timeZone: TZ,
    hourCycle: "h23",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  })
    .formatToParts(value)
    .reduce((parts, part) => ({ ...parts, [part.type]: part.value }), {});
}

export function toIso(date, time) {
  const [year, month, day] = date.split("-").map(Number);
  const [hour, minute] = time.split(":").map(Number);
  const requestedWallClock = Date.UTC(year, month - 1, day, hour, minute, 0);
  let candidate = requestedWallClock;

  // Iterate because the UTC guess and the requested Chicago time can sit on
  // opposite sides of a daylight-saving transition.
  for (let attempt = 0; attempt < 4; attempt += 1) {
    const parts = centralDateTimeParts(new Date(candidate));
    const renderedWallClock = Date.UTC(
      Number(parts.year),
      Number(parts.month) - 1,
      Number(parts.day),
      Number(parts.hour),
      Number(parts.minute),
      Number(parts.second),
    );
    const correction = requestedWallClock - renderedWallClock;
    if (correction === 0) return new Date(candidate).toISOString();
    candidate += correction;
  }

  throw new Error("The selected Central Time does not exist on this date");
}

export function formatCentral(value, includeDate = false) {
  return new Intl.DateTimeFormat("en-US", {
    timeZone: TZ,
    ...(includeDate ? { month: "short", day: "numeric" } : {}),
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(value));
}

export function dateInCentral(value) {
  return centralDateString(new Date(value));
}

export function minutesInCentral(value) {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: TZ,
    hourCycle: "h23",
    hour: "2-digit",
    minute: "2-digit",
  }).formatToParts(new Date(value));
  const values = Object.fromEntries(
    parts.map((part) => [part.type, part.value]),
  );
  return Number(values.hour) * 60 + Number(values.minute);
}

export function isElapsedStart(date, time) {
  return new Date(toIso(date, time)).getTime() <= Date.now();
}

export const slots = Array.from({ length: 33 }, (_, i) => {
  const minutes = 360 + i * 30;
  return `${String(Math.floor(minutes / 60)).padStart(2, "0")}:${String(minutes % 60).padStart(2, "0")}`;
});
