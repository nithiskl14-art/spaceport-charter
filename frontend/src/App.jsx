import { useEffect, useMemo, useState } from "react";

import {
  createBooking,
  getBookings,
  getBookingSummary,
  getShips,
  getUnavailable,
} from "./api";
import { intervalConflicts, validReturnSlots } from "./availability";
import spaceportMark from "./assets/spaceport-mark.svg";
import {
  formatCentral,
  isElapsedStart,
  minutesInCentral,
  slots,
  todayInCentral,
  toIso,
} from "./time";

const OPERATING_START_MINUTES = 6 * 60;
const OPERATING_LENGTH_MINUTES = 16 * 60;

function pageFromHash() {
  return window.location.hash === "#fleet" ? "fleet" : "charter";
}

function Header({ page, onNavigate }) {
  return (
    <header>
      <div className="brand">
        <img className="brand-mark" src={spaceportMark} alt="" />
        <div>
          <strong>PACIFIC</strong>
          <small>SPACEPORT</small>
        </div>
      </div>

      <nav aria-label="Primary navigation">
        <button
          className={page === "charter" ? "active" : ""}
          onClick={() => onNavigate("charter")}
        >
          Charter a ship
        </button>

        <button
          className={page === "fleet" ? "active" : ""}
          onClick={() => onNavigate("fleet")}
        >
          Fleet manager
        </button>
      </nav>
    </header>
  );
}

function Availability({ schedule }) {
  if (!schedule) {
    return <span>Loading flight schedule…</span>;
  }

  if (!schedule.unavailable.length) {
    return <span>Clear skies — all windows available</span>;
  }

  return schedule.unavailable.map((period) => (
    <span key={period.startTime}>
      {formatCentral(period.startTime)} — {formatCentral(period.endTime)}
    </span>
  ));
}

function Charter({ ships }) {
  const [shipId, setShipId] = useState("");
  const [date, setDate] = useState(todayInCentral());
  const [pilotName, setPilotName] = useState("");
  const [start, setStart] = useState("09:00");
  const [end, setEnd] = useState("10:00");
  const [schedule, setSchedule] = useState(null);
  const [message, setMessage] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!shipId && ships.length) {
      setShipId(String(ships[0].id));
    }
  }, [ships, shipId]);

  useEffect(() => {
    if (!shipId || !date) {
      return undefined;
    }

    let active = true;
    setSchedule(null);

    getUnavailable(shipId, date)
      .then((data) => {
        if (active) {
          setSchedule(data);
        }
      })
      .catch((error) => {
        if (active) {
          setMessage({
            type: "error",
            text: error.message,
          });
        }
      });

    return () => {
      active = false;
    };
  }, [shipId, date]);

  useEffect(() => {
    setMessage(null);
  }, [shipId, date, start, end]);

  const departureSlots = useMemo(
    () =>
      slots
        .slice(0, -1)
        .filter((time) => !isElapsedStart(date, time)),
    [date],
  );

  const selectableDepartureSlots = useMemo(
    () =>
      departureSlots.filter(
        (departure) =>
          validReturnSlots(
            date,
            departure,
            schedule,
            slots.slice(1),
          ).length > 0,
      ),
    [date, departureSlots, schedule],
  );

  const enabledReturnSlots = useMemo(
    () =>
      validReturnSlots(
        date,
        start,
        schedule,
        slots.slice(1),
      ),
    [date, schedule, start],
  );

  useEffect(() => {
    if (selectableDepartureSlots.includes(start)) {
      return;
    }

    const nextStart = selectableDepartureSlots[0] || "";
    setStart(nextStart);
  }, [selectableDepartureSlots, start]);

  useEffect(() => {
    if (enabledReturnSlots.includes(end)) {
      return;
    }

    setEnd(enabledReturnSlots[0] || "");
  }, [enabledReturnSlots, end]);

  const selectedShip = ships.find(
    (ship) => String(ship.id) === shipId,
  );

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setMessage(null);

    try {
      if (end <= start) {
        throw new Error("End time must be after start time");
      }

      if (intervalConflicts(date, start, end, schedule)) {
        throw new Error(
          "Select a time outside the unavailable windows",
        );
      }

      const booking = await createBooking({
        shipId: Number(shipId),
        pilotName,
        startTime: toIso(date, start),
        endTime: toIso(date, end),
      });

      setMessage({
        type: "success",
        text: `Confirmed! ${booking.shipName} is reserved for ${pilotName}.`,
      });

      setPilotName("");
      setSchedule(await getUnavailable(shipId, date));
    } catch (error) {
      setMessage({
        type: "error",
        text: error.message,
      });
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="charter-grid">
      <section className="intro">
        <p className="eyebrow">
          <span /> PRIVATE CHARTER SERVICE
        </p>

        <h1>
          Your next mission
          <br />
          <em>starts here.</em>
        </h1>

        <p>
          Choose a ship and an available time. The system handles
          scheduling conflicts and required refueling time.
        </p>

        <div className="facts">
          <span>
            OPEN DAILY
            <br />
            <b>6:00 AM — 10:00 PM CT</b>
          </span>

          <span>
            TURNAROUND
            <br />
            <b>30 MINUTES</b>
          </span>
        </div>
      </section>

      <section className="panel">
        <div className="step">
          <span>CHARTER DETAILS</span>
        </div>

        <form onSubmit={submit}>
          <label>
            Vessel
            <select
              value={shipId}
              disabled={!ships.length}
              onChange={(event) =>
                setShipId(event.target.value)
              }
            >
              {ships.length ? (
                ships.map((ship) => (
                  <option
                    key={ship.id}
                    value={ship.id}
                  >
                    {ship.name}
                  </option>
                ))
              ) : (
                <option>Loading fleet…</option>
              )}
            </select>
          </label>

          <label>
            Mission date
            <input
              type="date"
              min={todayInCentral()}
              value={date}
              onChange={(event) =>
                setDate(event.target.value)
              }
              required
            />
          </label>

          <div className="two">
            <label>
              Departure
              <select
                value={start}
                disabled={!selectableDepartureSlots.length}
                onChange={(event) =>
                  setStart(event.target.value)
                }
              >
                {departureSlots.length ? (
                  departureSlots.map((time) => {
                    const unavailable =
                      !selectableDepartureSlots.includes(time);

                    return (
                      <option
                        key={time}
                        value={time}
                        disabled={unavailable}
                      >
                        {unavailable
                          ? `${time} — Unavailable`
                          : time}
                      </option>
                    );
                  })
                ) : (
                  <option value="">
                    No remaining times
                  </option>
                )}
              </select>
            </label>

            <label>
              Return
              <select
                value={end}
                disabled={
                  !start || !enabledReturnSlots.length
                }
                onChange={(event) =>
                  setEnd(event.target.value)
                }
              >
                {slots
                  .slice(1)
                  .filter((time) => time > start)
                  .map((time) => {
                    const unavailable =
                      !enabledReturnSlots.includes(time);

                    return (
                      <option
                        key={time}
                        value={time}
                        disabled={unavailable}
                      >
                        {unavailable
                          ? `${time} — Unavailable`
                          : time}
                      </option>
                    );
                  })}
              </select>
            </label>
          </div>

          <p className="time-help">
            Grayed-out times conflict with another reservation or
            the required refueling period.
          </p>

          <label>
            Pilot name
            <input
              value={pilotName}
              maxLength="100"
              onChange={(event) =>
                setPilotName(event.target.value)
              }
              placeholder="Enter pilot name"
              required
            />
          </label>

          <div className="availability">
            <b>Unavailable windows</b>
            <Availability schedule={schedule} />
          </div>

          {message && (
            <div
              role="alert"
              className={`notice ${message.type}`}
            >
              {message.text}
            </div>
          )}

          <button
            className="primary"
            disabled={
              busy || !shipId || !start || !end
            }
          >
            {busy
              ? "Reserving…"
              : `Reserve ${
                  selectedShip?.name || "ship"
                } →`}
          </button>
        </form>
      </section>
    </main>
  );
}

