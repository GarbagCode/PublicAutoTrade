import pandas as pd
import numpy as np

def rsi_wilder(close: pd.Series, period: int = 14) -> pd.Series:
    """
    Computes RSI using Wilder's smoothing.
    Note: Need ~3x the period length of data to closely match ThinkOrSwim RSI.
    """
    if close is None or len(close) < period * 3:
        raise ValueError("Input series is too short for RSI calculation")

    try:
        delta = close.diff()
        gain = delta.clip(lower=0).ewm(alpha=1/period, adjust=False).mean()
        loss = (-delta.clip(upper=0)).ewm(alpha=1/period, adjust=False).mean()
        rs = gain / loss.replace(0, np.nan)
        return 100 - (100 / (1 + rs))
    except Exception as e:
        print(f"Error occurred in rsi_wilder: {e}")
        return pd.Series(dtype=float)

if __name__ == "__main__":
    # Example test
    data = pd.Series([1, 2, 3, 2, 4, 5, 4, 6, 7, 6, 8, 9, 8, 10, 9, 11, 10])
    print(rsi_wilder(data, period=14))