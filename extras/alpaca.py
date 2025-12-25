import websocket
import json
import os
from dotenv import load_dotenv


load_dotenv()

# Your Alpaca credentials
API_KEY = os.getenv("ALPACA_APP_KEY")
API_SECRET = os.getenv("ALPACA_SECRET_KEY")

# WebSocket URL (use paper trading URL for testing)
SOCKET_URL = "wss://stream.data.alpaca.markets/v2/sip"  # Free IEX data
# For SIP data (paid): "wss://stream.data.alpaca.markets/v2/sip"

def on_open(ws):
    print("Connection opened")
    
    # Authenticate
    auth_message = {
        "action": "auth",
        "key": API_KEY,
        "secret": API_SECRET
    }
    ws.send(json.dumps(auth_message))
    
    # Subscribe to 1-minute bars
    subscribe_message = {
        "action": "subscribe",
        "bars": ["AAPL"]  # Add your symbols here
    }
    ws.send(json.dumps(subscribe_message))

def on_message(ws, message):
    data = json.loads(message)
    print(json.dumps(data, indent=2))

def on_error(ws, error):
    print(f"Error: {error}")

def on_close(ws, close_status_code, close_msg):
    print("Connection closed")

# Create WebSocket connection
ws = websocket.WebSocketApp(
    SOCKET_URL,
    on_open=on_open,
    on_message=on_message,
    on_error=on_error,
    on_close=on_close
)

# Run forever
ws.run_forever()


