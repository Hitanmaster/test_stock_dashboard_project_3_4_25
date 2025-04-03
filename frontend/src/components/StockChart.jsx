import React, { useRef, useEffect } from "react";
import { Chart, LineController, LineElement, PointElement, LinearScale, TimeScale, Title, Tooltip, Legend, Filler } from "chart.js";
import "chartjs-adapter-date-fns";

Chart.register(LineController, LineElement, PointElement, LinearScale, TimeScale, Title, Tooltip, Legend, Filler);

function StockChart({ historyData, ticker, interval }) {
  const chartRef = useRef(null);
  const chartInstanceRef = useRef(null);

  useEffect(() => {
    if (!chartRef.current) return;
    const ctx = chartRef.current.getContext("2d");
    if (!ctx) return;

    const sortedData = historyData?.sort((a, b) => new Date(a.Date) - new Date(b.Date));
    const chartData = {
      labels: sortedData.map(record => new Date(record.Date)),
      datasets: [{
        label: `Close Price (${ticker}) - ${interval}`,
        data: sortedData.map(record => Number(record.Close) || null),
        borderColor: "rgb(54, 162, 235)",
        backgroundColor: "rgba(54, 162, 235, 0.1)",
        tension: 0.1,
        fill: true,
        pointRadius: 1,
        pointHoverRadius: 5
      }]
    };

    if (chartInstanceRef.current) chartInstanceRef.current.destroy();
    chartInstanceRef.current = new Chart(ctx, {
      type: "line",
      data: chartData,
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { position: "top" }, title: { display: true, text: `${ticker} Price History (${interval})` } },
        scales: { x: { type: "time", time: { unit: "minute" } }, y: { title: { display: true, text: "Price (USD)" } } }
      }
    });

    return () => { if (chartInstanceRef.current) chartInstanceRef.current.destroy(); };
  }, [historyData, ticker, interval]);

  return <div className="relative h-96 w-full p-4 bg-white rounded-lg shadow"><canvas ref={chartRef}></canvas></div>;
}

export default StockChart;
