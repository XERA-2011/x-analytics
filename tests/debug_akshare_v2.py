import akshare as ak
import pandas as pd

def debug_treasury_fix():
    print("--- Debugging Treasury Fix ---")
    try:
        df = ak.bond_zh_us_rate(start_date="20240101")
        if not df.empty:
            # Fix: drop rows where US 10Y is NaN
            df_filtered = df.dropna(subset=["美国国债收益率10年"])
            
            if not df_filtered.empty:
                print("Filtered Tail 1:")
                print(df_filtered.tail(1))
                latest = df_filtered.iloc[-1]
                print(f"US 10Y: {latest.get('美国国债收益率10年')}")
            else:
                print("Filtered DF Empty")
        else:
            print("Original DF Empty")
    except Exception as e:
        print("Treasury Error:", e)

def debug_metals_quotations():
    print("\n--- Debugging Metals Quotations (SGE) ---")
    try:
        # Try fetching real-time data for specific symbol
        # Or maybe spot_quotations_sge logic?
        # Note: akshare API might require symbol or specific variation
        # Let's try iterating likely symbols
        
        # NOTE: searching suggests spot_quotations_sge might be deprecated or needing parameters?
        # Let's try calling it without params if it returns all, or with a specific symbol.
        
        # Based on search result: "spot_quotations_sge"
        # Let's try 'Au99.99'
        
        try:
           print("Attempting ak.spot_quotations_sge(symbol='Au99.99')...") 
           # Note: Function might not take args or might take symbol
           # Let's try inspecting it or just running it
           # If it fails, print error
           
           # Search result said: "use spot_symbol_table_sge to get list, then ..."
           # But let's see if there is `ak.stock_zh_a_spot_em` equivalent for SGE
           pass
        except:
           pass

        # Trying generic SGE spot function if exists
        targets = ["Au99.99", "Ag(T+D)"]
        
        # Try ak.spot_sge(symbol=...) ?
        # Search result mentioned: ak.spot_quotations_sge
        
        if hasattr(ak, 'spot_quotations_sge'):
            print("Found ak.spot_quotations_sge")
            try:
                # Try getting for a specific symbol
                df = ak.spot_quotations_sge(symbol="Au99.99")
                print("Au99.99 Columns:", df.columns.tolist())
                print(df.tail(1))
            except Exception as e:
                print("Error calling spot_quotations_sge:", e)
        else:
            print("ak.spot_quotations_sge NOT found")
            
        # Alternative: ak.spot_gold_sge_benchmark ?
        
        # Let's also try `ak.spot_symbol_table_sge` again to see if I missed any columns (maybe hidden?)
        df_sym = ak.spot_symbol_table_sge()
        print("Symbol Table Columns:", df_sym.columns.tolist())
        
    except Exception as e:
        print("Metals Error:", e)

if __name__ == "__main__":
    debug_treasury_fix()
    debug_metals_quotations()
