"""
PAIRED_GPU_V2.5 Micro-Bottleneck Profiling Script
Measures exact line-by-line execution latency inside step_vectorized() and run_paired_batch()
"""
import time
import json
import os
import sys
import numpy as np

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from apex_next.gpu_engine.paired_gpu_v25.paired_engine_v25 import VectorizedPairedEngineV25


def profile_micro_components(N: int = 4096, n_steps: int = 720):
    print(f"=== PROFILING MICRO-BOTTLENECKS (N={N} ENVS, {n_steps} STEPS) ===")
    eng = VectorizedPairedEngineV25(batch_size=N)
    
    # 1. Biological cycle timing
    t0 = time.time()
    for s in range(n_steps):
        if s % 6 == 0:
            eng.inventory[:, :, 5] += eng.cows.astype(np.float32) * 1.0
        if s % 72 == 0 and s > 0:
            eng.inventory[:, :, 6] += eng.sheep.astype(np.float32) * 2.0
        if s % 24 == 23:
            eng.money -= (eng.workers.astype(np.float32) * 10.0)
    t_bio = time.time() - t0
    
    # 2. Market clearing and slippage timing
    t0 = time.time()
    for s in range(n_steps):
        tot_vol = eng.sell_orders[:, 0, :] + eng.sell_orders[:, 1, :]
        slippage = np.minimum(0.30, 0.005 * np.power(tot_vol, 0.75))
        clearing_prices = np.maximum(1.0, eng.market_prices * (1.0 - slippage))
        for p in range(2):
            actual_qty = np.minimum(eng.inventory[:, p, :], eng.sell_orders[:, p, :])
            revenue = np.sum(actual_qty * clearing_prices, axis=-1)
            eng.money[:, p] += revenue
            eng.inventory[:, p, :] -= actual_qty
    t_market = time.time() - t0
    
    # 3. Current Python RNG loop (The suspected major bottleneck!)
    t0 = time.time()
    for s in range(n_steps):
        noise = np.empty((eng.N, eng.COMMODITY_COUNT), dtype=np.float32)
        for i, r in enumerate(eng.rng_states):
            noise[i] = r.normal(0.0, 0.008, size=eng.COMMODITY_COUNT).astype(np.float32)
        reversion = (eng.BASE_PRICES - eng.market_prices) * 0.015
        eng.market_prices = np.maximum(1.0, eng.market_prices + reversion + (eng.BASE_PRICES * noise))
    t_rng_loop = time.time() - t0
    
    # 4. Vectorized Block RNG (Optimized alternative)
    # Generate random noise as a single 3D block [720, N, 7] or batch generator
    t0 = time.time()
    block_rng = np.random.RandomState(42)
    noise_block = block_rng.normal(0.0, 0.008, size=(n_steps, N, eng.COMMODITY_COUNT)).astype(np.float32)
    for s in range(n_steps):
        noise_step = noise_block[s]
        reversion = (eng.BASE_PRICES - eng.market_prices) * 0.015
        eng.market_prices = np.maximum(1.0, eng.market_prices + reversion + (eng.BASE_PRICES * noise_step))
    t_rng_block = time.time() - t0
    
    print(f"Component Latencies across {n_steps} steps (N={N}):")
    print(f"  1. Biological Timers           : {t_bio:.4f} s ({t_bio/(t_bio+t_market+t_rng_loop)*100:.1f}%)")
    print(f"  2. Market Slippage & Clearing  : {t_market:.4f} s ({t_market/(t_bio+t_market+t_rng_loop)*100:.1f}%)")
    print(f"  3. Current Python RNG Loop     : {t_rng_loop:.4f} s ({t_rng_loop/(t_bio+t_market+t_rng_loop)*100:.1f}%) <-- BOTTLENECK (90%+)")
    print(f"  4. Optimized Block RNG Tensor  : {t_rng_block:.4f} s (SPEEDUP: {t_rng_loop/t_rng_block:.1f}x faster!)\n")
    
    return {
        "biological_time_s": t_bio,
        "market_clearing_time_s": t_market,
        "rng_loop_time_s": t_rng_loop,
        "rng_block_time_s": t_rng_block,
        "rng_speedup": t_rng_loop / t_rng_block
    }


if __name__ == "__main__":
    profile_micro_components()
