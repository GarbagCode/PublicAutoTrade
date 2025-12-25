import sys, os
import pytest
import pandas as pd
from datetime import datetime, timedelta
from tradeBot.functions.aggregateTimeFrames import aggregate_time_frame

def create_sample_df(minutes=10):
    """Create a 1-minute OHLCV DataFrame with datetime index."""
    start = datetime(2025, 10, 27, 9, 30)
    times = [start + timedelta(minutes=i) for i in range(minutes)]
    data = {
        "symbol": "test",
        "open": range(minutes),
        "high": range(1, minutes + 1),
        "low": range(minutes),
        "close": range(1, minutes + 1),
        "volume": [100]*minutes
    }
    df = pd.DataFrame(data, index=pd.DatetimeIndex(times))
    return df

def test_aggregate_time_frame_basic():
    df = create_sample_df(minutes=10)
    aggregated = aggregate_time_frame(df, 5)
    # Should produce two 5-minute bars
    assert len(aggregated) == 2
    # Columns should exist
    assert all(col in aggregated.columns for col in ["symbol", "open", "high", "low", "close", "volume"])
    # Values check: first bar
    first_bar = aggregated.iloc[0]
    assert first_bar["open"] == 0
    assert first_bar["high"] == 5
    assert first_bar["low"] == 0
    assert first_bar["close"] == 5
    assert first_bar["volume"] == 500  # 5 minutes * 100 volume each

def test_aggregate_time_frame_not_enough_data():
    df = create_sample_df(minutes=3)
    aggregated = aggregate_time_frame(df, 5)
    # Should return empty DataFrame with correct columns
    assert aggregated.empty
    assert list(aggregated.columns) == ["symbol", "open", "high", "low", "close", "volume"]
