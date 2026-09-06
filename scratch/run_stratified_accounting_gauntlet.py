import sys
sys.path.insert(0, r"D:\kaggriculture")

import os, json
import kaggle_environments

import submission_rc2_terminal_horizon as rc2_mod
import submission_rc3_h6 as rc3_mod
import submission_rc4_forecast_confirm as rc4_mod

# Stratified Matrix of Opponent Exposure & Selling Behavior
STRATIFIED_TESTS = [
    ("Low (Opp=1, Zero Sales)",       r"reports/step5b/old_loss_gauntlet/ppo_submission_replays/96184199/episode-96184199-replay.json", 1),
    ("Low-Mod (Opp=6, Passive)",      r"reports/step5b/old_loss_gauntlet/raw_replays/91297572/episode-91297572-replay.json", 1),
    ("Moderate (Opp=12, Normal)",     r"reports/step5b/old_loss_gauntlet/ppo_submission_replays/96179642/episode-96179642-replay.json", 1),
    ("Heavy (Opp=22, Passive Holder)",r"reports/live_match_telemetry/episode-104379472-replay.json", 1),
    ("Heavy (Opp=18, Active Flooder)",r"reports/live_match_telemetry/episode-104475527-replay.json", 1),
    ("Extreme (Opp=25, Flooder)",     r"reports/live_match_telemetry/episode-104388418-replay.json", 1),
    ("Hyper-Extreme (Opp=28, Flooder)",r"reports/step5b/old_loss_gauntlet/raw_replays/91694495/episode-91694495-replay.json", 1),
]

def run_audited_game(agent_under_test, agent_name, replay_path, seat=1):
    with open(replay_path) as f: rep = json.load(f)
    seed = rep["info"]["seed"]
    steps = rep["steps"]
    max_steps = len(steps) - 1
    opp_actions = [frame[1 - seat].get("action") for frame in steps[1:]]

    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": max_steps, "seed": seed})
    env.reset()

    # Economic Accounting Trackers
    straw_units_pre_confirm = 0
    straw_rev_pre_confirm = 0.0
    straw_units_post_confirm = 0
    straw_rev_post_confirm = 0.0
    replace_rev_total = 0.0
    
    opp_straw_d11 = 0
    first_warning_day = None
    confirm_day = None
    saturation_day = None

    for step in range(max_steps):
        if env.done: break
        obs = env.state[seat].observation
        day = obs.day
        hour = obs.hour
        mkt = obs.market
        inv_straw = int(mkt.inventory.get("STRAWBERRY", 10000))
        p_straw = float(mkt.prices.get("STRAWBERRY", 120))

        if day == 11 and hour == 0:
            opp_farm = obs.farms[1 - seat]
            opp_straw_d11 = sum(1 for r in opp_farm.tiles for t in r if isinstance(t, dict) and t.get("crop") == "STRAWBERRY")
            if opp_straw_d11 >= 16:
                first_warning_day = 11

        if inv_straw >= 10000 and saturation_day is None:
            saturation_day = day

        act_bot = agent_under_test.agent(obs)
        act_opp = opp_actions[step]
        acts = [act_opp, act_bot] if seat == 1 else [act_bot, act_opp]

        # Check if RC4 confirmed
        if agent_name == "RC4" and getattr(rc4_mod, "_FLOOD_CONFIRMED", False) and confirm_day is None:
            confirm_day = day

        # Accounting for sales
        if isinstance(act_bot, dict):
            for ord_item in act_bot.get("market", []):
                if len(ord_item) >= 3 and ord_item[0] == "SELL":
                    item, qty = ord_item[1], ord_item[2]
                    price = mkt.prices.get(item, 0)
                    r = qty * price * 0.95
                    if item == "STRAWBERRY":
                        is_pre = (confirm_day is None) or (day <= confirm_day)
                        if is_pre:
                            straw_units_pre_confirm += qty
                            straw_rev_pre_confirm += r
                        else:
                            straw_units_post_confirm += qty
                            straw_rev_post_confirm += r
                    else:
                        replace_rev_total += r

        env.step(acts)

    final_score = env.state[seat].observation.farms[seat].money
    return {
        "score": final_score,
        "opp_straw_d11": opp_straw_d11,
        "first_warning_day": first_warning_day,
        "confirm_day": confirm_day,
        "saturation_day": saturation_day,
        "straw_units_pre": straw_units_pre_confirm,
        "straw_rev_pre": straw_rev_pre_confirm,
        "straw_units_post": straw_units_post_confirm,
        "straw_rev_post": straw_rev_post_confirm,
        "replace_rev": replace_rev_total,
    }

