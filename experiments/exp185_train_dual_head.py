"""
EXP185 — Train Dual-Head Policy & Value Network (Stall Detector + Intervention Ranker).
Consumes 276,316 counterfactual rollouts from exp184_residual_q_dataset.csv.
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

CSV_PATH = r"D:\kaggriculture\data\exp184_residual_q_dataset.csv"
MODEL_JSON = r"D:\kaggriculture\models\exp185_dual_head_weights.json"
MODEL_NPZ = r"D:\kaggriculture\models\exp185_dual_head_weights.npz"

class DualHeadInterventionNetwork(nn.Module):
    def __init__(self, state_dim=16, num_actions=14, hidden_dim=128):
        super().__init__()
        self.trunk = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ReLU(),
        )
        self.policy_head = nn.Linear(hidden_dim, num_actions)
        self.value_head = nn.Linear(hidden_dim, num_actions)

    def forward(self, state):
        feat = self.trunk(state)
        logits = self.policy_head(feat)
        values = self.value_head(feat)
        return logits, values

def train():
    print("=" * 80)
    print("EXP185 -- TRAINING DUAL-HEAD INTERVENTION & VALUE NETWORK (GPU)")
    print("=" * 80)

    if not os.path.exists(CSV_PATH):
        print(f"Dataset not found at {CSV_PATH}")
        return

    df = pd.read_csv(CSV_PATH)
    print(f"Loaded {len(df):,} counterfactual samples.")

    feature_cols = [
        "step", "day", "hour", "money", "unlocked_quads", "num_hands",
        "num_plants", "num_cows", "shed_straw", "shed_milk", "shed_wheat",
        "p_straw", "p_milk", "p_melon", "opp_money", "opp_quads"
    ]

    # Group by (seed, step) to create unified (state, best_action, value_vector) samples
    print("Aggregating multi-action vectors per state checkpoint...")
    grouped = df.groupby(["seed", "step"])

    state_list = []
    best_action_list = []
    value_vec_list = []
    seed_list = []

    for (seed, step), g in grouped:
        first_row = g.iloc[0]
        st = first_row[feature_cols].values.astype(np.float32)

        # Build 14-dim delta value vector
        v_vec = np.zeros(14, dtype=np.float32)
        for _, row in g.iterrows():
            act = int(row["action_id"])
            if act < 14:
                v_vec[act] = float(row["delta_reward"])

        # Determine best action: if max delta > $300, choose that action; else 0 (BASELINE)
        max_delta = v_vec.max()
        if max_delta >= 300.0:
            best_act = int(v_vec.argmax())
        else:
            best_act = 0

        state_list.append(st)
        best_action_list.append(best_act)
        value_vec_list.append(v_vec)
        seed_list.append(seed)

    states = np.array(state_list, dtype=np.float32)
    best_actions = np.array(best_action_list, dtype=np.int64)
    value_vecs = np.array(value_vec_list, dtype=np.float32)
    seeds = np.array(seed_list, dtype=np.int64)

    print(f"Total Unique Decision States: {len(states):,}")
    print(f"States with Verified Alpha Interventions: {(best_actions > 0).sum():,} ({(best_actions > 0).mean()*100:.1f}%)")

    state_mean = states.mean(axis=0)
    state_std = states.std(axis=0) + 1e-6
    states_norm = (states - state_mean) / state_std

    # Train / Test split by seed (80/20)
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
        torch.tensor(best_actions[train_mask]),
        torch.tensor(value_vecs[train_mask])
    )
    test_dataset = TensorDataset(
        torch.tensor(states_norm[test_mask]),
        torch.tensor(best_actions[test_mask]),
        torch.tensor(value_vecs[test_mask])
    )

    train_loader = DataLoader(train_dataset, batch_size=128, shuffle=True)
    test_loader = DataLoader(test_dataset, batch_size=256, shuffle=False)

    model = DualHeadInterventionNetwork(state_dim=len(feature_cols), num_actions=14).to(device)
    optimizer = optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
    ce_loss_fn = nn.CrossEntropyLoss()
    val_loss_fn = nn.SmoothL1Loss(beta=100.0)

    print("\n--- Training Dual-Head Intervention Network (25 Epochs) ---")
    t0 = time.time()
    for epoch in range(25):
        model.train()
        total_loss = 0.0
        for b_st, b_act, b_val in train_loader:
            b_st, b_act, b_val = b_st.to(device), b_act.to(device), b_val.to(device)
            optimizer.zero_grad()
            logits, vals = model(b_st)
            l_ce = ce_loss_fn(logits, b_act)
            l_val = val_loss_fn(vals, b_val)
            loss = l_ce + 0.0005 * l_val
            loss.backward()
            optimizer.step()
            total_loss += loss.item() * len(b_act)

        train_loss = total_loss / train_mask.sum()

        if (epoch + 1) % 5 == 0 or epoch == 0:
            model.eval()
            correct = 0
            alpha_correct = 0
            alpha_total = 0
            with torch.no_grad():
                for b_st, b_act, b_val in test_loader:
                    b_st, b_act, b_val = b_st.to(device), b_act.to(device), b_val.to(device)
                    logits, vals = model(b_st)
                    preds = logits.argmax(dim=-1)
                    correct += (preds == b_act).sum().item()

                    is_alpha = (b_act > 0)
                    alpha_total += is_alpha.sum().item()
                    alpha_correct += ((preds == b_act) & is_alpha).sum().item()

            overall_acc = (correct / test_mask.sum()) * 100.0
            alpha_recall = (alpha_correct / max(alpha_total, 1)) * 100.0
            print(f"Epoch {epoch+1:2d}/25 | Train Loss: {train_loss:7.4f} | Test Policy Acc: {overall_acc:5.1f}% | Alpha Precision: {alpha_recall:5.1f}% ({alpha_correct}/{alpha_total})")

    elapsed = time.time() - t0
    print(f"\nDual-Head Training Complete in {elapsed:.1f}s")

    # Export weights to JSON for Rust FastSim
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
        "policy_head_weight": model.policy_head.weight.detach().cpu().numpy().tolist(),
        "policy_head_bias": model.policy_head.bias.detach().cpu().numpy().tolist(),
        "value_head_weight": model.value_head.weight.detach().cpu().numpy().tolist(),
        "value_head_bias": model.value_head.bias.detach().cpu().numpy().tolist(),
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
