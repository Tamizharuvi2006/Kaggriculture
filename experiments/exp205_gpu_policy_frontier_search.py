"""
EXP205 — GPU Massive Policy Frontier Search Engine (NVIDIA RTX 4050).
Evaluates 1,000 candidate policy parameterizations across 100,000 game states (100M evals)
on GPU Tensor Cores to rank and select the Top 5 Elite Frontier Candidates.
"""

import os
import sys
import time
import json
import numpy as np
import torch
import torch.nn.functional as F

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

EXPORT_PATH = r"D:\kaggriculture\models\exp205_top_frontier_candidates.json"

def run_gpu_policy_frontier_search():
    print("=" * 90)
    print("EXP205 -- GPU MASSIVE POLICY FRONTIER SEARCH (1,000 POLICIES x 100,000 STATES)")
    print("=" * 90)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Executing on device: {device} ({torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'})")

    num_policies = 1000
    num_states = 100000

    torch.manual_seed(42)
    np.random.seed(42)

    # 1. Generate 1,000 candidate policy parameter vectors:
    # Param 0: early_wheat_day2_thresh (cash needed) [80.0 - 250.0]
    # Param 1: worker_hire_day2_thresh (cash needed) [40.0 - 150.0]
    # Param 2: melon_seed_prob [0.0 - 1.0]
    # Param 3: fert_sell_price_min [50.0 - 100.0]
    # Param 4: fourth_cow_day6_thresh (cash needed) [800.0 - 1500.0]
    # Param 5: q2_land_day7_thresh (cash needed) [400.0 - 1000.0]
    # Param 6: sheep_low_liq_size (1 vs 2)
    # Param 7: sheep_fast_growth_size (2 vs 4)
    # Param 8: late_worker_max (3 to 6)
    # Param 9: margin_verification_gate [100.0 - 300.0]

    policy_params = torch.zeros((num_policies, 10), dtype=torch.float32, device=device)
    policy_params[:, 0] = torch.FloatTensor(num_policies).uniform_(80.0, 250.0).to(device)
    policy_params[:, 1] = torch.FloatTensor(num_policies).uniform_(40.0, 150.0).to(device)
    policy_params[:, 2] = torch.FloatTensor(num_policies).uniform_(0.0, 1.0).to(device)
    policy_params[:, 3] = torch.FloatTensor(num_policies).uniform_(50.0, 100.0).to(device)
    policy_params[:, 4] = torch.FloatTensor(num_policies).uniform_(800.0, 1500.0).to(device)
    policy_params[:, 5] = torch.FloatTensor(num_policies).uniform_(400.0, 1000.0).to(device)
    policy_params[:, 6] = torch.randint(1, 3, (num_policies,), device=device).float()
    policy_params[:, 7] = torch.randint(2, 5, (num_policies,), device=device).float()
    policy_params[:, 8] = torch.randint(3, 7, (num_policies,), device=device).float()
    policy_params[:, 9] = torch.FloatTensor(num_policies).uniform_(100.0, 300.0).to(device)

    # 2. Generate 100,000 realistic game states across diverse market regimes:
    # State features: p_fert, p_wheat, p_milk, p_wool, cash, cows, sheep, hands, quads, day, opp_cash
    p_fert = torch.FloatTensor(num_states).uniform_(40.0, 110.0).to(device)
    p_wheat = torch.FloatTensor(num_states).uniform_(20.0, 45.0).to(device)
    p_milk = torch.FloatTensor(num_states).uniform_(90.0, 210.0).to(device)
    p_wool = torch.FloatTensor(num_states).uniform_(110.0, 240.0).to(device)
    cash = torch.FloatTensor(num_states).uniform_(200.0, 5000.0).to(device)
    opp_cash = torch.FloatTensor(num_states).uniform_(200.0, 5000.0).to(device)
    day = torch.randint(0, 30, (num_states,), device=device).float()

    print(f"Generated {num_policies:,} policy vectors and {num_states:,} market states on GPU.")
    print("Executing batched GPU Tensor Core evaluation (100,000,000 evaluations)...")

    torch.cuda.synchronize()
    t0 = time.perf_counter()

    # Batch compute scores across all policies
    # Policy scoring kernel on GPU
    policy_scores = torch.zeros(num_policies, dtype=torch.float32, device=device)

    # Evaluate in chunks of 50 policies x 100,000 states to optimize L2 cache
    chunk_size = 50
    for c in range(0, num_policies, chunk_size):
        chunk_params = policy_params[c:c+chunk_size] # [chunk_size, 10]
        
        # Vectorized scoring logic:
        # 1. Fast growth bonus when fertilizer high & wheat low
        is_fast_growth = (p_fert >= chunk_params[:, 3].unsqueeze(1)) & (p_wheat <= 35.0)
        fast_growth_score = is_fast_growth.float() * (p_fert.unsqueeze(0) * 8.0 - chunk_params[:, 0].unsqueeze(1) * 0.5)
        
        # 2. Cow reinvestment yield
        cow_score = (chunk_params[:, 4].unsqueeze(1) <= cash.unsqueeze(0)).float() * (p_milk.unsqueeze(0) * 20.0 - 1000.0)
        
        # 3. Sheep yield in low vs high liquidity
        sheep_score = torch.where(
            cash.unsqueeze(0) >= 2400.0,
            chunk_params[:, 7].unsqueeze(1) * p_wool.unsqueeze(0) * 15.0 - 2400.0,
            chunk_params[:, 6].unsqueeze(1) * p_wool.unsqueeze(0) * 15.0 - 1200.0
        )
        
        # 4. Competitive margin delta estimation vs opponent cash
        est_margin = (fast_growth_score + cow_score + sheep_score) + (cash.unsqueeze(0) - opp_cash.unsqueeze(0)) * 0.8
        
        # Gating filter: margin verification gate
        gated_margin = torch.where(est_margin >= chunk_params[:, 9].unsqueeze(1), est_margin, torch.zeros_like(est_margin))
        
        chunk_means = gated_margin.mean(dim=1)
        policy_scores[c:c+chunk_size] = chunk_means

    torch.cuda.synchronize()
    elapsed = time.perf_counter() - t0

    throughput = (num_policies * num_states) / elapsed
    print(f"\n100,000,000 GPU evaluations completed in {elapsed:.3f}s ({throughput:>12,.1f} evals/sec) 🚀")

    # Select Top 5 Frontier Candidates
    top_k = 5
    top_scores, top_indices = torch.topk(policy_scores, top_k)
    top_indices_cpu = top_indices.cpu().numpy()
    top_scores_cpu = top_scores.cpu().numpy()

    print("\n" + "=" * 90)
    print("                                TOP 5 ELITE FRONTIER CANDIDATES                                ")
    print("=" * 90)
    print(f"{'Rank':<6} | {'Candidate ID':<14} | {'GPU Est. Margin':<18} | {'Key Parameter Configuration'}")
    print("-" * 90)

    top_candidates_data = []

    for rank, (idx, score) in enumerate(zip(top_indices_cpu, top_scores_cpu)):
        p = policy_params[idx].cpu().numpy()
        cand_dict = {
            "rank": rank + 1,
            "candidate_id": f"EXP205_Cand_{idx:03d}",
            "gpu_score": float(score),
            "early_wheat_thresh": float(p[0]),
            "worker_hire_thresh": float(p[1]),
            "melon_prob": float(p[2]),
            "fert_sell_min": float(p[3]),
            "fourth_cow_thresh": float(p[4]),
            "q2_land_thresh": float(p[5]),
            "sheep_low_liq": int(p[6]),
            "sheep_fast_growth": int(p[7]),
            "late_worker_max": int(p[8]),
            "margin_gate": float(p[9]),
        }
        top_candidates_data.append(cand_dict)
        
        summary_str = f"FertMin=${p[3]:.0f}, CowThresh=${p[4]:.0f}, SheepFast={int(p[7])}, Gate=${p[9]:.0f}"
        print(f"#{rank+1:<5} | {cand_dict['candidate_id']:<14} | +${score:>14,.1f} | {summary_str}")

    print("=" * 90)

    os.makedirs(os.path.dirname(EXPORT_PATH), exist_ok=True)
    with open(EXPORT_PATH, "w") as f:
        json.dump(top_candidates_data, f, indent=2)
    print(f"Exported Top 5 Frontier Candidates to {EXPORT_PATH}")

if __name__ == "__main__":
    run_gpu_policy_frontier_search()
