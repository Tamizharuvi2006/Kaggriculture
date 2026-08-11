import os
import sys
import importlib.util
import numpy as np
import kaggle_environments

v41_path = r"D:\kagriulture\Kaggriculture\baseline\kaitofukami-v18.py"
apex34_path = r"D:\kagriulture\Kaggriculture\generalization_pipeline\submission_candidate_apex34.py"

def load(path):
    spec = importlib.util.spec_from_file_location("mod", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return getattr(mod, "agent")

apex_fn = load(apex34_path)
v41_fn = load(v41_path)

# Let's run seed 504110 (one of the biggest loss seeds, Delta: -$36,266)
# and seed 502740 (one of the big win seeds, Delta: +$2,803)
for seed in [504110, 502740, 501918, 504932]:
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "townCenterSellInterval": 24, "seed": seed})
    trainer = env.train([None, v41_fn])
    obs = trainer.reset()
    
    p0_strawberry_sales = []
    p0_milk_sales = []
    
    for s in range(720):
        act0 = apex_fn(obs)
        for m in (act0.get("market") or []):
            if m[0] == "SELL":
                p = float(obs.get("market", {}).get("prices", {}).get(m[1], 0.0) or 0.0)
                if m[1] == "STRAWBERRY":
                    p0_strawberry_sales.append((s, m[2], p, s % 24 == 23))
                elif m[1] == "MILK":
                    p0_milk_sales.append((s, m[2], p, s % 24 == 23))
        obs, rew, done, info = trainer.step(act0)
        if done:
            break
        
    state = env.state
    farms = state[0]["observation"]["farms"]
    w0 = farms[0]["money"]
    w1 = farms[1]["money"]
    delta = w0 - w1
    print(f"Seed {seed}: P0 (APEX 3.4) = ${w0:,.1f} vs P1 (V4.1) = ${w1:,.1f} | Delta = ${delta:+,.1f}")
    print(f"  P0 Strawberry Sales Count: {len(p0_strawberry_sales)}, Preempt Sales: {sum(1 for x in p0_strawberry_sales if x[3])}")
    print(f"  P0 Milk Sales Count: {len(p0_milk_sales)}, Preempt Sales: {sum(1 for x in p0_milk_sales if x[3])}")
