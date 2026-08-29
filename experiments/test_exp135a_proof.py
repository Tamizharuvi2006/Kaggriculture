"""EXP135-A Calibrated Midgame Strawberry Peak Capture Probe.

Tests thresholds:
- Arm 1: p_straw >= $150.0 (Days 20-24)
- Arm 2: p_straw >= $160.0 (Days 20-24)
- Arm 3: p_straw >= $170.0 (Days 20-24)
- Arm 4: p_straw >= $190.0 (Days 20-24)
"""
from __future__ import annotations
import os
import sys
import importlib.util

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import kaggle_environments

# Load D.1 Baseline Agent
spec_d1 = importlib.util.spec_from_file_location("sub_d1", os.path.join(BASE_DIR, "submission_clean.py"))
sub_d1 = importlib.util.module_from_spec(spec_d1)
spec_d1.loader.exec_module(sub_d1)

# Load Benchmark Bot (kaitofukami-v18)
spec_v18 = importlib.util.spec_from_file_location("bot_v18", os.path.join(BASE_DIR, "baseline", "kaitofukami-v18.py"))
bot_v18_mod = importlib.util.module_from_spec(spec_v18)
spec_v18.loader.exec_module(bot_v18_mod)

class CalibratedStrawAgent:
    def __init__(self, thresh: float = 150.0):
        self.thresh = thresh
        self.peak_sales = []
        self.total_peak_cash = 0.0
        self.total_peak_qty = 0

    def act(self, obs: dict, config=None) -> dict:
        step = obs.get("step", 0) if isinstance(obs, dict) else getattr(obs, "step", 0)
        day = (step // 24) + 1

        base_act = sub_d1.agent(obs, config)
        farmer_act = list(base_act.get("farmer") or ["PASS"])
        hands_act = [list(h) for h in (base_act.get("hands") or [])]
        market_orders = list(base_act.get("market") or [])

        if 20 <= day <= 24:
            market = obs.get("market", {}) or {}
            prices = market.get("prices", market.get("current_prices", {})) or {}
            p_straw = float(prices.get("STRAWBERRY", 120.0) or 120.0)

            private_state = obs.get("private") or {}
            shed = private_state.get("shed", {}) or {}
            straw_in_shed = int(shed.get("STRAWBERRY", 0) or 0)

            if p_straw >= self.thresh and straw_in_shed > 0:
                if not any(isinstance(m, (list, tuple)) and len(m) >= 2 and m[0] == "SELL" and m[1] == "STRAWBERRY" for m in market_orders):
                    market_orders.append(["SELL", "STRAWBERRY", straw_in_shed])
                    realized_cash = straw_in_shed * p_straw
                    self.peak_sales.append({
                        "step": step,
                        "day": day,
                        "qty": straw_in_shed,
                        "price": p_straw,
                        "est_revenue": realized_cash,
                    })
                    self.total_peak_cash += realized_cash
                    self.total_peak_qty += straw_in_shed

        return {
            "farmer": farmer_act,
            "hands": hands_act,
            "market": market_orders[:10],
        }

def test_single_seed(seed: int, seat: int = 0):
    print(f"\n--- Testing Seed {seed} (Seat {seat}) ---")
    
    # 1. Run Pure D.1 Control
    env_ctrl = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env_ctrl.reset()
    while not env_ctrl.done:
        obs0 = env_ctrl.state[0].observation
        obs1 = env_ctrl.state[1].observation
        d1_obs = obs0 if seat == 0 else obs1
        opp_obs = obs1 if seat == 0 else obs0
        a_d1 = sub_d1.agent(d1_obs, env_ctrl.configuration)
        a_opp = bot_v18_mod.agent(opp_obs)
        env_ctrl.step([a_d1, a_opp] if seat == 0 else [a_opp, a_d1])
    
    r_ctrl = float(env_ctrl.state[seat].reward or 0.0)
    r_opp_ctrl = float(env_ctrl.state[1 - seat].reward or 0.0)
    ctrl_won = r_ctrl > r_opp_ctrl
    print(f"  [D.1 Control]: D.1=${r_ctrl:,.0f} | Opp=${r_opp_ctrl:,.0f} | Won={ctrl_won}")

    for t in [150.0, 160.0, 170.0, 190.0]:
        env_t = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
        env_t.reset()
        agent_t = CalibratedStrawAgent(thresh=t)
        while not env_t.done:
            obs0 = env_t.state[0].observation
            obs1 = env_t.state[1].observation
            d1_obs = obs0 if seat == 0 else obs1
            opp_obs = obs1 if seat == 0 else obs0
            a_d1 = agent_t.act(d1_obs, env_t.configuration)
            a_opp = bot_v18_mod.agent(opp_obs)
            env_t.step([a_d1, a_opp] if seat == 0 else [a_opp, a_d1])
        
        r_t = float(env_t.state[seat].reward or 0.0)
        r_opp_t = float(env_t.state[1 - seat].reward or 0.0)
        t_won = r_t > r_opp_t
        delta = r_t - r_ctrl
        print(f"  [Thresh >= ${t:.0f}]: D.1=${r_t:,.0f} | Opp=${r_opp_t:,.0f} | Won={t_won} | Delta=${delta:+,.0f} | Sales={len(agent_t.peak_sales)} events (Qty={agent_t.total_peak_qty})")

def main():
    print("=" * 115)
    print("EXP135-A THRESHOLD CALIBRATION PROBE (DAYS 20-24)")
    print("=" * 115)
    test_single_seed(seed=1000, seat=0)
    test_single_seed(seed=42, seat=0)
    test_single_seed(seed=20042, seat=0)

if __name__ == "__main__":
    main()
