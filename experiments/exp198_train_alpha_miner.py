"""
EXP198 — Train Two-Headed Alpha Opportunity Miner on GPU from exp198_alpha_dataset.csv.
Head 1: Alpha Gate P(Alpha Opportunity >= $500 | s)
Head 2: Best Intervention Logits P(a* | s, Alpha)
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

CSV_PATH = r"D:\kaggriculture\data\exp198_alpha_dataset.csv"
MODEL_JSON = r"D:\kaggriculture\models\exp198_alpha_miner_weights.json"
MODEL_NPZ = r"D:\kaggriculture\models\exp198_alpha_miner_weights.npz"

class AlphaMinerNetwork(nn.Module):
    def __init__(self, state_dim=16, num_actions=5, hidden_dim=128):
        super().__init__()
        self.trunk = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 64),
            nn.LayerNorm(64),
            nn.ReLU(),
        )
        self.alpha_gate = nn.Linear(64, 1)        # Logit of has_alpha (>= $500)
        self.action_head = nn.Linear(64, num_actions) # Logits over candidate actions (a1..a5)

    def forward(self, state):
        feat = self.trunk(state)
        gate_logit = self.alpha_gate(feat).squeeze(-1)
        action_logits = self.action_head(feat)
        return gate_logit, action_logits

def train():
    print("=" * 80)
    print("EXP198 -- TRAINING TWO-HEADED ALPHA OPPORTUNITY MINER ON GPU")
    print("=" * 80)

    if not os.path.exists(CSV_PATH):
        print(f"Dataset not found at {CSV_PATH}")
        return

    df = pd.read_csv(CSV_PATH)
    print(f"Loaded {len(df):,} records from EXP198 dataset.")

    feature_cols = [
        "p_milk", "cash", "cows", "sheep", "shed_wheat", "hands", "quads", "day", "unwatered", "mature",
        "opp_cash", "opp_cows", "opp_sheep", "opp_quads", "opp_workers", "opp_straws"
    ]
    states = df[feature_cols].values.astype(np.float32)

    has_alpha = (df["gain_vs_a0"].values >= 500.0).astype(np.float32)
    # Action labels (0..4 for a1..a5)
    best_actions = np.clip(df["best_a"].values - 1, 0, 4).astype(np.int64)
    max_gains = df["gain_vs_a0"].values.astype(np.float32)

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
    print(f"Alpha rate: Train={has_alpha[train_mask].mean()*100:.1f}% | Test={has_alpha[test_mask].mean()*100:.1f}%")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Training on: {device} ({torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'})")

    train_dataset = TensorDataset(
        torch.tensor(states_norm[train_mask]),
        torch.tensor(has_alpha[train_mask]),
        torch.tensor(best_actions[train_mask]),
        torch.tensor(max_gains[train_mask])
    )
    test_dataset = TensorDataset(
        torch.tensor(states_norm[test_mask]),
        torch.tensor(has_alpha[test_mask]),
        torch.tensor(best_actions[test_mask]),
        torch.tensor(max_gains[test_mask])
    )

    train_loader = DataLoader(train_dataset, batch_size=64, shuffle=True)
    test_loader = DataLoader(test_dataset, batch_size=128, shuffle=False)

    model = AlphaMinerNetwork(state_dim=len(feature_cols), num_actions=5).to(device)
    optimizer = optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)

    # Pos weight for gate BCE: balance alpha detection
    pos_weight = torch.tensor([(1.0 - has_alpha.mean()) / (has_alpha.mean() + 1e-5)], device=device)
    bce_loss = nn.BCEWithLogitsLoss(pos_weight=pos_weight)
    ce_loss = nn.CrossEntropyLoss()

    print("\n--- Training Alpha Miner Network (30 Epochs) ---")
    t0 = time.time()
    for epoch in range(30):
        model.train()
        total_loss = 0.0
        for b_st, b_gate, b_act, b_gain in train_loader:
            b_st, b_gate, b_act, b_gain = b_st.to(device), b_gate.to(device), b_act.to(device), b_gain.to(device)
            optimizer.zero_grad()
            gate_logits, act_logits = model(b_st)
            
            l_gate = bce_loss(gate_logits, b_gate)
            
            # Action loss masked to positive alpha samples only
            alpha_mask = (b_gate > 0.5)
            if alpha_mask.sum() > 0:
                l_act = ce_loss(act_logits[alpha_mask], b_act[alpha_mask])
            else:
                l_act = torch.tensor(0.0, device=device)
                
            loss = l_gate + l_act
            loss.backward()
            optimizer.step()
            total_loss += loss.item() * len(b_st)

        if (epoch + 1) % 5 == 0 or epoch == 0:
            model.eval()
            all_gate_probs = []
            all_true_gates = []
            all_act_preds = []
            all_true_acts = []
            all_gains = []
            with torch.no_grad():
                for b_st, b_gate, b_act, b_gain in test_loader:
                    b_st = b_st.to(device)
                    gate_logits, act_logits = model(b_st)
                    gate_probs = torch.sigmoid(gate_logits).cpu().numpy()
                    act_preds = act_logits.argmax(dim=-1).cpu().numpy()
                    
                    all_gate_probs.extend(gate_probs)
                    all_true_gates.extend(b_gate.numpy())
                    all_act_preds.extend(act_preds)
                    all_true_acts.extend(b_act.numpy())
                    all_gains.extend(b_gain.numpy())

            gate_probs_arr = np.array(all_gate_probs)
            true_gates_arr = np.array(all_true_gates)
            act_preds_arr = np.array(all_act_preds)
            true_acts_arr = np.array(all_true_acts)
            gains_arr = np.array(all_gains)

            # High-confidence threshold (0.65)
            fired_mask = (gate_probs_arr >= 0.65)
            true_alpha_mask = (true_gates_arr > 0.5)

            total_fired = fired_mask.sum()
            correct_fired = (fired_mask & true_alpha_mask).sum()
            
            gate_prec = (correct_fired / total_fired * 100.0) if total_fired > 0 else 100.0
            gate_rec = (correct_fired / true_alpha_mask.sum() * 100.0) if true_alpha_mask.sum() > 0 else 0.0
            
            act_acc = ((act_preds_arr[fired_mask] == true_acts_arr[fired_mask]).mean() * 100.0) if total_fired > 0 else 0.0
            avg_val = gains_arr[fired_mask].mean() if total_fired > 0 else 0.0

            print(f"Epoch {epoch+1:2d}/30 | Gate Prec (τ=0.65): {gate_prec:5.1f}% | Gate Rec: {gate_rec:5.1f}% | Fired: {total_fired:4d} | Action Acc: {act_acc:5.1f}% | Avg Alpha: +${avg_val:7.1f}")

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
        "alpha_gate_weight": model.alpha_gate.weight.detach().cpu().numpy().tolist(),
        "alpha_gate_bias": model.alpha_gate.bias.detach().cpu().numpy().tolist(),
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
