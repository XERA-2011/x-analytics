import akshare as ak
import pandas as pd

print("--- Testing index_us_stock_sina ---")
try:
    # This usually fetches specific symbol
    # Common symbols: .IXIC (Nasdaq), .INX (S&P 500), .DJI (Dow)
    # Sina might use: ixp (Nasdaq), dji (Dow), spx (S&P)
    
    # Let's try to find what symbols work.
    # Searching for documentation or trying generic fetches.
    pass
except Exception as e:
    print(e)

print("--- Testing index_global_em ---") # This often has global indices
try:
    df = ak.index_global_em()
    print(df.head())
    print(df[df['名称'].str.contains('纳斯达克|标普|道琼斯')])
except Exception as e:
    print(f"index_global_em error: {e}")

print("--- Testing stock_us_spot_em for Indices ---")
try:
    # Sometimes indices are in the spot list with special codes
    # But usually separated.
    pass
except Exception as e:
    print(e)
