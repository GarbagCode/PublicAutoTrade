import os, asyncio, time, sys, logging
from schwab.auth import client_from_manual_flow
from schwab.streaming import StreamClient
from dotenv import load_dotenv
import pandas as pd
from datetime import datetime
from aggregateTimeFrames import aggregate_time_frame
from tradeBot.strategies.leverageTurtle import leverage_turtle
from account.acc import send_strategy_orders
from keep_token_alive import token_refresh_loop

load_dotenv()
logger = logging.getLogger(__name__)

#Environment variables 
TRADING_APP_KEY = os.getenv("TRADING_APP_KEY")
TRADING_SECRET_KEY = os.getenv("TRADING_SECRET_KEY")
CALLBACK = "https://127.0.0.1:8182"
TOKEN_PATH = "token.json"
ACC_NUM = os.getenv("ACC_NUM")
TRADING_ACCESS_TOKEN = os.getenv("TRADING_ACCESS_TOKEN")
TRADING_REFRESH_TOKEN = os.getenv("TRADING_REFRESH_TOKEN")

#Simulate a databse of strategies
active_strategies = [leverage_turtle]
timeFrame = 5
itsTime = False
symbol = "SOXL"

# Global DataFrame to store bars
bars_df = pd.DataFrame(columns=['symbol', 'open', 'high', 'low', 'close', 'volume'])
bars_df.index.name = 'datetime'  # sets name of the index

def its_time(minute, timeFrame: int) -> bool:
    return minute % timeFrame == 0

async def token_refresh_loop(api_key, secret, refresh_token):
    while True:
        try:
            # refresh token logic here
            ...
        except Exception as e:
            print("Token refresh failed:", e)
        await asyncio.sleep(60 * 5)  # wait 5 minutes before next refresh
        
async def run_stream():

    global bars_df
    
    client = client_from_manual_flow(
        api_key=TRADING_APP_KEY,
        app_secret=TRADING_SECRET_KEY,
        callback_url=CALLBACK,
        token_path=TOKEN_PATH,
        asyncio=True
    )
    
    stream = StreamClient(client, account_id=ACC_NUM)

    def on_bar(msg):
        global bars_df
        global timeFrame
        global itsTime
        global symbol
    

        content = msg.get("content", [])
        if not content:
            return

        bar_ts = pd.to_datetime(content[0].get("CHART_TIME_MILLIS"), unit='ms', utc=True).tz_convert("America/New_York")
        bar_min = bar_ts.minute
        if not itsTime:
            if its_time(bar_min, timeFrame):
                itsTime = True
            else:
                return "It's not time yet"
        

        # Build DataFrame from all bars at once (faster)
        new_bars = pd.DataFrame([{
            'datetime': datetime.fromtimestamp(item.get('CHART_TIME_MILLIS', 0) / 1000),
            'symbol': item.get('key', symbol),
            'open': item.get('OPEN_PRICE', 0),
            'high': item.get('HIGH_PRICE', 0),
            'low': item.get('LOW_PRICE', 0),
            'close': item.get('CLOSE_PRICE', 0),
            'volume': item.get('VOLUME', 0)
        } for item in content])

        # Convert timezone safely (vectorized)
        new_bars['datetime'] = (
            pd.to_datetime(new_bars['datetime'], utc=True)
            .dt.tz_convert('America/New_York')
        )


        # Set datetime as index once (on new data only)
        new_bars.set_index('datetime', inplace=True)
        new_bars.sort_index(inplace=True)

        # Append the new bar first
        bars_df = pd.concat([bars_df, new_bars])

        if timeFrame == 1:
            candle_time_frame_df = bars_df
        else:
            # Aggregate to the target timeframe
            candle_time_frame_df = aggregate_time_frame(bars_df, aggregation=timeFrame)

        if not candle_time_frame_df.empty:
            tosDelay = 1
            if its_time(bar_min + tosDelay, timeFrame):
                for strat in active_strategies:
                    # Run the strategy on the aggregated data
                    strat_df = strat(candle_time_frame_df)
                    
                    recent_candle = strat_df.iloc[-1]
                    #Checks the most recent candle for signals
                    if recent_candle["strategy"]:
                        quantity = recent_candle["quantity"]
                        symbol = recent_candle["symbol"]
                        instruction = recent_candle["strategy"]
                        strategy_name = strat.__name__
                        """
                        print(
                            send_strategy_orders(
                                TRADING_ACCESS_TOKEN,
                                ACC_NUM,
                                quantity=quantity,
                                exp_min=timeFrame,
                                symbol=symbol,
                                strategy_name=strategy_name,
                                instruction=instruction
                            )
                        )
                        """
                    # Print summary
                    print(strat_df.tail())
                    #print(strat_df.loc[(strat_df["strategy"] == "buy") | (strat_df["strategy"] == "sell"), ["strategy"]])
                    #print(bars_df.tail())  # Show last 5 bars

    await stream.login()
    stream.add_chart_equity_handler(on_bar)
    await stream.chart_equity_subs([symbol])

    while True:
        await stream.handle_message()

async def main():
    # Run both token refresh and streaming concurrently
    token_task = asyncio.create_task(token_refresh_loop(TRADING_APP_KEY, TRADING_SECRET_KEY, TRADING_REFRESH_TOKEN))
    stream_task = asyncio.create_task(run_stream())

    await asyncio.gather(token_task, stream_task)

if __name__ == "__main__":
    asyncio.run(run_stream()) 