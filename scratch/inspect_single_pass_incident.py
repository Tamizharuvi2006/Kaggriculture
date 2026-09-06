import json, kaggle_environments, sys
sys.path.insert(0, r"D:\kaggriculture")
import submission_rc4_2_hybrid as rc42

path = r"D:\kaggriculture\reports\live_match_telemetry\episode-104388418-replay.json"
with open(path) as f: rep = json.load(f)
steps = rep["steps"]
opp_s0 = [frame[0].get("action") for frame in steps[1:]]

env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": len(steps)-1, "seed": rep["info"]["seed"]})
env.reset()

found_incidents = 0

for s in range(len(steps)-1):
    if env.done: break
    obs = env.state[1].observation
    day = obs["day"]
    hour = obs["hour"]
    if day < 12:
        act = rc42.agent(obs)
        env.step([opp_s0[s], act])
        continue
    
    # We want to instrument _assign_actions to see WHY a worker was left free
    farm = obs["farms"][1]
    workers = farm.get("workers", []) or farm.get("hands", []) or []
    positions = [farm.get("farmer", [4,4])] + workers
    private = obs.get("private", {}) or {}
    inventories = private.get("inventories", [])
    
    act = rc42.agent(obs)
    worker_acts = act.get("hands", []) if isinstance(act, dict) else []
    
    # Check if any worker passed
    for u_idx, w_act in enumerate(worker_acts):
        if (not w_act or w_act[0] == "PASS") and u_idx > 0: # unit u_idx is a hired hand
            # Let's inspect this hand
            hand_pos = positions[u_idx]
            hand_inv = inventories[u_idx] if u_idx < len(inventories) else {}
            
            # Let's check tasks generated
            tasks = rc42._build_tasks(obs, positions, inventories)
            
            # Check eligibility for tasks
            eligible_tasks = [t for t in tasks if rc42._eligible(t, hand_inv)]
            
            print("=" * 80)
            print(f"INCIDENT #{found_incidents+1}: Day {day:02d} Hour {hour:02d} | Hand #{u_idx} at {hand_pos} EMITTED PASS!")
            print(f"  Hand Inventory: {hand_inv}")
            print(f"  Total Tasks Generated: {len(tasks)}")
            print(f"  Eligible Tasks for Hand: {len(eligible_tasks)}")
            
            # Task types breakdown
            t_types = {}
            for t in tasks:
                t_types[t[4]] = t_types.get(t[4], 0) + 1
            print(f"  Generated Tasks Breakdown: {t_types}")
            
            # Why did matching fail?
            # Let's check how many total units vs total tasks
            print(f"  Total Units: {len(positions)} | Total Tasks: {len(tasks)}")
            found_incidents += 1
            break
    if found_incidents >= 5:
        break
    env.step([opp_s0[s], act])
