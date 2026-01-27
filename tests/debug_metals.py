import akshare as ak
import sys
import pandas as pd

try:
    print("Fetching ak.futures_global_spot_em()...")
    df = ak.futures_global_spot_em()
    print("Columns:", df.columns.tolist())
    
    # Filter for Gold/Silver
    gold = df[df["代码"].str.contains("GC", na=False)].head(2)
    silver = df[df["代码"].str.contains("SI", na=False)].head(2)
    
    print("\nGold:")
    print(gold)
    print("\nSilver:")
    print(silver)
    
except Exception as e:
    print(f"Error: {e}")
