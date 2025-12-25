import os, sys
from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock
from account.acc import fetch_accounts, send_orders, delete_orders, get_today_orders

@pytest.fixture(scope="module")
def credentials():
    from dotenv import load_dotenv
    load_dotenv(".env")
    return {
        "TRADING_ACCESS_TOKEN": os.getenv("TRADING_ACCESS_TOKEN"),
        "ACC_NUM": os.getenv("ACC_NUM")
    }

# --- Patch network calls ---
@patch("account.acc.requests.delete")
@patch("account.acc.requests.post")
def test_send_and_delete_order(mock_post, mock_delete, credentials):
    # Mock order placement
    mock_post_resp = MagicMock()
    mock_post_resp.status_code = 201
    mock_post_resp.headers = {"Location": "/orders/12345"}
    mock_post.return_value = mock_post_resp

    order_id = send_orders(credentials["TRADING_ACCESS_TOKEN"], credentials["ACC_NUM"], 1, 1, symbol="SOXL")
    assert order_id == "12345"

    # Mock deletion
    mock_delete_resp = MagicMock()
    mock_delete_resp.status_code = 200
    mock_delete.return_value = mock_delete_resp

    deleted = delete_orders(credentials["TRADING_ACCESS_TOKEN"], credentials["ACC_NUM"], order_id)
    assert deleted == True

# --- Success case --- #
@patch("account.acc.requests.get")
def test_get_today_orders_success(mock_get, credentials):
    # Mock a successful API response
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = [
        {"orderId": "1", "symbol": "SOXL", "status": "FILLED"},
        {"orderId": "2", "symbol": "SPY", "status": "FILLED"}
    ]
    mock_get.return_value = mock_resp

    orders = get_today_orders(credentials["TRADING_ACCESS_TOKEN"], credentials["ACC_NUM"])

    assert isinstance(orders, list)
    assert len(orders) == 2
    assert orders[0]["orderId"] == "1"
    mock_get.assert_called_once()

    # Check that the params passed include the correct account number and status
    called_params = mock_get.call_args[1]["params"]
    assert called_params["accountNumber"] == credentials["ACC_NUM"]
    assert called_params["status"] == "FILLED"


# --- Failure case --- #
@patch("account.acc.requests.get")
def test_get_today_orders_failure(mock_get, credentials):
    # Simulate an exception from requests
    mock_get.side_effect = Exception("Network error")

    orders = get_today_orders(credentials["TRADING_ACCESS_TOKEN"], credentials["ACC_NUM"])
    
    # Function should return empty list on error
    assert orders == None

import pytest
from unittest.mock import patch, MagicMock
import sys, os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from account.acc import get_orders


@pytest.fixture
def credentials():
    return {
        "TRADING_ACCESS_TOKEN": "fake_access_token",
        "ACC_NUM": "123456789",
        "ORDER_ID": "order123"
    }


# --- Success case --- #
@patch("account.acc.requests.get")
def test_get_orders_success(mock_get, credentials):
    # Mock a successful API response
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "orderId": credentials["ORDER_ID"],
        "symbol": "SOXL",
        "status": "FILLED"
    }
    mock_get.return_value = mock_resp

    order = get_orders(credentials["TRADING_ACCESS_TOKEN"], credentials["ACC_NUM"], credentials["ORDER_ID"])

    assert isinstance(order, dict)
    assert order["orderId"] == credentials["ORDER_ID"]
    assert order["status"] == "FILLED"
    mock_get.assert_called_once()

    # Verify URL and headers
    called_url = mock_get.call_args[0][0]
    called_headers = mock_get.call_args[1]["headers"]
    assert credentials["ACC_NUM"] in called_url
    assert credentials["ORDER_ID"] in called_url
    assert called_headers["Authorization"] == f"Bearer {credentials['TRADING_ACCESS_TOKEN']}"


# --- Failure case --- #
@patch("account.acc.requests.get")
def test_get_orders_failure(mock_get, credentials):
    # Simulate a network error or API failure
    mock_get.side_effect = Exception("Network error")

    order = get_orders(credentials["TRADING_ACCESS_TOKEN"], credentials["ACC_NUM"], credentials["ORDER_ID"])
    
    # Function should return empty dict on error
    assert order == None

