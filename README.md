# autoTrade

A trading infrastructure, It provides the execution layer and plumbing needed to run any custom trading strategy, as long as the strategy follows the required interface/format. The system handles order execution and data access using the Charles Schwab API, allowing strategies to trade without relying on paid platforms.

## Quick Start

### 1. Set up environment variables:
```bash
cp .env.example .env
```

### 2. Edit `.env` with your credentials:
Get your API keys from the Charles Schwab developer portal by creating trading and market data apps.

### 3. Install dependencies:
```bash
pip install -r requirements.txt
```

### 4. Set up the database:
See the Database Setup section below.

### 5. Verify your configuration:
Run the unit tests to ensure everything is configured correctly:
```bash
pytest test/unit
```

For integration tests that verify API calls to Charles Schwab:
```bash
pytest test/integration
```

## Strategy Requirements

All strategies must be placed in the `tradeBot/strategies/` folder and contain a `main(df)` function that returns a Pandas DataFrame with these columns:

**`signal` column** - One of three values:
- `"BUY"` - Enter a long position
- `"SELL"` - Exit a position
- `None` (null) - No action

**`quantity` column** - Positive integer representing the number of shares to buy when signal is `"BUY"`

### Example Strategy Structure
```python
# File: tradeBot/strategies/smaCross.py
import pandas as pd
import pandas_ta as ta

def main(df: pd.DataFrame) -> pd.DataFrame:
    """SMA Crossover Strategy"""
    
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
```

## Database Setup

The database file is located at `database/autoTrade.db`. For complete schema details, see `database/autoTrade.sql`.

### Database Configuration

| Column | Type | Description | Default |
|--------|------|-------------|---------|
| `id` | INTEGER | Auto-incrementing primary key | - |
| `name` | TEXT | Strategy module name (must match Python file) | - |
| `time_frame` | INTEGER | Bar aggregation in minutes (e.g., 1, 5, 15, 60) | - |
| `symbol` | TEXT | Trading symbol (e.g., 'SPY', 'AAPL', 'SOXL') | - |
| `order_type` | TEXT | Order execution type ('MARKET' or 'LIMIT') | 'MARKET' |
| `lookback_days` | INTEGER | Days of historical data (1-10) | 3 |
| `extended_hours` | INTEGER | Enable pre/post market (0=no, 1=yes) | 1 |
| `active` | INTEGER | Strategy enabled (0=no, 1=yes) | 1 |
| `created_at` | TIMESTAMP | Record creation timestamp | CURRENT_TIMESTAMP |
| `updated_at` | TIMESTAMP | Record last update timestamp | CURRENT_TIMESTAMP |

### Initialize a Strategy

Connect to the database:
```bash
sqlite3 database/autoTrade.db
```

Insert the SMA Cross strategy (example):
```sql
INSERT INTO day_trading_strategies(name, time_frame, symbol, order_type, active)
VALUES ('smaCross', 5, 'SPY', 'LIMIT', 1);
```

Verify the insertion:
```sql
SELECT * FROM day_trading_strategies;
```

Exit SQLite:
```
.quit
```

## Managing Strategies

### View all strategies:
```sql
SELECT id, name, symbol, time_frame, lookback_days, active 
FROM day_trading_strategies;
```

### Activate a strategy:
```sql
UPDATE day_trading_strategies 
SET active = 1 
WHERE id = 1;
```

### Deactivate a strategy:
```sql
UPDATE day_trading_strategies 
SET active = 0 
WHERE name = 'smaCross';
```

### Delete a strategy:
```sql
DELETE FROM day_trading_strategies 
WHERE id = 1;
```
**Note:** This will also delete related positions and trade history due to CASCADE constraints.

## Monitoring

### View active positions:
```sql
SELECT ap.*, dts.name as strategy_name 
FROM active_positions ap
JOIN day_trading_strategies dts ON ap.strategy_id = dts.id;
```

### View trade history:
```sql
SELECT th.*, dts.name as strategy_name 
FROM trade_history th
JOIN day_trading_strategies dts ON th.strategy_id = dts.id
ORDER BY th.date DESC
LIMIT 50;
```

## Configuration Defaults

- **Lookback Period:** 3 days (configurable per strategy, range: 1-10 days)
- **Time Frame:** Specified in minutes (e.g., 1, 5, 15, 30, 60)
- **Extended Hours:** Enabled by default
- **Symbol Format:** Uppercase (e.g., 'SPY', 'AAPL', 'SOXL')

## Important Notes

- Strategy module names must match the Python file name
- Each strategy must contain a `main(df)` function
- The `active` column controls which strategies run (1 = active, 0 = inactive)
- Lookback days are constrained to 1-10 days by the database schema