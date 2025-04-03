# --- Imports ---
import os
import yfinance as yf
from dotenv import load_dotenv
from flask import Flask, jsonify, Response, request
from flask_cors import CORS
import pandas as pd
import logging
from datetime import datetime, timedelta
import sys
from yfinance.exceptions import YFDataException
import numpy as np # Import numpy for checking numeric types

# --- Load Environment Variables ---
load_dotenv()

FRONTEND_PORT = os.getenv("FRONTEND_PORT")
BACKEND_PORT = os.getenv("BACKEND_PORT")

# --- Validate Environment Variables ---
if not FRONTEND_PORT:
    raise ValueError("FRONTEND_PORT environment variable not set.")
if not BACKEND_PORT:
    raise ValueError("BACKEND_PORT environment variable not set.")

# --- Version Check ---
if sys.version_info < (3, 7):
    print("Warning: This application is designed for Python 3.7+. You are using an older version.", file=sys.stderr)

# --- Flask App Setup ---
app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- CORS Configuration ---
FRONTEND_ORIGIN = f"http://localhost:{FRONTEND_PORT}"
CORS(app, resources={r"/api/*": {"origins": FRONTEND_ORIGIN}})
logging.info(f"CORS enabled for origin: {FRONTEND_ORIGIN}")

# --- Helper Functions ---
def safe_convert(value):
    """
    Safely converts values to JSON serializable types.
    Handles lists, tuples, pd.NA, np.nan, large numbers, numpy types, and array-like structures.
    """
    # --- >>> START OF REVISED FIX (v4) <<< ---
    # 1. Handle Python list/tuple types first
    if isinstance(value, (list, tuple)):
        # Recursively apply safe_convert to each item in the list/tuple
        return [safe_convert(item) for item in value]
    # 2. Handle NumPy arrays / Pandas Series next
    elif isinstance(value, (np.ndarray, pd.Series)):
        # Convert array/series to list and apply safe_convert recursively
        return [safe_convert(item) for item in value.tolist()]
    # --- >>> END OF REVISED FIX (v4) <<< ---

    # 3. Handle specific Pandas/Numpy scalars AFTER handling list-like types
    elif pd.isna(value) or value is pd.NA: # Should now be safe
        return None
    elif isinstance(value, (np.int64, np.int32, np.int16, np.int8)):
        # Ensure large numpy ints are handled if they exceed Python's limits for JSON (though less common)
        try:
            return int(value)
        except OverflowError:
            logging.warning(f"Large numpy integer detected (overflow): {value}, converting to None.")
            return None
    elif isinstance(value, (np.float64, np.float32, np.float16)):
        if np.isinf(value) or np.isnan(value): # Check for Inf/NaN floats
             return None
        return float(value)
    elif isinstance(value, (np.bool_)):
        return bool(value)

    # 4. Handle potentially large standard Python numbers
    elif isinstance(value, int) and abs(value) > 1e18: # Arbitrary threshold
         logging.warning(f"Large integer detected: {value}, converting to None.")
         return None

    # 5. Handle datetime objects (convert to ISO string)
    elif isinstance(value, (datetime, pd.Timestamp)):
         try:
             # Convert timezone-aware to naive UTC before formatting
             offset = value.utcoffset()
             if offset is not None:
                 # Create offset-naive UTC datetime
                 value_utc_naive = value.replace(tzinfo=None) - offset
             else:
                 # Assume naive datetime is already UTC (or handle as local if needed)
                 value_utc_naive = value

             # Format as ISO 8601 with 'Z' for UTC
             return value_utc_naive.strftime('%Y-%m-%dT%H:%M:%SZ')
         except Exception as dt_err:
             logging.warning(f"Could not convert datetime object {value} to string: {dt_err}")
             return None # Fallback if conversion fails

    # 6. Return value as is if none of the above conditions match (e.g., str, bool, simple float/int)
    return value

