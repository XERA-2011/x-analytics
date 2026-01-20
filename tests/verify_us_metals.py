import sys
from pprint import pprint

# Ensure analytics module is in path
sys.path.append(".")

from analytics.modules.market_us import USFearGreedIndex, USMarketHeat, USTreasury
from analytics.modules.metals import GoldSilverAnalysis, MetalSpotPrice

def verify_us():
    print("--- Verifying US Fear & Greed ---")
    try:
        data = USFearGreedIndex.get_cnn_fear_greed()
        print("CNN Fear & Greed:", data.get('current_value'), data.get('current_level'))
    except Exception as e:
        print("CNN Error:", e)

    print("\n--- Verifying US Market Heat ---")
    try:
        data = USMarketHeat.get_sector_performance()
        print(f"Sectors found: {len(data)}")
        if data:
            print("Top Sector:", data[0])
    except Exception as e:
        print("Heat Error:", e)

    print("\n--- Verifying US Treasury ---")
    try:
        data = USTreasury.get_us_bond_yields()
        print("Bond Data:", len(data))
        if data:
            pprint(data)
    except Exception as e:
        print("Treasury Error:", e)

def verify_metals():
    print("\n--- Verifying Metal Gold/Silver Ratio ---")
    try:
        data = GoldSilverAnalysis.get_gold_silver_ratio()
        print("Gold/Silver Data:", data.keys())
        if "ratio" in data:
            print("Ratio:", data["ratio"])
    except Exception as e:
        print("Gold/Silver Error:", e)

    print("\n--- Verifying Metal Spot Prices ---")
    try:
        data = MetalSpotPrice.get_spot_prices()
        print(f"Metals found: {len(data)}")
        if data:
            pprint(data[0])
    except Exception as e:
        print("Spot Price Error:", e)

if __name__ == "__main__":
    verify_us()
    verify_metals()
