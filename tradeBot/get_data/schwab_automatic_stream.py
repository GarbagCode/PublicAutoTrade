import os, sys, asyncio, websockets, logging
import pandas as pd
from schwab.auth import client_from_token_file
from schwab.streaming import StreamClient
from dotenv import load_dotenv
from datetime import datetime
from tradeBot.functions.aggregateTimeFrames import aggregate_time_frame
from tradeBot.get_data.historical_data import charles_get_candles
from account.acc import send_strategy_orders
import importlib

# Setup logging
logger = logging.getLogger("schwab_automatic_stream")

# Load Environment Variables
load_dotenv()

# Environment variables 
TRADING_APP_KEY = os.getenv("TRADING_APP_KEY")
TRADING_SECRET_KEY = os.getenv("TRADING_SECRET_KEY")
TOKEN_PATH = "token.json"
ACC_NUM = os.getenv("ACC_NUM")

df_dict = {}

# Global dict to store imported strategy functions
STRATEGY_CACHE = {}


def _import_strategy(strat_name: str) -> bool:
    """
    Dynamically import a strategy function and cache it globally.
    Only imports once at startup.
    
    Each strategy module should have a 'main' function that processes the dataframe.
    
    Args:
        strat_name: Name of the strategy module (e.g., 'sma_cross')
                   The module should be at tradeBot/strategies/{strat_name}.py
                   and contain a 'main' function
    
    Returns:
        bool: True if import successful, False otherwise
    
    Example:
        # File: tradeBot/strategies/sma_cross.py
        def main(df):
            # strategy logic
            return df
    """
    global STRATEGY_CACHE
    
    # Skip if already imported
    if strat_name in STRATEGY_CACHE:
        logger.debug(f"[IMPORT] Strategy '{strat_name}' already cached, skipping import")
        return True
    
    try:
        strat_folder = "tradeBot.strategies."
        module_path = strat_folder + strat_name
        logger.info(f"[IMPORT] Attempting to import strategy module '{module_path}'")

        # Import the module
        module = importlib.import_module(module_path)
        
        # Get the main function from the module
        if hasattr(module, 'main'):
            strat_func = getattr(module, 'main')
            
            # Cache the function globally
            STRATEGY_CACHE[strat_name] = strat_func
            
            logger.info(f"[IMPORT SUCCESS] Strategy '{strat_name}.main()' imported and cached")
            return True
        else:
            logger.error(
                f"[IMPORT ERROR] Module '{module_path}' does not contain a 'main' function. "
                f"Available attributes: {dir(module)}"
            )
            return False
            
    except ModuleNotFoundError as e:
        logger.error(
            f"[IMPORT ERROR] Strategy module '{module_path}' not found. "
            f"Ensure the file exists at 'tradeBot/strategies/{strat_name}.py'"
        )
        logger.exception(e)
        return False
        
    except ImportError as e:
        logger.error(
            f"[IMPORT ERROR] Failed to import strategy module '{module_path}'. "
            f"Check for syntax errors or missing dependencies in the strategy file."
        )
        logger.exception(e)
        return False
        
    except Exception as e:
        logger.error(
            f"[IMPORT ERROR] Unexpected error importing strategy '{strat_name}': {e}"
        )
        logger.exception(e)
        return False


def _import_all_strategies(strategy_info: list[dict]) -> None:
    """
    Import all strategy functions at startup.
    
    Args:
        strategy_info: List of strategy dicts from database
    """
    logger.info(f"[STARTUP] Importing {len(strategy_info)} strategy modules...")
    
    success_count = 0
    fail_count = 0
    
    # Get unique strategy names
    unique_strategies = set(strat['name'] for strat in strategy_info)
    
    for strat_name in unique_strategies:
        if _import_strategy(strat_name):
            success_count += 1
        else:
            fail_count += 1
    
    logger.info(
        f"[STARTUP] Strategy import complete: "
        f"{success_count} successful, {fail_count} failed"
    )
    
    if fail_count > 0:
        logger.warning(
            f"[STARTUP] {fail_count} strategies failed to import. "
            f"Check logs above for details."
        )


