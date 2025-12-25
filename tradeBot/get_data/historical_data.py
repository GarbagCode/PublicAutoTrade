import requests, logging
import pandas as pd
from zoneinfo import ZoneInfo
import matplotlib.pyplot as plt 
from datetime import datetime, timedelta, timezone
from requests.exceptions import Timeout, HTTPError


logger = logging.getLogger(__name__)
def charles_get_candles(
    MARKET_DATA_ACCESS_TOKEN: str,
    symbol: str,
    period_type: str = "day",
    frequency_type: str = "minute",
    period: int = 3,
    frequency: int = 1,
    need_extended_hours_data: bool = False,
) -> pd.DataFrame:
    """
    Fetch Schwab candles → DataFrame with ET DatetimeIndex and numeric OHLCV.
    
    Args:
        MARKET_DATA_ACCESS_TOKEN: Schwab API access token
        symbol: Stock symbol (e.g., 'SOXL')
        period_type: 'day', 'month', 'year', 'ytd'
        period: Number of periods
        frequency_type: 'minute', 'daily', 'weekly', 'monthly'
        frequency: Frequency value
        need_extended_hours_data: Include extended hours
        
    Returns:
        pd.DataFrame: OHLCV data with DatetimeIndex in ET timezone
        
    Raises:
        ValueError: Invalid response format or missing data
        HTTPError: API request failed
        ConnectionError: Network connectivity issues
    """
    logger.info(f"Fetching candles for {symbol} ({frequency}{frequency_type}, {period}{period_type})")
    
    url = "https://api.schwabapi.com/marketdata/v1/pricehistory"
    headers = {"Authorization": f"Bearer {MARKET_DATA_ACCESS_TOKEN}"}
    params = {
        "symbol": symbol,
        "periodType": period_type,
        "period": period,
        "frequencyType": frequency_type,
        "frequency": frequency,
        "needExtendedHoursData": str(need_extended_hours_data).lower(),
    }
    
    logger.debug(f"API request params: {params}")
    
    try:
        # Make API request
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        
    except Timeout as e:
        logger.error(f"Request timeout fetching {symbol} candles (30s)")
        logger.exception(e)
        raise ConnectionError(f"API request timed out for {symbol}") from e
        
    except HTTPError as e:
        if resp.status_code == 401:
            logger.critical(f"Authentication failed for {symbol} - invalid or expired token")
        elif resp.status_code == 403:
            logger.error(f"Access forbidden for {symbol} - check API permissions")
        elif resp.status_code == 404:
            logger.error(f"Symbol {symbol} not found or endpoint invalid")
        elif resp.status_code == 429:
            logger.warning(f"Rate limit exceeded for {symbol} - too many requests")
        else:
            logger.error(f"HTTP {resp.status_code} error fetching {symbol}: {resp.text}")
        
        logger.exception(e)
        raise
        
    except ConnectionError as e:
        logger.error(f"Network connection error fetching {symbol} candles")
        logger.exception(e)
        raise
        
    except RequestException as e:
        logger.error(f"Request error fetching {symbol} candles: {e}")
        logger.exception(e)
        raise
    
    try:
        # Parse JSON response
        data = resp.json()
        
    except ValueError as e:
        logger.error(f"Invalid JSON response for {symbol}")
        logger.debug(f"Response content: {resp.text[:500]}")
        logger.exception(e)
        raise ValueError(f"Failed to parse JSON response for {symbol}") from e
    
    # Validate response structure
    if "candles" not in data:
        logger.error(f"Unexpected response structure for {symbol} (no 'candles' key)")
        logger.debug(f"Response keys: {list(data.keys())}")
        raise ValueError(f"Unexpected response (no 'candles'): {data}")
    
    candles = data["candles"]
    
    # Handle empty candles
    if not candles:
        logger.warning(f"No candle data returned for {symbol}")
        cols = ["symbol", "open", "high", "low", "close", "volume"]
        return pd.DataFrame(columns=cols, index=pd.DatetimeIndex([], tz="America/New_York"))
    
    logger.info(f"Retrieved {len(candles)} candles for {symbol}")
    
    try:
        # Create DataFrame
        df = pd.DataFrame(candles)
        
        # Add symbol column
        df["symbol"] = symbol
        
        # Validate required columns exist
        required_cols = ["datetime", "open", "high", "low", "close", "volume"]
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            logger.error(f"Missing required columns for {symbol}: {missing_cols}")
            logger.debug(f"Available columns: {df.columns.tolist()}")
            raise ValueError(f"Missing required columns: {missing_cols}")
        
        # Ensure numeric types
        for col in ("open", "high", "low", "close", "volume"):
            df[col] = pd.to_numeric(df[col], errors="coerce")
            
            # Check for NaN values after conversion
            nan_count = df[col].isna().sum()
            if nan_count > 0:
                logger.warning(f"{nan_count} NaN values in '{col}' column for {symbol}")
        
        # Convert datetime from epoch ms UTC to tz-aware
        df["datetime"] = pd.to_datetime(df["datetime"], unit="ms", utc=True)
        df.set_index("datetime", inplace=True)
        
        # Convert to ET timezone
        df.index = df.index.tz_convert("America/New_York")
        
        # Reorder columns
        df = df[["symbol", "open", "high", "low", "close", "volume"]]
        
        # Sort by datetime
        df = df.sort_index()
        
        logger.debug(f"DataFrame created: {len(df)} rows, {df.index[0]} to {df.index[-1]}")
        
        return df
        
    except KeyError as e:
        logger.error(f"KeyError processing {symbol} candle data: {e}")
        logger.debug(f"Available columns: {df.columns.tolist() if 'df' in locals() else 'N/A'}")
        logger.exception(e)
        raise ValueError(f"Error processing candle data structure for {symbol}") from e
        
    except Exception as e:
        logger.error(f"Unexpected error processing {symbol} candle data")
        logger.exception(e)
        raise ValueError(f"Failed to process candle data for {symbol}") from e

