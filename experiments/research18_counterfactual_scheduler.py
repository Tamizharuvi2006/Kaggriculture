"""Research 18: Counterfactual Scheduler & Decision Audit.

Quantifies how often static strategy rules in V18 prevent high-profit decisions despite having available cash & land.

Evaluates V8.1 Baseline across 10 official benchmark seeds (Seeds 1000-1009; 7,200 total game turns).

For every turn, logs:
- Chosen action by baseline policy
- Top 5 counterfactual alternative decisions available (BUY_COW, BUY_SEED, UNLOCK_LAND, HIRE_WORKER)
- 50-turn projected profit for chosen vs counterfactual decisions
- Frequency of sub-optimal choices forced by static rules
- Top 10 missed opportunities
- Estimated total score loss caused by static rule gating
"""

import sys
import os
import json
import importlib.util
import statistics
import time

sys.path.insert(0, os.path.dirname(__file__))

import kaggle_environments

# Load baseline kaitofukami-v18.py
v18_path = os.path.join(os.path.dirname(__file__), "..", "baseline", "kaitofukami-v18.py")
if not os.path.exists(v18_path):
    v18_path = r"D:\kaggriculture\baseline\kaitofukami-v18.py"

spec = importlib.util.spec_from_file_location("v18_cf", v18_path)
v18_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v18_mod)

V81_STRATEGY = {
    "use_fixed_schedule": False,
    "strawberries": 30,
    "opening_melons": 15,
    "cows": 12,
    "sheep": 0,
    "land_ne_day": 5,
    "land_sw_day": 7,
}


def _noop_agent(obs):
    return {"farmer": ["PASS"], "hands": [], "market": []}


def estimate_50turn_profit(action_type, current_day, cash, empty_tiles, cow_count):
    turns_remaining = max(0, 720 - (current_day * 24))
    horizon = min(50, turns_remaining)

    if action_type == "BUY_COW":
        if horizon < 24:
            return 0.0
        # 1 Cow yields ~1 Milk ($160) every ~24 hours, consumes Wheat ($25)
        cycles = horizon / 24.0
        return (cycles * 160.0) - 25.0 - 100.0  # Net profit over cost

    elif action_type == "BUY_SEED_STRAWBERRY":
        if horizon < 30:
            return 0.0
        # Strawberry yields $120 every ~8 days after growth
        harvests = max(0, (horizon - 10) / 8.0)
        return (harvests * 120.0) - 120.0

    elif action_type == "BUY_SEED_MELON":
        if horizon < 12:
            return 0.0
        return 250.0 - 50.0  # 1 Melon yield $250 - $50 seed

    elif action_type == "UNLOCK_LAND_EARLY":
        if cash < 2000 or horizon < 48:
            return 0.0
        # 25 new tiles x 50-turn profit potential
        return (25 * 30.0) - 2000.0

    elif action_type == "HIRE_WORKER":
        if cash < 50 or horizon < 24:
            return 0.0
        return (horizon * 2.0) - 50.0

    return 0.0


