import os
import sys
import pytest
import pandas as pd
from extras.sample_data import create_sample_data


@pytest.fixture
def load_strategies() -> dict:
    """Load all strategy modules from the strategies folder"""
    strategies_folder_path = "tradeBot/strategies"
    strategies = {}
    sys.path.insert(0, strategies_folder_path)
    
    for file in os.listdir(strategies_folder_path):
        if file.endswith(".py") and not file.startswith("_"):
            module_name = file[:-3]  # Remove .py
            module = __import__(module_name)
            if hasattr(module, "main"):
                strategies[module_name] = module.main
    
    return strategies


@pytest.fixture
def sample_data():
    """Create sample data for testing"""
    return create_sample_data()


def test_strategies(load_strategies, sample_data):
    """Test that all loaded strategies work correctly"""
    
    # Check that strategies were loaded
    assert len(load_strategies) > 0, "No strategies loaded"
    
    expected_columns = ['quantity', 'signal']
    
    for strat_name, strat_func in load_strategies.items():
        print(f"Testing strategy: {strat_name}")
        
        # Run strategy
        result = strat_func(sample_data)
        
        # Check returned DataFrame
        assert isinstance(result, pd.DataFrame), f"{strat_name} did not return DataFrame"
        
        # Check required columns exist
        for col in expected_columns:
            assert col in result.columns, f"{strat_name} missing column: {col}"
        
        # Check signal column values (if any signals exist)
        if result['signal'].notna().any():
            signal_values = set(result['signal'].dropna().unique())
            valid_signals = {'BUY', 'SELL', 'buy', 'sell'} 
            assert signal_values.issubset(valid_signals), f"{strat_name} has invalid signals: {signal_values}"
        
        # Check quantity is numeric
        assert pd.api.types.is_numeric_dtype(result['quantity']), f"{strat_name} quantity is not numeric"
        
        print(f"✓ {strat_name} passed all tests")