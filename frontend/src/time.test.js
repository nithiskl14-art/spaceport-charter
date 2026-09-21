import { describe, expect, it } from "vitest";

import { dateInCentral, formatCentral, minutesInCentral, slots, toIso } from "./time";


describe("Central Time utilities", () => {
  it("converts winter Central Time to UTC", () => {
    expect(toIso("2027-01-15", "09:00")).toBe("2027-01-15T15:00:00.000Z");
  });

  it("converts summer Central Time using daylight saving time", () => {
    expect(toIso("2027-07-15", "09:00")).toBe("2027-07-15T14:00:00.000Z");
  });

  it("uses the new offset after the spring DST transition", () => {
    expect(toIso("2027-03-14", "06:00")).toBe("2027-03-14T11:00:00.000Z");
    expect(toIso("2027-03-14", "09:00")).toBe("2027-03-14T14:00:00.000Z");
  });

  it("uses the new offset after the fall DST transition", () => {
    expect(toIso("2027-11-07", "06:00")).toBe("2027-11-07T12:00:00.000Z");
    expect(toIso("2027-11-07", "09:00")).toBe("2027-11-07T15:00:00.000Z");
  });

  it("formats UTC timestamps in Central Time", () => {
    const timestamp = "2027-01-15T15:30:00Z";
    expect(formatCentral(timestamp)).toBe("9:30 AM");
    expect(dateInCentral(timestamp)).toBe("2027-01-15");
    expect(minutesInCentral(timestamp)).toBe(9 * 60 + 30);
  });

  it("provides half-hour choices from opening through closing", () => {
    expect(slots).toHaveLength(33);
    expect(slots[0]).toBe("06:00");
    expect(slots.at(-1)).toBe("22:00");
  });
});