def _initial_df(strategy_info: list[dict], MARKET_DATA_ACCESS_TOKEN: str) -> None:
    """
    Load initial historical data for each strategy configuration.
    Creates df_dict entries with [DataFrame, itsTime_flag] structure.
    
    Args:
        strategy_info: List of dicts containing strategy configuration
                      Keys: id, name, symbol, time_frame, lookback_days, extended_hours
        MARKET_DATA_ACCESS_TOKEN: Token for data access
    """
    global df_dict

    try:
        for strat in strategy_info:
            strat_id = strat["id"]
            strat_name = strat["name"]
            symbol = strat["symbol"].upper()
            order_type = strat["order_type"].upper()
            time_frame = strat["time_frame"]
            lookback_days = strat["lookback_days"]
            extended_hours = strat["extended_hours"] == 1  # Convert 0/1 to bool

            # Initialize with historical data
            historical_df = charles_get_candles(
                MARKET_DATA_ACCESS_TOKEN, 
                symbol, 
                period=lookback_days, 
                need_extended_hours_data=extended_hours
            )
            
            # Store using strategy_id as key
            df_dict[strat_id] = {
                'df': historical_df,
                'itsTime': False,
                'name': strat_name,
                'symbol': symbol,
                'order_type': order_type,
                'time_frame': time_frame,
                'extended_hours': extended_hours
            }
            
            logger.info(
                f"[INIT] Strategy ID {strat_id}: Loaded {symbol} historical data "
                f"for '{strat_name}' strategy (timeframe: {time_frame}min)"
            )

        logger.info(f"[INIT] Successfully loaded {len(df_dict)} strategy configurations")
        return None
        
    except Exception as e:
        logger.error(f"[INIT ERROR] Failed to initialize historical bars: {e}")
        logger.exception(e)
        return None


def its_time(minute, time_frame: int) -> bool:
    """Check if current minute aligns with timeframe"""
    return minute % time_frame == 0

        