def twelvedata_get_candles(
    API_KEY: str,
    symbol: str,
    period: int = 1,
    frequency: int = 1,
    need_extended_hours_data: bool = False,
) -> pd.DataFrame:
    """
    Fetch historical intraday data from Twelve Data (1-min resolution by default).

    Parameters
    ----------
    API_KEY : str
        Your Twelve Data API key.
    symbol : str
        The ticker symbol (e.g., 'SPXL').
    period : int
        How many days of data to fetch (default 1).
    frequency : int
        Timeframe in minutes (default 1).
    need_extended_hours_data : bool
        If True, include extended-session data (ignored by Twelve Data; it always includes full trading session).

    Returns
    -------
    pd.DataFrame
        Columns: open, high, low, close, volume; index = datetime (America/New_York).
        
    Raises
    ------
    ValueError: Invalid API response, missing data, or invalid parameters
    HTTPError: API request failed
    ConnectionError: Network connectivity issues
    """
    logger.info(f"Fetching Twelve Data candles for {symbol} ({frequency}min, {period} days)")
    
    # Validate inputs
    if not API_KEY:
        logger.error("API_KEY is empty or None")
        raise ValueError("API_KEY cannot be empty")
    
    if not symbol:
        logger.error("Symbol is empty or None")
        raise ValueError("Symbol cannot be empty")
    
    if period <= 0:
        logger.error(f"Invalid period: {period}")
        raise ValueError(f"Period must be positive, got {period}")
    
    if frequency <= 0:
        logger.error(f"Invalid frequency: {frequency}")
        raise ValueError(f"Frequency must be positive, got {frequency}")
    
    try:
        # Calculate time range
        interval = f"{frequency}min"
        now_et = datetime.now(ZoneInfo("America/New_York"))
        start_time = now_et - timedelta(days=period)
        
        logger.debug(f"Time range: {start_time} to {now_et}")
        
    except Exception as e:
        logger.error(f"Error calculating time range for {symbol}")
        logger.exception(e)
        raise ValueError(f"Failed to calculate time range") from e

    # Build API URL
    url = (
        f"https://api.twelvedata.com/time_series"
        f"?symbol={symbol}"
        f"&interval={interval}"
        f"&start_date={start_time.strftime('%Y-%m-%d %H:%M:%S')}"
        f"&end_date={now_et.strftime('%Y-%m-%d %H:%M:%S')}"
        f"&apikey={API_KEY}"
        f"&timezone=America/New_York"
        f"&format=JSON"
    )
    
    logger.debug(f"API URL: {url.replace(API_KEY, '***')}")  # Hide API key in logs
    
    try:
        # Make API request
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
    except Timeout as e:
        logger.error(f"Request timeout fetching {symbol} from Twelve Data (30s)")
        logger.exception(e)
        raise ConnectionError(f"API request timed out for {symbol}") from e
        
    except HTTPError as e:
        if response.status_code == 401:
            logger.critical(f"Authentication failed for {symbol} - invalid API key")
        elif response.status_code == 403:
            logger.error(f"Access forbidden for {symbol} - check API permissions or plan limits")
        elif response.status_code == 404:
            logger.error(f"Symbol {symbol} not found on Twelve Data")
        elif response.status_code == 429:
            logger.warning(f"Rate limit exceeded for {symbol} - too many requests to Twelve Data")
        else:
            logger.error(f"HTTP {response.status_code} error fetching {symbol}: {response.text[:200]}")
        
        logger.exception(e)
        raise
        
    except ConnectionError as e:
        logger.error(f"Network connection error fetching {symbol} from Twelve Data")
        logger.exception(e)
        raise
        
    except RequestException as e:
        logger.error(f"Request error fetching {symbol} from Twelve Data: {e}")
        logger.exception(e)
        raise
    
    try:
        # Parse JSON response
        raw = response.json()
        
    except ValueError as e:
        logger.error(f"Invalid JSON response for {symbol} from Twelve Data")
        logger.debug(f"Response content: {response.text[:500]}")
        logger.exception(e)
        raise ValueError(f"Failed to parse JSON response for {symbol}") from e
    
    # Check for API error messages
    if "status" in raw and raw["status"] == "error":
        error_msg = raw.get("message", "Unknown error")
        logger.error(f"Twelve Data API error for {symbol}: {error_msg}")
        raise ValueError(f"API returned error for {symbol}: {error_msg}")
    
    # Validate response structure
    if "values" not in raw:
        logger.error(f"No 'values' key in response for {symbol}")
        logger.debug(f"Response keys: {list(raw.keys())}")
        logger.debug(f"Response: {raw}")
        raise ValueError(f"No data returned for {symbol}: {raw}")
    
    values = raw["values"]
    
    # Handle empty data
    if not values:
        logger.warning(f"No candle data returned for {symbol} (empty 'values')")
        return pd.DataFrame(
            columns=["open", "high", "low", "close", "volume"],
            index=pd.DatetimeIndex([], tz="America/New_York", name="datetime")
        )
    
    logger.info(f"Retrieved {len(values)} candles for {symbol}")
    
    try:
        # Create DataFrame
        df = pd.DataFrame(values)
        
        # Validate required columns
        required_cols = ["datetime", "open", "high", "low", "close", "volume"]
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            logger.error(f"Missing required columns for {symbol}: {missing_cols}")
            logger.debug(f"Available columns: {df.columns.tolist()}")
            raise ValueError(f"Missing required columns: {missing_cols}")
        
        # Rename columns (already correct, but being explicit)
        df.rename(
            columns={
                "datetime": "datetime",
                "open": "open",
                "high": "high",
                "low": "low",
                "close": "close",
                "volume": "volume",
            },
            inplace=True,
        )
        
        # Convert datetime
        df["datetime"] = pd.to_datetime(df["datetime"], utc=False)
        df = df.set_index("datetime")
        
        # Localize to ET timezone
        try:
            df = df.tz_localize("America/New_York")
        except Exception as e:
            logger.warning(f"Timezone localization issue for {symbol}, attempting fix")
            logger.debug(f"Error: {e}")
            # If already has timezone info, convert instead
            if df.index.tz is not None:
                df = df.tz_convert("America/New_York")
            else:
                raise
        
        # Sort chronologically
        df = df.sort_index()
        
        # Ensure numeric columns
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
            
            # Check for NaN values
            nan_count = df[col].isna().sum()
            if nan_count > 0:
                logger.warning(f"{nan_count} NaN values in '{col}' column for {symbol}")
        
        # Filter to regular trading hours if requested
        if not need_extended_hours_data:
            initial_rows = len(df)
            df = df.between_time("09:30", "16:00")
            filtered_rows = initial_rows - len(df)
            if filtered_rows > 0:
                logger.debug(f"Filtered {filtered_rows} extended hours candles for {symbol}")
        
        # Select final columns
        df = df[["open", "high", "low", "close", "volume"]]
        
        logger.debug(f"DataFrame created: {len(df)} rows, {df.index[0]} to {df.index[-1]}")
        
        if df.empty:
            logger.warning(f"DataFrame is empty after processing for {symbol}")
        
        return df
        
    except KeyError as e:
        logger.error(f"KeyError processing {symbol} candle data: {e}")
        logger.debug(f"Available columns: {df.columns.tolist() if 'df' in locals() else 'N/A'}")
        logger.exception(e)
        raise ValueError(f"Error processing candle data structure for {symbol}") from e
        
    except Exception as e:
        logger.error(f"Unexpected error processing {symbol} candle data from Twelve Data")
        logger.exception(e)
        raise ValueError(f"Failed to process candle data for {symbol}") from e

