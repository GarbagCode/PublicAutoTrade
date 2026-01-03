from flask import Flask, request
import os, base64, requests
from dotenv import load_dotenv
from urllib.parse import unquote

#initialize flask app
app = Flask(__name__)

#get env variables
load_dotenv()
MARKET_DATA_APP_KEY = os.getenv("MARKET_DATA_APP_KEY")
MARKET_DATA_SECRET_KEY = os.getenv("MARKET_DATA_SECRET_KEY")
TRADING_APP_KEY = os.getenv("TRADING_APP_KEY")
TRADING_SECRET_KEY = os.getenv("TRADING_SECRET_KEY")

TOKEN_URL   = "https://api.schwabapi.com/v1/oauth/token"
MARKET_DATA_REDIRECT_URI = os.getenv("MARKET_DATA_REDIRECT_URI")
TRADING_REDIRECT_URI = os.getenv("TRADING_REDIRECT_URI")


@app.route("/")
def home():
    return "App working, please go to 'https://github.com/GarbagCode/PublicAutoTrade' for help on implementation" 


@app.route("/data", methods=["GET"])
def data_callback_root():
    qCode = request.args.get("code")

    if not qCode:
        return "No ?code=... in query string", 400

    code = unquote(qCode)
    basic = base64.b64encode(f"{MARKET_DATA_APP_KEY}:{MARKET_DATA_SECRET_KEY}".encode()).decode()

    resp = requests.post(
        TOKEN_URL,
        headers={
            "Authorization": f"Basic {basic}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={
            "grant_type": "authorization_code",
            "code": code,                   
            "redirect_uri": MARKET_DATA_REDIRECT_URI,     # exact string as registered
        },
        timeout=30,
    )

    return resp.json()


@app.route("/acc", methods=["GET"])
def acc_call_root():
    qCode = request.args.get("code")

    if not qCode:
        return "No ?code=... in query string", 400

    code = unquote(qCode)
    basic = base64.b64encode(f"{TRADING_APP_KEY}:{TRADING_SECRET_KEY}".encode()).decode()

    resp = requests.post(
        TOKEN_URL,
        headers={
            "Authorization": f"Basic {basic}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={
            "grant_type": "authorization_code",
            "code": code,                     
            "redirect_uri": TRADING_REDIRECT_URI,     # exact string as registered
        },
        timeout=30,
    )

    return resp.json()


if __name__ == "__main__":
    app.run(debug=True, port=5000)
