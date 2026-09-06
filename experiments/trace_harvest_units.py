#!/usr/bin/env python3
"""Count actual harvested units (inventory deltas) vs SELL requests."""
from __future__ import annotations
import importlib.util
import sys
from collections import Counter
from pathlib import Path

ROOT = Path("/home/user/Kaggriculture")
sys.path.insert(0, str(ROOT))
import kaggle_environments as ke


def load_agent(path):
    spec = importlib.util.spec_from_file_location("bot", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.agent


def inv_sum(priv, item):
    shed = priv.get("shed", {}) if isinstance(priv, dict) else getattr(priv, "shed", {}) or {}
    invs = priv.get("inventories", []) if isinstance(priv, dict) else getattr(priv, "inventories", []) or []
    n = int((shed or {}).get(item, 0) or 0)
    for inv in invs:
        if isinstance(inv, dict):
            n += int(inv.get(item, 0) or 0)
    return n


def run(path, seed=100):
    agent = load_agent(path)
    env = ke.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env.reset()
    harvested = Counter()
    sell_req = Counter()
    sell_ok_proxy = Counter()  # market inv increase when price>1 approximated by inv
    prev = Counter()
    items = ("STRAWBERRY", "MILK", "WOOL", "MELON", "WHEAT", "FERTILIZER", "CARROT", "TOMATO")
    while not env.done:
        st = env.state
        obs0 = st[0].observation
        priv = st[0].observation.private
        cur = Counter({k: inv_sum(priv if isinstance(priv, dict) else priv.__dict__ if hasattr(priv, "__dict__") else {}, k) for k in items})
        # After previous step, harvest shows as increase in held units (before sell).
        # We'll compute harvest as max(0, cur - prev) at START of turn (post overnight drop).
        a0 = agent(obs0)
        a1 = {"farmer": ["PASS"], "hands": [], "market": []}
        for order in a0.get("market") or []:
            if order and order[0] == "SELL" and len(order) > 2:
                sell_req[order[1]] += int(order[2])
        mkt_before = dict(st[0].observation.market["inventory"] if isinstance(st[0].observation.market, dict) else st[0].observation.market.inventory)
        env.step([a0, a1])
        st = env.state
        priv = st[0].observation.private
        pdict = priv if isinstance(priv, dict) else None
        after = Counter()
        shed = (pdict or {}).get("shed", {}) if pdict else getattr(priv, "shed", {})
        invs = (pdict or {}).get("inventories", []) if pdict else getattr(priv, "inventories", [])
        for k in items:
            n = int((shed or {}).get(k, 0) or 0)
            for inv in invs or []:
                if isinstance(inv, dict):
                    n += int(inv.get(k, 0) or 0)
            after[k] = n
        mkt_after = dict(st[0].observation.market["inventory"] if isinstance(st[0].observation.market, dict) else st[0].observation.market.inventory)
        for k in items:
            # harvest approx: held increased plus sold into market
            d_mkt = int(mkt_after.get(k, 0)) - int(mkt_before.get(k, 0))
            if d_mkt > 0:
                sell_ok_proxy[k] += d_mkt
        if env.done:
            break
    money = env.state[0].observation.farms[0]["money"]
    return money, sell_req, sell_ok_proxy


if __name__ == "__main__":
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    for name, path in [
        ("rc18", ROOT / "submission_rc18.py"),
        ("v18", ROOT / "baseline" / "kaitofukami-v18.py"),
    ]:
        print("running", name, flush=True)
        money, req, sold = run(str(path), seed)
        print(f"{name} ${money:.0f}")
        print("  SELL requested:", dict(req))
        print("  market +inv   :", dict(sold))
