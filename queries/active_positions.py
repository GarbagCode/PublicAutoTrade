from backend.dbConn import connect_to_db


def add_active_position(strategy_id: int, order_id: str, quantity: float, entry_price: float) -> None:
    """
    Add a new active position to the database.
    
    Args:
        strategy_id (int): The ID of the strategy associated with this position.
        order_id (str): The unique order identifier.
        quantity (float): The quantity of the position.
        entry_price (float): The entry price of the position.
    
    Raises:
        Exception: If database connection fails or insert operation fails.
    """
    conn = None
    try:
        # Connect to DB
        conn = connect_to_db()

        # Create a cursor
        cur = conn.cursor()

        # Add row into active_positions
        cur.execute("INSERT INTO active_positions(strategy_id, order_id, quantity, entry_price) VALUES (?, ?, ?, ?)", (strategy_id, order_id, quantity, entry_price))
        
        conn.commit()

    finally:
        if conn:
            conn.close()


def get_order_id_list(strategy_id: int) -> list:
    """
    Retrieve all order IDs associated with a specific strategy.
    
    Args:
        strategy_id (int): The ID of the strategy to query.
    
    Returns:
        list: A list of order ID strings for the given strategy.
    
    Raises:
        Exception: If database connection fails or query execution fails.
    """
    conn = None
    try:
        # Connect to DB
        conn = connect_to_db()

        # Create a cursor
        cur = conn.cursor()

        # Get all order id linked to strategy id
        cur.execute("SELECT order_id from active_positions WHERE strategy_id = ?", (strategy_id,))

        strategies = cur.fetchall()

        return [strat[0] for strat in strategies]

    finally:
        if conn:
            conn.close()


def delete_active_positions(strategy_id: int) -> None:
    """
    Delete all active positions associated with a specific strategy.
    
    Args:
        strategy_id (int): The ID of the strategy whose positions should be deleted.
    
    Raises:
        Exception: If database connection fails or delete operation fails.
    """
    conn = None
    try:
        # Connect to DB
        conn = connect_to_db()

        # Create a cursor
        cur = conn.cursor()

        # Delete all positions for the strategy
        cur.execute("DELETE FROM active_positions WHERE strategy_id = ?", (strategy_id,))
        
        conn.commit()

    finally:
        if conn:
            conn.close()
            
if __name__ == "__main__":
    print(add_active_position(1, "3847529", 1, 1))
