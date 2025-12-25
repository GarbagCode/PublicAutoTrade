import requests, time, os, base64, json, logging
from dotenv import load_dotenv, set_key
from pathlib import Path


# Setup logging
logger = logging.getLogger(__name__)

# Determine root directory of your project
root_dir = Path(__file__).resolve().parent.parent


def get_new_access_token(
    app_key: str,
    secret_key: str,
    refresh_token: str,
    token_url: str = "https://api.schwabapi.com/v1/oauth/token"
) -> tuple[str | None, str, int | None]:
    """
    Exchange a refresh token for a new access token.
    
    Args:
        app_key: Application key for authentication
        secret_key: Secret key for authentication
        refresh_token: Current refresh token
        token_url: Token endpoint URL
        
    Returns:
        Tuple of (access_token, refresh_token, expires_in)
    """
    # Encode client_id and client_secret for Basic Auth
    auth_str = f"{app_key}:{secret_key}"
    b64_auth_str = base64.b64encode(auth_str.encode()).decode()

    headers = {
        "Authorization": f"Basic {b64_auth_str}",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token
    }
    
    try:
        response = requests.post(token_url, headers=headers, data=data)

        if response.status_code == 200:
            tokens = response.json()
            new_access_token = tokens["access_token"]
            new_refresh_token = tokens.get("refresh_token", refresh_token)
            expires_in = tokens["expires_in"]
            return new_access_token, new_refresh_token, expires_in
        else:
            logger.error(f"Token refresh failed: {response.status_code} {response.text}")
            return None, refresh_token, None
    except requests.RequestException as e:
        logger.error(f"Token refresh request error: {e}")
        return None, refresh_token, None


def _load_and_validate_credentials() -> dict[str, list[str]]:
    """
    Load and validate credentials from environment variables.
    
    Returns:
        Dictionary with token configurations
        
    Raises:
        SystemExit: If required credentials are missing
    """
    load_dotenv()

    # Load TRADING credentials
    TRADING_APP_KEY = os.getenv("TRADING_APP_KEY")
    TRADING_SECRET_KEY = os.getenv("TRADING_SECRET_KEY")
    TRADING_REFRESH_TOKEN = os.getenv("TRADING_REFRESH_TOKEN")

    # Load DATA credentials
    MARKET_DATA_APP_KEY = os.getenv("MARKET_DATA_APP_KEY")
    MARKET_DATA_SECRET_KEY = os.getenv("MARKET_DATA_SECRET_KEY")
    MARKET_DATA_REFRESH_TOKEN = os.getenv("MARKET_DATA_REFRESH_TOKEN")

    # Validate TRADING credentials
    if not all([TRADING_APP_KEY, TRADING_SECRET_KEY, TRADING_REFRESH_TOKEN]):
        logger.error("Missing TRADING credentials in .env file")
        raise SystemExit(1)

    # Validate DATA credentials
    if not all([MARKET_DATA_APP_KEY, MARKET_DATA_SECRET_KEY, MARKET_DATA_REFRESH_TOKEN]):
        logger.error("Missing DATA credentials in .env file")
        raise SystemExit(1)

    # Build and return token dictionary
    return {
        "TRADING": [TRADING_APP_KEY, TRADING_SECRET_KEY, TRADING_REFRESH_TOKEN],
        "MARKET_DATA": [MARKET_DATA_APP_KEY, MARKET_DATA_SECRET_KEY, MARKET_DATA_REFRESH_TOKEN]
    }


def _update_env_file(env_path: Path, token_type: str, access_token: str, refresh_token: str) -> None:
    """Update .env file with new tokens."""
    set_key(env_path, f"{token_type}_ACCESS_TOKEN", access_token)
    set_key(env_path, f"{token_type}_REFRESH_TOKEN", refresh_token)
    logger.info(f"Updated {token_type} tokens in .env file")


