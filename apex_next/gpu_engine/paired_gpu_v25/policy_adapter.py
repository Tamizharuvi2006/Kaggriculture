"""
PAIRED_GPU_V2.5 Policy Adapter & Profiler
Adapts APEX 3.5 and candidate rules into vectorized tensor operations:
- Zero-copy tensor slice updates
- Parameterized candidate rule compilation
- Profiling harness for Policy Time vs Environment Time
"""
import time
import numpy as np
from typing import Dict, Any, Callable


def make_vector_apex35_policy() -> Callable[[Dict[str, np.ndarray], int], None]:
    """
    Vectorized APEX 3.5 tournament policy:
    - Sells milk whenever milk in inventory >= 2.0
    - Buys Land 2 at Step 170 if money >= 1000 and land == 4
    """
    def policy(state: Dict[str, np.ndarray], seat: int):
        step = state["step"]
        money = state["money"]
        land = state["land"]
        inv = state["inventory"] # [N, 7]
        sell_orders = state["sell_orders"] # [N, 7]
        buy_land = state["buy_land"] # [N]
        
        # 1. Milk Liquidation: Sell all available milk if >= 2.0
        milk_qty = inv[:, 5]
        sell_orders[:, 5] = np.where(milk_qty >= 2.0, milk_qty, 0.0)
        
        # 2. Fixed Step 170 Land 2 expansion
        if step == 170:
            buy_land[:] = (money >= 1000.0) & (land == 4)
            
    return policy


def make_vector_candidate_policy(
    min_land_step: int = 170,
    land_cash_threshold: float = 1000.0,
    milk_sell_threshold: float = 2.0,
    strawberry_front_run_step: int = -1
) -> Callable[[Dict[str, np.ndarray], int], None]:
    """
    Vectorized Parameterized Candidate policy:
    - Configurable Land 2 unlock step and cash threshold
    - Configurable Milk liquidation threshold
    - Configurable reflexivity triggers
    """
    def policy(state: Dict[str, np.ndarray], seat: int):
        step = state["step"]
        money = state["money"]
        land = state["land"]
        inv = state["inventory"]
        sell_orders = state["sell_orders"]
        buy_land = state["buy_land"]
        
        # Milk Liquidation
        milk_qty = inv[:, 5]
        sell_orders[:, 5] = np.where(milk_qty >= milk_sell_threshold, milk_qty, 0.0)
        
        # Land Expansion
        if step >= min_land_step:
            buy_land[:] = (money >= land_cash_threshold) & (land == 4)
            
    return policy


def profile_execution_breakdown(engine, n_steps: int = 720, batch_size: int = 4096) -> Dict[str, float]:
    """Measures precise execution breakdown: Environment vs Policy vs Overhead."""
    seeds = [1000 + i for i in range(batch_size)]
    engine.reset(seeds)
    pol_base = make_vector_apex35_policy()
    
    t_pol_total = 0.0
    t_env_total = 0.0
    
    t_start = time.time()
    for step in range(n_steps):
        t0 = time.time()
        state_p0 = {
            "step": engine.step_idx, "day": engine.day_idx, "hour": engine.hour_idx,
            "money": engine.money[:, 0], "land": engine.land_count[:, 0],
            "inventory": engine.inventory[:, 0, :], "market_prices": engine.market_prices,
            "opp_money": engine.money[:, 1], "opp_land": engine.land_count[:, 1],
            "sell_orders": engine.sell_orders[:, 0, :], "buy_land": engine.buy_land_orders[:, 0]
        }
        state_p1 = {
            "step": engine.step_idx, "day": engine.day_idx, "hour": engine.hour_idx,
            "money": engine.money[:, 1], "land": engine.land_count[:, 1],
            "inventory": engine.inventory[:, 1, :], "market_prices": engine.market_prices,
            "opp_money": engine.money[:, 0], "opp_land": engine.land_count[:, 0],
            "sell_orders": engine.sell_orders[:, 1, :], "buy_land": engine.buy_land_orders[:, 1]
        }
        pol_base(state_p0, 0)
        pol_base(state_p1, 1)
        t1 = time.time()
        t_pol_total += (t1 - t0)
        
        engine.step_vectorized()
        t2 = time.time()
        t_env_total += (t2 - t1)
        
    t_total = time.time() - t_start
    return {
        "total_wall_time_s": round(t_total, 4),
        "policy_time_s": round(t_pol_total, 4),
        "environment_time_s": round(t_env_total, 4),
        "policy_pct": round((t_pol_total / t_total) * 100, 1),
        "environment_pct": round((t_env_total / t_total) * 100, 1),
        "throughput_steps_per_sec": round((batch_size * n_steps) / t_total, 0)
    }
