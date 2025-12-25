-- ------------------------------------------------------------
-- day_trading_strategies TABLE
-- Stores trading strategy including timeframe and symbol
-- ------------------------------------------------------------
CREATE TABLE day_trading_strategies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    time_frame INTEGER NOT NULL,
    symbol TEXT NOT NULL,
    order_type TEXT NOT NULL DEFAULT 'MARKET' CHECK (order_type IN ('MARKET', 'LIMIT')), 
    lookback_days INTEGER NOT NULL DEFAULT 3 CHECK (lookback_days >=1 and lookback_days <= 10),
    extended_hours INTEGER NOT NULL DEFAULT 1 CHECK (extended_hours IN (0,1)), -- 0 = false, 1 = true
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0,1)), -- 0 = false, 1 = true
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for fast lookups
CREATE INDEX idx_day_trading_strategies_active ON day_trading_strategies(active);
CREATE INDEX idx_day_trading_strategies_time_frame ON day_trading_strategies(time_frame);
CREATE INDEX idx_day_trading_strategies_symbol ON day_trading_strategies(symbol);
CREATE INDEX idx_day_trading_strategies_name ON day_trading_strategies(name);
CREATE INDEX idx_day_trading_strategies_lookback_days ON day_trading_strategies(lookback_days);
CREATE INDEX idx_day_trading_strategies_extended_hours ON day_trading_strategies(extended_hours);


-- ------------------------------------------------------------
-- ACTIVE_POSITIONS TABLE
-- Stores currently open positions
-- ------------------------------------------------------------
CREATE TABLE active_positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    strategy_id INTEGER NOT NULL,
    order_id TEXT NOT NULL UNIQUE,
    
    -- Position details
    quantity REAL NOT NULL CHECK (quantity > 0),
    entry_price REAL NOT NULL CHECK (entry_price >= 0),  -- 0 = Market order
    
    -- Timestamp
    opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign key
    FOREIGN KEY (strategy_id) REFERENCES day_trading_strategies(id) ON DELETE CASCADE
);

-- Indexes for common queries
CREATE INDEX idx_active_positions_strategy ON active_positions(strategy_id);
CREATE INDEX idx_active_positions_order ON active_positions(order_id);

-- ------------------------------------------------------------
-- TRADE_HISTORY TABLE
-- Simple record of all buy/sell executions
-- ------------------------------------------------------------
CREATE TABLE trade_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    strategy_id INTEGER NOT NULL,
    active_position_id INTEGER,  
    
    -- Trade details
    quantity REAL NOT NULL CHECK (quantity > 0),
    price REAL NOT NULL CHECK (price >= 0), -- 0 = Market order
    side TEXT NOT NULL CHECK (side IN ('BUY', 'SELL')),
    
    -- Timestamp
    date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, 
    
    -- Foreign keys
    FOREIGN KEY (strategy_id) REFERENCES day_trading_strategies(id) ON DELETE CASCADE,
    FOREIGN KEY (active_position_id) REFERENCES active_positions(id) ON DELETE SET NULL
);

-- Indexes for querying history
CREATE INDEX idx_trade_history_strategy ON trade_history(strategy_id);
CREATE INDEX idx_trade_history_date ON trade_history(date);
CREATE INDEX idx_trade_history_side ON trade_history(side);


-- ------------------------------------------------------------
-- TRIGGERS (Automatic timestamp updates)
-- ------------------------------------------------------------

-- Update day_trading_strategies.updated_at on modification
CREATE TRIGGER update_day_trading_strategies_timestamp 
AFTER UPDATE ON day_trading_strategies
FOR EACH ROW
BEGIN
    UPDATE day_trading_strategies SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;