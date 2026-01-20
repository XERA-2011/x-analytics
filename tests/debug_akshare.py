import akshare as ak
import pandas as pd

def debug_treasury():
    print("--- Debugging Treasury ---")
    try:
        df = ak.bond_zh_us_rate(start_date="20240101")
        if not df.empty:
            print("Columns:", df.columns.tolist())
            print("Tail 1:")
            print(df.tail(1))
        else:
            print("Treasury DF Empty")
    except Exception as e:
        print("Treasury Error:", e)

def debug_metals():
    print("\n--- Debugging Metals (SGE) ---")
    try:
        df = ak.spot_symbol_table_sge()
        if not df.empty:
            print("Columns:", df.columns.tolist())
            print("First 5 rows:")
            print(df.head(5))
        else:
            print("Metals DF Empty")
    except Exception as e:
        print("Metals Error:", e)

if __name__ == "__main__":
    debug_treasury()
    debug_metals()
