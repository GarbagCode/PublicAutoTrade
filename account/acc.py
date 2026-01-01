import requests, csv, os, logging
from datetime import datetime, timezone, timedelta
from typing import Optional
from backend.queries.active_positions import add_active_position, get_order_id_list, delete_active_positions
import math


logger = logging.getLogger(__name__)

def round_price(price: float) -> float:
    """Round price to appropriate decimal places for trading."""
    if price < 1:
        return round(price, 4)  # 4 decimals
    return round(price, 2)      # 2 decimals


def fetch_accounts(TRADING_ACCESS_TOKEN: str) -> list:
    """
    Fetch Schwab account information with account numbers and hash values.

    Parameters
    ----------
    TRADING_ACCESS_TOKEN : str
        Bearer access token for the Schwab API.

    Returns
    -------
    list
        Dictionary containing account numbers and hash values.
        Returns empty list on failure.
    """
    url = "https://api.schwabapi.com/trader/v1/accounts/accountNumbers"
    headers = {"Authorization": f"Bearer {TRADING_ACCESS_TOKEN}"}

    try:
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()

        try:
            accounts = resp.json()
            logger.info(f"Successfully fetched account data: {len(accounts)} account(s)")
            return accounts
        except ValueError as e:
            logger.error(f"Invalid JSON response from Schwab API: {e}")
            return []

    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error: {e.response.status_code} - {e.response.text}")
    except requests.exceptions.Timeout:
        logger.error("Request to Schwab API timed out.")
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection error: {e}")
    except requests.exceptions.RequestException as e:
        logger.error(f"General request exception: {e}")
    except Exception as e:
        logger.exception(f"Unexpected error fetching account data: {e}")

    return []


def check_valid_acc_num(TRADING_ACCESS_TOKEN: str, acc_num: str) -> bool:
    """
    Check if a given account number is valid and exists.

    Parameters
    ----------
    TRADING_ACCESS_TOKEN : str
        Bearer access token for the Schwab API.
    acc_num : str
        Account number (hash value) to validate.

    Returns
    -------
    bool
        True if account exists, False otherwise.
    """
    if not acc_num:
        logger.warning("Account number cannot be empty")
        return False

    try:
        # Fetch account data
        accounts = fetch_accounts(TRADING_ACCESS_TOKEN)

        if not accounts:
            logger.warning("No account data returned from API")
            return False

        if not isinstance(accounts, list):
            logger.warning(f"Unexpected response format. Expected list, got {type(accounts)}")
            return False

        # Check if account number exists in the accounts list
        # accountNumbers is typically a list: [{"account_num": "hashValue", ...}]
        for account in accounts:
            if acc_num == account.get("hashValue"):
                logger.info(f"Account {acc_num} is valid")
                return True

        logger.warning(f"Account {acc_num} not found in account data")
        return False

    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error: {e.response.status_code} - {e.response.text}")
    except requests.exceptions.Timeout:
        logger.error("Request to Schwab API timed out")
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection error: {e}")
    except requests.exceptions.RequestException as e:
        logger.error(f"General request exception: {e}")
    except Exception as e:
        logger.exception(f"Unexpected error checking account validity: {e}")

    return False


def get_today_orders(TRADING_ACCESS_TOKEN: str, acc_num: str) -> list[dict] | None:
    """
    Retrieve all filled orders for the current UTC day.

    Parameters
    ----------
    TRADING_ACCESS_TOKEN : str
        Bearer access token for the Schwab API.
    acc_num : str
        Account number to query orders for.

    Returns
    -------
    list[dict] | None
        - List of filled orders for the current day, if successful.
        - None if the request fails or returns invalid data.
    """
    today = datetime.now(timezone.utc)
    tomorrow = today + timedelta(days=1)

    params = {
        "accountNumber": acc_num,
        "fromEnteredTime": today.strftime("%Y-%m-%dT00:00:00.000Z"),
        "toEnteredTime": tomorrow.strftime("%Y-%m-%dT00:00:00.000Z"),
        "status": "FILLED",
    }

    headers = {"Authorization": f"Bearer {TRADING_ACCESS_TOKEN}"}
    url = f"https://api.schwabapi.com/trader/v1/accounts/{acc_num}/orders"

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        resp.raise_for_status()

        try:
            data = resp.json()
        except ValueError as e:
            logger.error(f"Invalid JSON in response from Schwab API: {e}")
            return None

        if not isinstance(data, list):
            logger.warning(f"Unexpected response type: {type(data)}")
            return None

        return data

    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error {e.response.status_code}: {e.response.text}")
    except requests.exceptions.Timeout:
        logger.error("Request to Schwab API timed out.")
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection error while fetching orders: {e}")
    except requests.exceptions.RequestException as e:
        logger.error(f"General request exception: {e}")
    except Exception as e:
        logger.exception(f"Unexpected error in get_today_orders: {e}")

    return None