async def run_stream(strategy_info: list[dict]):
    """
    Main streaming function
    
    Args:
        strategy_info: List of dictionaries containing strategy configuration.
                      Each dict contains: id, name, symbol, time_frame, lookback_days, extended_hours
                      Example: [
                          {
                              'id': 1,
                              'name': 'smaCross',
                              'symbol': 'SPY',
                              'time_frame': 5,
                              'lookback_days': 10,
                              'extended_hours': 0
                          }
                      ]
    """
    global df_dict

    # Reloads dotenv in case variables are stale
    load_dotenv(override=True)
    MARKET_DATA_ACCESS_TOKEN = os.getenv("MARKET_DATA_ACCESS_TOKEN")

    # Extract unique symbols for subscription
    list_symbols = list(set(strat["symbol"].upper() for strat in strategy_info))
    logger.info(f"[STREAM INIT] Preparing to subscribe to {len(list_symbols)} unique symbols: {list_symbols}")

    # Load initial historical data
    _initial_df(strategy_info, MARKET_DATA_ACCESS_TOKEN)
    
    # Import all strategies ONCE at startup
    _import_all_strategies(strategy_info)


    try:
        client = client_from_token_file(
            token_path=TOKEN_PATH, 
            api_key=TRADING_APP_KEY,
            app_secret=TRADING_SECRET_KEY,
            asyncio=True,
        )

        stream = StreamClient(client, account_id=ACC_NUM)
        logger.info("[STREAM INIT] Stream client initialized successfully for account")

    except Exception as e:
        logger.critical(f"[STREAM INIT FAILED] Unable to initialize stream client: {e}")
        logger.exception(e)
        sys.exit(1)

    def on_bar(msg):
        """Handle incoming bar data from stream"""
        global df_dict

        content = msg.get("content", [])
        if not content:
            return

        for item in content:
            # Parse bar timestamp
            bar_ts = pd.to_datetime(
                item.get("CHART_TIME_MILLIS"), 
                unit='ms', 
                utc=True
            ).tz_convert("America/New_York")
            bar_min = bar_ts.minute

            # Get symbol from bar data
            bar_symbol = item.get('key', '').upper()
            if not bar_symbol:
                logger.warning("[BAR DATA] Received bar without symbol key, skipping")
                continue

            # Process each strategy configuration
            for strategy_id, strategy_data in df_dict.items():
                # Only process if symbol matches
                if strategy_data['symbol'] != bar_symbol:
                    continue

                strategy_name = strategy_data['name']
                symbol = strategy_data['symbol']
                time_frame = strategy_data['time_frame']

                # Check itsTime flag
                if not strategy_data['itsTime']:
                    # Check if current minute aligns with timeframe boundary
                    if its_time(bar_min, time_frame):
                        df_dict[strategy_id]['itsTime'] = True
                        logger.debug(
                            f"[TIMEFRAME] Strategy ID {strategy_id} ({symbol}): "
                            f"Reached {time_frame}min boundary at minute {bar_min}, activating processing"
                        )
                    else:
                        continue
                
                try:
                    # Create new bar DataFrame
                    new_bars = pd.DataFrame([{
                        'datetime': item.get('CHART_TIME_MILLIS', 0),
                        'symbol': bar_symbol, 
                        'open': item.get('OPEN_PRICE', 0),
                        'high': item.get('HIGH_PRICE', 0),
                        'low': item.get('LOW_PRICE', 0),
                        'close': item.get('CLOSE_PRICE', 0),
                        'volume': item.get('VOLUME', 0)
                    }])

                    new_bars['datetime'] = pd.to_datetime(
                        new_bars['datetime'], 
                        unit='ms', 
                        utc=True
                    ).dt.tz_convert('America/New_York')

                    new_bars.set_index('datetime', inplace=True)
                    new_bars.sort_index(inplace=True)

                    # Append new bar
                    df_dict[strategy_id]['df'] = pd.concat(
                        [df_dict[strategy_id]['df'], new_bars]
                    ).sort_index()
                    
                    logger.debug(
                        f"[DATA UPDATE] Strategy ID {strategy_id} ({symbol}): "
                        f"Added bar at {new_bars.index[0]}"
                    )

                    # Aggregate to desired timeframe
                    if time_frame == 1:
                        candle_time_frame_df = df_dict[strategy_id]['df']
                    else:
                        candle_time_frame_df = aggregate_time_frame(
                            df_dict[strategy_id]['df'],
                            aggregation=time_frame
                        )

                    if candle_time_frame_df.empty:
                        continue

                    # Add delay for TOS processing
                    tosDelay = 1
                    if its_time(bar_min + tosDelay, time_frame):
                        try:           
                            # Get the cached function (fast lookup, no import)
                            strat_func = STRATEGY_CACHE.get(strategy_name)
                            
                            if strat_func is None:
                                logger.error(
                                    f"[STRATEGY ERROR] Strategy '{strategy_name}' not found in cache. "
                                    f"Was it imported at startup?"
                                )
                                continue

                            new_strat_df = strat_func(candle_time_frame_df)
                                
                            logger.debug(
                                f"[STRATEGY EXEC] Strategy ID {strategy_id} ({strategy_name}): "
                                f"Executed on {symbol}"
                            )
                            print(f"\nStrategy ID: {strategy_id} output:")
                            print(new_strat_df.tail())

                            # Get most recent candle to check for signals
                            recent_candle = new_strat_df.iloc[-1]
                            
                            # Check if strategy generated a trading signal
                            if recent_candle.get("signal"):
                                # Reload env in case tokens are stale
                                load_dotenv(override=True)
                                TRADING_ACCESS_TOKEN = os.getenv("TRADING_ACCESS_TOKEN")
                                ACC_NUM = os.getenv("ACC_NUM")

                                quantity = recent_candle.get("quantity", 0)
                                instruction = recent_candle["signal"].upper()

                                logger.info(
                                    f"[ORDER] Strategy ID {strategy_id} ({strategy_name}): "
                                    f"Placing {instruction} {strategy_data['order_type']} order for {quantity} shares of {symbol}"
                                )
                                
                                # Price == 0, default to market order
                                price = 0 
                                # Price != 0 -> limit order
                                if strategy_data['order_type'] == "LIMIT":
                                    price = recent_candle.get('close')
                                    
                                
                                result = send_strategy_orders(
                                    TRADING_ACCESS_TOKEN,
                                    ACC_NUM,
                                    quantity=quantity,
                                    exp_min=time_frame,
                                    symbol=symbol, 
                                    strategy_id=strategy_id,
                                    price=price,
                                    instruction=instruction
                                )

                            logger.debug(f"Strategy {strategy_id} completed")
                            logger.debug(f"\n{new_strat_df.tail()}")
                            
                        except AttributeError:
                            logger.error(
                                f"[STRATEGY ERROR] Strategy function '{strategy_name}' not found. "
                                f"Ensure it's imported at the top of the file."
                            )
                        except KeyError as e:
                            logger.error(
                                f"[STRATEGY ERROR] KeyError in strategy '{strategy_name}' (ID {strategy_id}): {e}"
                            )
                            logger.error(f"[STRATEGY ERROR] Available columns: {candle_time_frame_df.columns.tolist()}")
                        except Exception as e:
                            logger.error(
                                f"[STRATEGY ERROR] Strategy '{strategy_name}' (ID {strategy_id}) "
                                f"encountered error: {e}"
                            )
                            logger.exception(e)
                                    
                except Exception as e:
                    logger.error(
                        f"[BAR PROCESSING ERROR] Failed to process bar data for {symbol} "
                        f"(Strategy ID {strategy_id}): {e}"
                    )
                    logger.exception(e)

    # Login and subscribe to streams
    await stream.login()
    logger.info(
        f"[STREAM CONNECTED] Logged into stream, subscribing to {len(list_symbols)} symbols: {list_symbols}"
    )
    
    stream.add_chart_equity_handler(on_bar)
    await stream.chart_equity_subs(list_symbols)
    logger.info(f"[STREAM ACTIVE] Successfully subscribed to equity chart data")

    # Main message handling loop
    while True:
        try:
            await stream.handle_message()
        except websockets.exceptions.ConnectionClosedOK:
            logger.warning("[WEBSOCKET] Connection closed normally. Attempting reconnection...")
            await asyncio.sleep(1)
            try:
                await stream.login()
                stream.add_chart_equity_handler(on_bar)
                await stream.chart_equity_subs(list_symbols)
                logger.info("[WEBSOCKET] Reconnected successfully")
            except Exception as e:
                logger.error(f"[WEBSOCKET] Reconnection attempt failed: {e}")
                await asyncio.sleep(5)
        except websockets.exceptions.ConnectionClosed as e:
            logger.error(f"[WEBSOCKET FATAL] Connection closed unexpectedly: {e}")
            logger.exception(e)
            logger.critical("[WEBSOCKET FATAL] Unable to maintain stream connection - exiting")
            sys.exit(1)
        except Exception as e:
            logger.critical(f"[STREAM FATAL] Unexpected error in stream handler: {e}")
            logger.exception(e)
            sys.exit(1)


if __name__ == "__main__":
    from queries.strategies import get_all_active_strategies

    # Get active strategies from database (now returns list of dicts)
    list_active_strategies = get_all_active_strategies()
    
    logger.info(f"[STARTUP] Loaded {len(list_active_strategies)} active strategies from database")
    
    # Log strategy details using dict keys
    strategy_summary = [
        (s['id'], s['name'], s['symbol'].upper(), s['time_frame']) 
        for s in list_active_strategies
    ]
    logger.info(f"[STARTUP] Strategy details: {strategy_summary}")

    load_dotenv()
    asyncio.run(run_stream(list_active_strategies))