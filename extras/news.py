import requests
import datetime as dt
from datetime import datetime
from zoneinfo import ZoneInfo


def get_polygon_news(api_key: str):
    """
    Fetches Polygon.io news from the past 2 hours and prints any items
    published exactly at the top or half of the hour (00 or 30 minutes).

    Parameters
    ----------
    api_key : str
        Polygon.io API key.
    """
    try:
        now = dt.datetime.utcnow()
        since = (now - dt.timedelta(hours=2)).isoformat(timespec="seconds") + "Z"

        url = "https://api.polygon.io/v2/reference/news"
        params = {
            "published_utc.gte": since,
            "limit": 1000,
            "apiKey": api_key,
        }

        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()

        results = data.get("results", [])
        if not results:
            print("No recent news found.")
            return []

        hits = [
            (n["published_utc"], n.get("tickers", []), n.get("title", ""))
            for n in results
        ]

        matched = []
        for ts, tickers, title in hits:
            dt_utc = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            dt_et = dt_utc.astimezone(ZoneInfo("America/New_York"))

            if dt_et.minute in (0, 30):
                matched.append((dt_et, tickers, title))
                print(dt_et, tickers, title)

        return matched

    except requests.exceptions.RequestException as e:
        print(f"Request error while fetching Polygon news: {e}")
        return []
    except Exception as e:
        print(f"Unexpected error: {e}")
        return []


if __name__ == "__main__":
    import os
    from dotenv import load_dotenv

    load_dotenv()
    POLYGON_KEY = os.getenv("POLYGONE_KEY") or os.getenv("POLYGON_KEY")

    if not POLYGON_KEY:
        raise ValueError("Missing POLYGON_KEY in environment variables")

    get_polygon_news(POLYGON_KEY)
