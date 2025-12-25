import pandas as pd
import numpy as np

def daily_percent_change(df: pd.DataFrame) -> pd.Series:
    """
    Percent change of **daily close**.
    If df is intraday, resample to daily close and forward-fill back to intraday index
    so it behaves like ThinkScript's close(period=AggregationPeriod.DAY).
    """
    if df.index.inferred_type in ("datetime64", "datetime64tz"):
        # build a daily close series on business days
        daily_close = df['close'].resample('1D').last()
        # limit to business days only if you prefer:
        # daily_close = df['close'].asfreq('B')  # optional
        pct_daily = daily_close.pct_change() * 100.0
        # align to original index by forward-filling yesterday’s computed value
        pct_on_intraday_index = pct_daily.reindex(df.index, method='ffill')
        return pct_on_intraday_index
    else:
        # if df is already daily, just use pct_change on close
        return df['close'].pct_change() * 100.0


if __name__ == "__main__":
    daily_percent_change()
