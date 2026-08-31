"""
EXP200.5 — FastSim GPU Batch Acceleration Engine.
Provides high-throughput tensorized batch evaluation, parallel Q-value ranking,
and counterfactual state assessment on NVIDIA RTX 4050 Laptop GPU.
"""

import os
import sys
import time
import json
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

class GPUBatchQEngine:
    def __init__(self, weights_path=r"D:\kaggriculture\models\exp200_competitive_q_weights.json", device="cuda"):
        self.device = torch.device(device if torch.cuda.is_available() else "cpu")
        with open(weights_path, "r") as f:
            w = json.load(f)
        
        self.state_mean = torch.tensor(w["state_mean"], dtype=torch.float32, device=self.device)
        self.state_std = torch.tensor(w["state_std"], dtype=torch.float32, device=self.device)
        
        # Build optimized GPU trunk
        hidden_dim = 128
        self.fc1 = nn.Linear(16, hidden_dim).to(self.device)
        self.fc1.weight.data = torch.tensor(w["trunk_fc1_weight"], dtype=torch.float32, device=self.device)
        self.fc1.bias.data = torch.tensor(w["trunk_fc1_bias"], dtype=torch.float32, device=self.device)
        
        self.ln1 = nn.LayerNorm(hidden_dim).to(self.device)
        self.ln1.weight.data = torch.tensor(w["trunk_ln1_weight"], dtype=torch.float32, device=self.device)
        self.ln1.bias.data = torch.tensor(w["trunk_ln1_bias"], dtype=torch.float32, device=self.device)
        
        self.fc2 = nn.Linear(hidden_dim, 64).to(self.device)
        self.fc2.weight.data = torch.tensor(w["trunk_fc2_weight"], dtype=torch.float32, device=self.device)
        self.fc2.bias.data = torch.tensor(w["trunk_fc2_bias"], dtype=torch.float32, device=self.device)
        
        self.ln2 = nn.LayerNorm(64).to(self.device)
        self.ln2.weight.data = torch.tensor(w["trunk_ln2_weight"], dtype=torch.float32, device=self.device)
        self.ln2.bias.data = torch.tensor(w["trunk_ln2_bias"], dtype=torch.float32, device=self.device)
        
        self.head = nn.Linear(64, 6).to(self.device)
        self.head.weight.data = torch.tensor(w["q_margin_head_weight"], dtype=torch.float32, device=self.device)
        self.head.bias.data = torch.tensor(w["q_margin_head_bias"], dtype=torch.float32, device=self.device)
        
        self.eval()

    def eval(self):
        self.fc1.eval()
        self.ln1.eval()
        self.fc2.eval()
        self.ln2.eval()
        self.head.eval()

    @torch.no_grad()
    def evaluate_batch_states(self, states_tensor):
        """
        states_tensor: [N, 16] torch.Tensor or np.ndarray
        Returns: q_margins [N, 6] on GPU or CPU
        """
        if isinstance(states_tensor, np.ndarray):
            states_tensor = torch.from_numpy(states_tensor).to(self.device)
            
        norm_states = (states_tensor - self.state_mean) / self.state_std
        h1 = F.relu(self.ln1(self.fc1(norm_states)))
        h2 = F.relu(self.ln2(self.fc2(h1)))
        q_margins = self.head(h2)
        return q_margins

    @torch.no_grad()
    def rank_macro_actions_batch(self, states_tensor, threshold_margin=150.0):
        """
        Ranks all 6 macro actions for N states simultaneously.
        Returns: (best_actions [N], best_margins [N], should_intervene [N])
        """
        q_margins = self.evaluate_batch_states(states_tensor)
        best_margins, best_actions = torch.max(q_margins, dim=-1)
        base_margins = q_margins[:, 0]
        
        margin_advantages = best_margins - base_margins
        should_intervene = (margin_advantages >= threshold_margin) & (best_actions != 0)
        
        return best_actions, margin_advantages, should_intervene

def benchmark_gpu_throughput():
    print("=" * 80)
    print("EXP200.5 -- GPU BATCH ACCELERATION BENCHMARK (NVIDIA RTX 4050)")
    print("=" * 80)
    
    engine = GPUBatchQEngine()
    print(f"GPU Backend initialized on: {torch.cuda.get_device_name(0)}")
    
    batch_sizes = [1000, 10000, 100000, 1000000]
    
    # Warmup
    dummy = torch.randn(1000, 16, device=engine.device)
    for _ in range(10):
        _ = engine.evaluate_batch_states(dummy)
    torch.cuda.synchronize()
    
    results = []
    
    for bs in batch_sizes:
        raw_states = np.random.randn(bs, 16).astype(np.float32)
        
        # 1. Measure Host-to-Device Transfer
        torch.cuda.synchronize()
        t_transfer_0 = time.perf_counter()
        states_gpu = torch.from_numpy(raw_states).to(engine.device)
        torch.cuda.synchronize()
        t_transfer = (time.perf_counter() - t_transfer_0) * 1000.0 # ms
        
        # 2. Measure Pure Kernel Execution Time
        torch.cuda.synchronize()
        t_kernel_0 = time.perf_counter()
        best_acts, margin_advs, should_interv = engine.rank_macro_actions_batch(states_gpu)
        torch.cuda.synchronize()
        t_kernel = (time.perf_counter() - t_kernel_0) * 1000.0 # ms
        
        # 3. Measure Device-to-Host Transfer
        torch.cuda.synchronize()
        t_d2h_0 = time.perf_counter()
        acts_cpu = best_acts.cpu().numpy()
        torch.cuda.synchronize()
        t_d2h = (time.perf_counter() - t_d2h_0) * 1000.0 # ms
        
        total_time_ms = t_transfer + t_kernel + t_d2h
        throughput = bs / (total_time_ms / 1000.0)
        pure_kernel_throughput = bs / (t_kernel / 1000.0)
        
        vram_mb = torch.cuda.memory_allocated() / (1024 * 1024)
        
        results.append({
            "batch_size": bs,
            "h2d_ms": t_transfer,
            "kernel_ms": t_kernel,
            "d2h_ms": t_d2h,
            "total_ms": total_time_ms,
            "end_to_end_throughput": throughput,
            "pure_kernel_throughput": pure_kernel_throughput,
            "vram_mb": vram_mb
        })
        
        print(f"Batch Size: {bs:>7,d} | Total Time: {total_time_ms:6.2f} ms (Kernel: {t_kernel:5.2f} ms, H2D: {t_transfer:5.2f} ms) | Throughput: {throughput:>12,.0f} eval/s (Kernel: {pure_kernel_throughput:>12,.0f} eval/s) | VRAM: {vram_mb:5.1f} MB")
        
    return results

if __name__ == "__main__":
    benchmark_gpu_throughput()