print("=" * 135)
print("STRATIFIED OUT-OF-SAMPLE AUDIT: RC2 vs RC3 vs RC4 (ECONOMETRIC TIME-TO-CONFIRMATION & REVENUE BREAKDOWN)")
print("=" * 135)

report_rows = []
for label, r_relpath, seat in STRATIFIED_TESTS:
    r_path = os.path.join(r"D:\kaggriculture", r_relpath)
    res_rc2 = run_audited_game(rc2_mod, "RC2", r_path, seat=seat)
    res_rc3 = run_audited_game(rc3_mod, "RC3", r_path, seat=seat)
    res_rc4 = run_audited_game(rc4_mod, "RC4", r_path, seat=seat)

    c_day_str = f"D{res_rc4['confirm_day']}" if res_rc4['confirm_day'] else "NO"
    sat_day_str = f"D{res_rc4['saturation_day']}" if res_rc4['saturation_day'] else "NO"

    d_rc2 = res_rc4["score"] - res_rc2["score"]
    d_rc3 = res_rc4["score"] - res_rc3["score"]

    row = {
        "regime": label,
        "opp_straw": res_rc4["opp_straw_d11"],
        "rc2_score": res_rc2["score"],
        "rc3_score": res_rc3["score"],
        "rc4_score": res_rc4["score"],
        "diff_rc2": d_rc2,
        "diff_rc3": d_rc3,
        "confirm_day": c_day_str,
        "saturation_day": sat_day_str,
        "rc4_straw_pre": res_rc4["straw_rev_pre"],
        "rc3_straw_pre": res_rc3["straw_rev_pre"],
        "rc4_units_pre": res_rc4["straw_units_pre"],
        "rc4_replace_rev": res_rc4["replace_rev"]
    }
    report_rows.append(row)

print(f"{'EXPOSURE REGIME':<33} | {'OPP':>3} | {'RC2 SCORE':>10} | {'RC3 SCORE':>10} | {'RC4 SCORE':>10} | {'Diff(RC4-RC2)':>13} | {'Diff(RC4-RC3)':>13} | {'CONFIRM':>7} | {'SATURATED':>9}")
print("-" * 135)
for r in report_rows:
    print(f"{r['regime']:<33} | {r['opp_straw']:>3} | ${r['rc2_score']:>9,.0f} | ${r['rc3_score']:>9,.0f} | ${r['rc4_score']:>9,.0f} | ${r['diff_rc2']:>+12,.0f} | ${r['diff_rc3']:>+12,.0f} | {r['confirm_day']:>7} | {r['saturation_day']:>9}")

print("=" * 135)

print("\n" + "=" * 115)
print("RC4 TIME-TO-CONFIRMATION & HIGH-PRICE STRAWBERRY HARVEST ACCOUNTING:")
print("=" * 115)
print(f"{'EXPOSURE REGIME':<33} | {'CONFIRM':>7} | {'PRE-CONF UNITS':>14} | {'RC4 PRE-CONF $':>15} | {'RC3 TOTAL STRAW $':>18} | {'RECOVERED ALPHA':>15}")
print("-" * 115)
for r in report_rows:
    alpha = r['rc4_straw_pre'] - r['rc3_straw_pre']
    print(f"{r['regime']:<33} | {r['confirm_day']:>7} | {r['rc4_units_pre']:>14} | ${r['rc4_straw_pre']:>14,.0f} | ${r['rc3_straw_pre']:>17,.0f} | ${alpha:>+14,.0f}")
print("=" * 115)

with open("reports/RC4_STRATIFIED_ACCOUNTING_AUDIT.json", "w") as f:
    json.dump(report_rows, f, indent=2)
print("Complete audit saved to reports/RC4_STRATIFIED_ACCOUNTING_AUDIT.json")
