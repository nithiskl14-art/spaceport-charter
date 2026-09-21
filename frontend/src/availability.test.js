import { describe, expect, it } from "vitest";

import { intervalConflicts, validReturnSlots } from "./availability";


const schedule = {
  refuelBufferMinutes: 30,
  unavailable: [
    {
      startTime: "2027-01-15T15:00:00Z",
      endTime: "2027-01-15T16:30:00Z",
    },
  ],
};


describe("availability choices", () => {
  it("disables direct overlaps and the post-booking refueling window", () => {
    expect(intervalConflicts("2027-01-15", "09:30", "10:30", schedule)).toBe(true);
    expect(intervalConflicts("2027-01-15", "10:15", "11:00", schedule)).toBe(true);
    expect(intervalConflicts("2027-01-15", "10:30", "11:00", schedule)).toBe(false);
  });

  it("requires the proposed booking's refueling time before an existing booking", () => {
    expect(intervalConflicts("2027-01-15", "08:00", "08:30", schedule)).toBe(false);
    expect(intervalConflicts("2027-01-15", "08:00", "08:31", schedule)).toBe(true);
  });

  it("returns only valid end choices for the selected departure", () => {
    expect(
      validReturnSlots("2027-01-15", "08:00", schedule, ["08:30", "09:00", "10:30"]),
    ).toEqual(["08:30"]);
  });
});
