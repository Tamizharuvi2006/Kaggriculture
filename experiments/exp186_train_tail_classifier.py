"""
EXP186 — Train Binary Tail-Stall Classifier & Emergency Action Ranker (GPU).
Consumes binary ground-truth stall labels from exp186_tail_risk_dataset.csv.
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

CSV_PATH = r"D:\kaggriculture\data\exp186_tail_risk_dataset.csv"
MODEL_JSON = r"D:\kaggriculture\models\exp186_tail_classifier_weights.json"
MODEL_NPZ = r"D:\kaggriculture\models\exp186_tail_classifier_weights.npz"

class TailStallClassifier(nn.Module):
    def __init__(self, state_dim=16, hidden_dim=128):
        super().__init__()
        self.trunk = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 64),
            nn.LayerNorm(64),
            nn.ReLU(),
        )
        self.stall_head = nn.Linear(64, 1) # Logit for P(stall)
        self.action_head = nn.Linear(64, 3) # Expected Delta for [BUY_WHEAT_4, HIRE_1, HIRE_2]

    def forward(self, state):
        feat = self.trunk(state)
        stall_logit = self.stall_head(feat).squeeze(-1)
        action_deltas = self.action_head(feat)
        return stall_logit, action_deltas

def train():
    print("=" * 80)
    print("EXP186 -- TRAINING BINARY TAIL-STALL CLASSIFIER ON GPU")
    print("=" * 80)

    if not os.path.exists(CSV_PATH):
        print(f"Dataset not found at {CSV_PATH}")
        return

    df = pd.read_csv(CSV_PATH)
    print(f"Loaded {len(df):,} state snapshots across {df['seed'].nunique():,} seeds.")

    total_stalls = (df['is_stall'] == 1).sum()
    print(f"Ground-Truth Stall Snapshots: {total_stalls:,} ({total_stalls/len(df)*100:.2f}%)")

    feature_cols = [
        "step", "day", "hour", "money", "unlocked_quads", "num_hands",
        "num_plants", "num_cows", "shed_straw", "shed_milk", "shed_wheat",
        "p_straw", "p_milk", "p_melon", "opp_money", "opp_quads"
    ]

    states = df[feature_cols].values.astype(np.float32)
    stalls = df["is_stall"].values.astype(np.float32)

    # Compute rescue deltas relative to baseline
    delta_wheat = (df["rescue_wheat_reward"] - df["final_baseline_reward"]).values.astype(np.float32)
    delta_hire1 = (df["rescue_hire1_reward"] - df["final_baseline_reward"]).values.astype(np.float32)
    delta_hire2 = (df["rescue_hire2_reward"] - df["final_baseline_reward"]).values.astype(np.float32)
    rescue_deltas = np.stack([delta_wheat, delta_hire1, delta_hire2], axis=1)

    state_mean = states.mean(axis=0)
    state_std = states.std(axis=0) + 1e-6
    states_norm = (states - state_mean) / state_std

    # Seed-based Train/Test Split (80/20)
    seeds = df["seed"].values
    unique_seeds = np.unique(seeds)
    np.random.seed(42)
    np.random.shuffle(unique_seeds)
    split_idx = int(0.8 * len(unique_seeds))
    train_seeds = set(unique_seeds[:split_idx])

    train_mask = np.isin(seeds, list(train_seeds))
    test_mask = ~train_mask

    print(f"Train states: {train_mask.sum():,} | Test states: {test_mask.sum():,}")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Training on device: {device} ({torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'})")

    train_dataset = TensorDataset(
        torch.tensor(states_norm[train_mask]),
        torch.tensor(stalls[train_mask]),
        torch.tensor(rescue_deltas[train_mask])
    )
    test_dataset = TensorDataset(
        torch.tensor(states_norm[test_mask]),
        torch.tensor(stalls[test_mask]),
        torch.tensor(rescue_deltas[test_mask])
    )

    train_loader = DataLoader(train_dataset, batch_size=128, shuffle=True)
    test_loader = DataLoader(test_dataset, batch_size=256, shuffle=False)

    model = TailStallClassifier(state_dim=len(feature_cols)).to(device)

    # Class-weighted BCE loss (pos_weight ~ 6.0 to account for 15% stall frequency)
    pos_weight = torch.tensor([(1.0 - stalls.mean()) / (stalls.mean() + 1e-5)]).to(device)
    bce_loss_fn = nn.BCEWithLogitsLoss(pos_weight=pos_weight)
    val_loss_fn = nn.SmoothL1Loss(beta=100.0)

    optimizer = optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)

    print("\n--- Training Binary Stall Classifier (20 Epochs) ---")
    t0 = time.time()
    for epoch in range(20):
        model.train()
        total_loss = 0.0
        for b_st, b_stall, b_act in train_loader:
            b_st, b_stall, b_act = b_st.to(device), b_stall.to(device), b_act.to(device)
            optimizer.zero_grad()
            stall_logits, act_preds = model(b_st)
            l_bce = bce_loss_fn(stall_logits, b_stall)
            l_act = val_loss_fn(act_preds, b_act)
            loss = l_bce + 0.0002 * l_act
            loss.backward()
            optimizer.step()
            total_loss += loss.item() * len(b_stall)

        if (epoch + 1) % 5 == 0 or epoch == 0:
            model.eval()
            all_preds = []
            all_targets = []
            with torch.no_grad():
                for b_st, b_stall, b_act in test_loader:
                    b_st = b_st.to(device)
                    logits, _ = model(b_st)
                    probs = torch.sigmoid(logits).cpu().numpy()
                    all_preds.extend(probs)
                    all_targets.extend(b_stall.numpy())

            preds_arr = np.array(all_preds)
            targets_arr = np.array(all_targets)

            # Evaluate at threshold 0.65
            pred_stalls = (preds_arr >= 0.65).astype(int)
            tp = ((pred_stalls == 1) & (targets_arr == 1)).sum()
            fp = ((pred_stalls == 1) & (targets_arr == 0)).sum()
            fn = ((pred_stalls == 0) & (targets_arr == 1)).sum()
            precision = (tp / max(tp + fp, 1)) * 100.0
            recall = (tp / max(tp + fn, 1)) * 100.0

            print(f"Epoch {epoch+1:2d}/20 | Test Stall Recall: {recall:5.1f}% | Precision: {precision:5.1f}% (TP={tp}, FP={fp}, FN={fn})")

    elapsed = time.time() - t0
    print(f"\nClassifier Training Complete in {elapsed:.1f}s")

    # Export native JSON weights for Rust FastSim
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
        "stall_head_weight": model.stall_head.weight.detach().cpu().numpy().tolist(),
        "stall_head_bias": model.stall_head.bias.detach().cpu().numpy().tolist(),
        "action_head_weight": model.action_head.weight.detach().cpu().numpy().tolist(),
        "action_head_bias": model.action_head.bias.detach().cpu().numpy().tolist(),
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
