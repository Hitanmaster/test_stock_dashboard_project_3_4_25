import React, { useState } from "react";

const SearchBar = ({ onSearch, stockList }) => {
  const [searchTerm, setSearchTerm] = useState("");

  const handleChange = (event) => {
    setSearchTerm(event.target.value);
  };

  const handleSubmit = (event) => {
    event.preventDefault();
    if (stockList.includes(searchTerm.toUpperCase())) {
      onSearch(searchTerm.toUpperCase());
    } else {
      alert("Stock not found in the list.");
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex">
      <input
        type="text"
        placeholder="Search for a stock (e.g., AAPL)"
        value={searchTerm}
        onChange={handleChange}
        className="border border-gray-300 px-4 py-2 flex-grow"
      />
      <button
        type="submit"
        className="bg-blue-500 text-white px-4 py-2 ml-2"
      >
        Search
      </button>
    </form>
  );
};

export default SearchBar;
