import pytest
import os
import json
import time
from pathlib import Path
from dotenv import load_dotenv
from keep_token_alive import refresh_tokens_once


@pytest.mark.integration
class TestRefreshTokensOnceIntegration:
    """Integration tests for refresh_tokens_once - calls API ONCE per class"""
    
    @pytest.fixture(scope="class")
    def project_root(self):
        """Get project root directory"""
        return Path(__file__).resolve().parents[2]
    
    @pytest.fixture(scope="class")
    def api_response(self, project_root):
        """
        Call the API ONCE for the entire test class.
        All tests inspect this single response.
        """
        # Verify credentials exist before calling API
        load_dotenv(override=True)
        
        for var in ["TRADING_APP_KEY", "TRADING_SECRET_KEY", "TRADING_REFRESH_TOKEN"]:
            assert os.getenv(var), f"Missing {var}"
        
        # Call API exactly once
        refresh_tokens_once()
        
        # Load the generated files
        env_path = project_root / ".env"
        token_json_path = project_root / "token.json"
        
        assert env_path.exists(), f".env not found at {env_path}"
        assert token_json_path.exists(), f"token.json not found at {token_json_path}"
        
        with open(token_json_path) as f:
            token_data = json.load(f)
        
        return {
            "env_path": env_path,
            "token_json_path": token_json_path,
            "env_content": env_path.read_text(),
            "token_data": token_data,
            "token": token_data["token"],
        }

    def test_env_file_contains_access_token(self, api_response):
        """Test .env file has TRADING_ACCESS_TOKEN"""
        env_content = api_response["env_content"]
        assert "TRADING_ACCESS_TOKEN=" in env_content, "TRADING_ACCESS_TOKEN not in .env"

    def test_env_file_contains_refresh_token(self, api_response):
        """Test .env file has TRADING_REFRESH_TOKEN"""
        env_content = api_response["env_content"]
        assert "TRADING_REFRESH_TOKEN=" in env_content, "TRADING_REFRESH_TOKEN not in .env"

    def test_token_json_has_creation_timestamp(self, api_response):
        """Test token.json includes creation_timestamp"""
        token_data = api_response["token_data"]
        assert "creation_timestamp" in token_data, "creation_timestamp missing"
        assert isinstance(token_data["creation_timestamp"], int)

    def test_token_json_has_token_object(self, api_response):
        """Test token.json has token object"""
        token_data = api_response["token_data"]
        assert "token" in token_data, "token object missing"
        assert isinstance(token_data["token"], dict)

    def test_token_has_access_token_field(self, api_response):
        """Test token contains access_token"""
        token = api_response["token"]
        assert "access_token" in token, "access_token missing"
        assert isinstance(token["access_token"], str)
        assert len(token["access_token"]) > 0, "access_token is empty"

    def test_token_has_refresh_token_field(self, api_response):
        """Test token contains refresh_token"""
        token = api_response["token"]
        assert "refresh_token" in token, "refresh_token missing"
        assert isinstance(token["refresh_token"], str)
        assert len(token["refresh_token"]) > 0, "refresh_token is empty"

    def test_token_has_expires_in_field(self, api_response):
        """Test token contains expires_in"""
        token = api_response["token"]
        assert "expires_in" in token, "expires_in missing"
        assert isinstance(token["expires_in"], int)
        assert token["expires_in"] > 0

    def test_token_has_expires_at_field(self, api_response):
        """Test token contains expires_at"""
        token = api_response["token"]
        assert "expires_at" in token, "expires_at missing"
        assert isinstance(token["expires_at"], int)
        assert token["expires_at"] > 0

    def test_token_has_token_type_field(self, api_response):
        """Test token contains token_type"""
        token = api_response["token"]
        assert "token_type" in token, "token_type missing"
        assert token["token_type"] == "Bearer"

    def test_access_token_length_reasonable(self, api_response):
        """Test access token has reasonable length (likely JWT)"""
        access_token = api_response["token"]["access_token"]
        assert len(access_token) > 50, "access_token seems too short to be valid"

    def test_refresh_token_length_reasonable(self, api_response):
        """Test refresh token has reasonable length"""
        refresh_token = api_response["token"]["refresh_token"]
        assert len(refresh_token) > 20, "refresh_token seems too short"

    def test_expires_at_is_in_future(self, api_response):
        """Test token expiration is in the future"""
        expires_at = api_response["token"]["expires_at"]
        current_time = int(time.time())
        assert expires_at > current_time, "Token already expired"

    def test_expires_at_matches_expires_in(self, api_response):
        """Test expires_at is consistent with expires_in"""
        token = api_response["token"]
        creation_timestamp = api_response["token_data"]["creation_timestamp"]
        
        # expires_at should be approximately creation_timestamp + expires_in
        expected_expires_at = creation_timestamp + token["expires_in"]
        
        # Allow 2 second tolerance for execution time
        assert abs(token["expires_at"] - expected_expires_at) <= 2, \
            "expires_at doesn't match creation_timestamp + expires_in"

    def test_data_credentials_optional(self, project_root):
        """Test DATA credentials are optional but work if present"""
        load_dotenv(override=True)
        
        MARKET_DATA_APP_KEY = os.getenv("MARKET_DATA_APP_KEY")
        MARKET_DATA_SECRET_KEY = os.getenv("MARKET_DATA_SECRET_KEY")
        MARKET_DATA_REFRESH_TOKEN = os.getenv("MARKET_DATA_REFRESH_TOKEN")
        
        if not all([MARKET_DATA_APP_KEY, MARKET_DATA_SECRET_KEY, MARKET_DATA_REFRESH_TOKEN]):
            pytest.skip("DATA credentials not configured - this is optional")
        
        # If DATA creds exist, they should have been refreshed
        env_path = project_root / ".env"
        env_content = env_path.read_text()
        
        assert "MARKET_DATA_ACCESS_TOKEN=" in env_content, "MARKET_DATA_ACCESS_TOKEN not in .env"