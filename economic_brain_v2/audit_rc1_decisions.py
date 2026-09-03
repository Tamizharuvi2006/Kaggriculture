import sys
sys.path.insert(0, r"D:\kaggriculture")

import json, os, kaggle_environments
import submission_rc1_ev_dispatcher as rc1

replay_path = r"D:\kaggriculture\reports\live_match_telemetry\episode-104475527-replay.json"
with open(replay_path) as f: rep = json.load(f)
seed = rep["info"]["seed"]
steps = rep["steps"]
opp_actions = [frame[1].get("action") for frame in steps[1:]]

env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": len(steps), "seed": seed})
env.reset()

print("=" * 90)
print("     RC1 DECISION AUDIT & EV/TURN VERIFICATION (Day 14 Telemetry)                ")
print("=" * 90)

audit_done = False

for s in range(len(opp_actions)):
    if env.done: break
    obs = env.state[0].observation
    day = s // 24
    hour = s % 24
    
    # Audit Day 14 at Hour 2 (Peak operations: animals, watering, care, harvesting)
    if day == 14 and hour == 2 and not audit_done:
        farm = obs["farms"][0]
        positions = [tuple(farm.get("farmer", (4, 4)))] + [tuple(p) for p in farm.get("hands", [])]
        private = obs.get("private", {}) or {}
        inventories = list(private.get("inventories", []) or [])
        while len(inventories) < len(positions): inventories.append({})
        
        tasks = rc1._build_tasks(obs, positions, inventories)
        free = set(range(len(positions)))
        
        print(f"\n--- AUDITING STEP {s} (Day 14, Hour 2) ---")
        print(f"Active Workers: {len(positions)} | Total Tasks in Queue: {len(tasks)}")
        
        # Trace EV/turn calculations for top decisions
        pending = [t for t in tasks if t[0] > 0]
        assigned_decisions = []
        
        while pending and free:
            candidates = []
            for unit in free:
                inv = inventories[unit]
                pos_u = positions[unit]
                q_u = rc1._quadrant(pos_u)
                carried_animal = any(int(inv.get(a, 0)) > 0 for a in rc1.ANIMALS) if isinstance(inv, dict) else False
                for j, task in enumerate(pending):
                    if not rc1._eligible(task, inv): continue
                    if carried_animal and task[4] != "place": continue
                    dist = rc1._distance(pos_u, task[1])
                    friction = 2.0 if task[4] in ("water", "dig", "plant", "fertilizer") and rc1._quadrant(task[1]) != q_u else 0.0
                    turns = 1.0 + dist + friction
                    ev = task[5] if len(task) > 5 else 10.0
                    ev_per_turn = ev / turns
                    candidates.append((ev_per_turn, dist, friction, ev, unit, j, task))
            if not candidates: break
            
            candidates.sort(key=lambda c: c[0], reverse=True)
            best = candidates[0]
            best_ev_per_turn, dist, friction, ev, unit, task_idx, chosen_task = best
            
            # Find runner-up alternatives for this unit
            alt = [c for c in candidates[1:] if c[4] == unit]
            runner_up = alt[0] if alt else None
            
            assigned_decisions.append({
                "unit": unit,
                "pos": positions[unit],
                "task_tag": chosen_task[4],
                "task_pos": chosen_task[1],
                "task_action": chosen_task[2],
                "task_ev": ev,
                "dist": dist,
                "friction": friction,
                "ev_per_turn": best_ev_per_turn,
                "runner_up": runner_up,
            })
            pending.pop(task_idx)
            free.remove(unit)
            
        print("\nWorker Task Dispatch Decisions:")
        for d in assigned_decisions:
            u = d["unit"]
            role = "Farmer" if u == 0 else f"Hand {u}"
            r_str = "None"
            if d["runner_up"]:
                r_ev_turn, r_d, r_f, r_ev, _, _, r_task = d["runner_up"]
                r_str = f"{r_task[4]}@{r_task[1]} (EV:${r_ev:.0f}, dist:{r_d} -> ${r_ev_turn:.1f}/turn)"
            print(f"  [{role:<7}] Pos: {d['pos']} -> Action: {d['task_action']} ({d['task_tag']} at {d['task_pos']})")
            print(f"            EV: ${d['task_ev']:>5.1f} | Dist: {d['dist']} | Friction: {d['friction']} | Net EV/Turn: ${d['ev_per_turn']:>5.2f}/turn")
            print(f"            Rejected Runner-Up: {r_str}")
        audit_done = True
        
    act = rc1.agent(obs)
    env.step([act, opp_actions[s]])

print("\n" + "=" * 90)
print(f"Match Complete! Final Score: ${env.state[0].reward:,.0f} (Zero Exceptions)")
print("=" * 90)
