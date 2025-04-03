const API_BASE_URL = "http://localhost:5000";

export async function fetchStockDataApi(ticker, period, interval) {
  const upperTicker = ticker.trim().toUpperCase();
  if (!upperTicker) throw new Error("Ticker symbol is required.");
  const params = new URLSearchParams({ period, interval });
  const apiUrl = `${API_BASE_URL}/api/stockdata/${upperTicker}?${params}`;

  console.log(`Fetching data from: ${apiUrl}`);
  const response = await fetch(apiUrl);
  if (!response.ok) throw new Error(`API Error (${response.status}): ${response.statusText}`);

  const data = await response.json();
  if (!data || !Array.isArray(data.history)) throw new Error("Invalid data format received from API.");

  return data;
}
