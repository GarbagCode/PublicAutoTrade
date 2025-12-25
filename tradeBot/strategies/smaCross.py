import pandas_ta as ta
import pandas as pd

def main(df: pd.DataFrame, position_size: float = 150, length: int = 200) -> pd.DataFrame:
    """
    Simple Moving Average Crossover Strategy
    
    Generates BUY signal when price crosses above SMA
    Generates SELL signal when price crosses below SMA
    
    Args:
        df: DataFrame with OHLCV data (must have 'close' column)
        position_size: Dollar amount or position size for each trade
        length: SMA period (default: 200)
    
    Returns:
        DataFrame with added 'SMA200', 'signal', and 'quantity' columns
    """

    # Make a copy to avoid modifying original dataframe
    df = df.copy()
    
    # Initialize columns 
    df["signal"] = None

    # Initialize quantity column
    df["quantity"] = 0.0

    # Calculate the SMA
    sma = ta.sma(df["close"], length=length)
    df[f"SMA{length}"] = sma
    
    # BUY: prev close < SMA AND current close > SMA (crossover above)
    buy_condition = (df["close"].shift(1) < sma.shift(1)) & (df["close"] > sma)

    # SELL: prev close > SMA AND current close < SMA (crossover below)    
    sell_condition = (df["close"].shift(1) > sma.shift(1)) & (df["close"] < sma)
    
    # Generate buy signals
    df.loc[buy_condition, "signal"] = "BUY"
    df.loc[buy_condition, "quantity"] = position_size / df.loc[buy_condition, "close"]

    # Generate sell signals
    df.loc[sell_condition, "signal"] = "SELL"
    df.loc[sell_condition, "quantity"] = position_size / df.loc[sell_condition, "close"]


    return df

if __name__ == "__main__":
    from dotenv import load_dotenv
    from tradeBot.get_data.historical_data import charles_get_candles, plot
    import os

    load_dotenv()
    MARKET_DATA_ACCESS_TOKEN = os.getenv("MARKET_DATA_ACCESS_TOKEN")
    
    # Define symbol
    symbol = "SPY"  # Add your symbol here
    
    # Get candles
    df = charles_get_candles(MARKET_DATA_ACCESS_TOKEN, symbol, period=90)
    
    # Apply strategy
    dfStrat = sma_cross(df, length=200)
    
    # Display results
    print("\n=== SMA Crossover Strategy Results ===")
    print(f"Total bars: {len(dfStrat)}")
    print(f"Buy signals: {(dfStrat['signal'] == 'BUY').sum()}")
    print(f"Sell signals: {(dfStrat['signal'] == 'SELL').sum()}")
    
    # Show recent signals
    signals = dfStrat[dfStrat['signal'].notna()]
    if not signals.empty:
        print("\n=== Recent Signals ===")
        print(signals[['close', 'SMA200', 'signal']].tail(10))
    
    # Plot
    plot(dfStrat, True)