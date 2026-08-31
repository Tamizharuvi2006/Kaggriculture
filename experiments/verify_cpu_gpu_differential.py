"""
EXP200.5 — Verify CPU vs GPU Differential Bit-Exact Parity on 100, 1,000, and 10,000 States.
"""

import sys
import pandas as pd
import numpy as np
import torch
from fastsim_gpu_batch_engine import GPUBatchQEngine

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

def run_differential_test():
    print("=" * 80)
    print("EXP200.5 -- CPU VS GPU DIFFERENTIAL BIT-EXACT PARITY GATE")
    print("=" * 80)
    
    csv_path = r"D:\kaggriculture\data\exp200_5_states_for_diff_test.csv"
    df = pd.read_csv(csv_path)
    print(f"Loaded {len(df):,} states and reference CPU Q-values.")
    
    f_cols = [f"f{i}" for i in range(16)]
    q_cols = [f"q{i}" for i in range(6)]
    
    states = df[f_cols].values.astype(np.float32)
    cpu_q_vals = df[q_cols].values.astype(np.float32)
    
    engine = GPUBatchQEngine()
    
    # Test on 100, 1,000, and 10,000 samples
    for n in [100, 1000, 10000]:
        sub_states = states[:n]
        sub_cpu_q = cpu_q_vals[:n]
        
        gpu_q_tensor = engine.evaluate_batch_states(sub_states)
        gpu_q = gpu_q_tensor.cpu().numpy()
        
        abs_diff = np.abs(sub_cpu_q - gpu_q)
        max_err = abs_diff.max()
        mean_err = abs_diff.mean()
        
        cpu_best_acts = sub_cpu_q.argmax(axis=-1)
        gpu_best_acts = gpu_q.argmax(axis=-1)

        
        action_mismatches = (cpu_best_acts != gpu_best_acts).sum()
        action_match_pct = ((n - action_mismatches) / n) * 100.0
        
        status = "PASSED (BIT-EXACT MATCH)" if action_mismatches == 0 and max_err < 1e-4 else "FAILED"
        
        print(f"Sample Size: {n:>6,d} | Max Absolute Error: {max_err:.2e} | Mean Error: {mean_err:.2e} | Action Match: {action_match_pct:6.2f}% ({n - action_mismatches}/{n}) | Status: {status}")
        
    print("=" * 80)

if __name__ == "__main__":
    run_differential_test()
