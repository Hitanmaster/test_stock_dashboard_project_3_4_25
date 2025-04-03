const BASE_URL = "http://127.0.0.1:5000"; // Replace with your backend URL

export const fetchStockData = async (symbol) => {
  try {
    const response = await fetch(`${BASE_URL}/api/stock/${symbol}`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error("Error fetching stock data:", error);
    throw error;
  }
};

export const fetchStockList = async () => {
  try {
    const response = await fetch(`${BASE_URL}/api/stock/list`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error("Error fetching stock list:", error);
    throw error;
  }
};