def _update_token_json(
    token_json_path: Path, 
    access_token: str, 
    refresh_token: str, 
    expires_in: int
) -> None:
    """Update token.json file with new TRADING token data."""
    token_data = {
        "creation_timestamp": int(time.time()),
        "token": {
            "expires_in": expires_in,
            "token_type": "Bearer",
            "scope": "api",
            "refresh_token": refresh_token,
            "access_token": access_token,
            "expires_at": int(time.time()) + expires_in
        }
    }
    token_json_path.write_text(json.dumps(token_data, indent=2))
    logger.info(f"Updated Schwab token JSON: {token_json_path}")


def refresh_tokens_once() -> None:
    """
    Refresh Schwab access tokens and update .env and token.json files only once.
    """
    # Load credentials
    token_dict = _load_and_validate_credentials()

    # Define paths
    env_path = Path(__file__).resolve().parent / ".env"
    token_json_path = Path(__file__).resolve().parent / "token.json"

    try:
        for token_type, credentials in token_dict.items():
            app_key, secret_key, refresh_token = credentials
            
            logger.info(f"Refreshing {token_type} token once...")
            
            # Get new tokens
            access_token, new_refresh_token, expires_in = get_new_access_token(
                app_key, 
                secret_key, 
                refresh_token
            )
            
            if access_token is None:
                logger.warning(f"Failed to refresh {token_type} token. Skipping...")
                continue

            # Update .env file
            _update_env_file(env_path, token_type, access_token, new_refresh_token)
            logger.info(f"{token_type} token refreshed successfully.")

            # Create token.json for TRADING tokens only
            if token_type == "TRADING":
                try:
                    token_json_path.parent.mkdir(parents=True, exist_ok=True)
                    _update_token_json(
                        token_json_path, 
                        access_token, 
                        new_refresh_token, 
                        expires_in or 1800
                    )
                    if not token_json_path.exists():
                        logger.info(f"Created new token.json file: {token_json_path}")
                except Exception as e:
                    logger.error(f"Failed to create/update token.json: {e}", exc_info=True)

    except Exception as e:
        logger.error(f"Token refresh once error: {e}", exc_info=True)


def tokens_refresh_loop(interval_min: int = 25) -> None:
    """
    Continuously refresh Schwab access tokens and update .env and token.json files.
    
    Args:
        interval_min: Minutes between refresh attempts (default: 25)
    """
    # Load credentials
    token_dict = _load_and_validate_credentials()

    # Define paths
    env_path = Path(__file__).resolve().parent / ".env"
    token_json_path = Path(__file__).resolve().parent / "token.json"
    
    logger.info(f"Starting token refresh loop with {interval_min} minute interval...")
    
    while True:
        try:
            for token_type, credentials in token_dict.items():
                app_key, secret_key, refresh_token = credentials
                
                logger.info(f"Refreshing {token_type} token...")
                
                # Get new tokens
                access_token, new_refresh_token, expires_in = get_new_access_token(
                    app_key, 
                    secret_key, 
                    refresh_token
                )
                
                if access_token is None:
                    logger.warning(f"Failed to refresh {token_type} token. Skipping...")
                    continue

                # Update in-memory token dict
                token_dict[token_type][2] = new_refresh_token

                # Update .env file
                _update_env_file(env_path, token_type, access_token, new_refresh_token)
                logger.info(f"{token_type} token refreshed successfully.")

                # Create/Update token.json for TRADING tokens only
                if token_type == "TRADING":
                    try:
                        token_json_path.parent.mkdir(parents=True, exist_ok=True)
                        _update_token_json(
                            token_json_path, 
                            access_token, 
                            new_refresh_token, 
                            expires_in or 1800
                        )
                    except Exception as e:
                        logger.error(f"Failed to update token.json: {e}", exc_info=True)

            logger.info(f"Sleeping for {interval_min} minutes until next refresh...")
            time.sleep(interval_min * 60)

        except Exception as e:
            logger.error(f"Token refresh loop error: {e}", exc_info=True)
            logger.info("Retrying in 60 seconds...")
            time.sleep(60)


if __name__ == "__main__":
    logger.info("Starting token refresh...")
    refresh_tokens_once()
    tokens_refresh_loop()