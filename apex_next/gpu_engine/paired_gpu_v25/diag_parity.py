import os
import sys
import numpy as np

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from apex_next.gpu_engine.paired_gpu_v25.paired_engine_v25 import VectorizedPairedEngineV25
from apex_next.gpu_engine.paired_gpu_v25.policy_adapter import make_vector_apex35_policy, make_vector_candidate_policy
from apex_next.gpu_engine.paired_sim_v2 import PairedSimV2Engine

seeds = [101, 202, 303, 404, 505, 606, 707, 808, 909, 1010]

def v2_cand(obs):
    farm0 = obs['farms'][0]
    inv = farm0['inventory']
    orders = []
    if inv.get('MILK', 0) >= 2.0: orders.append(['SELL', 'MILK', inv['MILK']])
    if farm0['land'] == 4:
        if obs['step'] >= 120 and farm0['money'] >= 1800:
            orders.append(['BUY_LAND'])
    return {'market': orders}
    
def v2_base(obs):
    farm0 = obs['farms'][0]
    inv = farm0['inventory']
    orders = []
    if inv.get('MILK', 0) >= 2.0: orders.append(['SELL', 'MILK', inv['MILK']])
    if farm0['land'] == 4:
        if obs['step'] >= 170 and farm0['money'] >= 1000:
            orders.append(['BUY_LAND'])
    return {'market': orders}

print("=== V2 PER SEED ===")
v2_cand_mcvs, v2_base_mcvs = [], []
for s in seeds:
    eng = PairedSimV2Engine(seed=s)
    res_v2 = eng.run_paired_match(v2_cand, v2_base)
    print(f"Seed {s}: Cand={res_v2['mean_cand_mcv']}, Base={res_v2['mean_base_mcv']}, WR={res_v2['win_rate']}")
    v2_cand_mcvs.append(res_v2['mean_cand_mcv'])
    v2_base_mcvs.append(res_v2['mean_base_mcv'])

print("\n=== V2.5 BATCH ===")
engine_v25 = VectorizedPairedEngineV25(batch_size=len(seeds))
res_v25 = engine_v25.run_paired_batch(make_vector_candidate_policy(min_land_step=120, land_cash_threshold=1800.0), make_vector_apex35_policy(), seeds)
print(f"V2.5: Cand Mean={res_v25['mean_cand_mcv']}, Base Mean={res_v25['mean_base_mcv']}, WR={res_v25['paired_win_rate']}")
