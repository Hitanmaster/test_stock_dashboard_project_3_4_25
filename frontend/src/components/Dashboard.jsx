import React, { useState, useEffect } from "react";
import SearchBar from "./SearchBar";
import StockCard from "./StockCard";
import ChartComponent from "./ChartComponent";
import Loading from "./Loading";
import { fetchStockData, fetchStockList } from "../utils/api";

const Dashboard = () => {
  const [stockData, setStockData] = useState(null);
  const [stockList, setStockList] = useState([]);
  const [selectedStock, setSelectedStock] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    const loadStockList = async () => {
      try {
        setLoading(true);
        const list = await fetchStockList();
        setStockList(list);
      } catch (err) {
        setError(err.message || "Failed to load stock list.");
      } finally {
        setLoading(false);
      }
    };
    loadStockList();
  }, []);

  const handleSearch = async (symbol) => {
    setSelectedStock(symbol);
    setStockData(null);
    setError(null);
    setLoading(true);
    try {
      const data = await fetchStockData(symbol);
      setStockData(data);
    } catch (err) {
      setError(err.message || "Failed to load stock data.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-4">
      <SearchBar onSearch={handleSearch} stockList={stockList} />
      {loading && <Loading />}
      {error && <div className="text-red-500">{error}</div>}
      {stockData && (
        <div className="mt-4">
          <StockCard stock={stockData.stock} />
          <ChartComponent data={stockData.data} />
        </div>
      )}
    </div>
  );
};

export default Dashboard;
