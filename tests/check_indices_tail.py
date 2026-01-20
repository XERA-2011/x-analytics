import akshare as ak
import pandas as pd

symbols = [".IXIC", ".DJI", ".INX"]
for s in symbols:
    try:
        print(f"--- {s} ---")
        df = ak.index_us_stock_sina(symbol=s)
        print(df.tail(3))
    except Exception as e:
        print(e)
