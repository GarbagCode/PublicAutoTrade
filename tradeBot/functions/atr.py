import pandas as pd


def atr_wilder(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    Need 3x the period length to closely match tos atr
    """

    h, l, c = df["high"], df["low"], df["close"]
    pc = c.shift(1)
    tr = pd.concat([(h - l), (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1/period, adjust=False).mean()

if __name__ == "__main__":
    atr_wilder()