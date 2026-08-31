"""
EXP193 — Train Multi-Action Macro Q-Network on GPU from exp193_macro_dataset.csv.
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

CSV_PATH = r"D:\kaggriculture\data\exp193_macro_dataset.csv"
MODEL_JSON = r"D:\kaggriculture\models\exp193_macro_q_weights.json"
MODEL_NPZ = r"D:\kaggriculture\models\exp193_macro_q_weights.npz"

class MacroQNetwork(nn.Module):
    def __init__(self, state_dim=10, num_actions=6, hidden_dim=128):
        super().__init__()
        self.trunk = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 64),
            nn.LayerNorm(64),
            nn.ReLU(),
        )
        self.advantage_head = nn.Linear(64, num_actions) # ΔQ(s, a) relative to a0
        self.policy_logits = nn.Linear(64, num_actions)  # P(best_a | s)

    def forward(self, state):
        feat = self.trunk(state)
        adv = self.advantage_head(feat)
        logits = self.policy_logits(feat)
        return adv, logits

def train():
    print("=" * 80)
    print("EXP193 -- TRAINING GENERALIZED MACRO Q-NETWORK ON GPU")
    print("=" * 80)

    if not os.path.exists(CSV_PATH):
        print(f"Dataset not found at {CSV_PATH}")
        return

    df = pd.read_csv(CSV_PATH)
    print(f"Loaded {len(df):,} records from EXP193 dataset.")

    feature_cols = ["p_milk", "cash", "cows", "sheep", "shed_wheat", "hands", "quads", "day", "unwatered", "mature"]
    states = df[feature_cols].values.astype(np.float32)

    score_cols = [f"score_a{i}" for i in range(6)]
    scores = df[score_cols].values.astype(np.float32)
    base_scores = scores[:, 0:1] # a0 baseline score
    advantages = scores - base_scores
    best_actions = df["best_a"].values.astype(np.int64)

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

    model = MacroQNetwork(state_dim=len(feature_cols), num_actions=6).to(device)
    optimizer = optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
    smooth_l1 = nn.SmoothL1Loss(beta=500.0)
    ce_loss = nn.CrossEntropyLoss()

    print("\n--- Training Macro Q-Network (30 Epochs) ---")
    t0 = time.time()
    for epoch in range(30):
        model.train()
        total_loss = 0.0
        for b_st, b_adv, b_act, b_sc in train_loader:
            b_st, b_adv, b_act = b_st.to(device), b_adv.to(device), b_act.to(device)
            optimizer.zero_grad()
            adv_preds, logits = model(b_st)
            l_adv = smooth_l1(adv_preds, b_adv)
            l_ce = ce_loss(logits, b_act)
            loss = 0.0005 * l_adv + l_ce
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
            
            chosen_rewards = scores_arr[np.arange(len(preds_arr)), preds_arr]
            max_rewards = scores_arr.max(axis=-1)
            mean_regret = (max_rewards - chosen_rewards).mean()
            base_rewards = scores_arr[:, 0]
            base_regret = (max_rewards - base_rewards).mean()

            print(f"Epoch {epoch+1:2d}/30 | Top-1 Accuracy: {top1_acc:5.1f}% | Model Mean Regret: ${mean_regret:6.1f} (vs Baseline Regret: ${base_regret:6.1f})")

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
