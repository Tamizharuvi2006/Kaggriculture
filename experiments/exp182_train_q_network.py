"""
EXP182 — Train Action-Value Q(s, a) and State-Value V(s) Networks.
Consumes counterfactual rollouts from exp182_q_dataset.csv.
"""

import os
import time
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import TensorDataset, DataLoader

CSV_PATH = r"D:\kaggriculture\data\exp182_q_dataset.csv"
MODEL_OUT = r"D:\kaggriculture\models\exp182_q_weights.npz"

class QNetwork(nn.Module):
    def __init__(self, state_dim=10, num_actions=12, hidden_dim=128):
        super().__init__()
        self.action_embed = nn.Embedding(num_actions, 16)
        self.net = nn.Sequential(
            nn.Linear(state_dim + 16, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 1),
        )

    def forward(self, state, action):
        a_emb = self.action_embed(action)
        x = torch.cat([state, a_emb], dim=-1)
        return self.net(x).squeeze(-1)

class ValueNetwork(nn.Module):
    def __init__(self, state_dim=10, hidden_dim=128):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 1),
        )

    def forward(self, state):
        return self.net(state).squeeze(-1)

def train_models():
    print("=" * 80)
    print("EXP182 — TRAINING ACTION-VALUE Q(s, a) & STATE-VALUE V(s) NETWORKS")
    print("=" * 80)

    if not os.path.exists(CSV_PATH):
        print(f"Dataset not found at {CSV_PATH}")
        return

    df = pd.read_csv(CSV_PATH)
    print(f"Loaded {len(df):,} counterfactual samples.")

    # Features: step, day, money, melon_seeds, wheat_seeds, straw_seeds, unlocked_quads, num_plants, num_cows, num_hands
    feature_cols = [
        "step", "day", "money", "melon_seeds", "wheat_seeds", "straw_seeds",
        "unlocked_quads", "num_plants", "num_cows", "num_hands"
    ]

    states = df[feature_cols].values.astype(np.float32)
    actions = df["action_id"].values.astype(np.int64)
    returns = df["terminal_return"].values.astype(np.float32)
    deltas = df["delta_vs_baseline"].values.astype(np.float32)

    # Normalize state features
    state_mean = states.mean(axis=0)
    state_std = states.std(axis=0) + 1e-6
    states_norm = (states - state_mean) / state_std

    # Train / Test split (80/20 by seed)
    unique_seeds = df["seed"].unique()
    np.random.seed(42)
    np.random.shuffle(unique_seeds)
    split_idx = int(0.8 * len(unique_seeds))
    train_seeds = set(unique_seeds[:split_idx])

    train_mask = df["seed"].isin(train_seeds).values
    test_mask = ~train_mask

    print(f"Train samples: {train_mask.sum():,} | Test samples: {test_mask.sum():,}")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Training on device: {device}")

    # Train Q-Network
    train_dataset = TensorDataset(
        torch.tensor(states_norm[train_mask]),
        torch.tensor(actions[train_mask]),
        torch.tensor(returns[train_mask])
    )
    test_dataset = TensorDataset(
        torch.tensor(states_norm[test_mask]),
        torch.tensor(actions[test_mask]),
        torch.tensor(returns[test_mask])
    )

    train_loader = DataLoader(train_dataset, batch_size=256, shuffle=True)
    test_loader = DataLoader(test_dataset, batch_size=512, shuffle=False)

    q_model = QNetwork().to(device)
    optimizer = optim.AdamW(q_model.parameters(), lr=1e-3, weight_decay=1e-4)
    criterion = nn.SmoothL1Loss()

    print("\n--- Training Q-Network (15 Epochs) ---")
    t0 = time.time()
    for epoch in range(15):
        q_model.train()
        total_loss = 0.0
        for b_states, b_actions, b_returns in train_loader:
            b_states, b_actions, b_returns = b_states.to(device), b_actions.to(device), b_returns.to(device)
            optimizer.zero_grad()
            pred_q = q_model(b_states, b_actions)
            loss = criterion(pred_q, b_returns)
            loss.backward()
            optimizer.step()
            total_loss += loss.item() * len(b_returns)

        train_loss = total_loss / train_mask.sum()

        if (epoch + 1) % 5 == 0 or epoch == 0:
            q_model.eval()
            test_loss = 0.0
            test_mae = 0.0
            with torch.no_grad():
                for b_states, b_actions, b_returns in test_loader:
                    b_states, b_actions, b_returns = b_states.to(device), b_actions.to(device), b_returns.to(device)
                    pred_q = q_model(b_states, b_actions)
                    loss = criterion(pred_q, b_returns)
                    test_loss += loss.item() * len(b_returns)
                    test_mae += torch.abs(pred_q - b_returns).sum().item()

            print(f"Epoch {epoch+1:2d}/15 | Train Loss: {train_loss:8.2f} | Test Loss: {test_loss/test_mask.sum():8.2f} | Test MAE: ${test_mae/test_mask.sum():7.1f}")

    elapsed = time.time() - t0
    print(f"Q-Network Training complete in {elapsed:.1f}s")

    # Evaluate Q-ranking accuracy (how often Q correctly predicts the highest-return counterfactual action)
    q_model.eval()
    with torch.no_grad():
        test_states_t = torch.tensor(states_norm[test_mask]).to(device)
        test_actions_t = torch.tensor(actions[test_mask]).to(device)
        pred_q_all = q_model(test_states_t, test_actions_t).cpu().numpy()

    # Save weights and parameters to JSON for native Rust FastSim inference
    import json
    weights_dict = {
        "feature_cols": feature_cols,
        "state_mean": state_mean.tolist(),
        "state_std": state_std.tolist(),
        "action_embed": q_model.action_embed.weight.detach().cpu().numpy().tolist(),
        "fc1_weight": q_model.net[0].weight.detach().cpu().numpy().tolist(),
        "fc1_bias": q_model.net[0].bias.detach().cpu().numpy().tolist(),
        "ln1_weight": q_model.net[1].weight.detach().cpu().numpy().tolist(),
        "ln1_bias": q_model.net[1].bias.detach().cpu().numpy().tolist(),
        "fc2_weight": q_model.net[3].weight.detach().cpu().numpy().tolist(),
        "fc2_bias": q_model.net[3].bias.detach().cpu().numpy().tolist(),
        "ln2_weight": q_model.net[4].weight.detach().cpu().numpy().tolist(),
        "ln2_bias": q_model.net[4].bias.detach().cpu().numpy().tolist(),
        "fc3_weight": q_model.net[6].weight.detach().cpu().numpy().tolist(),
        "fc3_bias": q_model.net[6].bias.detach().cpu().numpy().tolist(),
    }
    
    JSON_OUT = r"D:\kaggriculture\models\exp182_q_weights.json"
    with open(JSON_OUT, "w") as f:
        json.dump(weights_dict, f)
    print(f"Exported native Rust weights to {JSON_OUT}")

    np.savez_compressed(
        MODEL_OUT,
        state_mean=state_mean,
        state_std=state_std,
        feature_cols=feature_cols,
        **{k: v.detach().cpu().numpy() for k, v in q_model.state_dict().items()}
    )
    print(f"Saved PyTorch weights and normalization statistics to {MODEL_OUT}")

if __name__ == "__main__":
    train_models()

