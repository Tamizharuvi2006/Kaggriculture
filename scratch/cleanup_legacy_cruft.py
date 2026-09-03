with open(r"D:\kaggriculture\submission_v4_1_clean.py", "r", encoding="utf-8") as f:
    text = f.read()

# 1. Clean DEFAULT_STRATEGY
active_strategy = """DEFAULT_STRATEGY = {
    'adaptive_animal_lead': 2,
    'adaptive_animal_max_day': 14,
    'adaptive_animal_min_day': 2,
    'adaptive_animal_min_herd': 4,
    'adaptive_animal_mode': 'mirror',
    'adaptive_animal_target_share': 0.72,
    'adaptive_capital_animal_lead': 2,
    'adaptive_capital_land_lead': 1,
    'adaptive_capital_max_day': 12,
    'adaptive_capital_priority': False,
    'adaptive_tempo_animal_lead': 1,
    'adaptive_tempo_cow': False,
    'adaptive_tempo_land_lead': 1,
    'animal_daily_cap': 3,
    'animal_ne_day': 8,
    'animal_nw_day': 4,
    'animal_price_sensitivity': 2.0,
    'animal_sw_day': 12,
    'cash_reserve': 150,
    'cow_expert_cows': 2,
    'cow_expert_sheep': 0,
    'cows': 2,
    'crop_transition_day': 5,
    'drop_load_threshold': 30,
    'early_liquidity_floor': 0,
    'feed_days_buffer': 1,
    'fertilizer_roi': 1.5,
    'force_expert': None,
    'hands': 11,
    'land_ne_day': 5,
    'land_sw_day': 10,
    'livestock_animal_cap': 3,
    'livestock_cash_reserve': 150,
    'livestock_cows': 2,
    'livestock_sheep': 0,
    'livestock_strawberries': 34,
    'livestock_tomatoes': 0,
    'ongoing_harvest_threshold': 3,
    'opening_animals': 0,
    'opening_carrots': 2,
    'opening_cows': None,
    'opening_melon_day0_cap': None,
    'opening_melon_early_cap': None,
    'opening_melons': 9,
    'opening_sheep': None,
    'opening_wheat': 10,
    'premium_animal_cap': 3,
    'premium_cash_reserve': 250,
    'premium_cows': 2,
    'premium_sheep': 0,
    'premium_strawberries': 34,
    'premium_tomatoes': 0,
    'price_adaptive_animals': False,
    'price_buffer_pct': 5,
    'rotation_evidence_threshold': 0.9,
    'sheep': 0,
    'sheep_expert_cows': 2,
    'sheep_expert_sheep': 12,
    'strawberries': 34,
    'strawberry_activation_day': 4,
    'strawberry_last_plant': 18,
    'strawberry_staging': False,
    'top_hire_ramp': False,
    'wheat_rush_animal_cap': 1,
    'wheat_rush_cash_reserve': 150,
    'zoned_workers': False,
}
STRATEGY = dict(DEFAULT_STRATEGY)
"""

# Find where DEFAULT_STRATEGY starts and where it ends (before def _spread_animals)
start_pos = text.find("DEFAULT_STRATEGY = {")
end_pos = text.find("def _spread_animals(")

text = text[:start_pos] + active_strategy + "\n" + text[end_pos:]

# 2. Remove legacy globals from configure_strategy
legacy_decl = """    global _V11_SELECTED_RADIANT_VARIANT
    global _V13_MARKET_MODE, _V13_MARKET_CONFIDENCE, _V13_MARKET_LOCK_UNTIL
    global _V14_MARKET_MODE, _V14_MARKET_CONFIDENCE, _V14_MARKET_LOCK_UNTIL
    global _V15_MARKET_MODE, _V15_MARKET_CONFIDENCE, _V15_MARKET_LOCK_UNTIL
    global _V16_MARKET_MODE, _V16_MARKET_CONFIDENCE, _V16_MARKET_LOCK_UNTIL
    global _V18_SELECTED_MARKET, _V18_SELECTED_DAY, _V18_SELECTED_BOARD\n"""
text = text.replace(legacy_decl, "")

legacy_inits = """    _V11_SELECTED_RADIANT_VARIANT = None
    _V13_MARKET_MODE = "BASE"
    _V13_MARKET_CONFIDENCE = 0.0
    _V13_MARKET_LOCK_UNTIL = -1
    _V14_MARKET_MODE = "BASE"
    _V14_MARKET_CONFIDENCE = 0.0
    _V14_MARKET_LOCK_UNTIL = -1
    _V15_MARKET_MODE = "BASE"
    _V15_MARKET_CONFIDENCE = 0.0
    _V15_MARKET_LOCK_UNTIL = -1
    _V16_MARKET_MODE = "BASE"
    _V16_MARKET_CONFIDENCE = 0.0
    _V16_MARKET_LOCK_UNTIL = -1
    _V18_SELECTED_MARKET = {0: None, 1: None}
    _V18_SELECTED_DAY = {0: None, 1: None}
    _V18_SELECTED_BOARD = {0: None, 1: None}\n"""
text = text.replace(legacy_inits, "")

with open(r"D:\kaggriculture\submission_v4_1_clean.py", "w", encoding="utf-8") as f:
    f.write(text)

print("Cleaned submission_v4_1_clean.py successfully!")
