"""
EXP195 — Train Temporal Sequence Action Ranker on GPU from exp195_temporal_dataset.csv.
Uses ListNet / Softmax Cross-Entropy Ranking Loss to optimize relative action ranking.
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

CSV_PATH = r"D:\kaggriculture\data\exp195_temporal_dataset.csv"
MODEL_JSON = r"D:\kaggriculture\models\exp195_ranking_weights.json"
MODEL_NPZ = r"D:\kaggriculture\models\exp195_ranking_weights.npz"

class TemporalRankerNetwork(nn.Module):
    def __init__(self, state_dim=60, num_actions=6, hidden_dim=128):
        super().__init__()
        self.trunk = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 64),
            nn.LayerNorm(64),
            nn.ReLU(),
        )
        self.score_head = nn.Linear(64, num_actions) # Action Ranking Scores

    def forward(self, state):
        feat = self.trunk(state)
        scores = self.score_head(feat)
        return scores

def train():
    print("=" * 80)
    print("EXP195 -- TRAINING TEMPORAL SEQUENCE ACTION RANKER ON GPU")
    print("=" * 80)

    if not os.path.exists(CSV_PATH):
        print(f"Dataset not found at {CSV_PATH}")
        return

    df = pd.read_csv(CSV_PATH)
    print(f"Loaded {len(df):,} temporal records from EXP195 dataset.")

    # 60 feature columns: t0..t4 x 12 features
    feature_cols = [c for c in df.columns if c.startswith("t0_") or c.startswith("t1_") or c.startswith("t2_") or c.startswith("t3_") or c.startswith("t4_")]
    states = df[feature_cols].values.astype(np.float32)

    score_cols = [f"score_a{i}" for i in range(6)]
    raw_returns = df[score_cols].values.astype(np.float32)
    base_returns = raw_returns[:, 0:1] # a0 baseline
    deltas = raw_returns - base_returns # Δ vs a0

    # Softmax target ranking distribution (ListNet / Plackett-Luce formulation)
    # Temperature 2000.0 smooths the return distribution into soft ranking probabilities
    target_probs = F.softmax(torch.tensor(deltas) / 2000.0, dim=-1).numpy().astype(np.float32)
    best_actions = deltas.argmax(axis=-1).astype(np.int64)

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
        torch.tensor(target_probs[train_mask]),
        torch.tensor(best_actions[train_mask]),
        torch.tensor(raw_returns[train_mask])
    )
    test_dataset = TensorDataset(
        torch.tensor(states_norm[test_mask]),
        torch.tensor(target_probs[test_mask]),
        torch.tensor(best_actions[test_mask]),
        torch.tensor(raw_returns[test_mask])
    )

    train_loader = DataLoader(train_dataset, batch_size=64, shuffle=True)
    test_loader = DataLoader(test_dataset, batch_size=128, shuffle=False)

    model = TemporalRankerNetwork(state_dim=len(feature_cols), num_actions=6).to(device)
    optimizer = optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)

    print("\n--- Training Ranking Network with ListNet Loss (30 Epochs) ---")
    t0 = time.time()
    for epoch in range(30):
        model.train()
        total_loss = 0.0
        for b_st, b_target, b_act, b_sc in train_loader:
            b_st, b_target = b_st.to(device), b_target.to(device)
            optimizer.zero_grad()
            scores = model(b_st)
            
            # ListNet Cross-Entropy Loss: - sum(Y_true * log_softmax(pred))
            pred_log_probs = F.log_softmax(scores, dim=-1)
            loss = -(b_target * pred_log_probs).sum(dim=-1).mean()
            
            loss.backward()
            optimizer.step()
            total_loss += loss.item() * len(b_st)

        if (epoch + 1) % 5 == 0 or epoch == 0:
            model.eval()
            all_preds = []
            all_true_best = []
            all_scores = []
            with torch.no_grad():
                for b_st, b_target, b_act, b_sc in test_loader:
                    b_st = b_st.to(device)
                    scores = model(b_st)
                    preds = scores.argmax(dim=-1).cpu().numpy()
                    all_preds.extend(preds)
                    all_true_best.extend(b_act.numpy())
                    all_scores.extend(b_sc.numpy())

            preds_arr = np.array(all_preds)
            best_arr = np.array(all_true_best)
            scores_arr = np.array(all_scores)

            top1_acc = (preds_arr == best_arr).mean() * 100.0
            
            chosen_rewards = scores_arr[np.arange(len(preds_arr)), preds_arr]
            max_rewards = scores_arr.max(axis=-1)
            mean_regret = (max_rewards - chosen_rewards).mean()
            base_rewards = scores_arr[:, 0]
            base_regret = (max_rewards - base_rewards).mean()

            print(f"Epoch {epoch+1:2d}/30 | Top-1 Rank Accuracy: {top1_acc:5.1f}% | Model Regret: ${mean_regret:6.1f} (vs Baseline Regret: ${base_regret:6.1f})")

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
        "score_head_weight": model.score_head.weight.detach().cpu().numpy().tolist(),
        "score_head_bias": model.score_head.bias.detach().cpu().numpy().tolist(),
    }

    with open(MODEL_JSON, "w") as f:
        json.dump(weights_dict, f)
    print(f"Exported native Rust ranking weights to {MODEL_JSON}")

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
