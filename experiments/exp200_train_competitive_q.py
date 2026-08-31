"""
EXP200 — Train Competitive Margin-Advantage Q-Network on GPU from exp200_competitive_dataset.csv.
Optimizes Margin Delta ΔMargin = (R_hero(a) - R_opp(a)) - (R_hero(a0) - R_opp(a0)) instead of solo wealth.
"""

import os
import sys
import json
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.utils.data import TensorDataset, DataLoader

CSV_PATH = r"D:\kaggriculture\data\exp200_competitive_dataset.csv"
MODEL_JSON = r"D:\kaggriculture\models\exp200_competitive_q_weights.json"
MODEL_NPZ = r"D:\kaggriculture\models\exp200_competitive_q_weights.npz"

class CompetitiveMarginQNetwork(nn.Module):
    def __init__(self, state_dim=16, num_actions=6, hidden_dim=128):
        super().__init__()
        self.trunk = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 64),
            nn.LayerNorm(64),
            nn.ReLU(),
        )
        self.q_margin_head = nn.Linear(64, num_actions)

    def forward(self, state):
        feat = self.trunk(state)
        q_margin = self.q_margin_head(feat)
        return q_margin

def pairwise_margin_loss(pred_q, true_margin_deltas):
    B, A = pred_q.shape
    pred_diff = pred_q.unsqueeze(2) - pred_q.unsqueeze(1)
    true_diff = true_margin_deltas.unsqueeze(2) - true_margin_deltas.unsqueeze(1)
    
    target_sign = torch.sign(true_diff)
    weights = torch.abs(true_diff) / 1000.0
    
    pair_loss = F.softplus(-target_sign * pred_diff) * weights
    mask = (1.0 - torch.eye(A, device=pred_q.device)).unsqueeze(0)
    return (pair_loss * mask).sum() / (B * A * (A - 1))

