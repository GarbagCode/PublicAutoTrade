import numpy as np
from datetime import datetime, timedelta
import pandas as pd

import numpy as np
import pandas as pd
from datetime import datetime, timedelta


def create_sample_data():
    """Generate large sample dataset with realistic price movement"""
    np.random.seed(42)
    
    # Generate 1 year of 1-minute data (252 trading days * 6.5 hours * 60 minutes)
    num_candles = 252 * 6 * 60  # ~90k candles
    
    start = datetime(2024, 1, 1, 9, 30)
    timestamps = [start + timedelta(minutes=i) for i in range(num_candles)]
    
    # Generate realistic price movement using random walk
    close_prices = 100 + np.cumsum(np.random.randn(num_candles) * 0.5)
    
    # Generate OHLC from close prices
    open_prices = close_prices + np.random.randn(num_candles) * 0.3
    high_prices = np.maximum(open_prices, close_prices) + np.abs(np.random.randn(num_candles) * 0.5)
    low_prices = np.minimum(open_prices, close_prices) - np.abs(np.random.randn(num_candles) * 0.5)
    
    # Generate volume with some patterns
    base_volume = np.random.randint(1000, 5000, num_candles)
    volume = base_volume * (1 + np.sin(np.arange(num_candles) / 1000) * 0.5)
    
    data = {
        'open': open_prices,
        'high': high_prices,
        'low': low_prices,
        'close': close_prices,
        'volume': volume.astype(int)
    }
    
    df = pd.DataFrame(data, index=pd.DatetimeIndex(timestamps))
    return df

if __name__ == "__main__":
    create_sample_data()