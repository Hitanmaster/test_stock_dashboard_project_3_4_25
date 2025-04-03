import yfinance as yf

ticker = yf.Ticker("AAPL")
data = ticker.history(period="1d")

if data.empty:
    print("No data found for AAPL.")
else:
    print(data)
