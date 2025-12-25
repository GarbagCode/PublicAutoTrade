import sys
import os
import numpy as np
import pandas as pd
from tradeBot.data import get_candles, plot
from tradeBot.functions import atr, daily_percent_change, hot_stock_swing_mask

#runs strategy on data
def runners_swing_large_cap(df, percent_change_threshold: float = 5.0, atr_len: int = 14) -> pd.DataFrame:
    """
    Translate the ThinkScript into Python.
    Returns a DataFrame with a 'strategy' column that has values:
    'buy', 'sell', or None.
    """
    df = df.copy()

    # --- Indicators ---
    atr_series = atr(df, period=atr_len)  # same ATR helper as before
    s = df["close"].shift(1) - atr_series.shift(1) * 2.5
    hot = hot_stock_swing_mask(df, percent_change_threshold)
    long_condition = hot & (df["low"] > s)

    # --- Initialize ---
    df["strategy"] = None  # This is the only column for signals
    in_pos = False
    entry_price = np.nan

    for i in range(1, len(df)):
        if not in_pos:
            # Entry: BUY
            if bool(long_condition.iloc[i]):
                in_pos = True
                entry_price = df["close"].iloc[i]
                df.iat[i, df.columns.get_loc("strategy")] = "buy"
        else:
            # Threshold t depends on entry price
            t = entry_price - atr_series.shift(1).iloc[i] * 1.5

            # Exit 1: low < s
            if df["low"].iloc[i] < s.iloc[i]:
                df.iat[i, df.columns.get_loc("strategy")] = "sell"
                in_pos, entry_price = False, np.nan
                continue

            # Exit 2: close < t
            if df["close"].iloc[i] < t:
                df.iat[i, df.columns.get_loc("strategy")] = "sell"
                in_pos, entry_price = False, np.nan
                continue

            # Exit 3: daily percent change < -10
            pct_today = daily_percent_change(df).iloc[i]
            if pct_today < -10.0:
                df.iat[i, df.columns.get_loc("strategy")] = "sell"
                in_pos, entry_price = False, np.nan
                continue

    return df


    runners_swing_large_cap


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    MARKET_DATA_ACCESS_TOKEN = os.getenv("MARKET_DATA_ACCESS_TOKEN")

    #The type of data that i want
    symbol = "AAPL"
    period_type = "year"
    frequency_type = "daily"


    df = get_candles(MARKET_DATA_ACCESS_TOKEN, symbol, period_type, frequency_type)
    dfStrat = runners_swing_large_cap(df)
    mask = dfStrat["strategy"] == "buy"
    print(mask)

    plot(dfStrat, show_strategy = True)

    