def polygon_get_candles(
    symbol: str, 
    api_key: str, 
    days_back: int = 10,
    multiplier: int = 1,
    timespan: str = "minute"
) -> pd.DataFrame:
    """
    Fetch historical candle data from Polygon.io API.

    Parameters
    ----------
    symbol : str
        The ticker symbol (e.g., 'AAPL').
    api_key : str
        Your Polygon.io API key.
    days_back : int
        Number of days of historical data to fetch (default 10).
    multiplier : int
        Size of the timespan multiplier (default 1).
    timespan : str
        Size of the time window ('minute', 'hour', 'day', etc.) (default 'minute').

    Returns
    -------
    pd.DataFrame
        Columns: symbol, open, high, low, close, volume; 
        index = datetime (America/New_York timezone).
        
    Raises
    ------
    ValueError: Invalid API response, missing data, or invalid parameters
    HTTPError: API request failed
    ConnectionError: Network connectivity issues
    """
    logger.info(f"Fetching Polygon.io candles for {symbol} ({multiplier}{timespan}, {days_back} days)")
    
    # Validate inputs
    if not api_key:
        logger.error("API key is empty or None")
        raise ValueError("API key cannot be empty")
    
    if not symbol:
        logger.error("Symbol is empty or None")
        raise ValueError("Symbol cannot be empty")
    
    if days_back <= 0:
        logger.error(f"Invalid days_back: {days_back}")
        raise ValueError(f"days_back must be positive, got {days_back}")
    
    if multiplier <= 0:
        logger.error(f"Invalid multiplier: {multiplier}")
        raise ValueError(f"multiplier must be positive, got {multiplier}")
    
    valid_timespans = ["minute", "hour", "day", "week", "month", "quarter", "year"]
    if timespan not in valid_timespans:
        logger.error(f"Invalid timespan: {timespan}")
        raise ValueError(f"timespan must be one of {valid_timespans}, got {timespan}")
    
    try:
        # Compute time range in UTC
        to_date = datetime.now(timezone.utc) - timedelta(minutes=15)
        from_date = to_date - timedelta(days=days_back)
        
        # Convert to milliseconds since epoch
        to_ts = int(to_date.timestamp() * 1000)
        from_ts = int(from_date.timestamp() * 1000)
        
        logger.debug(f"Time range: {from_date} to {to_date} (UTC)")
        logger.debug(f"Timestamp range: {from_ts} to {to_ts}")
        
    except Exception as e:
        logger.error(f"Error calculating time range for {symbol}")
        logger.exception(e)
        raise ValueError(f"Failed to calculate time range") from e
    
    # Build API URL
    url = (
        f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/"
        f"{multiplier}/{timespan}/{from_ts}/{to_ts}"
        f"?adjusted=true&sort=asc&limit=50000&apiKey={api_key}"
    )
    
    logger.debug(f"API URL: {url.replace(api_key, '***')}")  # Hide API key in logs
    
    try:
        # Make API request
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
    except Timeout as e:
        logger.error(f"Request timeout fetching {symbol} from Polygon.io (30s)")
        logger.exception(e)
        raise ConnectionError(f"API request timed out for {symbol}") from e
        
    except HTTPError as e:
        if response.status_code == 401:
            logger.critical(f"Authentication failed for {symbol} - invalid Polygon.io API key")
        elif response.status_code == 403:
            logger.error(f"Access forbidden for {symbol} - check API plan or subscription")
        elif response.status_code == 404:
            logger.error(f"Symbol {symbol} not found on Polygon.io or invalid endpoint")
        elif response.status_code == 429:
            logger.warning(f"Rate limit exceeded for {symbol} - too many requests to Polygon.io")
        else:
            logger.error(f"HTTP {response.status_code} error fetching {symbol}: {response.text[:200]}")
        
        logger.exception(e)
        raise
        
    except ConnectionError as e:
        logger.error(f"Network connection error fetching {symbol} from Polygon.io")
        logger.exception(e)
        raise
        
    except RequestException as e:
        logger.error(f"Request error fetching {symbol} from Polygon.io: {e}")
        logger.exception(e)
        raise
    
    try:
        # Parse JSON response
        data = response.json()
        
    except ValueError as e:
        logger.error(f"Invalid JSON response for {symbol} from Polygon.io")
        logger.debug(f"Response content: {response.text[:500]}")
        logger.exception(e)
        raise ValueError(f"Failed to parse JSON response for {symbol}") from e
    
    # Check for API error status
    if "status" in data:
        if data["status"] == "ERROR":
            error_msg = data.get("error", "Unknown error")
            logger.error(f"Polygon.io API error for {symbol}: {error_msg}")
            raise ValueError(f"API returned error for {symbol}: {error_msg}")
        elif data["status"] == "NOT_FOUND":
            logger.error(f"Symbol {symbol} not found on Polygon.io")
            raise ValueError(f"Symbol {symbol} not found")
    
    # Check for results
    if "results" not in data:
        logger.error(f"No 'results' key in response for {symbol}")
        logger.debug(f"Response keys: {list(data.keys())}")
        logger.debug(f"Response: {data}")
        raise ValueError(f"No results in response for {symbol}: {data}")
    
    results = data["results"]
    
    # Handle empty results
    if not results:
        logger.warning(f"No candle data returned for {symbol} (empty 'results')")
        logger.debug(f"API response: {data}")
        return pd.DataFrame(
            columns=["symbol", "open", "high", "low", "close", "volume"],
            index=pd.DatetimeIndex([], tz="America/New_York", name="datetime")
        )
    
    logger.info(f"Retrieved {len(results)} candles for {symbol}")
    
    try:
        eastern = ZoneInfo("America/New_York")
        
        # Process candles
        candles = []
        for i, c in enumerate(results):
            try:
                # Validate required fields
                required_fields = ["t", "o", "h", "l", "c", "v"]
                missing_fields = [f for f in required_fields if f not in c]
                if missing_fields:
                    logger.warning(f"Candle {i} for {symbol} missing fields: {missing_fields}, skipping")
                    continue
                
                candle = {
                    "datetime": datetime.fromtimestamp(
                        c["t"] / 1000, 
                        tz=timezone.utc
                    ).astimezone(eastern),
                    "symbol": symbol,
                    "open": c["o"],
                    "high": c["h"],
                    "low": c["l"],
                    "close": c["c"],
                    "volume": c["v"],
                }
                candles.append(candle)
                
            except (KeyError, TypeError, ValueError) as e:
                logger.warning(f"Error processing candle {i} for {symbol}: {e}, skipping")
                continue
        
        if not candles:
            logger.warning(f"No valid candles after processing for {symbol}")
            return pd.DataFrame(
                columns=["symbol", "open", "high", "low", "close", "volume"],
                index=pd.DatetimeIndex([], tz="America/New_York", name="datetime")
            )
        
        # Create DataFrame
        df = pd.DataFrame(candles)
        df.set_index("datetime", inplace=True)
        
        # Ensure index is tz-aware in ET
        if df.index.tz is None:
            logger.warning(f"Index not timezone-aware for {symbol}, localizing to ET")
            df.index = df.index.tz_localize("America/New_York")
        else:
            df.index = df.index.tz_convert("America/New_York")
        
        # Ensure numeric columns
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
            
            # Check for NaN values
            nan_count = df[col].isna().sum()
            if nan_count > 0:
                logger.warning(f"{nan_count} NaN values in '{col}' column for {symbol}")
        
        # Reorder columns
        df = df[["symbol", "open", "high", "low", "close", "volume"]]
        
        # Sort by datetime
        df = df.sort_index()
        
        logger.debug(f"DataFrame created: {len(df)} rows, {df.index[0]} to {df.index[-1]}")
        
        if df.empty:
            logger.warning(f"DataFrame is empty after processing for {symbol}")
        
        return df
        
    except Exception as e:
        logger.error(f"Unexpected error processing {symbol} candle data from Polygon.io")
        logger.exception(e)
        raise ValueError(f"Failed to process candle data for {symbol}") from e


