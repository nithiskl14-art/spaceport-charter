import { toIso } from "./time";


export function intervalConflicts(date, start, end, schedule) {
  if (!schedule || !start || !end || end <= start) return false;

  const proposedStart = new Date(toIso(date, start)).getTime();
  const proposedEndWithRefueling =
    new Date(toIso(date, end)).getTime() +
    schedule.refuelBufferMinutes * 60 * 1000;

  return schedule.unavailable.some((period) => {
    const existingStart = new Date(period.startTime).getTime();
    const existingEndWithRefueling = new Date(period.endTime).getTime();
    return (
      existingStart < proposedEndWithRefueling &&
      existingEndWithRefueling > proposedStart
    );
  });
}


export function validReturnSlots(date, start, schedule, choices) {
  if (!start) return [];
  return choices.filter(
    (end) => end > start && !intervalConflicts(date, start, end, schedule),
  );
}
