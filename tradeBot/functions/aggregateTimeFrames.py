import pandas as pd
import logging


logger = logging.getLogger(__name__)

def aggregate_time_frame(df: pd.DataFrame, aggregation: int) -> pd.DataFrame:
    """
    Trim the input to start/end on aligned datetime boundaries, then aggregate to OHLCV.

    Only includes rows where the index is datetime-aligned to the specified aggregation.
    For example, for 5-minute bars: starts at xx:00, xx:05, ..., ends before a non-divisible minute.
    
    Parameters
    ----------
    df : pd.DataFrame
        Input DataFrame with DatetimeIndex and columns: symbol, open, high, low, close, volume
    aggregation : int
        Aggregation period in minutes (e.g., 5 for 5-minute bars)
        
    Returns
    -------
    pd.DataFrame
        Aggregated OHLCV DataFrame with columns: symbol, open, high, low, close, volume
        Returns empty DataFrame with correct columns if aggregation fails
        
    Raises
    ------
    ValueError: Invalid input DataFrame or aggregation parameter
    """
    logger.info(f"Aggregating time frame to {aggregation} minutes")
    logger.debug(f"Input DataFrame shape: {df.shape}")
    
    # Validate inputs
    if df is None:
        logger.error("DataFrame is None")
        raise ValueError("DataFrame cannot be None")
    
    if not isinstance(df, pd.DataFrame):
        logger.error(f"Expected pd.DataFrame, got {type(df)}")
        raise TypeError(f"Expected pd.DataFrame, got {type(df)}")
    
    if df.empty:
        logger.warning("Input DataFrame is empty")
        return pd.DataFrame(columns=['symbol', 'open', 'high', 'low', 'close', 'volume'])
    
    # Validate index type
    if not isinstance(df.index, pd.DatetimeIndex):
        logger.error(f"DataFrame index must be DatetimeIndex, got {type(df.index)}")
        raise ValueError(f"DataFrame index must be a DatetimeIndex, got {type(df.index)}")
    
    # Check if index is timezone-aware
    if df.index.tz is None:
        logger.warning("DatetimeIndex is not timezone-aware")
    
    # Validate aggregation parameter
    if not isinstance(aggregation, int):
        logger.error(f"Aggregation must be int, got {type(aggregation)}")
        raise TypeError(f"Aggregation must be an integer, got {type(aggregation)}")
    
    if aggregation <= 0:
        logger.error(f"Invalid aggregation value: {aggregation}")
        raise ValueError(f"Aggregation must be positive, got {aggregation}")
    
    # Check if we have enough data
    if len(df) < aggregation:
        logger.warning(f"Not enough data to aggregate: {len(df)} rows < {aggregation} minute window")
        return pd.DataFrame(columns=['symbol', 'open', 'high', 'low', 'close', 'volume'])
    
    # Validate required columns
    required_cols = ['symbol', 'open', 'high', 'low', 'close', 'volume']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        logger.error(f"Missing required columns: {missing_cols}")
        logger.debug(f"Available columns: {df.columns.tolist()}")
        raise ValueError(f"Missing required columns: {missing_cols}")
    
    try:
        # Create copy to avoid mutating original
        df_1m = df.copy()
        logger.debug("Created DataFrame copy for aggregation")
        
        # Build resampling rule
        rule = f"{aggregation}min"
        logger.debug(f"Resampling with rule: {rule}")
        
        # Perform aggregation
        try:
            s = df_1m["symbol"].resample(rule).first()
            o = df_1m["open"].resample(rule).first()
            h = df_1m["high"].resample(rule).max()
            l = df_1m["low"].resample(rule).min()
            c = df_1m["close"].resample(rule).last()
            v = df_1m["volume"].resample(rule).sum()
            
            logger.debug("Resampling completed for all columns")
            
        except Exception as e:
            logger.error(f"Error during resampling operation: {e}")
            logger.exception(e)
            raise ValueError(f"Resampling failed: {e}") from e
        
        # Create output DataFrame
        try:
            out = pd.DataFrame({
                "symbol": s,
                "open": o, 
                "high": h, 
                "low": l, 
                "close": c, 
                "volume": v
            })
            
            logger.debug(f"Created aggregated DataFrame: {out.shape}")
            
        except Exception as e:
            logger.error(f"Error creating output DataFrame: {e}")
            logger.exception(e)
            raise ValueError(f"Failed to create output DataFrame: {e}") from e
        
        # Drop incomplete bars (NaNs in OHLC indicate partial windows)
        initial_rows = len(out)
        out = out.dropna(subset=["open", "high", "low", "close"])
        dropped_rows = initial_rows - len(out)
        
        if dropped_rows > 0:
            logger.debug(f"Dropped {dropped_rows} incomplete bars at edges")
        
        if out.empty:
            logger.warning("All aggregated bars were incomplete (all NaN)")
            return pd.DataFrame(columns=['symbol', 'open', 'high', 'low', 'close', 'volume'])
        
        # Check for any remaining NaN values
        for col in ['open', 'high', 'low', 'close', 'volume']:
            nan_count = out[col].isna().sum()
            if nan_count > 0:
                logger.warning(f"{nan_count} NaN values remain in '{col}' column after aggregation")
        
        logger.info(f"Successfully aggregated to {len(out)} bars ({aggregation}-minute)")
        logger.debug(f"Time range: {out.index[0]} to {out.index[-1]}")
        
        return out
        
    except ValueError as e:
        # Re-raise ValueError (already logged)
        raise
        
    except Exception as e:
        logger.error(f"Unexpected error in aggregate_time_frame: {e}")
        logger.exception(e)
        logger.warning("Returning empty DataFrame due to error")
        return pd.DataFrame(columns=['symbol', 'open', 'high', 'low', 'close', 'volume'])