import pandas_ta as ta
import pandas as pd
import numpy as np


def strategy_sma_rsi(df):
    """
    ThinkScript:
      SMA = simplemovingavg(length=200)
      FMA = simplemovingavg(length=400)
      BUY  when RSI() < 40 and low > SMA      (filled at close)
      SELL when RSI() > 55                    (filled at close)
           or low <= FMA                      (filled at close)
    """
    out = df.copy()
    out["SMA_200"] = ta.sma(out["close"], length=200)
    out["FMA_400"] = ta.sma(out["close"], length=400)
    out["RSI_14"]  = ta.rsi(out["close"], length=14)

    entry_mask = (out["RSI_14"] < 40) & (out["low"] > out["SMA_200"])
    exit_mask  = (out["RSI_14"] > 55) | (out["low"] <= out["FMA_400"])

    out["strategy"] = None
    in_pos = False
    for i in range(len(out)):
        if not in_pos and entry_mask.iat[i]:
            out.iat[i, out.columns.get_loc("strategy")] = "buy"
            in_pos = True
        elif in_pos and exit_mask.iat[i]:
            out.iat[i, out.columns.get_loc("strategy")] = "sell"
            in_pos = False

    return out


if __name__ == "__main__":
    import os
    import sys
    from dotenv import load_dotenv
    from tradeBot.data import get_candles, plot

    load_dotenv()
    MARKET_DATA_ACCESS_TOKEN = os.getenv("MARKET_DATA_ACCESS_TOKEN")

    #The type of data that i want
    symbol = "SPY"
    period_type = "year"
    frequency_type = "daily"


    df = get_candles(MARKET_DATA_ACCESS_TOKEN, symbol, period_type, frequency_type, period=10)
    dfStrat = strategy_sma_rsi(df)
    plot(dfStrat, True)