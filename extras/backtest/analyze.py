import logging
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

def analyze_trades(df: pd.DataFrame, position_size: float = 2500) -> tuple:
    """
    Analyzes trades with pyramiding (multiple buys with increasing position sizes).
    Tracks quantity for each buy to calculate accurate P&L.
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with 'strategy', 'close', and 'quantity' columns.
        Index should be DatetimeIndex for proper time tracking.
    position_size : float
        Default position size (currently unused, kept for backwards compatibility).
        
    Returns
    -------
    tuple
        (trades_df, summary_dict) where:
        - trades_df: DataFrame with individual trade details
        - summary_dict: Dictionary with performance metrics
        Returns (empty DataFrame, error dict) if analysis fails.
    """
    logger.info("Starting trade analysis")
    logger.debug(f"Input DataFrame shape: {df.shape}, position_size: {position_size}")
    
    # Validate input DataFrame
    if df is None:
        logger.error("DataFrame is None")
        return pd.DataFrame(), {"error": "DataFrame cannot be None"}
    
    if not isinstance(df, pd.DataFrame):
        logger.error(f"Expected pd.DataFrame, got {type(df)}")
        return pd.DataFrame(), {"error": f"Expected DataFrame, got {type(df)}"}
    
    if df.empty:
        logger.warning("Input DataFrame is empty")
        return pd.DataFrame(), {"error": "No data or 'strategy' column missing."}
    
    # Validate required columns
    if "strategy" not in df.columns:
        logger.error("Missing 'strategy' column")
        logger.debug(f"Available columns: {df.columns.tolist()}")
        return pd.DataFrame(), {"error": "No data or 'strategy' column missing."}
    
    required_cols = ["strategy", "close", "quantity"]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        logger.error(f"Missing required columns: {missing_cols}")
        logger.debug(f"Available columns: {df.columns.tolist()}")
        return pd.DataFrame(), {"error": f"Missing required columns: {missing_cols}"}
    
    # Check for NaN values in critical columns
    for col in required_cols:
        nan_count = df[col].isna().sum()
        if nan_count > 0:
            logger.warning(f"{nan_count} NaN values in '{col}' column")
    
    try:
        # Filter only buy/sell events
        signals = df[df["strategy"].isin(["buy", "sell"])][required_cols].copy()
        
        if signals.empty:
            logger.warning("No buy/sell signals found in DataFrame")
            return pd.DataFrame(), {"error": "No buy/sell signals found."}
        
        logger.info(f"Found {len(signals)} trading signals ({(signals['strategy'] == 'buy').sum()} buys, {(signals['strategy'] == 'sell').sum()} sells)")
        
    except Exception as e:
        logger.error(f"Error filtering signals: {e}")
        logger.exception(e)
        return pd.DataFrame(), {"error": f"Failed to filter signals: {e}"}
    
    try:
        # Reset index to access datetime
        signals = signals.reset_index()
        time_col = signals.columns[0]
        logger.debug(f"Using time column: {time_col}")
        
    except Exception as e:
        logger.error(f"Error resetting index: {e}")
        logger.exception(e)
        return pd.DataFrame(), {"error": f"Failed to process index: {e}"}
    
    # Initialize tracking variables
    trades = []
    open_positions = []  # list of (price, shares, time)
    total_shares = 0
    total_cost = 0
    
    logger.debug("Starting trade matching loop")
    
    try:
        for idx, row in signals.iterrows():
            try:
                action = row["strategy"]
                price = row["close"]
                shares = row["quantity"]
                tstamp = row[time_col]
                
                # Validate individual values
                if pd.isna(price):
                    logger.warning(f"NaN price at index {idx}, skipping signal")
                    continue
                    
                if pd.isna(shares) or shares <= 0:
                    logger.warning(f"Invalid quantity ({shares}) at index {idx}, skipping signal")
                    continue
                
                if action == "buy":
                    # Add new position
                    open_positions.append((price, shares, tstamp))
                    total_shares += shares
                    total_cost += price * shares
                    logger.debug(f"Buy: {shares} shares @ ${price:.2f}, total positions: {len(open_positions)}")
                
                elif action == "sell" and open_positions:
                    # Calculate actual P&L based on all positions
                    exit_value = total_shares * price
                    profit_dollars = exit_value - total_cost
                    
                    # Avoid division by zero
                    if total_cost == 0:
                        logger.warning(f"Total cost is zero at sell signal {idx}, skipping")
                        continue
                    
                    profit_pct = (profit_dollars / total_cost) * 100
                    
                    # Average entry price (weighted by shares)
                    avg_entry_price = total_cost / total_shares
                    
                    entry_time = open_positions[0][2]  # First buy time
                    exit_time = tstamp
                    
                    trade = {
                        "Entry Time": entry_time,
                        "Exit Time": exit_time,
                        "Avg Entry Price": round(avg_entry_price, 2),
                        "Exit Price": round(price, 2),
                        "Total Shares": int(total_shares),
                        "Total Cost": round(total_cost, 2),
                        "Exit Value": round(exit_value, 2),
                        "Profit $": round(profit_dollars, 2),
                        "Profit %": round(profit_pct, 2),
                        "Number of Buys": len(open_positions),
                    }
                    
                    trades.append(trade)
                    logger.debug(f"Sell: {total_shares} shares @ ${price:.2f}, P&L: ${profit_dollars:.2f} ({profit_pct:.2f}%)")
                    
                    # Reset after full exit
                    open_positions = []
                    total_shares = 0
                    total_cost = 0
                
                elif action == "sell" and not open_positions:
                    logger.warning(f"Sell signal at {tstamp} without open positions, skipping")
                    
            except Exception as e:
                logger.error(f"Error processing signal at index {idx}: {e}")
                logger.exception(e)
                continue  # Skip this signal, continue with others
        
    except Exception as e:
        logger.error(f"Critical error in trade matching loop: {e}")
        logger.exception(e)
        return pd.DataFrame(), {"error": f"Trade matching failed: {e}"}
    
    # Check if we have any completed trades
    if not trades:
        msg = "No complete trades found."
        if open_positions:
            logger.warning(f"Found {len(open_positions)} open position(s) without exit")
            msg += f" ({len(open_positions)} open position(s) without exit.)"
        else:
            logger.warning("No trades were completed")
        return pd.DataFrame(), {"error": msg}
    
    logger.info(f"Completed analysis of {len(trades)} trades")
    
    try:
        # Create trades DataFrame
        trades_df = pd.DataFrame(trades)
        
        logger.debug("Calculating performance metrics")
        
        # --- Compute performance metrics ---
        wins = trades_df[trades_df["Profit %"] > 0]
        losses = trades_df[trades_df["Profit %"] <= 0]
        
        # Avoid division by zero
        win_rate = (len(wins) / len(trades_df) * 100) if len(trades_df) > 0 else 0
        avg_win = wins["Profit %"].mean() if not wins.empty else 0
        avg_loss = losses["Profit %"].mean() if not losses.empty else 0
        win_loss_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else np.inf
        
        # Dollar-based metrics (more meaningful for pyramiding)
        total_profit_dollars = trades_df["Profit $"].sum()
        avg_profit_dollars = trades_df["Profit $"].mean()
        max_profit_dollars = trades_df["Profit $"].max()
        max_loss_dollars = trades_df["Profit $"].min()
        
        # Percentage metrics
        total_return_pct = trades_df["Profit %"].sum()
        avg_return_pct = trades_df["Profit %"].mean()
        return_std = trades_df["Profit %"].std()
        
        # Risk-adjusted return
        sharpe_like = (avg_return_pct / return_std) if return_std > 0 else 0
        
        # Average capital deployed per trade
        avg_capital = trades_df["Total Cost"].mean()
        
        summary = {
            "Total Trades": len(trades_df),
            "Winning Trades": len(wins),
            "Losing Trades": len(losses),
            "Win Rate (%)": round(win_rate, 2),
            
            "--- Dollar Metrics ---": "",
            "Total Profit ($)": round(total_profit_dollars, 2),
            "Avg Profit per Trade ($)": round(avg_profit_dollars, 2),
            "Max Win ($)": round(max_profit_dollars, 2),
            "Max Loss ($)": round(max_loss_dollars, 2),
            "Avg Capital Deployed ($)": round(avg_capital, 2),
            
            "--- Percentage Metrics ---": "",
            "Total Return (%)": round(total_return_pct, 2),
            "Avg Return per Trade (%)": round(avg_return_pct, 2),
            "Avg Win (%)": round(avg_win, 2),
            "Avg Loss (%)": round(avg_loss, 2),
            "Win/Loss Ratio": round(win_loss_ratio, 2),
            "Std Dev (%)": round(return_std, 2),
            "Return/Risk Ratio": round(sharpe_like, 2),
        }
        
        logger.info(f"Analysis complete: {len(trades_df)} trades, Win Rate: {win_rate:.2f}%, Total P&L: ${total_profit_dollars:.2f}")
        logger.debug(f"Summary: {summary}")
        
        return trades_df, summary
        
    except Exception as e:
        logger.error(f"Error calculating performance metrics: {e}")
        logger.exception(e)
        return pd.DataFrame(), {"error": f"Failed to calculate metrics: {e}"}