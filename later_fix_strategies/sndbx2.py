import numpy as np
import pandas as pd

from tradeBot.functions.atr import atr_wilder
from tradeBot.functions.rsi import rsi_wilder


def main(df: pd.DataFrame, pt: float = 5, stop_loss_percentage: float = 0.9) -> pd.DataFrame:
    from datetime import time

    df = df.copy()

    # --- Indicators on full series (includes extended hours, like TOS on extended-hours charts) ---
    df["ATR"] = atr_wilder(df)
    df["RSI"] = rsi_wilder(df["close"])
    df["RSI_prev"] = df["RSI"].shift(1)
    df["ATR_prev"] = df["ATR"].shift(1)
    df["close_prev"] = df["close"].shift(1)
    df["low_prev"] = df["low"].shift(1)

    # --- Time windows (ET) ---
    t = df.index.time
    buy_open  = ((t >= time(9, 40)) & (t < time(9, 50)))
    df["in_buy_window"] = buy_open

    # Hard exit at/after exactly 16:00 ET
    df["is_4pm_or_later"] = (t >= time(16, 0))

    # --- Entry Conditions (no rounding; mirrors your ThinkScript: RSI() - RSI()[1] > 10) ---
    df["is_bullish"] = df["close"] > df["close_prev"]
    df["meets_volume_req"] = df["volume"] > (3000 / df["close"]) * 100
    df["meets_rsi_req"] = (df["RSI"] - df["RSI_prev"]) > 10
    df["strategy"] = df["in_buy_window"] & df["is_bullish"] & df["meets_volume_req"] & df["meets_rsi_req"]

    # --- Output columns ---
    df["EntryPrice"] = np.nan
    df["HighATR"] = np.nan
    df["LowATR"] = np.nan
    df["strategy"] = None

    # --- Position tracking ---
    in_position = False
    entry_price = np.nan

    for i in range(len(df)):
        if not in_position and df["strategy"].iat[i]:
            # BUY
            entry_price = df["close"].iat[i]
            atr_val = df["ATR"].iat[i]
            df.at[df.index[i], "EntryPrice"] = entry_price
            df.at[df.index[i], "HighATR"] = entry_price + atr_val * pt
            df.at[df.index[i], "LowATR"]  = entry_price - atr_val * stop_loss_percentage
            df.at[df.index[i], "strategy"] = "buy"
            in_position = True

        elif in_position:
            # Maintain targets while in trade
            atr_val = df["ATR"].iat[i]
            high_target = entry_price + atr_val * pt
            low_stop    = entry_price - atr_val * stop_loss_percentage

            df.at[df.index[i], "EntryPrice"] = entry_price
            df.at[df.index[i], "HighATR"] = high_target
            df.at[df.index[i], "LowATR"]  = low_stop

            # SELL: hit stop, target, or 4:00pm (first bar at/after 16:00 ET)
            hit_stop   = df["low"].iat[i]  < low_stop
            hit_target = df["high"].iat[i] >= high_target
            is_close   = df["is_4pm_or_later"].iat[i]

            if hit_stop or hit_target or is_close:
                df.at[df.index[i], "strategy"] = "sell"
                in_position = False
                entry_price = np.nan

    df["quantity"] = 0.0
    df["signal"] = "sell"

    return df




if __name__ == "__main__":
    import os
    import sys
    from dotenv import load_dotenv
    from tradeBot.get_data.historical_data import twelvedata_get_candles, plot, charles_get_candles
    from tradeBot.backtest.analyze import analyze_trades
    from tradeBot.get_data.polygon import fetch_5min_candles
    
    load_dotenv()
    API_KEY = os.getenv("MARKET_DATA_ACCESS_TOKEN")
    POLYGONE_KEY = os.getenv('POLYGONE_KEY')

    #The type of data that i want
    symbol = "SPXL"
    period_type = "day"
    frequency_type = "minute"


    df = fetch_5min_candles(symbol, 2020, 2025, POLYGONE_KEY)
    #df = charles_get_candles(API_KEY, symbol="SPXL", period=10, frequency=5, period_type="day", frequency_type="minute", need_extended_hours_data=True)
    result = sand_box_2(df)
    print(result[(result["strategy"] == "buy") | (result["strategy"] == "sell")])
    #print(analyze_trades(result))

    """
    print(result[(result["strategy"] == "buy") | (result["strategy"] == "sell")])
    print(result.loc[(result["strategy"] == "buy") | (result["strategy"] == "sell"), ["ATR", "RSI", "strategy"]])
    print(result.loc[:, ["ATR", "RSI", "strategy"]])

    #print(df[["close", "volume"]].tail(10))
    #print(result.loc["2025-10-08 09:30":"2025-10-08 10:00", ["close", "ATR", "RSI", "strategy"]])
    #print(result.tail())
    #plot(result, True)

    trades_df, summary = analyze_trades(result)

    print("Trade Summary:")
    for k, v in summary.items():
        print(f"{k}: {v}")

    print("\nDetailed Trades:")
    print(trades_df)
    """