def plot(
    df: pd.DataFrame, 
    show_signal: bool = False, 
    filename: str = "chart.png"
) -> None:
    """
    Plot close price and optionally overlay signal buy/sell signals.
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with 'close' column and optionally 'signal' column.
        Index should be datetime for proper x-axis display.
    show_signal : bool
        If True, overlay buy/sell signals from 'signal' column (default False).
    filename : str
        Output filename for the chart (default "chart.png").
        
    Raises
    ------
    ValueError: Missing required columns or invalid data
    IOError: Cannot save file to specified location
    """
    logger.info(f"Generating chart{' with signal signals' if show_signal else ''}")
    logger.debug(f"DataFrame shape: {df.shape}, filename: {filename}")
    
    # Validate inputs
    if df is None:
        logger.error("DataFrame is None")
        raise ValueError("DataFrame cannot be None")
    
    if df.empty:
        logger.error("DataFrame is empty")
        raise ValueError("Cannot plot empty DataFrame")
    
    if not isinstance(df, pd.DataFrame):
        logger.error(f"Expected pd.DataFrame, got {type(df)}")
        raise TypeError(f"Expected pd.DataFrame, got {type(df)}")
    
    # Validate required columns
    if "close" not in df.columns:
        logger.error(f"Missing 'close' column in DataFrame")
        logger.debug(f"Available columns: {df.columns.tolist()}")
        raise ValueError("DataFrame must contain 'close' column")
    
    # Check for valid close data
    if df["close"].isna().all():
        logger.error("All 'close' values are NaN")
        raise ValueError("'close' column contains only NaN values")
    
    nan_count = df["close"].isna().sum()
    if nan_count > 0:
        logger.warning(f"{nan_count} NaN values in 'close' column ({nan_count/len(df)*100:.1f}%)")
    
    # Validate signal column if needed
    if show_signal:
        if "signal" not in df.columns:
            logger.warning("show_signal=True but 'signal' column not found, plotting without signals")
            show_signal = False
        else:
            # Check if signal column has any signals
            signal_values = df["signal"].dropna()
            if signal_values.empty:
                logger.warning("'signal' column exists but contains no signals")
            else:
                buy_count = (df["signal"] == "buy").sum()
                sell_count = (df["signal"] == "sell").sum()
                logger.info(f"signal signals: {buy_count} buys, {sell_count} sells")
    
    # Validate filename
    if not filename:
        logger.error("Filename is empty")
        raise ValueError("Filename cannot be empty")
    
    # Check if directory exists and is writable
    try:
        output_path = Path(filename)
        if output_path.parent != Path('.'):
            output_path.parent.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Ensured directory exists: {output_path.parent}")
    except Exception as e:
        logger.error(f"Cannot create directory for {filename}")
        logger.exception(e)
        raise IOError(f"Cannot create directory for output file: {filename}") from e
    
    try:
        # Create figure
        logger.debug("Creating matplotlib figure")
        plt.figure(figsize=(10, 5))
        
        # Plot close price
        plt.plot(df.index, df["close"], label="Close", color="blue", linewidth=1.5)
        logger.debug("Plotted close price")
        
        # Plot signal signals if requested
        if show_signal and "signal" in df.columns:
            try:
                # Plot buy signals
                buys = df[df["signal"] == "buy"]
                if not buys.empty:
                    plt.scatter(
                        buys.index, 
                        buys["close"], 
                        marker="^", 
                        color="green", 
                        label="Buy", 
                        s=100,
                        zorder=5  # Ensure markers appear on top
                    )
                    logger.debug(f"Plotted {len(buys)} buy signals")
                
                # Plot sell signals
                sells = df[df["signal"] == "sell"]
                if not sells.empty:
                    plt.scatter(
                        sells.index, 
                        sells["close"], 
                        marker="v", 
                        color="red", 
                        label="Sell", 
                        s=100,
                        zorder=5  # Ensure markers appear on top
                    )
                    logger.debug(f"Plotted {len(sells)} sell signals")
                    
            except Exception as e:
                logger.error("Error plotting signals")
                logger.exception(e)
                # Continue without signals rather than failing completely
                logger.warning("Continuing with close price only")
        
        # Add labels and formatting
        plt.legend(loc="best")
        plt.title("strategy Chart", fontsize=14, fontweight="bold")
        plt.xlabel("Time", fontsize=10)
        plt.ylabel("Price", fontsize=10)
        plt.grid(True, alpha=0.3)
        
        # Rotate x-axis labels for better readability
        plt.xticks(rotation=45, ha='right')
        
        logger.debug("Added chart formatting")
        
    except Exception as e:
        logger.error("Error creating plot")
        logger.exception(e)
        plt.close()  # Clean up
        raise ValueError(f"Failed to create plot: {e}") from e
    
    try:
        # Save figure
        logger.debug(f"Saving chart to {filename}")
        plt.savefig(filename, dpi=300, bbox_inches="tight")
        logger.info(f"Chart saved successfully: {filename}")
        
    except PermissionError as e:
        logger.error(f"Permission denied writing to {filename}")
        logger.exception(e)
        plt.close()
        raise IOError(f"Permission denied: cannot write to {filename}") from e
        
    except OSError as e:
        logger.error(f"OS error saving chart to {filename}")
        logger.exception(e)
        plt.close()
        raise IOError(f"Cannot save chart to {filename}: {e}") from e
        
    except Exception as e:
        logger.error(f"Unexpected error saving chart to {filename}")
        logger.exception(e)
        plt.close()
        raise IOError(f"Failed to save chart: {e}") from e
    
    finally:
        # Always close the plot to free memory
        plt.close()
        logger.debug("Matplotlib figure closed")



if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    from tradeBot.get_data.aggregateTimeFrames import aggregate_time_frame
    from tradeBot.strategies.leverageTurtle import leverage_turtle

    load_dotenv()

    MARKET_DATA_ACCESS_TOKEN = os.getenv("MARKET_DATA_ACCESS_TOKEN")
    symbol = "SOXL"
    df =   charles_get_candles(MARKET_DATA_ACCESS_TOKEN, symbol=symbol, period=3, frequency=1, period_type="day", frequency_type="minute", need_extended_hours_data=False)
    strat_df = leverage_turtle(aggregate_time_frame(df, 5))
    print(strat_df)
    print(strat_df["SMA200"])