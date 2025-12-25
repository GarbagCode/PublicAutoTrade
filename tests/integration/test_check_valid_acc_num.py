import pytest
import os
from dotenv import load_dotenv
from account.acc import check_valid_acc_num
from keep_token_alive import refresh_tokens_once


@pytest.mark.integration
class TestCheckValidAccNumIntegration:
    """Integration tests for check_valid_acc with real API calls"""

    @pytest.fixture(scope="class")
    def integration_context(self):
        """Fixture to provide a valid access token"""

        refresh_tokens_once()
        load_dotenv(override=True)

        access_token = os.getenv("TRADING_ACCESS_TOKEN")
        acc_num = os.getenv("ACC_NUM")
        assert access_token, "TRADING_ACCESS_TOKEN not set in environment"
        assert acc_num, "ACC_NUM not set in environment"
        return {
            "access_token" : access_token,
            "acc_num" : acc_num
        }


    def test_fetch_specific_account_by_number(self, integration_context):
        """Test validating a specific account by account number"""
        acc_num = integration_context["acc_num"]
        access_token = integration_context["access_token"]

        # First makes sure the account number is valid
        result = check_valid_acc_num(access_token, acc_num)
        assert result is True, \
            f"Failed to fetch account {acc_num}"

        print(f"✓ Fetched specific account: {acc_num}")

    def test_fetch_nonexistent_account(self, integration_context):
        """Test fetching an account number that doesn't exist"""

        access_token = integration_context["access_token"]
        
        # Try to fetch with fake account number
        result = check_valid_acc_num(access_token, acc_num="999999999")
        
        assert result is False, "Should return False for nonexistent account"
        print("✓ Correctly returns False for nonexistent account")