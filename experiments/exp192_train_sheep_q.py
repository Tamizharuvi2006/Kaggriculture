"""
EXP192 — Train State-Conditioned Sheep Q-Network Q(s, N) & Regret Minimizer on GPU.
Consumes 5,000 seed counterfactual rollouts from exp191_sheep_q_dataset.csv.
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
import torch.optim as optim
from torch.utils.data import TensorDataset, DataLoader

CSV_PATH = r"D:\kaggriculture\data\exp191_sheep_q_dataset.csv"
MODEL_JSON = r"D:\kaggriculture\models\exp192_sheep_q_weights.json"
MODEL_NPZ = r"D:\kaggriculture\models\exp192_sheep_q_weights.npz"

class SheepQNetwork(nn.Module):
    def __init__(self, state_dim=7, num_options=5, hidden_dim=128):
        super().__init__()
        self.trunk = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 64),
            nn.LayerNorm(64),
            nn.ReLU(),
        )
        self.advantage_head = nn.Linear(64, num_options) # ΔQ(s, N) relative to N=4
        self.policy_logits = nn.Linear(64, num_options)  # P(best_N | s)

    def forward(self, state):
        feat = self.trunk(state)
        adv = self.advantage_head(feat)
        logits = self.policy_logits(feat)
        return adv, logits

def train():
    print("=" * 80)
    print("EXP192 -- TRAINING STATE-CONDITIONED SHEEP Q-NETWORK ON GPU")
    print("=" * 80)

    if not os.path.exists(CSV_PATH):
        print(f"Dataset not found at {CSV_PATH}")
        return

    df = pd.read_csv(CSV_PATH)
    print(f"Loaded {len(df):,} seed records from EXP191.")

    feature_cols = ["p_milk", "cash", "cow_count", "shed_wheat", "hands", "quads"]
    states = df[feature_cols].values.astype(np.float32)

    # Compute ground-truth values and advantages for N=0,1,2,3,4
    scores = df[["score_0", "score_1", "score_2", "score_3", "score_4"]].values.astype(np.float32)
    base_scores = scores[:, 4:5]
    advantages = scores - base_scores # Δ vs N=4 (N=4 adv is exactly 0)
    best_actions = scores.argmax(axis=-1).astype(np.int64)

    state_mean = states.mean(axis=0)
    state_std = states.std(axis=0) + 1e-6
    states_norm = (states - state_mean) / state_std

    # Seed-based 80/20 Train/Test split
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
    print(f"Training on device: {device} ({torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'})")

    train_dataset = TensorDataset(
        torch.tensor(states_norm[train_mask]),
        torch.tensor(advantages[train_mask]),
        torch.tensor(best_actions[train_mask]),
        torch.tensor(scores[train_mask])
    )
    test_dataset = TensorDataset(
        torch.tensor(states_norm[test_mask]),
        torch.tensor(advantages[test_mask]),
        torch.tensor(best_actions[test_mask]),
        torch.tensor(scores[test_mask])
    )

    train_loader = DataLoader(train_dataset, batch_size=64, shuffle=True)
    test_loader = DataLoader(test_dataset, batch_size=128, shuffle=False)

    model = SheepQNetwork(state_dim=len(feature_cols), num_options=5).to(device)
    optimizer = optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
    smooth_l1 = nn.SmoothL1Loss(beta=100.0)
    ce_loss = nn.CrossEntropyLoss()

    print("\n--- Training Sheep Q-Network (25 Epochs) ---")
    t0 = time.time()
    for epoch in range(25):
        model.train()
        total_loss = 0.0
        for b_st, b_adv, b_act, b_sc in train_loader:
            b_st, b_adv, b_act = b_st.to(device), b_adv.to(device), b_act.to(device)
            optimizer.zero_grad()
            adv_preds, logits = model(b_st)
            l_adv = smooth_l1(adv_preds, b_adv)
            l_ce = ce_loss(logits, b_act)
            loss = 0.001 * l_adv + l_ce
            loss.backward()
            optimizer.step()
            total_loss += loss.item() * len(b_st)

        if (epoch + 1) % 5 == 0 or epoch == 0:
            model.eval()
            all_preds = []
            all_true_best = []
            all_scores = []
            with torch.no_grad():
                for b_st, b_adv, b_act, b_sc in test_loader:
                    b_st = b_st.to(device)
                    _, logits = model(b_st)
                    preds = logits.argmax(dim=-1).cpu().numpy()
                    all_preds.extend(preds)
                    all_true_best.extend(b_act.numpy())
                    all_scores.extend(b_sc.numpy())

            preds_arr = np.array(all_preds)
            best_arr = np.array(all_true_best)
            scores_arr = np.array(all_scores)

            top1_acc = (preds_arr == best_arr).mean() * 100.0
            
            # Compute regret on test set: R(best) - R(chosen)
            chosen_rewards = scores_arr[np.arange(len(preds_arr)), preds_arr]
            max_rewards = scores_arr.max(axis=-1)
            mean_regret = (max_rewards - chosen_rewards).mean()

            # Baseline regret (always choosing N=4)
            base_rewards = scores_arr[:, 4]
            base_regret = (max_rewards - base_rewards).mean()

            print(f"Epoch {epoch+1:2d}/25 | Top-1 Accuracy: {top1_acc:5.1f}% | Model Mean Regret: ${mean_regret:5.1f} (vs Baseline Regret: ${base_regret:5.1f})")

    elapsed = time.time() - t0
    print(f"\nTraining Complete in {elapsed:.1f}s")

    # Export JSON weights for FastSim Rust engine
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
        "advantage_head_weight": model.advantage_head.weight.detach().cpu().numpy().tolist(),
        "advantage_head_bias": model.advantage_head.bias.detach().cpu().numpy().tolist(),
        "policy_logits_weight": model.policy_logits.weight.detach().cpu().numpy().tolist(),
        "policy_logits_bias": model.policy_logits.bias.detach().cpu().numpy().tolist(),
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
