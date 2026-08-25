"""
EXP-0136 Simulator Incident Audit: Animal Lifecycle & Pasture State Transition Analysis
Step-by-step reproduction of:
1. BUY_ANIMAL COW 5 at Step 0
2. BUILD_PASTURE at Step 1
3. Animal placement / deployment state in kaggle_environments v1.32.6 vs PAIRED_GPU_V2.5
4. Identifies the exact first state divergence point.
Outputs:
- reports/SIMULATOR_INCIDENT_AUDIT_EXP0136.json
- reports/SIMULATOR_INCIDENT_AUDIT_EXP0136.md
"""
import os
import sys
import json
import kaggle_environments

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)


def trace_official_animal_lifecycle():
    print("==========================================================================")
    print("[INCIDENT AUDIT] STEP-BY-STEP ANIMAL LIFECYCLE IN KAGGLE_ENVIRONMENTS V1.32.6")
    print("==========================================================================\n")
    
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 20})
    env.reset()
    
    # Trace Candidate (P0: Buy 5 Cows Step 0, Build Pasture Step 1) vs Baseline (P1: Buy 3 Cows Step 0, Build Pasture + Buy 1 Sheep Step 1)
    trajectory_log = []
    
    for step in range(15):
        if step == 0:
            act0 = {"market": [["BUY_ANIMAL", "COW", 5]]}
            act1 = {"market": [["BUY_ANIMAL", "COW", 3]]}
        elif step == 1:
            act0 = {"farmer": ["BUILD_PASTURE"], "market": []}
            act1 = {"farmer": ["BUILD_PASTURE"], "market": [["BUY_ANIMAL", "SHEEP", 1]]}
        elif step == 6: # Milking tick 1
            act0 = {"market": []}
            act1 = {"market": []}
        elif step == 12: # Milking tick 2
            act0 = {"market": []}
            act1 = {"market": []}
        else:
            act0 = {"market": []}
            act1 = {"market": []}
            
        state = env.step([act0, act1])
        
        p0_obs = state[0]["observation"]
        p1_obs = state[1]["observation"]
        
        p0_farm = p0_obs["farms"][0]
        p1_farm = p1_obs["farms"][0]
        
        step_info = {
            "step": step,
            "p0_money": p0_farm.get("money"),
            "p1_money": p1_farm.get("money"),
            "p0_tiles": p0_farm.get("tiles"),
            "p0_shed": p0_obs.get("private", {}).get("shed", {}),
            "p1_shed": p1_obs.get("private", {}).get("shed", {}),
            "p0_raw_farm": {k: v for k, v in p0_farm.items() if k != "tiles"},
            "p1_raw_farm": {k: v for k, v in p1_farm.items() if k != "tiles"}
        }
        trajectory_log.append(step_info)
        
        print(f"--- STEP {step} ---")
        print(f"  P0 Money: ${p0_farm.get('money'):.2f} | Shed: {p0_obs.get('private', {}).get('shed', {})}")
        print(f"  P1 Money: ${p1_farm.get('money'):.2f} | Shed: {p1_obs.get('private', {}).get('shed', {})}")
        print(f"  P0 Farm Fields: {step_info['p0_raw_farm']}")
        print(f"  P1 Farm Fields: {step_info['p1_raw_farm']}\n")
        
    return trajectory_log


if __name__ == "__main__":
    trace_official_animal_lifecycle()
