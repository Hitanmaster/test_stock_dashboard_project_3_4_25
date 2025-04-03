import React, { useState, useEffect, useCallback, useRef } from "react";
import { fetchStockDataApi } from "./services/stockApi";
import StockChart from "./components/StockChart";

const DEFAULT_TICKER = "AAPL";
const DEFAULT_INTERVAL = "15m";
const POLLING_INTERVAL_MS = 30000;
const PERIOD_FOR_INTRADAY = "5d";

export default function App() {
  const [ticker, setTicker] = useState(DEFAULT_TICKER);
  const [interval, setInterval] = useState(DEFAULT_INTERVAL);
  const [stockData, setStockData] = useState({ info: null, history: [] });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const pollingTimerRef = useRef(null);

  const fetchData = useCallback(async (currentTicker, currentInterval) => {
    setIsLoading(true);
    setError(null);
    const period = ["1m", "5m", "15m"].includes(currentInterval) ? PERIOD_FOR_INTRADAY : "1y";
    try {
      const data = await fetchStockDataApi(currentTicker, period, currentInterval);
      setStockData(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData(ticker, interval);
    if (pollingTimerRef.current) clearInterval(pollingTimerRef.current);
    pollingTimerRef.current = setInterval(() => fetchData(ticker, interval), POLLING_INTERVAL_MS);
    return () => clearInterval(pollingTimerRef.current);
  }, [ticker, interval, fetchData]);

  return (
    <div className="min-h-screen bg-gray-100 p-4">
      <h1 className="text-3xl font-bold text-center">Stock Price Visualizer</h1>
      <form onSubmit={(e) => e.preventDefault()} className="bg-white p-6 shadow mb-6">
        <input value={ticker} onChange={(e) => setTicker(e.target.value)} placeholder="Stock Ticker" className="border p-2" />
        <select value={interval} onChange={(e) => setInterval(e.target.value)} className="ml-2 border p-2">
          <option value="5m">5m</option>
          <option value="15m">15m</option>
        </select>
      </form>
      {isLoading && <p>Loading...</p>}
      {error && <p className="text-red-500">{error}</p>}
      {!error && stockData.history.length > 0 && <StockChart historyData={stockData.history} ticker={ticker} interval={interval} />}
    </div>
  );
}
