import logging, asyncio, time, sys
from log.setupLogger import setup_logging
from keep_token_alive import tokens_refresh_loop, refresh_tokens_once
from tradeBot.get_data.schwab_automatic_stream import run_stream
from backend.queries.strategies import get_all_active_day_trading_strategies
from dotenv import load_dotenv
from threading import Thread

# Get logger for this module
logger = logging.getLogger("trading_bot")

# Load strategies after logging is setup
list_active_strategies = get_all_active_day_trading_strategies()

if not list_active_strategies:
    logger.error("No active day trading strategies found in DataBase. Exiting...")
    sys.exit(0)
    
async def main():
    try:
        # Step 1: Refresh tokens once at startup 
        logger.info("Performing initial token refresh...")
        refresh_tokens_once()
        logger.info("Initial token refresh completed")

        # Step 2: Start token refresh in background thread
        logger.info("Starting keep token alive thread")
        token_thread = Thread(target=tokens_refresh_loop, daemon=True)
        token_thread.start()

        # Step 3: Start the stream
        logger.info("Starting trading bot")
        stream_task = asyncio.create_task(run_stream(list_active_strategies))

        await stream_task
    except KeyboardInterrupt:
        logger.info("Shutdown requested by user")
        sys.exit(0)  # Clean exit
    except Exception as e:
        logger.critical("Critical error in main")
        logger.exception(e)
        sys.exit(1)  # FATAL


if __name__ == "__main__":
    setup_logging(modules_with_files=["keep_token_alive", "trading_bot", "schwab_automatic_stream"])
    load_dotenv()

    asyncio.run(main())