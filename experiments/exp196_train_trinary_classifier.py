"""
EXP196 — Train 3-Class Macro Intervention Classifier (BAD / NEUTRAL / GOOD) on GPU.
Objective: Maximize Precision of GOOD interventions (>+$500) to eliminate false alarms.
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

CSV_PATH = r"D:\kaggriculture\data\exp193_macro_dataset.csv"
MODEL_JSON = r"D:\kaggriculture\models\exp196_trinary_weights.json"
MODEL_NPZ = r"D:\kaggriculture\models\exp196_trinary_weights.npz"

class TrinaryInterventionNetwork(nn.Module):
    def __init__(self, state_dim=10, num_actions=5, hidden_dim=128):
        super().__init__()
        self.trunk = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 64),
            nn.LayerNorm(64),
            nn.ReLU(),
        )
        # 5 actions (a1..a5), each with 3 logits: [BAD, NEUTRAL, GOOD]
        self.action_heads = nn.Linear(64, num_actions * 3)

    def forward(self, state):
        feat = self.trunk(state)
        logits = self.action_heads(feat) # [B, 15]
        return logits.view(-1, 5, 3) # [B, num_actions, 3]

def train():
    print("=" * 80)
    print("EXP196 -- TRAINING 3-CLASS INTERVENTION CLASSIFIER ON GPU")
    print("=" * 80)

    if not os.path.exists(CSV_PATH):
        print(f"Dataset not found at {CSV_PATH}")
        return

    df = pd.read_csv(CSV_PATH)
    print(f"Loaded {len(df):,} records from EXP193 dataset.")

    feature_cols = ["p_milk", "cash", "cows", "sheep", "shed_wheat", "hands", "quads", "day", "unwatered", "mature"]
    states = df[feature_cols].values.astype(np.float32)

    # Compute deltas for actions a1..a5 vs baseline a0
    base_scores = df["score_a0"].values.astype(np.float32)
    deltas = np.zeros((len(df), 5), dtype=np.float32)
    for i in range(1, 6):
        deltas[:, i - 1] = df[f"score_a{i}"].values.astype(np.float32) - base_scores

    # 3-Class Target Labeling:
    # 0: BAD (Δ < -$250)
    # 1: NEUTRAL (-$250 <= Δ <= +$500)
    # 2: GOOD (Δ > +$500)
    labels = np.ones((len(df), 5), dtype=np.int64) # Default NEUTRAL (1)
    labels[deltas < -250.0] = 0 # BAD
    labels[deltas > 500.0] = 2  # GOOD

    good_counts = (labels == 2).sum(axis=0)
    bad_counts = (labels == 0).sum(axis=0)
    neutral_counts = (labels == 1).sum(axis=0)
    print(f"Distribution per action (a1..a5):")
    for i in range(5):
        print(f"  Action a{i+1}: BAD={bad_counts[i]:4d} | NEUTRAL={neutral_counts[i]:4d} | GOOD={good_counts[i]:4d}")

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

    print(f"\nTrain samples: {train_mask.sum():,} | Test samples: {test_mask.sum():,}")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Training on: {device} ({torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'})")

    train_dataset = TensorDataset(
        torch.tensor(states_norm[train_mask]),
        torch.tensor(labels[train_mask]),
        torch.tensor(deltas[train_mask])
    )
    test_dataset = TensorDataset(
        torch.tensor(states_norm[test_mask]),
        torch.tensor(labels[test_mask]),
        torch.tensor(deltas[test_mask])
    )

    train_loader = DataLoader(train_dataset, batch_size=64, shuffle=True)
    test_loader = DataLoader(test_dataset, batch_size=128, shuffle=False)

    model = TrinaryInterventionNetwork(state_dim=len(feature_cols), num_actions=5).to(device)
    optimizer = optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)

    # Class weights to balance precision and recall: [BAD=1.0, NEUTRAL=1.0, GOOD=2.0]
    class_weights = torch.tensor([1.0, 1.0, 2.0], device=device)
    ce_loss = nn.CrossEntropyLoss(weight=class_weights)

    print("\n--- Training Trinary Classifier (30 Epochs) ---")
    t0 = time.time()
    for epoch in range(30):
        model.train()
        total_loss = 0.0
        for b_st, b_lbl, b_del in train_loader:
            b_st, b_lbl = b_st.to(device), b_lbl.to(device)
            optimizer.zero_grad()
            logits = model(b_st) # [B, 5, 3]
            
            # Loss across all 5 actions
            loss = ce_loss(logits.view(-1, 3), b_lbl.view(-1))
            loss.backward()
            optimizer.step()
            total_loss += loss.item() * len(b_st)

        if (epoch + 1) % 5 == 0 or epoch == 0:
            model.eval()
            all_preds = []
            all_true = []
            all_deltas = []
            with torch.no_grad():
                for b_st, b_lbl, b_del in test_loader:
                    b_st = b_st.to(device)
                    logits = model(b_st) # [B, 5, 3]
                    probs = F.softmax(logits, dim=-1)
                    good_probs = probs[:, :, 2] # Probability of GOOD class
                    preds = (good_probs > 0.50).long().cpu().numpy()
                    all_preds.extend(preds)
                    all_true.extend((b_lbl.numpy() == 2).astype(np.int64))
                    all_deltas.extend(b_del.numpy())

            preds_arr = np.array(all_preds) # [N, 5]
            true_arr = np.array(all_true)   # [N, 5]
            deltas_arr = np.array(all_deltas)

            # Measure Precision & Recall across all predicted GOOD actions
            pred_positives = (preds_arr == 1)
            true_positives = (true_arr == 1)
            
            total_interventions = pred_positives.sum()
            correct_interventions = (pred_positives & true_positives).sum()
            good_precision = (correct_interventions / total_interventions * 100.0) if total_interventions > 0 else 100.0
            good_recall = (correct_interventions / true_positives.sum() * 100.0) if true_positives.sum() > 0 else 0.0

            # Average gain when model proposes intervention
            avg_gain = deltas_arr[pred_positives].mean() if total_interventions > 0 else 0.0

            print(f"Epoch {epoch+1:2d}/30 | GOOD Precision: {good_precision:5.1f}% | Recall: {good_recall:5.1f}% | Interventions: {total_interventions:4d} | Avg Delta when intervening: +${avg_gain:7.1f}")

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
        "action_heads_weight": model.action_heads.weight.detach().cpu().numpy().tolist(),
        "action_heads_bias": model.action_heads.bias.detach().cpu().numpy().tolist(),
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