def get_orders(TRADING_ACCESS_TOKEN: str, acc_num: str, order_id: str) -> dict | None:
    """
    Retrieve details for a specific order.

    Parameters
    ----------
    TRADING_ACCESS_TOKEN : str
        Bearer access token for the Schwab API.
    acc_num : str
        Account number.
    order_id : str
        The Schwab order ID to look up.

    Returns
    -------
    dict | None
        Order details if successful, otherwise None.
    """
    url = f"https://api.schwabapi.com/trader/v1/accounts/{acc_num}/orders/{order_id}"
    headers = {"Authorization": f"Bearer {TRADING_ACCESS_TOKEN}"}

    try:
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()

        try:
            data = resp.json()
        except ValueError as e:
            logger.error(f"Invalid JSON for order {order_id}: {e}")
            return None

        if not isinstance(data, dict):
            logger.warning(f"Unexpected response type for order {order_id}: {type(data)}")
            return None

        return data

    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error fetching order {order_id}: {e.response.status_code} - {e.response.text}")
    except requests.exceptions.Timeout:
        logger.error(f"Request timed out while fetching order {order_id}.")
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection error while fetching order {order_id}: {e}")
    except requests.exceptions.RequestException as e:
        logger.error(f"General request exception fetching order {order_id}: {e}")
    except Exception as e:
        logger.exception(f"Unexpected error fetching order {order_id}: {e}")

    return None


def delete_orders(TRADING_ACCESS_TOKEN: str, acc_num: str, order_id: str) -> bool:
    """
    Cancel (delete) a pending Schwab order.

    Parameters
    ----------
    TRADING_ACCESS_TOKEN : str
        Bearer access token for the Schwab API.
    acc_num : str
        Account number.
    order_id : str
        ID of the order to cancel.

    Returns
    -------
    bool
        True if successfully deleted, False otherwise.
    """    
    url = f"https://api.schwabapi.com/trader/v1/accounts/{acc_num}/orders/{order_id}"
    headers = {"Authorization": f"Bearer {TRADING_ACCESS_TOKEN}"}

    try:
        resp = requests.delete(url, headers=headers, timeout=30)
        if resp.status_code in (200, 204):
            logger.info(f"Order {order_id} deleted successfully.")
            return True
        else:
            logger.warning(f"Failed to delete order {order_id}: {resp.status_code} - {resp.text}")
            return False

    except requests.exceptions.Timeout:
        logger.error(f"Request to cancel order {order_id} timed out.")
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection error cancelling order {order_id}: {e}")
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error cancelling order {order_id}: {e.response.status_code} - {e.response.text}")
    except requests.exceptions.RequestException as e:
        logger.error(f"General request exception cancelling order {order_id}: {e}")
    except Exception as e:
        logger.exception(f"Unexpected error cancelling order {order_id}: {e}")

    return False


def send_orders(
    TRADING_ACCESS_TOKEN: str,
    acc_num: str,
    quantity: float,
    exp_min: int,
    price: float = 0,
    symbol: str = None,
    instruction: str = "BUY",
) -> Optional[str]:
    """
    Send a market or limit order to the Schwab API.

    Parameters
    ----------
    TRADING_ACCESS_TOKEN : str
        Bearer access token for the Schwab API.
    acc_num : str
        Account number for placing the order.
    quantity : float
        Number of shares to trade.
    exp_min : int
        Minutes until order expiration (sets cancelTime).
    price : float, optional
        Limit price. Use 0 for market orders.
    symbol : str, optional
        Ticker symbol for the asset.
    instruction : str, optional
        "BUY" or "SELL".

    Returns
    -------
    str or None
        Order ID if successfully created, None otherwise.
    """
    if not symbol:
        raise ValueError("symbol must be provided")
    if quantity <= 0:
        raise ValueError("quantity must be greater than zero")

    url = f"https://api.schwabapi.com/trader/v1/accounts/{acc_num}/orders"
    headers = {
        "Authorization": f"Bearer {TRADING_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    cancel_time = (
        datetime.now(timezone.utc) + timedelta(minutes=exp_min)
    ).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

    # Rounds price to brokerages specified needs
    price = round_price(price)
    order_type = "MARKET" if price == 0 else "LIMIT"
    order_data = {
        "session": "NORMAL",
        "duration": "DAY",
        "orderType": order_type,
        "orderStrategyType": "SINGLE",
        "orderLegCollection": [
            {
                "instruction": instruction.upper(),
                "quantity": quantity,
                "instrument": {"symbol": symbol, "assetType": "EQUITY"},
            }
        ],
    }

    if price > 0:
        order_data["price"] = str(price)
    if exp_min > 0:
        order_data["cancelTime"] = cancel_time

    try:
        resp = requests.post(url, headers=headers, json=order_data, timeout=30)
        resp.raise_for_status()

        if resp.status_code == 201:
            location = resp.headers.get("Location")
            return location.split("/")[-1] if location else None

        logger.error(f"Unexpected response: {resp.status_code} - {resp.text}")
        return None

    except requests.Timeout:
        logger.error("Order request timed out.")
        return None
    except requests.ConnectionError:
        logger.error("Connection error while sending order.")
        return None
    except requests.HTTPError as e:
        logger.error(f"HTTP error: {e}")
        return None
    except Exception as e:
        logger.exception(f"Unexpected error sending order: {e}")
        return None


