"""
EXP179 — Step 2 & 3: Hierarchical Behavioral Cloning (BC) & Value Model Training Pipeline.
Trains PyTorch MacroPolicy and ValueModel on 47,454 authentic state-action-reward samples,
evaluates precision across tiers, and exports NumPy weights for fast native FastSim scoring.
"""

import os
import time
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import TensorDataset, DataLoader
from sklearn.model_selection import train_test_split

class MacroPolicyNet(nn.Module):
    def __init__(self, in_dim=635, hidden_dim=256, num_classes=16):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(in_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.LayerNorm(hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(hidden_dim // 2, num_classes)
        )
    def forward(self, x):
        return self.net(x)

class ValueNet(nn.Module):
    def __init__(self, in_dim=635, hidden_dim=256):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(in_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.LayerNorm(hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(hidden_dim // 2, 1)
        )
    def forward(self, x):
        return self.net(x).squeeze(-1)

def main():
    print("=" * 80)
    print("EXP179 — HIERARCHICAL BC & VALUE MODEL TRAINING")
    print("=" * 80)
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using compute device: {device}")
    
    # 1. Load Dataset
    data_path = "D:/kaggriculture/data/exp179_dataset.npz"
    if not os.path.exists(data_path):
        print(f"Error: Dataset {data_path} not found!")
        return
        
    data = np.load(data_path)
    states = data["states"]
    actions = data["actions"]
    rewards = data["rewards"]
    tiers = data["tiers"]
    
    N, D = states.shape
    print(f"Loaded {N:,} samples with feature dimension {D}.")
    
    # Stratified Train/Test Split (80% Train, 20% Test)
    idx_train, idx_test = train_test_split(np.arange(N), test_size=0.20, random_state=42, stratify=tiers)
    
    X_train, y_act_train, y_rew_train, t_train = states[idx_train], actions[idx_train], rewards[idx_train], tiers[idx_train]
    X_test, y_act_test, y_rew_test, t_test = states[idx_test], actions[idx_test], rewards[idx_test], tiers[idx_test]
    
    # Sample Weights: Grandmaster (Tier 1) = 3.0, Competitive (Tier 2) = 1.0, Population = 0.25
    weights_train = np.where(t_train == 1, 3.0, np.where(t_train == 2, 1.0, 0.25)).astype(np.float32)
    
    # Reward Normalization (target in units of $100k)
    y_rew_train_norm = (y_rew_train / 100000.0).astype(np.float32)
    y_rew_test_norm = (y_rew_test / 100000.0).astype(np.float32)
    
    train_dataset = TensorDataset(
        torch.tensor(X_train),
        torch.tensor(y_act_train, dtype=torch.long),
        torch.tensor(y_rew_train_norm),
        torch.tensor(weights_train)
    )
    test_dataset = TensorDataset(
        torch.tensor(X_test),
        torch.tensor(y_act_test, dtype=torch.long),
        torch.tensor(y_rew_test_norm)
    )
    
    train_loader = DataLoader(train_dataset, batch_size=256, shuffle=True)
    test_loader = DataLoader(test_dataset, batch_size=512, shuffle=False)
    
    # 2. Initialize Models
    policy_net = MacroPolicyNet(in_dim=D).to(device)
    value_net = ValueNet(in_dim=D).to(device)
    
    crit_policy = nn.CrossEntropyLoss(reduction='none')
    crit_value = nn.SmoothL1Loss(reduction='mean')
    
    opt_policy = optim.AdamW(policy_net.parameters(), lr=1e-3, weight_decay=1e-4)
    opt_value = optim.AdamW(value_net.parameters(), lr=1e-3, weight_decay=1e-4)
    
    print("\n--- Training Hierarchical Macro Policy & Value Model (20 Epochs) ---")
    t0 = time.time()
    
    for epoch in range(1, 21):
        policy_net.train()
        value_net.train()
        
        train_p_loss, train_v_loss = 0.0, 0.0
        correct_p, total_p = 0, 0
        
        for batch_x, batch_a, batch_r, batch_w in train_loader:
            batch_x = batch_x.to(device)
            batch_a = batch_a.to(device)
            batch_r = batch_r.to(device)
            batch_w = batch_w.to(device)
            
            # Policy update
            opt_policy.zero_grad()
            logits = policy_net(batch_x)
            loss_p_raw = crit_policy(logits, batch_a)
            loss_p = (loss_p_raw * batch_w).mean()
            loss_p.backward()
            opt_policy.step()
            
            train_p_loss += loss_p.item() * len(batch_a)
            preds = logits.argmax(dim=-1)
            correct_p += (preds == batch_a).sum().item()
            total_p += len(batch_a)
            
            # Value update
            opt_value.zero_grad()
            val_preds = value_net(batch_x)
            loss_v = crit_value(val_preds, batch_r)
            loss_v.backward()
            opt_value.step()
            
            train_v_loss += loss_v.item() * len(batch_r)
            
        train_acc = (correct_p / total_p) * 100.0
        
        # Test Evaluation
        if epoch % 5 == 0 or epoch == 20:
            policy_net.eval()
            value_net.eval()
            test_correct, test_total = 0, 0
            val_errs = []
            
            with torch.no_grad():
                for batch_x, batch_a, batch_r in test_loader:
                    batch_x = batch_x.to(device)
                    batch_a = batch_a.to(device)
                    batch_r = batch_r.to(device)
                    
                    logits = policy_net(batch_x)
                    preds = logits.argmax(dim=-1)
                    test_correct += (preds == batch_a).sum().item()
                    test_total += len(batch_a)
                    
                    v_pred = value_net(batch_x)
                    # Realized absolute error in dollars
                    err_dollars = torch.abs((v_pred - batch_r) * 100000.0)
                    val_errs.extend(err_dollars.cpu().numpy().tolist())
                    
            test_acc = (test_correct / test_total) * 100.0
            mean_val_mae = np.mean(val_errs)
            
            print(f"Epoch [{epoch:2d}/20] | Train Acc: {train_acc:5.1f}% | Test Acc: {test_acc:5.1f}% | Value MAE: ${mean_val_mae:7.0f}")
            
    train_time = time.time() - t0
    print(f"\nTraining completed in {train_time:.2f}s!")
    
    # 3. Stratified Accuracy per Tier
    policy_net.eval()
    value_net.eval()
    with torch.no_grad():
        test_x_tensor = torch.tensor(X_test).to(device)
        test_logits = policy_net(test_x_tensor)
        test_preds = test_logits.argmax(dim=-1).cpu().numpy()
        test_v = (value_net(test_x_tensor).cpu().numpy() * 100000.0)
        
    for t_id, t_name in [(1, "Grandmaster (Tier 1 >= $120k)"), (2, "Competitive (Tier 2 $70k-$120k)"), (3, "Population (Tier 3 < $70k)")]:
        mask = (t_test == t_id)
        if np.sum(mask) > 0:
            acc_t = (np.mean(test_preds[mask] == y_act_test[mask])) * 100.0
            mae_t = np.mean(np.abs(test_v[mask] - y_rew_test[mask]))
            print(f"  * {t_name:<32}: Action Accuracy = {acc_t:5.1f}% | Value MAE = ${mae_t:7.0f}")
            
    # 4. Export Model Weights as NumPy Arrays for FastSim Runtime
    os.makedirs("D:/kaggriculture/models", exist_ok=True)
    export_path = "D:/kaggriculture/models/exp179_bc_weights.npz"
    
    # Extract weights
    p_w0 = policy_net.net[0].weight.detach().cpu().numpy()
    p_b0 = policy_net.net[0].bias.detach().cpu().numpy()
    p_w4 = policy_net.net[4].weight.detach().cpu().numpy()
    p_b4 = policy_net.net[4].bias.detach().cpu().numpy()
    p_w8 = policy_net.net[8].weight.detach().cpu().numpy()
    p_b8 = policy_net.net[8].bias.detach().cpu().numpy()
    
    v_w0 = value_net.net[0].weight.detach().cpu().numpy()
    v_b0 = value_net.net[0].bias.detach().cpu().numpy()
    v_w4 = value_net.net[4].weight.detach().cpu().numpy()
    v_b4 = value_net.net[4].bias.detach().cpu().numpy()
    v_w8 = value_net.net[8].weight.detach().cpu().numpy()
    v_b8 = value_net.net[8].bias.detach().cpu().numpy()
    
    np.savez_compressed(
        export_path,
        p_w0=p_w0, p_b0=p_b0,
        p_w4=p_w4, p_b4=p_b4,
        p_w8=p_w8, p_b8=p_b8,
        v_w0=v_w0, v_b0=v_b0,
        v_w4=v_w4, v_b4=v_b4,
        v_w8=v_w8, v_b8=v_b8
    )
    print(f"\nSuccessfully exported neural policy & value model weights to {export_path} ({os.path.getsize(export_path)/(1024*1024):.2f} MB)!")

if __name__ == "__main__":
    main()
