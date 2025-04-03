# --- Imports ---
import yfinance as yf
from dotenv import load_dotenv
from flask import Flask, jsonify, Response, request
from flask_cors import CORS # Import CORS
import pandas as pd
import logging
from datetime import datetime, timedelta
import sys # To check Python version

load_dotenv()

FRONTEND_PORT = os.getenv("FRONTEND_PORT")
BACKEND_PORT = os.getenv("BACKEND_PORT")

if not FRONTEND_PORT or not BACKEND_PORT:
    raise ValueError("FRONTEND_PORT or BACKEND_PORT environment variables not set.")


# --- Version Check ---
# yfinance often requires newer Python versions
if sys.version_info < (3, 7):
    print("Warning: This application is designed for Python 3.7+. You are using an older version.", file=sys.stderr)

# --- Flask App Setup ---
app = Flask(__name__)

# Configure logging
# Log to stdout for easier container/cloud deployment logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Enable CORS - Allow requests from typical React dev server port
# Use environment variable for frontend URL in production, fallback for dev
FRONTEND_ORIGIN = f"http://localhost:{FRONTEND_PORT}" # Get port from script variable
CORS(app, resources={r"/api/*": {"origins": FRONTEND_ORIGIN}})
logging.info(f"CORS enabled for origin: {FRONTEND_ORIGIN}")

# --- Helper Functions ---
def get_stock_data(ticker_symbol):
    """
    Fetches stock information and 1-year historical data for a given ticker symbol.

    Args:
        ticker_symbol (str): The stock ticker symbol (e.g., 'AAPL').

    Returns:
        dict: A dictionary containing 'info' and 'history' data,
              or None if the ticker is invalid or data fetching fails.
    """
    logging.info(f"Attempting to fetch data for ticker: {ticker_symbol}")
    try:
        # Create Ticker object
        ticker = yf.Ticker(ticker_symbol)

        # 1. Get Stock Info
        # Use history() first to check if ticker is valid, as .info can sometimes
        # return partial data for invalid tickers before eventually erroring.
        # Fetching 1 day is usually enough to validate.
        quick_hist = ticker.history(period="1d")
        if quick_hist.empty:
            logging.warning(f"Ticker '{ticker_symbol}' may be invalid or has no recent data (history check failed).")
            # Attempt .info anyway, but be prepared for it to be empty/fail
            info = ticker.info
            if not info or info.get('regularMarketPrice') is None:
                 logging.warning(f"No valid info found for ticker: {ticker_symbol}")
                 return None # Definitely invalid or no data
        else:
            # If history check passed, proceed to get full info
            info = ticker.info

        # Check for essential data points in info
        if not info or info.get('regularMarketPrice') is None:
            logging.warning(f"Could not find essential market data in 'info' for ticker: {ticker_symbol}")
            # Allow proceeding if history might be available, but log warning
            # return None # Stricter check: uncomment to require valid info

        # 2. Get Historical Data (Past Year)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)
        history = ticker.history(start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'))

        if history.empty:
            logging.warning(f"No historical data found for ticker '{ticker_symbol}' in the last year.")
            # Decide if this is an error or just missing data
            # If info exists, we might still return it
            history_list = []
        else:
            # --- Data Cleaning and Formatting ---
            # a. Reset index to make 'Date' a column
            history.reset_index(inplace=True)

            # b. Convert Timestamp objects to ISO format strings for JSON
            #    Handle potential NaT (Not a Time) values
            history['Date'] = history['Date'].dt.strftime('%Y-%m-%dT%H:%M:%SZ').fillna('N/A')

            # c. Handle potential NaN/Infinity values in numeric columns
            numeric_cols = history.select_dtypes(include=['number']).columns
            # Replace NaN with None (which becomes 'null' in JSON)
            history[numeric_cols] = history[numeric_cols].fillna(value=pd.NA)
            # Convert pandas NA back to None for JSON serialization compatibility if needed,
            # although pd.io.json.dumps often handles it.
            history = history.where(pd.notnull(history), None)

            # d. Convert history DataFrame to list of dictionaries
            history_list = history.to_dict('records')

        # 3. Clean info dictionary
        cleaned_info = {}
        if info: # Only clean if info was retrieved
            for key, value in info.items():
                if pd.isna(value):
                    cleaned_info[key] = None # Convert NaN/NaT to None for JSON null
                # Check for excessively large numbers that might break JSON
                elif isinstance(value, (int, float)) and (abs(value) > 1e18):
                    logging.warning(f"Found potentially problematic large number for key '{key}' in ticker '{ticker_symbol}'. Setting to None.")
                    cleaned_info[key] = None
                else:
                    cleaned_info[key] = value
        else:
             # If info failed but history might exist (less common)
             logging.warning(f"Proceeding without 'info' data for ticker {ticker_symbol}")


        # Return combined data (info might be empty dict if it failed)
        return {
            "info": cleaned_info,
            "history": history_list
        }

    except Exception as e:
        # Log the full error traceback for debugging
        logging.error(f"Error fetching or processing data for {ticker_symbol}: {e}", exc_info=True)
        return None # Indicate failure

# --- API Route ---
@app.route('/api/stockdata/<ticker_symbol>', methods=['GET'])
def stock_data_endpoint(ticker_symbol):
    """
    API endpoint to get stock data (info and history) for a specific ticker.
    """
    # Sanitize input slightly (though yfinance handles most cases)
    sanitized_ticker = ticker_symbol.strip().upper()

    if not sanitized_ticker:
        logging.warning("API call received without a valid ticker symbol.")
        return jsonify({"error": "Ticker symbol is required"}), 400

    logging.info(f"API request received for ticker: {sanitized_ticker}")
    data = get_stock_data(sanitized_ticker)

    if data:
        # Check if essential data is present (e.g., at least history or some info)
        if not data.get("info") and not data.get("history"):
             logging.warning(f"No data (info or history) could be retrieved for ticker: {sanitized_ticker}")
             return jsonify({"error": f"No data found for ticker symbol: {sanitized_ticker}"}), 404

        logging.info(f"Successfully retrieved data for {sanitized_ticker}")
        try:
            # Use pandas JSON serializer - handles NaNs, Timestamps, etc. well
            # ignore_nan=False ensures NaN becomes null (standard JSON)
            json_response = pd.io.json.dumps(data, default_handler=str, date_format='iso', ignore_nan=False)
            return Response(json_response, mimetype='application/json')
        except Exception as json_error:
             logging.error(f"Error serializing data for {sanitized_ticker} to JSON: {json_error}", exc_info=True)
             return jsonify({"error": "Internal server error during data serialization"}), 500
    else:
        # Failure occurred in get_stock_data (already logged)
        logging.warning(f"Failed to fetch or process data for ticker: {sanitized_ticker}")
        return jsonify({"error": f"Could not retrieve valid data for ticker symbol: {sanitized_ticker}. It might be invalid or API failed."}), 404

# --- Health Check Route ---
@app.route('/health', methods=['GET'])
def health_check():
    """ Basic health check endpoint """
    return jsonify({"status": "ok"}), 200

# --- Run the App ---
if __name__ == '__main__':
    # Use host='0.0.0.0' to make the server accessible on your network
    # Fetch port from script variable
    port = int(BACKEND_PORT)
    logging.info(f"Starting Flask server on host 0.0.0.0 port {port}")
    # Set debug=False for production environments
    app.run(host='0.0.0.0', port=port, debug=True)

