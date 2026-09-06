import importlib.util
from collections import Counter
from pathlib import Path

SRC = Path('/mnt/data/submission_rc3_laboratory.py')
spec = importlib.util.spec_from_file_location('rc3', SRC)
rc3 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rc3)

# Engine-reference curve anchors from the supplied Kaggriculture market table.
expected = {
    'WHEAT': (45, 20, 19),
    'CARROT': (42, 10, 1),
    'TOMATO': (84, 24, 9),
    'STRAWBERRY': (204, 1, 1),
    'MELON': (300, 1, 1),
}
for crop, (below, above, above2) in expected.items():
    p = rc3._MARKET_CURVES[crop]
    assert rc3._rc3_market_price(crop, p['I0'] - p['T']) == below
    assert rc3._rc3_market_price(crop, p['I0'] + p['T']) == above
    assert rc3._rc3_market_price(crop, p['I0'] + 2 * p['T']) == above2

# Visible shop-demand sanity check.
rc3._RC3_LIVE_TOWN_SHOPS = ['BAKERY', 'PIZZA_SHOP', 'SMOOTHIE_SHOP']
assert rc3._rc3_daily_town_demand('WHEAT') == 13.0  # center + 6 + 6
assert rc3._rc3_daily_town_demand('STRAWBERRY') == 7.0  # center + 6
assert rc3._rc3_daily_town_demand('CARROT') == 1.0

# Portfolio should react monotonically to strawberry/melon glut in this isolated planner test.
prices = {'WHEAT': 25, 'STRAWBERRY': 120, 'MELON': 250, 'CARROT': 35, 'TOMATO': 60}
base = {'WHEAT': 10000, 'STRAWBERRY': 10000, 'MELON': 10000, 'CARROT': 10000, 'TOMATO': 10000}

def plan_counts(inv):
    rc3._LATEST_PRICES = dict(prices)
    rc3._RC3_LIVE_MARKET_INVENTORY = dict(inv)
    return Counter(rc3._crop_plan(5).values())

c0 = plan_counts(base)
c_straw = plan_counts({**base, 'STRAWBERRY': 10100})
c_melon = plan_counts({**base, 'MELON': 10150})
assert c_straw['STRAWBERRY'] < c0['STRAWBERRY']
assert c_melon['MELON'] < c0['MELON']

print('RC3-A unit tests: PASS')
print('base plan:', dict(c0))
print('strawberry-glut plan:', dict(c_straw))
print('melon-glut plan:', dict(c_melon))
print('full 5-seed Kaggriculture gauntlet: NOT RUN (local kaggriculture engine unavailable in this runtime)')
