"""
EXP179 — Level 2/3 Worker Execution Network Trainer.
Trains PyTorch WorkerPolicyNet on 480,300 authentic worker step demonstrations,
evaluates per-action physical execution accuracy, and exports weights.
"""

import os
import time
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import TensorDataset, DataLoader
from sklearn.model_selection import train_test_split

ACTION_NAMES = [
    "PASS", "NORTH", "SOUTH", "EAST", "WEST", "TILL",
    "PLANT_MELON", "PLANT_STRAWBERRY", "PLANT_WHEAT", "PLANT_CARROT", "PLANT_TOMATO",
    "WATER", "HARVEST", "FEED_CARE", "COLLECT_FERT", "DROP_PICKUP"
]

class WorkerPolicyNet(nn.Module):
    def __init__(self, in_dim=48, hidden_dim=128, num_classes=16):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(in_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.05),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.LayerNorm(hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(0.05),
            nn.Linear(hidden_dim // 2, num_classes)
        )
    def forward(self, x):
        return self.net(x)

def main():
    print("=" * 80)
    print("EXP179 — LEVEL 2/3 WORKER EXECUTION POLICY TRAINING (480,300 SAMPLES)")
    print("=" * 80)
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")
    
    data_path = "D:/kaggriculture/data/exp179_worker_dataset.npz"
    data = np.load(data_path)
    X = data["features"]
    y = data["labels"]
    t = data["tiers"]
    
    N, D = X.shape
    print(f"Loaded {N:,} worker execution step samples (Feature dim: {D}).")
    
    idx_train, idx_test = train_test_split(np.arange(N), test_size=0.15, random_state=42, stratify=y)
    
    X_train, y_train, t_train = X[idx_train], y[idx_train], t[idx_train]
    X_test, y_test, t_test = X[idx_test], y[idx_test], t[idx_test]
    
    weights_train = np.where(t_train == 1, 3.0, np.where(t_train == 2, 1.0, 0.25)).astype(np.float32)
    
    train_dataset = TensorDataset(
        torch.tensor(X_train),
        torch.tensor(y_train, dtype=torch.long),
        torch.tensor(weights_train)
    )
    test_dataset = TensorDataset(
        torch.tensor(X_test),
        torch.tensor(y_test, dtype=torch.long)
    )
    
    train_loader = DataLoader(train_dataset, batch_size=512, shuffle=True)
    test_loader = DataLoader(test_dataset, batch_size=1024, shuffle=False)
    
    model = WorkerPolicyNet(in_dim=D).to(device)
    crit = nn.CrossEntropyLoss(reduction='none')
    opt = optim.AdamW(model.parameters(), lr=2e-3, weight_decay=1e-4)
    
    print("\n--- Training Worker Motion & Task Policy (15 Epochs) ---")
    t0 = time.time()
    
    for epoch in range(1, 16):
        model.train()
        train_loss = 0.0
        correct, total = 0, 0
        
        for bx, by, bw in train_loader:
            bx, by, bw = bx.to(device), by.to(device), bw.to(device)
            opt.zero_grad()
            logits = model(bx)
            loss_raw = crit(logits, by)
            loss = (loss_raw * bw).mean()
            loss.backward()
            opt.step()
            
            preds = logits.argmax(dim=-1)
            correct += (preds == by).sum().item()
            total += len(by)
            
        train_acc = (correct / total) * 100.0
        
        if epoch % 5 == 0 or epoch == 15:
            model.eval()
            test_correct, test_total = 0, 0
            with torch.no_grad():
                for bx, by in test_loader:
                    bx, by = bx.to(device), by.to(device)
                    logits = model(bx)
                    preds = logits.argmax(dim=-1)
                    test_correct += (preds == by).sum().item()
                    test_total += len(by)
            test_acc = (test_correct / test_total) * 100.0
            print(f"Epoch [{epoch:2d}/15] | Train Acc: {train_acc:5.1f}% | Held-Out Test Acc: {test_acc:5.1f}%")
            
    train_time = time.time() - t0
    print(f"\nWorker policy training completed in {train_time:.2f}s!")
    
    # Per-action breakdown
    model.eval()
    with torch.no_grad():
        test_x_tensor = torch.tensor(X_test).to(device)
        test_logits = model(test_x_tensor)
        test_preds = test_logits.argmax(dim=-1).cpu().numpy()
        
    print("\nAction-Specific Accuracy Breakdown on Held-Out Test Set:")
    for a_idx, a_name in enumerate(ACTION_NAMES):
        mask = (y_test == a_idx)
        if np.sum(mask) > 0:
            acc = np.mean(test_preds[mask] == y_test[mask]) * 100.0
            print(f"  * [{a_idx:2d}] {a_name:<18}: {acc:5.1f}% (Count: {np.sum(mask):,})")
            
    # Export weights
    export_path = "D:/kaggriculture/models/exp179_worker_weights.npz"
    w0 = model.net[0].weight.detach().cpu().numpy()
    b0 = model.net[0].bias.detach().cpu().numpy()
    w4 = model.net[4].weight.detach().cpu().numpy()
    b4 = model.net[4].bias.detach().cpu().numpy()
    w8 = model.net[8].weight.detach().cpu().numpy()
    b8 = model.net[8].bias.detach().cpu().numpy()
    
    np.savez_compressed(
        export_path,
        w0=w0, b0=b0,
        w4=w4, b4=b4,
        w8=w8, b8=b8
    )
    print(f"\nSuccessfully exported worker motion policy weights to {export_path} ({os.path.getsize(export_path)/(1024*1024):.2f} MB)!")

if __name__ == "__main__":
    main()
