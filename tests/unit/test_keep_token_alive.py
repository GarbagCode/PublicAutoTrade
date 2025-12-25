from unittest.mock import patch, MagicMock
import sys, os
from keep_token_alive import get_new_access_token


# --- Test get_new_access_token --- #

@patch("keep_token_alive.requests.post")
def test_get_new_access_token_success(mock_post):
    """Test successful token refresh API call."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "access_token": "new_access",
        "refresh_token": "new_refresh",
        "expires_in": 1800
    }
    mock_post.return_value = mock_resp

    access, refresh, expires_in = get_new_access_token("app", "secret", "old_refresh")
    
    assert access == "new_access"
    assert refresh == "new_refresh"
    mock_post.assert_called_once()


@patch("keep_token_alive.requests.post")
def test_get_new_access_token_failure(mock_post):
    """Test token refresh failure handling."""
    mock_resp = MagicMock()
    mock_resp.status_code = 400
    mock_resp.text = "Invalid credentials"
    mock_post.return_value = mock_resp

    access, refresh, expires_in = get_new_access_token("app", "secret", "old_refresh")
    
    assert access is None
    assert refresh == "old_refresh"
    mock_post.assert_called_once()

