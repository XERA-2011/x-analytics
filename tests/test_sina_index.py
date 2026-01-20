import akshare as ak
import pandas as pd

print("--- Testing index_us_stock_sina ---")
symbols = [".IXIC", ".DJI", ".INX", "IXIC", "DJI", "INX"]
for s in symbols:
    try:
        print(f"Fetching {s}...")
        df = ak.index_us_stock_sina(symbol=s)
        print(df.head())
    except Exception as e:
        print(f"Error {s}: {e}")
