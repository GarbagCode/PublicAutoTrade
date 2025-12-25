import os
import pandas as pd
import logging

logger = logging.getLogger(__name__)

def save_df_to_csv(df: pd.DataFrame, path="data/stream_data.csv"):
    try:
        # Validate input
        if df is None or df.empty:
            raise ValueError("DataFrame is empty or None.")

        # Ensure directory exists
        dir_path = os.path.dirname(path)
        if dir_path:
            try:
                os.makedirs(dir_path, exist_ok=True)
            except PermissionError as e:
                logger.error(f"Permission denied creating directory {dir_path}: {e}")
                return
            except OSError as e:
                logger.error(f"OS error creating directory {dir_path}: {e}")
                return

        # Save CSV
        try:
            df.to_csv(path, mode='a', header=not os.path.exists(path), index=False)
        except PermissionError as e:
            logger.error(f"Permission denied writing to {path}: {e}")
        except OSError as e:
            logger.error(f"OS error writing to {path}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error saving CSV: {e}")

    except ValueError as e:
        logger.warning(f"Invalid DataFrame: {e}")
    except Exception as e:
        logger.exception(f"Unexpected error in save_df_to_csv: {e}")

if __name__ == "__main__":
    save_df_to_csv()