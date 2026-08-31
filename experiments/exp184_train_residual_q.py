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
MODEL_JSON = r"D:\kaggriculture\models\exp184_residual_q_weights.json"
MODEL_NPZ = r"D:\kaggriculture\models\exp184_residual_q_weights.npz"

class ResidualQNetwork(nn.Module):
    def __init__(self, state_dim=16, num_actions=14, hidden_dim=128):
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

def train():
    print("=" * 80)
    print("EXP184 -- TRAINING RESIDUAL Q-NETWORK DELTA-Q(s, a) ON ADAPTIVETERMINAL")
    print("=" * 80)


    if not os.path.exists(CSV_PATH):
        print(f"Dataset not found at {CSV_PATH}")
        return

    df = pd.read_csv(CSV_PATH)
    print(f"Loaded {len(df):,} residual counterfactual samples.")

    feature_cols = [
        "step", "day", "hour", "money", "unlocked_quads", "num_hands",
        "num_plants", "num_cows", "shed_straw", "shed_milk", "shed_wheat",
        "p_straw", "p_milk", "p_melon", "opp_money", "opp_quads"
    ]

    states = df[feature_cols].values.astype(np.float32)
    actions = df["action_id"].values.astype(np.int64)
    deltas = df["delta_reward"].values.astype(np.float32)

    state_mean = states.mean(axis=0)
    state_std = states.std(axis=0) + 1e-6
    states_norm = (states - state_mean) / state_std

    # Train / Test split by seed (80/20)
    unique_seeds = df["seed"].unique()
    np.random.seed(42)
    np.random.shuffle(unique_seeds)
    split_idx = int(0.8 * len(unique_seeds))
    train_seeds = set(unique_seeds[:split_idx])

    train_mask = df["seed"].isin(train_seeds).values
    test_mask = ~train_mask

    print(f"Train samples: {train_mask.sum():,} | Test samples: {test_mask.sum():,}")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Training on device: {device} ({torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'})")

    train_dataset = TensorDataset(
        torch.tensor(states_norm[train_mask]),
        torch.tensor(actions[train_mask]),
        torch.tensor(deltas[train_mask])
    )
    test_dataset = TensorDataset(
        torch.tensor(states_norm[test_mask]),
        torch.tensor(actions[test_mask]),
        torch.tensor(deltas[test_mask])
    )

    train_loader = DataLoader(train_dataset, batch_size=256, shuffle=True)
    test_loader = DataLoader(test_dataset, batch_size=512, shuffle=False)

    model = ResidualQNetwork(state_dim=len(feature_cols), num_actions=14).to(device)
    optimizer = optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
    criterion = nn.SmoothL1Loss(beta=100.0)

    print("\n--- Training Residual Q-Network (20 Epochs) ---")
    t0 = time.time()
    for epoch in range(20):
        model.train()
        total_loss = 0.0
        for b_states, b_actions, b_deltas in train_loader:
            b_states, b_actions, b_deltas = b_states.to(device), b_actions.to(device), b_deltas.to(device)
            optimizer.zero_grad()
            pred = model(b_states, b_actions)
            loss = criterion(pred, b_deltas)
            loss.backward()
            optimizer.step()
            total_loss += loss.item() * len(b_deltas)

        train_loss = total_loss / train_mask.sum()

        if (epoch + 1) % 5 == 0 or epoch == 0:
            model.eval()
            test_loss = 0.0
            test_mae = 0.0
            with torch.no_grad():
                for b_states, b_actions, b_deltas in test_loader:
                    b_states, b_actions, b_deltas = b_states.to(device), b_actions.to(device), b_deltas.to(device)
                    pred = model(b_states, b_actions)
                    loss = criterion(pred, b_deltas)
                    test_loss += loss.item() * len(b_deltas)
                    test_mae += torch.abs(pred - b_deltas).sum().item()

            print(f"Epoch {epoch+1:2d}/20 | Train Loss: {train_loss:8.2f} | Test Loss: {test_loss/test_mask.sum():8.2f} | Test MAE: ${test_mae/test_mask.sum():7.1f}")

    elapsed = time.time() - t0
    print(f"\nTraining Complete in {elapsed:.1f}s")

    # Export weights to JSON for Rust FastSim
    os.makedirs(os.path.dirname(MODEL_JSON), exist_ok=True)
    weights_dict = {
        "feature_cols": feature_cols,
        "state_mean": state_mean.tolist(),
        "state_std": state_std.tolist(),
        "action_embed": model.action_embed.weight.detach().cpu().numpy().tolist(),
        "fc1_weight": model.net[0].weight.detach().cpu().numpy().tolist(),
        "fc1_bias": model.net[0].bias.detach().cpu().numpy().tolist(),
        "ln1_weight": model.net[1].weight.detach().cpu().numpy().tolist(),
        "ln1_bias": model.net[1].bias.detach().cpu().numpy().tolist(),
        "fc2_weight": model.net[3].weight.detach().cpu().numpy().tolist(),
        "fc2_bias": model.net[3].bias.detach().cpu().numpy().tolist(),
        "ln2_weight": model.net[4].weight.detach().cpu().numpy().tolist(),
        "ln2_bias": model.net[4].bias.detach().cpu().numpy().tolist(),
        "fc3_weight": model.net[6].weight.detach().cpu().numpy().tolist(),
        "fc3_bias": model.net[6].bias.detach().cpu().numpy().tolist(),
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
