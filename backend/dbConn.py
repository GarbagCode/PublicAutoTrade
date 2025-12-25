import sqlite3
import logging


logger = logging.getLogger(__name__)
def connect_to_db():
    try:
        conn = None
        # connect to DB (creates file if it doesn't exist)
        conn = sqlite3.connect("database/autoTrade.db")
        conn.row_factory = sqlite3.Row # Always return dicts
        
        # Return connection to DB
        return conn

    except Exception as e:
        logger.critical("Error connecting to db {e}")
        if conn:
            conn.close()
        return None

if __name__ == "__main__":
    connect_to_db()