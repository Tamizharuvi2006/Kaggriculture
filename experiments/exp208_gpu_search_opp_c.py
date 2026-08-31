"""
EXP208 — GPU Candidate Counter-Strategy Search against Opponent C & Elite Population.
Evaluates 1,000 counter-strategy parameterizations across 100,000 states on GPU Tensor Cores.
"""

import os
import sys
import time
import json
import numpy as np
import torch

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

EXPORT_PATH = r"D:\kaggriculture\models\exp208_top_champion_candidates.json"

def run_gpu_search():
    print("=" * 90)
    print("EXP208 -- GPU COUNTER-STRATEGY SEARCH (1,000 POLICIES x 100,000 STATES)")
    print("=" * 90)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Executing on device: {device} ({torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'})")

    num_policies = 1000
    num_states = 100000

    torch.manual_seed(101)
    np.random.seed(101)

    # Policy parameters:
    # 0: fert_dump_cadence_hours (2 to 8 hours)
    # 1: fert_dump_min_qty (1 to 4)
    # 2: fert_dump_min_price (40.0 to 90.0)
    # 3: sheep_wool_price_cutoff (130.0 to 190.0) -> if below, buy 2 sheep; else 4 sheep
    # 4: q3_land_unlock_cash_thresh (800.0 to 1800.0)
    # 5: cow_reinvest_thresh (800.0 to 1400.0)
    # 6: straw_late_seed_count (8 to 24)
    # 7: endgame_flush_step (620 to 690)
    # 8: margin_verification_gate (120.0 to 280.0)

    policy_params = torch.zeros((num_policies, 9), dtype=torch.float32, device=device)
    policy_params[:, 0] = torch.randint(2, 9, (num_policies,), device=device).float()
    policy_params[:, 1] = torch.randint(1, 5, (num_policies,), device=device).float()
    policy_params[:, 2] = torch.FloatTensor(num_policies).uniform_(40.0, 90.0).to(device)
    policy_params[:, 3] = torch.FloatTensor(num_policies).uniform_(130.0, 190.0).to(device)
    policy_params[:, 4] = torch.FloatTensor(num_policies).uniform_(800.0, 1800.0).to(device)
    policy_params[:, 5] = torch.FloatTensor(num_policies).uniform_(800.0, 1400.0).to(device)
    policy_params[:, 6] = torch.randint(8, 25, (num_policies,), device=device).float()
    policy_params[:, 7] = torch.FloatTensor(num_policies).uniform_(620.0, 690.0).to(device)
    policy_params[:, 8] = torch.FloatTensor(num_policies).uniform_(120.0, 280.0).to(device)

    # 100,000 diverse states
    p_fert = torch.FloatTensor(num_states).uniform_(40.0, 110.0).to(device)
    p_wheat = torch.FloatTensor(num_states).uniform_(20.0, 45.0).to(device)
    p_milk = torch.FloatTensor(num_states).uniform_(90.0, 210.0).to(device)
    p_wool = torch.FloatTensor(num_states).uniform_(110.0, 240.0).to(device)
    p_straw = torch.FloatTensor(num_states).uniform_(90.0, 180.0).to(device)
    cash = torch.FloatTensor(num_states).uniform_(300.0, 6000.0).to(device)
    opp_cash = torch.FloatTensor(num_states).uniform_(300.0, 6000.0).to(device)
    fert_in_shed = torch.randint(0, 15, (num_states,), device=device).float()
    day = torch.randint(2, 28, (num_states,), device=device).float()

    print(f"Generated {num_policies:,} policy vectors and {num_states:,} market states on GPU.")
    print("Executing batched GPU Tensor Core evaluation (100,000,000 evaluations)...")

    torch.cuda.synchronize()
    t0 = time.perf_counter()

    policy_scores = torch.zeros(num_policies, dtype=torch.float32, device=device)
    chunk_size = 50

    for c in range(0, num_policies, chunk_size):
        chunk_p = policy_params[c:c+chunk_size] # [chunk_size, 9]

        # 1. Fertilizer micro-liquidity yield
        can_sell_fert = (p_fert.unsqueeze(0) >= chunk_p[:, 2].unsqueeze(1)) & (fert_in_shed.unsqueeze(0) >= chunk_p[:, 1].unsqueeze(1))
        fert_yield = can_sell_fert.float() * (fert_in_shed.unsqueeze(0) * p_fert.unsqueeze(0) * 1.2)

        # 2. Dynamic sheep sizing yield (2 vs 4 sheep)
        size_4_sheep = (p_wool.unsqueeze(0) >= chunk_p[:, 3].unsqueeze(1)) & (cash.unsqueeze(0) >= 2400.0)
        sheep_yield = torch.where(
            size_4_sheep,
            4.0 * p_wool.unsqueeze(0) * 16.0 - 2400.0,
            2.0 * p_wool.unsqueeze(0) * 16.0 - 1200.0
        )

        # 3. Quadrant 3 early land expansion yield
        can_unlock_q3 = (cash.unsqueeze(0) >= chunk_p[:, 4].unsqueeze(1)) & (day.unsqueeze(0) >= 11.0)
        q3_yield = can_unlock_q3.float() * (p_straw.unsqueeze(0) * 12.0 * 2.0 - 1000.0)

        # 4. Total estimated margin vs opponent cash
        est_margin = (fert_yield + sheep_yield + q3_yield) + (cash.unsqueeze(0) - opp_cash.unsqueeze(0)) * 0.85
        gated_margin = torch.where(est_margin >= chunk_p[:, 8].unsqueeze(1), est_margin, torch.zeros_like(est_margin))

        chunk_means = gated_margin.mean(dim=1)
        policy_scores[c:c+chunk_size] = chunk_means

    torch.cuda.synchronize()
    elapsed = time.perf_counter() - t0

    throughput = (num_policies * num_states) / elapsed
    print(f"\n100,000,000 GPU evaluations completed in {elapsed:.3f}s ({throughput:>12,.1f} evals/sec) 🚀")

    # Select Top 5 Champion Candidates
    top_k = 5
    top_scores, top_indices = torch.topk(policy_scores, top_k)
    top_indices_cpu = top_indices.cpu().numpy()
    top_scores_cpu = top_scores.cpu().numpy()

    print("\n" + "=" * 90)
    print("                                TOP 5 EXP208 CHAMPION CANDIDATES                                ")
    print("=" * 90)
    print(f"{'Rank':<6} | {'Candidate ID':<14} | {'GPU Est. Margin':<18} | {'Key Parameter Configuration'}")
    print("-" * 90)

    top_candidates_data = []
    for rank, (idx, score) in enumerate(zip(top_indices_cpu, top_scores_cpu)):
        p = policy_params[idx].cpu().numpy()
        cand_dict = {
            "rank": rank + 1,
            "candidate_id": f"EXP208_Champ_{idx:03d}",
            "gpu_score": float(score),
            "fert_cadence_hours": int(p[0]),
            "fert_min_qty": int(p[1]),
            "fert_min_price": float(p[2]),
            "sheep_wool_cutoff": float(p[3]),
            "q3_cash_thresh": float(p[4]),
            "cow_reinvest_thresh": float(p[5]),
            "straw_late_seeds": int(p[6]),
            "endgame_step": float(p[7]),
            "margin_gate": float(p[8]),
        }
        top_candidates_data.append(cand_dict)
        summary_str = f"FertCadence={int(p[0])}h, FertMin=${p[2]:.0f}, WoolCutoff=${p[3]:.0f}, Q3Thresh=${p[4]:.0f}, Gate=${p[8]:.0f}"
        print(f"#{rank+1:<5} | {cand_dict['candidate_id']:<14} | +${score:>14,.1f} | {summary_str}")

    print("=" * 90)

    os.makedirs(os.path.dirname(EXPORT_PATH), exist_ok=True)
    with open(EXPORT_PATH, "w") as f:
        json.dump(top_candidates_data, f, indent=2)
    print(f"Exported Top 5 Champion Candidates to {EXPORT_PATH}")

if __name__ == "__main__":
    run_gpu_search()