def send_strategy_orders(
    TRADING_ACCESS_TOKEN: str,
    acc_num: str,
    quantity: float,
    exp_min: int,
    symbol: str,
    strategy_id: int,
    price: float = 0,
    instruction: str = "BUY",
) -> Optional[str]:
    """
    Manage strategy-specific buy/sell orders and track them in a DB.

    - BUY: Sends a new order and logs it to the database.
    - SELL: Finds existing orders for the strategy, checks if filled, 
      and issues a sell or deletes pending ones.

    Parameters
    ----------
    TRADING_ACCESS_TOKEN : str
        Bearer access token for the Schwab API.
    acc_num : str
        Account number.
    quantity : float
        Quantity to trade.
    exp_min : int
        Order expiration in minutes.
    symbol : str
        Ticker symbol.
    strategy_id : int
        ID of the trading strategy.
    price : float, optional
        Limit price; 0 for market orders. Default is 0.
    instruction : str, optional
        Either "BUY" or "SELL". Default is "BUY".

    Returns
    -------
    Optional[str]
        "BUY completed" or "SELL completed" on success, None if order fails.
    
    Raises
    ------
    ValueError
        If instruction is not "BUY" or "SELL".
    """

    # Round price to broker's specified needs
    price = round_price(price)

    instruction = instruction.upper()
    if instruction not in ("BUY", "SELL"):
        raise ValueError("Instruction must be 'BUY' or 'SELL'")

    if instruction == "BUY":
        order_id: Optional[str] = send_orders(
            TRADING_ACCESS_TOKEN, acc_num, quantity, exp_min, price, symbol, "BUY"
        )
        if order_id:
            try:
                # Add the sent order to DB
                add_active_position(strategy_id, order_id, quantity, price)
            except Exception as e:
                logger.error(f"Error inserting order to DB: {e}")

            logger.info(f"Sent buy order for {symbol}, Price: {price}")
            return "BUY completed"
        return None
        

    # === SELL ===
    try:
        order_id_list = get_order_id_list(strategy_id)
        for order_id in order_id_list:
            order = get_orders(TRADING_ACCESS_TOKEN, acc_num, order_id)
            if not order:
                continue

            status = order.get("status")
            if status == "FILLED":
                filled_qty = order.get("filledQuantity", 0.0)
                if filled_qty > 0:
                    send_orders(
                        TRADING_ACCESS_TOKEN,
                        acc_num,
                        filled_qty,
                        1440,  # one-day expiry for sell
                        price,
                        symbol,
                        "SELL",
                    )
            else:
                delete_orders(TRADING_ACCESS_TOKEN, acc_num, order_id)

        # Delete sold positions
        delete_active_positions(strategy_id)

    except Exception as e:
        logger.error(f"Error processing SELL for strategy {strategy_id}: {e}")

    logger.info(f"Sent sell order for {symbol}")
    return "SELL completed"



if __name__ == "__main__":
    from dotenv import load_dotenv
    from log.setupLogger import setup_logging


    setup_logging()
    load_dotenv()
    TRADING_ACCESS_TOKEN = os.getenv("TRADING_ACCESS_TOKEN")
    ACC_NUM = os.getenv("ACC_NUM")

    if not TRADING_ACCESS_TOKEN or not ACC_NUM:
        raise EnvironmentError("Missing Schwab credentials in environment variables")

    print(send_strategy_orders(
        TRADING_ACCESS_TOKEN,
        ACC_NUM,
        quantity=1,
        exp_min=1,
        price=0,
        symbol="TQQQ",
        strategy_id=1,
        instruction="SELL"
    ))
