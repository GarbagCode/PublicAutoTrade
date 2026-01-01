from backend.dbConn import connect_to_db


def get_all_active_day_trading_strategies() -> list[dict]:
    """
    Retrieve all active trading strategies from the database.
    
    Returns:
        list[dict]: A list of dictionaries containing strategy information.
                    Each dict has keys: id, name, symbol, time_frame, lookback_days, extended_hours
    
    Example:
        [
            {
                'id': 1,
                'name': 'momentum_scalp',
                'symbol': 'SOXL',
                'order_type': 'market'
                'time_frame': '5min',
                'lookback_days': 10,
                'extended_hours': 0
            },
            ...
        ]
    
    Raises:
        Exception: If database connection fails or query execution fails.
    """
    conn = None
    try:
        # Connect to DB
        conn = connect_to_db()
        
        # Create a cursor
        cur = conn.cursor()
        
        # Get all active strategies
        cur.execute("""
            SELECT *  
            FROM day_trading_strategies 
            WHERE active = 1
        """)
        
        rows = cur.fetchall()
        
        # Convert Row objects to actual dictionaries
        return [dict(row) for row in rows]
    
    finally:
        if conn:
            conn.close()


# Usage - MUCH CLEANER:
if __name__ == "__main__":
    strategies = get_all_active_strategies()
    
    for strategy in strategies:
        print(f"Strategy: {strategy['name']}")
        print(f"  Symbol: {strategy['symbol']}")
        print(f"  Time Frame: {strategy['time_frame']}")
        print(f"  Extended Hours: {strategy['extended_hours']}")
        print()