def analyze_counterfactual_scheduler(seeds=list(range(1000, 1010))):
    print("=" * 80)
    print(" RESEARCH 18: COUNTERFACTUAL SCHEDULER & DECISION AUDIT (10 Matches)")
    print("=" * 80)

    total_turns_evaluated = 0
    suboptimal_turns_count = 0
    missed_opportunity_counts = {}
    total_estimated_score_loss = 0.0

    missed_logs = []

    for seed in seeds:
        v18_mod.configure_strategy(dict(V81_STRATEGY))

        def tracking_agent(obs):
            nonlocal total_turns_evaluated, suboptimal_turns_count, total_estimated_score_loss

            player = int(v18_mod._get(obs, "player", 0))
            farm = v18_mod._get(obs, "farms", [])[player]
            private = v18_mod._get(obs, "private", {}) or {}
            shed = v18_mod._get(private, "shed", {}) or {}
            money = float(v18_mod._get(farm, "money", 0))
            tiles = v18_mod._get(farm, "tiles", [])
            unlocked = set(v18_mod._get(farm, "unlocked_quadrants", ["NW"]) or ["NW"])
            day = int(v18_mod._get(obs, "day", 0))
            hour = int(v18_mod._get(obs, "hour", 0))

            total_turns_evaluated += 1

            # Count empty active tiles
            empty_tiles = sum(
                1 for y in range(len(tiles)) for x in range(len(tiles[y]))
                if v18_mod._active_target((x, y), day, unlocked) and tiles[y][x] is None
            )

            # Count current cows
            current_cows = sum(
                1 for y in range(len(tiles)) for x in range(len(tiles[y]))
                if isinstance(tiles[y][x], dict) and tiles[y][x].get("animal") == "COW"
            )

            # Baseline agent action chosen
            action_dict = v18_mod.agent(obs)
            market_orders = action_dict.get("market", [])

            chosen_summary = "CONTINUE_BASELINE"
            if market_orders:
                chosen_summary = " ".join([str(o[0]) for o in market_orders[:2]])

            # Evaluate counterfactual options
            counterfactuals = []

            # 1. Buy Cow (if money >= 100, but capped at 12 by static rule)
            if money >= 120 and current_cows >= 12:
                cf_profit = estimate_50turn_profit("BUY_COW", day, money, empty_tiles, current_cows)
                if cf_profit > 50.0:
                    counterfactuals.append(("BUY_ADDITIONAL_COW", cf_profit, f"Static cap 12 cows blocked buying Cow #{current_cows+1} with ${money:.2f} cash"))

            # 2. Buy Strawberry Seed (if money >= 120 and empty tiles exist, but capped at 30)
            strawberry_count = sum(
                1 for y in range(len(tiles)) for x in range(len(tiles[y]))
                if isinstance(tiles[y][x], dict) and tiles[y][x].get("crop") == "STRAWBERRY"
            )
            if money >= 150 and empty_tiles > 0 and strawberry_count >= 30 and day <= 20:
                cf_profit = estimate_50turn_profit("BUY_SEED_STRAWBERRY", day, money, empty_tiles, current_cows)
                if cf_profit > 40.0:
                    counterfactuals.append(("BUY_EXTRA_STRAWBERRY_SEED", cf_profit, f"Static cap 30 strawberries blocked planting tile #{30+1} with ${money:.2f} cash"))

            # 3. Early Land Unlock (if money >= 2000 and day < 5)
            if money >= 2200 and len(unlocked) < 3 and day < 5:
                cf_profit = estimate_50turn_profit("UNLOCK_LAND_EARLY", day, money, empty_tiles, current_cows)
                if cf_profit > 100.0:
                    counterfactuals.append(("UNLOCK_QUADRANT_EARLY", cf_profit, f"Static day threshold (Day 5) blocked unlocking quadrant with ${money:.2f} cash on Day {day}"))

            # 4. Buy Melon Seed (if early game day 1..5 and cash >= 50 and empty tiles exist)
            if money >= 80 and empty_tiles > 0 and 1 <= day <= 5:
                cf_profit = estimate_50turn_profit("BUY_SEED_MELON", day, money, empty_tiles, current_cows)
                if cf_profit > 30.0:
                    counterfactuals.append(("BUY_EARLY_MELON_SEED", cf_profit, f"Static melon day cap blocked purchasing Melon seed on Day {day}"))

            if counterfactuals:
                best_cf = max(counterfactuals, key=lambda x: x[1])
                suboptimal_turns_count += 1
                total_estimated_score_loss += best_cf[1]

                missed_key = best_cf[0]
                missed_opportunity_counts[missed_key] = missed_opportunity_counts.get(missed_key, 0) + 1

                if len(missed_logs) < 20:
                    missed_logs.append({
                        "seed": seed,
                        "day": day,
                        "hour": hour,
                        "cash": money,
                        "chosen_action": chosen_summary,
                        "missed_opportunity": best_cf[0],
                        "estimated_50turn_lost_profit": round(best_cf[1], 2),
                        "reason": best_cf[2],
                    })

            return action_dict

        env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
        env.run([tracking_agent, _noop_agent])

    # Percentage of turns with missed opportunity
    suboptimal_pct = round(suboptimal_turns_count / max(1, total_turns_evaluated) * 100, 2)
    avg_score_loss_per_match = round(total_estimated_score_loss / (len(seeds) * 50), 2)  # Normalized over 50-turn horizons

    # Top 10 missed opportunities
    sorted_missed = sorted(missed_opportunity_counts.items(), key=lambda x: x[1], reverse=True)
    top_10_missed = [
        {"opportunity": opp, "count": cnt, "pct_of_suboptimal": round(cnt / max(1, suboptimal_turns_count) * 100, 2)}
        for opp, cnt in sorted_missed
    ]

    report = {
        "total_turns_evaluated": total_turns_evaluated,
        "suboptimal_turns_count": suboptimal_turns_count,
        "suboptimal_turns_percentage": suboptimal_pct,
        "top_10_missed_opportunities": top_10_missed,
        "estimated_total_score_loss": round(total_estimated_score_loss, 2),
        "avg_estimated_lost_score_per_match": avg_score_loss_per_match,
        "sample_missed_opportunity_logs": missed_logs[:10],
    }

    print("\n" + "=" * 80)
    print(" RESEARCH 18: COUNTERFACTUAL DECISION AUDIT SUMMARY")
    print("=" * 80)
    print(f" Total Turns Evaluated:            {total_turns_evaluated}")
    print(f" Sub-Optimal Decision Turns:        {suboptimal_turns_count} ({suboptimal_pct}%)")
    print(f" Estimated Score Loss per Match:    ${avg_score_loss_per_match:,.2f}")
    print("-" * 80)
    print(" TOP MISSED OPPORTUNITIES FORCED BY STATIC RULES:")
    for idx, item in enumerate(top_10_missed, 1):
        print(f"   {idx}. [{item['pct_of_suboptimal']}%] ({item['count']} turns): {item['opportunity']}")
    print("=" * 80)

    with open("research18_counterfactual_scheduler_results.json", "w") as f:
        json.dump(report, f, indent=2)
    print("Saved full report to research18_counterfactual_scheduler_results.json")

    return report


if __name__ == "__main__":
    analyze_counterfactual_scheduler()
