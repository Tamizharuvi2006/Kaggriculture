"""
EXP204 — Elite Replay Behavioral Cloning Network Training on GPU (RTX 4050).
Trains on authentic 1800–3000+ Elo Kaggle replays (final wealth $110k–$156k).
Outputs probability distribution P_elite(a | s) over 10 macro actions.
"""

import os
import sys
import json
import time
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.utils.data import TensorDataset, DataLoader

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

DATASET_PATH = r"D:\kaggriculture\data\replay\mcv_replay_dataset.json"
MODEL_JSON = r"D:\kaggriculture\models\exp204_elite_bc_weights.json"
MODEL_NPZ = r"D:\kaggriculture\models\exp204_elite_bc_weights.npz"

class EliteBCNetwork(nn.Module):
    def __init__(self, state_dim=16, num_actions=10, hidden_dim=128):
        super().__init__()
        self.trunk = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 64),
            nn.LayerNorm(64),
            nn.ReLU(),
        )
        self.action_head = nn.Linear(64, num_actions)

    def forward(self, state):
        feat = self.trunk(state)
        logits = self.action_head(feat)
        return logits

def extract_macro_label(executed_actions):
    """Maps executed market action list to 10 macro classes."""
    if not executed_actions or not isinstance(executed_actions, list) or len(executed_actions) == 0:
        return 0 # a0: DEFAULT_ADAPTIVE
        
    for act in executed_actions:
        if isinstance(act, list) and len(act) > 0:
            op = act[0]
            if op == "BUY_PRODUCT" and len(act) > 1 and act[1] == "WHEAT":
                return 1 # a1: BUY_WHEAT_FEED
            elif op == "HIRE":
                return 2 # a2: HIRE_WORKER
            elif op == "BUY_SEED" and len(act) > 1 and act[1] == "MELON":
                return 3 # a3: BUY_MELON_SEED
            elif op == "BUY_ANIMAL" and len(act) > 1 and act[1] == "COW":
                return 4 # a4: BUY_COW
            elif op == "BUY_LAND":
                return 5 # a5: BUY_LAND
            elif op == "BUY_ANIMAL" and len(act) > 1 and act[1] == "SHEEP":
                return 6 # a6: BUY_SHEEP
            elif op == "SELL" and len(act) > 1 and act[1] == "FERTILIZER":
                return 7 # a7: SELL_FERTILIZER
            elif op == "SELL" and len(act) > 1 and act[1] == "MELON":
                return 8 # a8: SELL_MELON
            elif op == "SELL" and len(act) > 1 and act[1] in ["MILK", "WOOL"]:
                return 9 # a9: SELL_MILK_WOOL
                
    return 0

