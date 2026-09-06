#!/usr/bin/env python3
"""Official-sim forensic of strawberry generations for RC18 vs v18 vs pass."""
from __future__ import annotations

import importlib.util
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path("/home/user/Kaggriculture")
sys.path.insert(0, str(ROOT))

import kaggle_environments as ke


def load_agent(path):
    spec = importlib.util.spec_from_file_location("bot", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.agent


def tile_stats(farm):
    straw = []
    weeds = 0
    melon = 0
    wheat = 0
    cows = 0
    fert_on = 0
    unwatered = 0
    ripe = 0
    for y, row in enumerate(farm["tiles"]):
        for x, t in enumerate(row):
            if not isinstance(t, dict):
                continue
            if t.get("kind") == "WEED":
                weeds += 1
            if t.get("animal") == "COW":
                cows += 1
            if t.get("kind") != "PLANT":
                continue
            crop = t.get("crop")
            if crop == "WHEAT":
                wheat += 1
            elif crop == "MELON":
                melon += 1
            elif crop == "STRAWBERRY":
                straw.append(t)
                if int(t.get("fertilized_until_day", -1)) >= farm_day_placeholder:
                    fert_on += 1
                if not t.get("watered_today"):
                    unwatered += 1
                if int(t.get("yield_units", 0)) > 0:
                    ripe += 1
    return straw, weeds, melon, wheat, cows, ripe, unwatered


# patched below with day
farm_day_placeholder = 0


def run(bot_path, seed=100, opponent="pass"):
    agent = load_agent(bot_path)
    env = ke.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env.reset()
    daily = []
    sold = Counter()
    harvested_straw = 0
    plant_events = []  # (day, hour, planted_day_on_tile after)
    prev_plants = {}

    trainer = env
    # Use env.run is easier but we need per-step. Manual loop.
    # kaggle env: env.step([a0,a1])
    agents = [agent, "pass" if opponent == "pass" else load_agent(opponent)]

    def act(obs, bot):
        if bot == "pass":
            return {"farmer": ["PASS"], "hands": [], "market": []}
        return bot(obs)

    # initial
    state = env.state
    steps = 0
    last_sold = 0
    while not env.done and steps < 720:
        obs0 = state[0].observation
        day = int(getattr(obs0, "day", 0))
        hour = int(getattr(obs0, "hour", 0))
        farm = obs0.farms[0]
        priv = state[0].observation.private
        tiles = farm["tiles"]
        plants = {}
        for y, row in enumerate(tiles):
            for x, t in enumerate(row):
                if isinstance(t, dict) and t.get("kind") == "PLANT" and t.get("crop") == "STRAWBERRY":
                    plants[(x, y)] = int(t.get("planted_day", day))
                if isinstance(t, dict) and t.get("kind") == "PLANT" and t.get("crop") == "STRAWBERRY":
                    harvested_straw += 0
        # detect new plants
        for pos, pd in plants.items():
            if pos not in prev_plants:
                plant_events.append((day, hour, pos, pd))
        prev_plants = plants

        a0 = act(obs0, agents[0])
        a1 = act(state[1].observation, agents[1])
        # count SELL strawberry
        for order in (a0.get("market") or []):
            if order and order[0] == "SELL" and len(order) > 2 and order[1] == "STRAWBERRY":
                sold["requested"] += int(order[2])
        state = env.step([a0, a1])
        steps += 1
        if hour == 23 or env.done:
            farm = env.state[0].observation.farms[0]
            priv = env.state[0].observation.private
            straw = []
            weeds = melon = wheat = cows = ripe = unwatered = fert = 0
            ages = Counter()
            for y, row in enumerate(farm["tiles"]):
                for x, t in enumerate(row):
                    if not isinstance(t, dict):
                        continue
                    if t.get("kind") == "WEED":
                        weeds += 1
                    if t.get("animal") == "COW":
                        cows += 1
                    if t.get("kind") != "PLANT":
                        continue
                    c = t.get("crop")
                    if c == "WHEAT":
                        wheat += 1
                    elif c == "MELON":
                        melon += 1
                    elif c == "STRAWBERRY":
                        straw.append(t)
                        ages[int(t.get("planted_day", day))] += 1
                        if int(t.get("fertilized_until_day", -1)) >= day:
                            fert += 1
                        if not t.get("watered_today"):
                            unwatered += 1
                        if int(t.get("yield_units", 0)) > 0:
                            ripe += 1
            shed = priv.get("shed", {}) if isinstance(priv, dict) else getattr(priv, "shed", {})
            money = farm["money"]
            hands = len(farm.get("hands", []))
            daily.append({
                "day": day,
                "straw": len(straw),
                "ages": dict(ages),
                "weeds": weeds,
                "melon": melon,
                "wheat": wheat,
                "cows": cows,
                "ripe": ripe,
                "unwatered": unwatered,
                "fert": fert,
                "money": round(money, 1),
                "hands": hands,
                "shed_straw": int((shed or {}).get("STRAWBERRY", 0) or 0),
                "shed_milk": int((shed or {}).get("MILK", 0) or 0),
                "seeds_straw": int((priv.get("seeds", {}) if isinstance(priv, dict) else getattr(priv, "seeds", {}) or {}).get("STRAWBERRY", 0) or 0),
            })
        if env.done:
            break

    final = env.state[0].observation.farms[0]["money"]
    # market inventory delta for strawberry as proxy of actual sold
    mkt = env.state[0].observation.market
    inv = mkt.get("inventory") if isinstance(mkt, dict) else getattr(mkt, "inventory", {})
    straw_inv = int((inv or {}).get("STRAWBERRY", 10000))
    milk_inv = int((inv or {}).get("MILK", 10000))
    return {
        "money": final,
        "straw_inv": straw_inv,
        "milk_inv": milk_inv,
        "sold_requested": sold["requested"],
        "plant_events": plant_events,
        "daily": daily,
        "n_plant_events": len(plant_events),
        "unique_tiles_planted": len({p[2] for p in plant_events}),
        "plant_days": Counter(p[0] for p in plant_events),
    }


def summarize(name, r):
    print(f"\n===== {name}  money=${r['money']:.0f}  straw_mkt_inv={r['straw_inv']} (sold~{r['straw_inv']-10000 if r['straw_inv']>=10000 else 'n/a'}) milk_inv={r['milk_inv']}")
    print(f"plant_events={r['n_plant_events']} unique_tiles={r['unique_tiles_planted']} plant_days={dict(r['plant_days'])}")
    print(f"{'d':>3} {'straw':>5} {'weed':>4} {'mel':>3} {'wht':>3} {'cow':>3} {'ripe':>4} {'unw':>3} {'fert':>4} {'$':>8} ages")
    for d in r["daily"]:
        ages = ",".join(f"{k}:{v}" for k, v in sorted(d["ages"].items()))
        print(f"{d['day']:3d} {d['straw']:5d} {d['weeds']:4d} {d['melon']:3d} {d['wheat']:3d} {d['cows']:3d} {d['ripe']:4d} {d['unwatered']:3d} {d['fert']:4d} {d['money']:8.0f} {ages}")


if __name__ == "__main__":
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    bots = {
        "rc18": ROOT / "submission_rc18.py",
        "v18": ROOT / "baseline" / "kaitofukami-v18.py",
    }
    out = {}
    for name, path in bots.items():
        print(f"running {name} seed={seed} ...", flush=True)
        r = run(str(path), seed=seed)
        summarize(name, r)
        # compact json
        out[name] = {
            "money": r["money"],
            "straw_inv": r["straw_inv"],
            "milk_inv": r["milk_inv"],
            "n_plant_events": r["n_plant_events"],
            "unique_tiles": r["unique_tiles_planted"],
            "plant_days": dict(r["plant_days"]),
            "daily": r["daily"],
            "plant_events_sample": r["plant_events"][:80],
        }
    Path("/tmp/straw_trace.json").write_text(json.dumps(out, indent=2))
    print("wrote /tmp/straw_trace.json")
