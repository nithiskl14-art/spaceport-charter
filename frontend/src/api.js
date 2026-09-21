const API = import.meta.env.VITE_API_URL || "";

async function request(path, options) {
  const response = await fetch(`${API}${path}`, options);
  const contentType = response.headers.get("content-type") || "";
  if (!contentType.includes("application/json")) {
    throw new Error(
      "The API returned an invalid response. Confirm that the backend is running on port 8000.",
    );
  }
  const body = await response.json();
  if (!response.ok) {
    const detail = body.detail;
    throw new Error(
      typeof detail === "string"
        ? detail
        : detail?.message || "Something went wrong",
    );
  }
  return body;
}

export const getShips = () => request("/api/ships");
export const getUnavailable = (shipId, date) =>
  request(`/api/ships/${shipId}/unavailable?date=${date}`);
export const getBookingSummary = () => request("/api/bookings/summary");
export const getBookings = (start, end) => {
  const params = new URLSearchParams();
  if (start) params.set("startDate", start);
  if (end) params.set("endDate", end);
  const query = params.toString();
  return request(`/api/bookings${query ? `?${query}` : ""}`);
};
export const createBooking = (booking) =>
  request("/api/bookings", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(booking),
  });