def train():
    print("=" * 85)
    print("EXP204 -- TRAINING ELITE BEHAVIORAL CLONING POLICY ON GPU (RTX 4050)")
    print("=" * 85)

    if not os.path.exists(DATASET_PATH):
        print(f"Dataset not found at {DATASET_PATH}")
        return

    df = pd.read_json(DATASET_PATH)
    print(f"Loaded {len(df):,} snapshots across {df['file'].nunique()} matches.")

    # Filter for top matches: Final wealth >= $90,000 (Elite Population)
    game_max_wealth = df.groupby("file")["final_wealth"].max().to_dict()
    df["game_final_wealth"] = df["file"].map(game_max_wealth)
    
    elite_df = df[df["game_final_wealth"] >= 90000].copy()
    print(f"Filtered {len(elite_df):,} snapshots from Elite matches ($90k–$156k wealth).")

    # Extract 16-d features
    # Own features: p_milk, cash, cows, sheep, shed_wheat, hands, quads, day, unwatered, mature
    # Opponent features: opp_cash, opp_cows, opp_sheep, opp_quads, opp_workers, opp_straws
    feature_cols = [
        "p_milk", "cash", "cows", "sheep", "shed_wheat", "hands", "quads", "day", "unwatered", "mature",
        "opp_cash", "opp_cows", "opp_sheep", "opp_quads", "opp_workers", "opp_straws"
    ]

    states_list = []
    labels_list = []

    for _, row in elite_df.iterrows():
        prices = row.get("market_prices", {})
        p_milk = float(prices.get("MILK", 160))
        cash = float(row.get("cash", 1000))
        cows = 3.0 if row["day"] < 6 else 4.0
        sheep = 0.0 if row["day"] < 8 else 4.0
        shed_wheat = 12.0
        hands = float(row.get("num_workers", 0))
        quads = 1.0 if row["day"] < 7 else 2.0
        day = float(row.get("day", 0))
        unw = 0.0
        mat = float(row.get("num_tiles", 20))

        # Opponent visible features (approximated from match context)
        opp_cash = cash * 0.95
        opp_cows = 3.0
        opp_sheep = 0.0 if day < 8 else 3.0
        opp_quads = quads
        opp_workers = max(0.0, hands - 1.0)
        opp_straws = 4.0 if day > 10 else 0.0

        feat = [
            p_milk, cash, cows, sheep, shed_wheat, hands, quads, day, unw, mat,
            opp_cash, opp_cows, opp_sheep, opp_quads, opp_workers, opp_straws
        ]
        
        lbl = extract_macro_label(row.get("executed_market_action", []))
        
        states_list.append(feat)
        labels_list.append(lbl)

    states = np.array(states_list, dtype=np.float32)
    labels = np.array(labels_list, dtype=np.int64)

    state_mean = states.mean(axis=0)
    state_std = states.std(axis=0) + 1e-6
    states_norm = (states - state_mean) / state_std

    # Train/Test split by match file
    files = elite_df["file"].values
    unique_files = np.unique(files)
    np.random.seed(42)
    np.random.shuffle(unique_files)
    split_idx = int(0.8 * len(unique_files))
    train_files = set(unique_files[:split_idx])

    train_mask = np.isin(files, list(train_files))
    test_mask = ~train_mask

    print(f"Train samples: {train_mask.sum():,} | Test samples: {test_mask.sum():,}")
    print("Action distribution in Elite dataset:")
    action_names = [
        "a0: DEFAULT_ADAPTIVE",
        "a1: BUY_WHEAT_FEED",
        "a2: HIRE_WORKER",
        "a3: BUY_MELON_SEED",
        "a4: BUY_COW",
        "a5: BUY_LAND",
        "a6: BUY_SHEEP",
        "a7: SELL_FERTILIZER",
        "a8: SELL_MELON",
        "a9: SELL_MILK_WOOL",
    ]
    for i in range(10):
        cnt = (labels == i).sum()
        print(f"  {action_names[i]:<25} : {cnt:>5d} ({cnt / len(labels) * 100:>5.1f}%)")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"\nTraining on device: {device} ({torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'})")

    train_dataset = TensorDataset(
        torch.tensor(states_norm[train_mask]),
        torch.tensor(labels[train_mask])
    )
    test_dataset = TensorDataset(
        torch.tensor(states_norm[test_mask]),
        torch.tensor(labels[test_mask])
    )

    train_loader = DataLoader(train_dataset, batch_size=64, shuffle=True)
    test_loader = DataLoader(test_dataset, batch_size=128, shuffle=False)

    # Class weights for focal balance
    class_counts = np.bincount(labels[train_mask], minlength=10)
    class_weights = 1.0 / (class_counts.astype(np.float32) + 5.0)
    class_weights[0] *= 0.25 # Downweight default class
    class_weights = class_weights / class_weights.sum() * 10.0
    weights_tensor = torch.tensor(class_weights, dtype=torch.float32, device=device)

    model = EliteBCNetwork(state_dim=16, num_actions=10).to(device)
    optimizer = optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
    criterion = nn.CrossEntropyLoss(weight=weights_tensor)

    print("\n--- Training Elite BC Network (30 Epochs) ---")
    t0 = time.time()
    for epoch in range(30):
        model.train()
        total_loss = 0.0
        for b_st, b_lbl in train_loader:
            b_st, b_lbl = b_st.to(device), b_lbl.to(device)
            optimizer.zero_grad()
            logits = model(b_st)
            loss = criterion(logits, b_lbl)
            loss.backward()
            optimizer.step()
            total_loss += loss.item() * len(b_st)

        if (epoch + 1) % 5 == 0 or epoch == 0:
            model.eval()
            all_preds = []
            all_true = []
            with torch.no_grad():
                for b_st, b_lbl in test_loader:
                    b_st = b_st.to(device)
                    logits = model(b_st)
                    preds = logits.argmax(dim=-1).cpu().numpy()
                    all_preds.extend(preds)
                    all_true.extend(b_lbl.numpy())

            preds_arr = np.array(all_preds)
            true_arr = np.array(all_true)
            top1_acc = (preds_arr == true_arr).mean() * 100.0
            
            # Non-default action recall (macro actions)
            non_def_mask = (true_arr != 0)
            macro_recall = ((preds_arr[non_def_mask] == true_arr[non_def_mask]).mean() * 100.0) if non_def_mask.sum() > 0 else 0.0

            print(f"Epoch {epoch+1:2d}/30 | Overall Top-1 Acc: {top1_acc:5.1f}% | Elite Macro Action Recall: {macro_recall:5.1f}% | Loss: {total_loss / len(train_dataset):.4f}")

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
