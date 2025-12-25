import pandas as pd


def hot_stock_swing_mask(df: pd.Series, percent_change_threshold: float = 5.0) -> pd.Series:
    """
    ThinkScript:
      def hotstockswing =
        PercentChg(price=close(period=DAY))[1] > PercentChange AND
        PercentChg(price=close(period=DAY))[2] > PercentChange AND
        PercentChg(price=close(period=DAY))     > PercentChange;
    """
    pct = daily_percent_change(df)  # on intraday this is the daily change aligned to each bar
    cond = (pct.shift(1) > percent_change_threshold) & \
           (pct.shift(2) > percent_change_threshold) & \
           (pct > percent_change_threshold)
    return cond.fillna(False)


if __name__ == "__main__":
    hot_stock_swing_mask()