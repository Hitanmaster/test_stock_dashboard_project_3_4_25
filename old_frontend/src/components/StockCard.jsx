import React from "react";

const StockCard = ({ stock }) => {
  return (
    <div className="bg-gray-100 p-4 rounded-md shadow-md mb-4">
      <h2 className="text-xl font-bold">{stock.symbol}</h2>
      <p>Name: {stock.name}</p>
      <p>Price: {stock.price}</p>
    </div>
  );
};

export default StockCard;
