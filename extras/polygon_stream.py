from dotenv import load_dotenv
import websocket
import json, os, logging
from log.setupLogger import setup_logging


setup_logging()
logger = logging.getLogger(__name__)

load_dotenv()
# Replace with your Polygon API key
API_KEY = os.getenv("POLYGONE_KEY")

# Polygon's WebSocket endpoint for stocks
#SOCKET = "wss://socket.polygon.io/stocks"
SOCKET = "wss://delayed.polygon.io/stocks"


def on_open(ws):
    print("Connection opened")
    # Authenticate
    ws.send(json.dumps({"action": "auth", "params": API_KEY}))
    # Subscribe to 1-minute aggregate bars for a ticker, e.g., AAPL
    ws.send(json.dumps({"action": "subscribe", "params": "A.AAPL"}))

def on_message(ws, message):
    print("RAW MESSAGE:", message)  # print everything first
    data = json.loads(message)
    for item in data:
        if item['ev'] == 'A':
            print(f"Ticker: {item['sym']}, Open: {item['o']}, High: {item['h']}, Low: {item['l']}, Close: {item['c']}, Volume: {item['v']}, Timestamp: {item['s']}")

def on_close(ws):
    print("Connection closed")

ws = websocket.WebSocketApp(
    SOCKET,
    on_open=on_open,
    on_message=on_message,
    on_close=on_close
)

ws.run_forever()