def train():
    print("=" * 80)
    print("EXP200 -- TRAINING COMPETITIVE MARGIN-ADVANTAGE Q-NETWORK ON GPU")
    print("=" * 80)

    if not os.path.exists(CSV_PATH):
        print(f"Dataset not found at {CSV_PATH}")
        return

    df = pd.read_csv(CSV_PATH)
    print(f"Loaded {len(df):,} competitive records from EXP200 dataset.")

    feature_cols = [
        "p_milk", "cash", "cows", "sheep", "shed_wheat", "hands", "quads", "day", "unwatered", "mature",
        "opp_cash", "opp_cows", "opp_sheep", "opp_quads", "opp_workers", "opp_straws"
    ]
    states = df[feature_cols].values.astype(np.float32)

    margin_delta_cols = [f"d_m{i}" for i in range(6)]
    margin_deltas = df[margin_delta_cols].values.astype(np.float32)
    best_actions = df["best_a"].values.astype(np.int64)
    max_margin_gains = df["max_margin_gain"].values.astype(np.float32)

    state_mean = states.mean(axis=0)
    state_std = states.std(axis=0) + 1e-6
    states_norm = (states - state_mean) / state_std

    seeds = df["seed"].values
    unique_seeds = np.unique(seeds)
    np.random.seed(42)
    np.random.shuffle(unique_seeds)
    split_idx = int(0.8 * len(unique_seeds))
    train_seeds = set(unique_seeds[:split_idx])

    train_mask = np.isin(seeds, list(train_seeds))
    test_mask = ~train_mask

    print(f"Train samples: {train_mask.sum():,} | Test samples: {test_mask.sum():,}")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Training on: {device} ({torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'})")

    train_dataset = TensorDataset(
        torch.tensor(states_norm[train_mask]),
        torch.tensor(margin_deltas[train_mask]),
        torch.tensor(best_actions[train_mask]),
        torch.tensor(max_margin_gains[train_mask])
    )
    test_dataset = TensorDataset(
        torch.tensor(states_norm[test_mask]),
        torch.tensor(margin_deltas[test_mask]),
        torch.tensor(best_actions[test_mask]),
        torch.tensor(max_margin_gains[test_mask])
    )

    train_loader = DataLoader(train_dataset, batch_size=64, shuffle=True)
    test_loader = DataLoader(test_dataset, batch_size=128, shuffle=False)

    model = CompetitiveMarginQNetwork(state_dim=len(feature_cols), num_actions=6).to(device)
    optimizer = optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
    smooth_l1 = nn.SmoothL1Loss(beta=500.0)

    print("\n--- Training Competitive Margin Q-Network (30 Epochs) ---")
    t0 = time.time()
    for epoch in range(30):
        model.train()
        total_loss = 0.0
        for b_st, b_mdel, b_act, b_mgain in train_loader:
            b_st, b_mdel = b_st.to(device), b_mdel.to(device)
            optimizer.zero_grad()
            q_vals = model(b_st) # [B, 6]
            
            l_pair = pairwise_margin_loss(q_vals, b_mdel)
            l_anchor = smooth_l1(q_vals - q_vals[:, 0:1], b_mdel)
            loss = l_pair + 0.001 * l_anchor
            
            loss.backward()
            optimizer.step()
            total_loss += loss.item() * len(b_st)

        if (epoch + 1) % 5 == 0 or epoch == 0:
            model.eval()
            all_preds = []
            all_true_best = []
            all_margin_deltas = []
            with torch.no_grad():
                for b_st, b_mdel, b_act, b_mgain in test_loader:
                    b_st = b_st.to(device)
                    q_vals = model(b_st)
                    preds = q_vals.argmax(dim=-1).cpu().numpy()
                    all_preds.extend(preds)
                    all_true_best.extend(b_act.numpy())
                    all_margin_deltas.extend(b_mdel.cpu().numpy())

            preds_arr = np.array(all_preds)
            best_arr = np.array(all_true_best)
            mdels_arr = np.array(all_margin_deltas)

            top1_acc = (preds_arr == best_arr).mean() * 100.0
            
            # Margin regret
            chosen_margins = mdels_arr[np.arange(len(preds_arr)), preds_arr]
            max_margins = mdels_arr.max(axis=-1)
            mean_margin_regret = (max_margins - chosen_margins).mean()
            base_margin_regret = max_margins.mean() # Since base margin delta is 0

            # When model proposes intervention (pred != 0)
            interv_mask = (preds_arr != 0)
            avg_interv_gain = chosen_margins[interv_mask].mean() if interv_mask.sum() > 0 else 0.0

            print(f"Epoch {epoch+1:2d}/30 | Top-1 Margin Acc: {top1_acc:5.1f}% | Margin Regret: ${mean_margin_regret:6.1f} (vs Base Regret: ${base_margin_regret:6.1f}) | Interv Count: {interv_mask.sum():4d} | Avg Margin Gain: +${avg_interv_gain:7.1f}")

    elapsed = time.time() - t0
    print(f"\nTraining Complete in {elapsed:.1f}s")

    os.makedirs(os.path.dirname(MODEL_JSON), exist_ok=True)
    weights_dict = {
        "feature_cols": feature_cols,
        "state_mean": state_mean.tolist(),
        "state_std": state_std.tolist(),
        "trunk_fc1_weight": model.trunk[0].weight.detach().cpu().numpy().tolist(),
        "trunk_fc1_bias": model.trunk[0].bias.detach().cpu().numpy().tolist(),
        "trunk_ln1_weight": model.trunk[1].weight.detach().cpu().numpy().tolist(),
        "trunk_ln1_bias": model.trunk[1].bias.detach().cpu().numpy().tolist(),
        "trunk_fc2_weight": model.trunk[3].weight.detach().cpu().numpy().tolist(),
        "trunk_fc2_bias": model.trunk[3].bias.detach().cpu().numpy().tolist(),
        "trunk_ln2_weight": model.trunk[4].weight.detach().cpu().numpy().tolist(),
        "trunk_ln2_bias": model.trunk[4].bias.detach().cpu().numpy().tolist(),
        "q_margin_head_weight": model.q_margin_head.weight.detach().cpu().numpy().tolist(),
        "q_margin_head_bias": model.q_margin_head.bias.detach().cpu().numpy().tolist(),
    }

    with open(MODEL_JSON, "w") as f:
        json.dump(weights_dict, f)
    print(f"Exported native Rust weights to {MODEL_JSON}")

    np.savez_compressed(
        MODEL_NPZ,
        state_mean=state_mean,
        state_std=state_std,
        feature_cols=feature_cols,
        **{k: v.detach().cpu().numpy() for k, v in model.state_dict().items()}
    )
    print(f"Saved PyTorch weights to {MODEL_NPZ}")

if __name__ == "__main__":
    train()
