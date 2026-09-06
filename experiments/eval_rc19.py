#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
import sys
from collections import Counter
from pathlib import Path

ROOT = Path("/home/user/Kaggriculture")
sys.path.insert(0, str(ROOT))
import kaggle_environments as ke

SEEDS = [100, 101, 102, 103, 200, 201, 202, 203]


def load_agent(path):
    spec = importlib.util.spec_from_file_location("bot_" + Path(path).stem, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.agent


def run_vs_pass(path, seed):
    agent = load_agent(path)
    env = ke.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env.reset()
    sold = Counter()
    while not env.done:
        st = env.state
        a0 = agent(st[0].observation)
        mkt_before = dict(st[0].observation.market["inventory"] if isinstance(st[0].observation.market, dict) else st[0].observation.market.inventory)
        env.step([a0, {"farmer": ["PASS"], "hands": [], "market": []}])
        st = env.state
        mkt_after = dict(st[0].observation.market["inventory"] if isinstance(st[0].observation.market, dict) else st[0].observation.market.inventory)
        for k, v in mkt_after.items():
            d = int(v) - int(mkt_before.get(k, 0))
            if d > 0:
                sold[k] += d
        if env.done:
            break
    money = float(env.state[0].observation.farms[0]["money"])
    return money, sold


def run_paired(path_a, path_b, seed):
    a = load_agent(path_a)
    b = load_agent(path_b)
    env = ke.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env.reset()
    while not env.done:
        st = env.state
        env.step([a(st[0].observation), b(st[1].observation)])
        if env.done:
            break
    m0 = float(env.state[0].observation.farms[0]["money"])
    m1 = float(env.state[1].observation.farms[1]["money"])
    return m0, m1


if __name__ == "__main__":
    rc19 = ROOT / "submission_rc19.py"
    rc18 = ROOT / "submission_rc18.py"
    print("=== vs pass ===", flush=True)
    rows = []
    for seed in SEEDS:
        money, sold = run_vs_pass(str(rc19), seed)
        rows.append((seed, money, sold))
        print(
            f"seed={seed} ${money:.0f}  straw={sold.get('STRAWBERRY',0)} wheat={sold.get('WHEAT',0)} "
            f"melon={sold.get('MELON',0)} milk={sold.get('MILK',0)} wool={sold.get('WOOL',0)} fert={sold.get('FERTILIZER',0)}",
            flush=True,
        )
    mean = sum(r[1] for r in rows) / len(rows)
    mx = max(r[1] for r in rows)
    n150 = sum(1 for r in rows if r[1] >= 150000)
    print(f"MEAN ${mean:.0f}  MAX ${mx:.0f}  n>=150k {n150}/{len(rows)}", flush=True)

    print("=== paired rc19 vs rc18 (rc19 seat0) ===", flush=True)
    w = l = 0
    for seed in SEEDS:
        m0, m1 = run_paired(str(rc19), str(rc18), seed)
        w += m0 > m1
        l += m1 > m0
        print(f"seed={seed} rc19=${m0:.0f} rc18=${m1:.0f} {'W' if m0>m1 else 'L' if m1>m0 else 'T'}", flush=True)
    print(f"WR {w}-{l}", flush=True)
