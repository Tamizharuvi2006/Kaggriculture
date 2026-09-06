"""Paired seat-swapped evaluation: RC17 vs RC15 (current production).

Hypothesis: removing the slot-0 sell priority (milk/strawberry before fertilizer) lets the bot
finish its planned 8-cow / 4-sheep herd after Day-11 cash arrives, converting
peer-match coin-flips.

Must be run with the project venv that has kaggle_environments.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from concurrent.futures import ProcessPoolExecutor
from statistics import mean, median

import kaggle_environments as ke

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RC15 = os.path.join(ROOT, "submission.py")
RC17 = os.path.join(ROOT, "submission_rc17.py")


def _count_animals(farm):
    n = 0
    cows = 0
    sheep = 0
    for row in farm.get("tiles") or []:
        for tile in row:
            if not isinstance(tile, dict):
                continue
            animal = tile.get("animal")
            if animal == "COW":
                cows += 1
                n += 1
            elif animal == "SHEEP":
                sheep += 1
                n += 1
            elif animal:
                n += 1
    return n, cows, sheep


def _play(seed: int, cand_seat: int):
    agents = [RC17, RC15] if cand_seat == 0 else [RC15, RC17]
    env = ke.make("kaggriculture", configuration={"episodeSteps": 720, "seed": int(seed)})
    res = env.run(agents)
    last = res[-1]
    cand = last[cand_seat]
    base = last[1 - cand_seat]
    cand_obs = cand["observation"]
    base_obs = base["observation"]
    cand_farm = cand_obs["farms"][cand_seat]
    base_farm = base_obs["farms"][1 - cand_seat]
    cand_money = float(cand_farm.get("money") or 0)
    base_money = float(base_farm.get("money") or 0)
    cand_an, cand_cows, cand_sheep = _count_animals(cand_farm)
    base_an, base_cows, base_sheep = _count_animals(base_farm)
    if cand_money > base_money:
        outcome = "W"
    elif cand_money < base_money:
        outcome = "L"
    else:
        outcome = "T"
    return {
        "seed": int(seed),
        "cand_seat": cand_seat,
        "cand_money": cand_money,
        "base_money": base_money,
        "delta": cand_money - base_money,
        "outcome": outcome,
        "cand_animals": cand_an,
        "cand_cows": cand_cows,
        "cand_sheep": cand_sheep,
        "base_animals": base_an,
        "cand_status": cand.get("status"),
        "base_status": base.get("status"),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=int, default=30)
    parser.add_argument("--start-seed", type=int, default=2000)
    parser.add_argument("--workers", type=int, default=10)
    args = parser.parse_args()

    jobs = []
    for i in range(args.seeds):
        seed = args.start_seed + i * 137
        jobs.append((seed, 0))
        jobs.append((seed, 1))

    t0 = time.time()
    rows = []
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futs = [pool.submit(_play, seed, seat) for seed, seat in jobs]
        for fut in futs:
            rows.append(fut.result())
    elapsed = time.time() - t0

    wins = sum(r["outcome"] == "W" for r in rows)
    losses = sum(r["outcome"] == "L" for r in rows)
    ties = sum(r["outcome"] == "T" for r in rows)
    deltas = [r["delta"] for r in rows]
    summary = {
        "candidate": "submission_rc17.py",
        "baseline": "submission.py (RC15)",
        "matches": len(rows),
        "seeds": args.seeds,
        "wins": wins,
        "losses": losses,
        "ties": ties,
        "win_rate": wins / len(rows),
        "tied_or_won": (wins + ties) / len(rows),
        "mean_delta": mean(deltas),
        "median_delta": median(deltas),
        "mean_cand": mean(r["cand_money"] for r in rows),
        "mean_base": mean(r["base_money"] for r in rows),
        "mean_cand_animals": mean(r["cand_animals"] for r in rows),
        "mean_base_animals": mean(r["base_animals"] for r in rows),
        "mean_cand_cows": mean(r["cand_cows"] for r in rows),
        "mean_cand_sheep": mean(r["cand_sheep"] for r in rows),
        "p05_delta": sorted(deltas)[max(0, int(0.05 * len(deltas)))],
        "elapsed_seconds": elapsed,
        "rows": rows,
    }
    out_path = os.path.join(ROOT, "reports", "RC17_PAIRED_VS_RC15.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)
    print(json.dumps({k: v for k, v in summary.items() if k != "rows"}, indent=2))
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