def get_stock_data(ticker_symbol):
    """
    Fetches stock information and historical data for a given ticker symbol using yfinance.
    Cleans the data for JSON serialization.
    """
    logging.info(f"Attempting to fetch data for ticker: {ticker_symbol}")
    try:
        ticker = yf.Ticker(ticker_symbol)

        # --- Fetch Ticker Info ---
        # Use download first for a quick check if the ticker likely exists and has recent data
        quick_hist = ticker.history(period="5d", interval="1d")
        info = {} # Initialize info dictionary

        # Attempt to fetch info regardless, but log warnings if quick_hist failed
        if quick_hist.empty:
            logging.warning(f"No recent history found for ticker '{ticker_symbol}' via quick check. Attempting to fetch info directly.")

        try:
            info = ticker.info
            # Basic check if info seems valid (e.g., contains a price)
            if not info or (info.get('regularMarketPrice') is None and info.get('currentPrice') is None and info.get('symbol') is None):
                logging.warning(f"Fetched info for '{ticker_symbol}' seems incomplete or lacks essential data. It might be invalid/delisted.")
                # Decide if you want to proceed even with potentially bad info, or clear it
                # info = {} # Option: Clear info if it seems invalid
        except Exception as info_err:
            logging.error(f"Failed to fetch .info for {ticker_symbol}: {info_err}. Proceeding without info.")
            info = {} # Ensure info is an empty dict if fetch fails

        # --- Clean Ticker Info ---
        cleaned_info = {}
        if info: # Process info only if it's not empty
            logging.debug(f"Raw info keys for {ticker_symbol}: {list(info.keys())}") # Add debug log
            for key, value in info.items():
                try:
                    # Apply safe conversion to each value
                    cleaned_info[key] = safe_convert(value) # Uses the fixed safe_convert
                except Exception as convert_err:
                    # Log error during conversion of a specific key
                    logging.error(f"Error converting info key '{key}' for {ticker_symbol}: {convert_err}", exc_info=True)
                    cleaned_info[key] = None # Set to None if conversion fails for a specific key
        else:
             logging.warning(f"No 'info' data available or fetched for ticker {ticker_symbol}")


        # --- Fetch Historical Data ---
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365) # Fetch one year
        history_df = pd.DataFrame() # Initialize empty DataFrame
        try:
            history_df = ticker.history(start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'))
        except Exception as hist_err:
            logging.error(f"Failed to fetch history for {ticker_symbol}: {hist_err}")
            # Continue without history data

        history_list = []
        if history_df.empty:
            logging.warning(f"No historical data found for ticker '{ticker_symbol}' in the specified date range (or fetch failed).")
        else:
            history_df.reset_index(inplace=True)
            if 'Date' in history_df.columns:
                 # Ensure Date is datetime before formatting
                 history_df['Date'] = pd.to_datetime(history_df['Date'], errors='coerce')
                 # Format valid dates, leave NaT as is (will become None later)
                 history_df['Date_str'] = history_df['Date'].dt.strftime('%Y-%m-%dT%H:%M:%SZ')
                 # Use the string version, keep original Date if needed elsewhere
                 history_df['Date'] = history_df['Date_str']
                 history_df.drop(columns=['Date_str'], inplace=True)
            else:
                 logging.warning(" 'Date' column not found in historical data after reset_index.")

            # Replace pd.NA/np.nan/NaT with None before converting to dict
            # Convert entire DataFrame to objects first to ensure replace works broadly
            history_df = history_df.astype(object).replace({pd.NA: None, np.nan: None, pd.NaT: None})

            history_list = history_df.to_dict('records')
            # Apply safe_convert to history records as well for consistency
            cleaned_history_list = []
            for record in history_list:
                cleaned_record = {}
                for k, v in record.items():
                    try:
                        cleaned_record[k] = safe_convert(v)
                    except Exception as convert_hist_err:
                        logging.error(f"Error converting history key '{k}' for {ticker_symbol}: {convert_hist_err}")
                        cleaned_record[k] = None # Fallback for history conversion error
                cleaned_history_list.append(cleaned_record)
            history_list = cleaned_history_list


        # --- Combine and Return ---
        # Return None only if both info and history are empty/failed
        if not cleaned_info and not history_list:
             logging.warning(f"No data (info or history) could be compiled for {ticker_symbol}.")
             return None

        return {"info": cleaned_info, "history": history_list}

    except YFDataException as e:
        # Handle yfinance specific data errors (like 404s)
        logging.error(f"YFinance data exception for {ticker_symbol}: {e}", exc_info=False) # Less verbose log
        return None
    except Exception as e:
        # Catch any other unexpected errors during the main process
        logging.error(f"Unexpected error during get_stock_data for {ticker_symbol}: {e}", exc_info=True)
        return None

# --- API Route ---
@app.route('/api/stockdata/<ticker_symbol>', methods=['GET'])
def stock_data_endpoint(ticker_symbol):
    """ API endpoint to get stock data. """
    sanitized_ticker = ticker_symbol.strip().upper()
    if not sanitized_ticker:
        logging.warning("API call received without a valid ticker symbol.")
        return jsonify({"error": "Ticker symbol is required"}), 400

    logging.info(f"API request received for ticker: {sanitized_ticker}")
    data = get_stock_data(sanitized_ticker)

    if data:
        try:
            # Attempt to jsonify the cleaned data
            response = jsonify(data)
            return response
        except Exception as json_error:
            # This error should be much rarer now after safe_convert
            logging.error(f"FATAL: Error serializing final data for {sanitized_ticker} to JSON: {json_error}", exc_info=True)
            # Log the problematic data structure if possible (be careful with large data)
            # logging.debug(f"Data structure causing serialization error: {data}")
            return jsonify({"error": "Internal server error during final data serialization"}), 500
    else:
        # If get_stock_data returned None
        logging.warning(f"Failed to fetch or process data for ticker: {sanitized_ticker}. Returning 404.")
        return jsonify({"error": f"No data found or error processing for ticker symbol: {sanitized_ticker}"}), 404

# --- Health Check Route ---
@app.route('/health', methods=['GET'])
def health_check():
    """ Basic health check endpoint """
    return jsonify({"status": "ok"}), 200

# --- Run the App ---
if __name__ == '__main__':
    port = int(BACKEND_PORT)
    logging.info(f"Starting Flask server on host 0.0.0.0 port {port}")
    # Set debug=False for production
    app.run(host='0.0.0.0', port=port, debug=True)