function Timeline({ bookings }) {
  return (
    <div
      className="timeline"
      aria-label="Daily schedule from 6 AM to 10 PM"
    >
      <div className="timeline-grid" />

      {bookings.map((booking) => {
        const start = minutesInCentral(
          booking.startTime,
        );
        const end = minutesInCentral(
          booking.endTime,
        );

        const left =
          ((start - OPERATING_START_MINUTES) /
            OPERATING_LENGTH_MINUTES) *
          100;

        const width =
          ((end - start) /
            OPERATING_LENGTH_MINUTES) *
          100;

        return (
          <div
            className="timeline-block"
            key={booking.id}
            style={{
              left: `${left}%`,
              width: `${width}%`,
            }}
            title={`${booking.pilotName}: ${formatCentral(
              booking.startTime,
            )}–${formatCentral(booking.endTime)}`}
          />
        );
      })}

      <div className="timeline-labels">
        <span>06</span>
        <span>10</span>
        <span>14</span>
        <span>18</span>
        <span>22</span>
      </div>
    </div>
  );
}

function Fleet({ ships }) {
  const [date, setDate] = useState("");
  const [bookings, setBookings] = useState([]);
  const [totalRecords, setTotalRecords] =
    useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [
    showingLatestFallback,
    setShowingLatestFallback,
  ] = useState(false);

  useEffect(() => {
    let active = true;

    getBookingSummary()
      .then((summary) => {
        if (!active) {
          return;
        }

        setTotalRecords(summary.totalRecords);

        const today = todayInCentral();

        if (
          summary.todayCount > 0 ||
          !summary.latestBookingDate
        ) {
          setDate(today);
          setShowingLatestFallback(false);
        } else {
          setDate(summary.latestBookingDate);
          setShowingLatestFallback(true);
        }
      })
      .catch((requestError) => {
        if (active) {
          setError(requestError.message);
          setLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!date) {
      return undefined;
    }

    let active = true;

    setLoading(true);
    setError("");

    getBookings(date, date)
      .then((data) => {
        if (active) {
          setBookings(data);
        }
      })
      .catch((requestError) => {
        if (active) {
          setError(requestError.message);
        }
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [date]);

  const visibleBookings = bookings;

  const activeShips = new Set(
    visibleBookings.map(
      (booking) => booking.shipId,
    ),
  ).size;

  const formattedDate = date
    ? new Intl.DateTimeFormat("en-US", {
        month: "long",
        day: "numeric",
        year: "numeric",
        timeZone: "UTC",
      }).format(
        new Date(`${date}T12:00:00Z`),
      )
    : "";

  function selectDate(nextDate) {
    setDate(nextDate);
    setShowingLatestFallback(false);
  }

  return (
    <main className="fleet">
      <div className="fleet-title">
        <div>
          <p className="eyebrow">
            <span /> OPERATIONS CONTROL
          </p>

          <h1>Fleet manifest</h1>

          <p className="fleet-subtitle">
            Review bookings across the fleet by mission date.
          </p>
        </div>

        <div className="fleet-date-controls">
          <label>
            Mission date
            <input
              type="date"
              value={date}
              onChange={(event) =>
                selectDate(event.target.value)
              }
            />
          </label>
        </div>
      </div>

      {showingLatestFallback && (
        <div
          className="notice fallback-notice"
          role="status"
        >
          No missions scheduled today. Showing the latest
          activity from{" "}
          <strong>{formattedDate}</strong>.
        </div>
      )}

      <div className="fleet-stats">
        <div>
          <b>{totalRecords.toLocaleString()}</b>
          <span>Total records</span>
        </div>

        <div>
          <b>{visibleBookings.length}</b>
          <span>Missions this day</span>
        </div>

        <div>
          <b>
            {activeShips} / {ships.length}
          </b>
          <span>Vessels active</span>
        </div>

        <div>
          <b>CT</b>
          <span>Schedule timezone</span>
        </div>
      </div>

      {loading && (
        <div className="loading-state">
          Loading fleet history…
        </div>
      )}

      {error && (
        <div className="notice error">
          {error}
        </div>
      )}

      {!loading && !error && (
        <div className="ship-list">
          {ships.map((ship) => {
            const rows =
              visibleBookings.filter(
                (booking) =>
                  booking.shipId === ship.id,
              );

            return (
              <section
                className="ship-card"
                key={ship.id}
              >
                <div className="ship-head">
                  <span>0{ship.id}</span>
                  <h2>{ship.name}</h2>
                  <b>
                    {rows.length} mission
                    {rows.length === 1
                      ? ""
                      : "s"}
                  </b>
                </div>

                <Timeline bookings={rows} />

                {rows.length ? (
                  <>
                    <div
                      className="booking-columns"
                      aria-hidden="true"
                    >
                      <span>Time</span>
                      <span>Pilot name</span>
                      <span>Status</span>
                    </div>

                    {rows.map((booking) => (
                      <div
                        className="booking"
                        key={booking.id}
                      >
                        <time>
                          {formatCentral(
                            booking.startTime,
                          )}
                          <i>→</i>
                          {formatCentral(
                            booking.endTime,
                          )}
                        </time>

                        <strong>
                          {booking.pilotName}
                        </strong>

                        <span>CONFIRMED</span>
                      </div>
                    ))}
                  </>
                ) : (
                  <div className="empty">
                    No missions scheduled. Vessel ready.
                  </div>
                )}
              </section>
            );
          })}
        </div>
      )}
    </main>
  );
}

export default function App() {
  const [page, setPage] =
    useState(pageFromHash);
  const [ships, setShips] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    getShips()
      .then((data) => {
        if (!Array.isArray(data)) {
          throw new Error(
            "The fleet response was not a list",
          );
        }

        setShips(data);
      })
      .catch((requestError) => {
        setError(requestError.message);
      });
  }, []);

  useEffect(() => {
    if (!window.location.hash) {
      window.history.replaceState(
        null,
        "",
        "#charter",
      );
    }

    const syncPageWithUrl = () => {
      setPage(pageFromHash());
    };

    window.addEventListener(
      "hashchange",
      syncPageWithUrl,
    );

    return () => {
      window.removeEventListener(
        "hashchange",
        syncPageWithUrl,
      );
    };
  }, []);

  function navigate(pageName) {
    window.location.hash = pageName;
  }

  return (
    <>
      <Header
        page={page}
        onNavigate={navigate}
      />

      {error ? (
        <main>
          <div className="notice error">
            Unable to load fleet: {error}
          </div>
        </main>
      ) : page === "charter" ? (
        <Charter ships={ships} />
      ) : (
        <Fleet ships={ships} />
      )}

      <footer>
        PACIFIC SPACEPORT · CENTRAL TIME OPERATIONS
      </footer>
    </>
  );
}