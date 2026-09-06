import sys
sys.path.insert(0, r"D:\kaggriculture")

import os, json
import kaggle_environments

import submission_rc2_terminal_horizon as rc2_mod
import submission_rc3_h6 as rc3_mod

# Let's inspect how RC4 Forecast -> Confirm -> Act performs on Soumi Ghosh vs Arao vs Seed 628719714

replays = [
    ("episode-104388418-replay.json", "Soumi Ghosh (Active Flooder)", 1),
    ("episode-104379472-replay.json", "arao (Passive Holder)", 1),
]

def run_game(mode="rc2", replay_file=None, seed_val=None, seat=1):
    if replay_file:
        path = os.path.join(r"D:\kaggriculture\reports\live_match_telemetry", replay_file)
        with open(path) as f: rep = json.load(f)
        seed = rep["info"]["seed"]
        steps = rep["steps"]
        opp_actions = [frame[1 - seat].get("action") for frame in steps[1:]]
        max_steps = len(steps) - 1
    else:
        seed = seed_val
        opp_actions = None
        max_steps = 720

    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": max_steps, "seed": seed})
    env.reset()

    # RC4 State
    potential_risk = False
    flood_confirmed = False
    prev_inv = 10000

    orig_crop_plan = rc2_mod._crop_plan

    for step in range(max_steps):
        if env.done: break
        obs = env.state[seat].observation
        day = obs.day
        hour = obs.hour
        mkt = obs.market
        inv_straw = int(mkt.inventory.get("STRAWBERRY", 10000))
        delta_inv = inv_straw - prev_inv
        prev_inv = inv_straw

        if day == 11 and hour == 0:
            opp_farm = obs.farms[1 - seat]
            opp_s = sum(1 for r in opp_farm.tiles for t in r if isinstance(t, dict) and t.get("crop") == "STRAWBERRY")
            if opp_s >= 16:
                potential_risk = True

        # Confirm flood: inventory crosses 9,960 with positive delta
        if potential_risk and day >= 12:
            if inv_straw >= 9960 and delta_inv > 0:
                flood_confirmed = True

        if mode == "rc2":
            rc2_mod._crop_plan = orig_crop_plan
        elif mode == "rc3":
            # RC3 cuts immediately at Day 11 if opp_s >= 16
            if potential_risk and day >= 11:
                rc2_mod._crop_plan = lambda d: {
                    pos: ("CARROT" if c == "STRAWBERRY" and i >= 10 else c)
                    for i, (pos, c) in enumerate(orig_crop_plan(d).items())
                }
            else:
                rc2_mod._crop_plan = orig_crop_plan
        elif mode == "rc4":
            # RC4: If potential risk, plant initial tranche (14 bushes).
            # ONLY if flood is CONFIRMED (inv >= 9960 + delta > 0), slash to 10 and divert!
            # If flood NOT confirmed (opponent holds, inv stays < 9960), maintain full 26-strawberry harvest!
            if potential_risk and day >= 11:
                if flood_confirmed:
                    # Confirmed flood: restrict to 10 bushes
                    rc2_mod._crop_plan = lambda d: {
                        pos: ("CARROT" if c == "STRAWBERRY" and i >= 10 else c)
                        for i, (pos, c) in enumerate(orig_crop_plan(d).items())
                    }
                else:
                    # Not yet confirmed (or passive holder): allow up to 22 bushes!
                    rc2_mod._crop_plan = lambda d: {
                        pos: ("CARROT" if c == "STRAWBERRY" and i >= 22 else c)
                        for i, (pos, c) in enumerate(orig_crop_plan(d).items())
                    }
            else:
                rc2_mod._crop_plan = orig_crop_plan

        try:
            if replay_file:
                act0 = opp_actions[step] if seat == 1 else rc2_mod.agent(env.state[0].observation)
                act1 = rc2_mod.agent(env.state[1].observation) if seat == 1 else opp_actions[step]
            else:
                act0 = rc2_mod.agent(env.state[0].observation)
                act1 = rc2_mod.agent(env.state[1].observation)
        finally:
            rc2_mod._crop_plan = orig_crop_plan

        env.step([act0, act1])

    return env.state[seat].observation.farms[seat].money, flood_confirmed

print("=" * 95)
print("RC4 PROTOTYPE EVALUATION: FORECAST -> CONFIRM -> ACT (THREE-WAY COMPARISON)")
print("=" * 95)
print(f"{'TARGET':<35} | {'RC2 CONTROL':>12} | {'RC3-H6':>12} | {'RC4 PROTOTYPE':>14} | {'FLOOD CONFIRMED?':>16}")
print("-" * 95)

for r_name, label, seat in replays:
    s_rc2, _ = run_game(mode="rc2", replay_file=r_name, seat=seat)
    s_rc3, _ = run_game(mode="rc3", replay_file=r_name, seat=seat)
    s_rc4, conf = run_game(mode="rc4", replay_file=r_name, seat=seat)
    print(f"{label:<35} | ${s_rc2:>11,.0f} | ${s_rc3:>11,.0f} | ${s_rc4:>13,.0f} | {'YES' if conf else 'NO':>16}")

# Also test Seed 628719714
s_rc2_ceil, _ = run_game(mode="rc2", seed_val=628719714)
s_rc3_ceil, _ = run_game(mode="rc3", seed_val=628719714)
s_rc4_ceil, conf_ceil = run_game(mode="rc4", seed_val=628719714)
print(f"{'Seed 628719714 (High Ceiling)':<35} | ${s_rc2_ceil:>11,.0f} | ${s_rc3_ceil:>11,.0f} | ${s_rc4_ceil:>13,.0f} | {'YES' if conf_ceil else 'NO':>16}")
print("=" * 95)
