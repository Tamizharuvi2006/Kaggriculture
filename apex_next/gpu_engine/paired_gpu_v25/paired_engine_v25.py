"""
PAIRED_GPU_V2.5 Vectorized Batch Tensor Co-Simulation Engine
Simulates N parallel 2-player episodes (Candidate vs APEX 3.5) with:
- Contiguous C-aligned tensor memory layout across N environments
- Vectorized biological production cycles (6h milk, 72h wool, 24h wages)
- Shared town market order book with non-linear power-law volume slippage
- Vectorized mean-reversion market price drift with deterministic per-env RNG
- Paired seat-swapping execution harness (Match A: P0/P1, Match B: P1/P0)
- Zero Python dictionary allocations in inner simulation loop
"""
import time
import numpy as np
from typing import Dict, Any, List, Tuple, Optional, Callable


class VectorizedPairedEngineV25:
    STEPS_PER_DAY = 24
    EPISODE_STEPS = 720
    PRODUCTS = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "MILK", "WOOL"]
    COMMODITY_COUNT = 7
    
    BASE_PRICES = np.array([25.0, 35.0, 60.0, 120.0, 250.0, 160.0, 200.0], dtype=np.float32)
    
    def __init__(self, batch_size: int = 4096, base_seed: int = 42):
        self.N = batch_size
        self.base_seed = base_seed
        
        # State tensors: shape [N, 2] for players 0 and 1
        self.money = np.full((self.N, 2), 3000.0, dtype=np.float32)
        self.land_count = np.full((self.N, 2), 1, dtype=np.int32)
        self.cows = np.full((self.N, 2), 2, dtype=np.int32)
        self.sheep = np.full((self.N, 2), 0, dtype=np.int32)
        self.workers = np.full((self.N, 2), 0, dtype=np.int32)
        
        # Inventory tensor: shape [N, 2, 7]
        self.inventory = np.zeros((self.N, 2, self.COMMODITY_COUNT), dtype=np.float32)
        
        # Market prices tensor: shape [N, 7]
        self.market_prices = np.tile(self.BASE_PRICES, (self.N, 1)).astype(np.float32)
        
        # Order buffer: shape [N, 2, 7] sell quantities
        self.sell_orders = np.zeros((self.N, 2, self.COMMODITY_COUNT), dtype=np.float32)
        
        # Land buy orders buffer: shape [N, 2] boolean flags
        self.buy_land_orders = np.zeros((self.N, 2), dtype=bool)
        
        # Deterministic per-environment RNG streams & pre-allocated noise block [720, N, 7]
        self.seeds = np.array([base_seed + i for i in range(self.N)], dtype=np.int64)
        self.rng_states = [np.random.RandomState(int(s)) for s in self.seeds]
        self.market_noise = np.empty((self.EPISODE_STEPS, self.N, self.COMMODITY_COUNT), dtype=np.float32)
        self._pregenerate_noise_block()
        
        self.step_idx = 0
        self.day_idx = 0
        self.hour_idx = 0

    def _pregenerate_noise_block(self):
        for i, r in enumerate(self.rng_states):
            self.market_noise[:, i, :] = r.normal(0.0, 0.008, size=(self.EPISODE_STEPS, self.COMMODITY_COUNT)).astype(np.float32)

    def reset(self, seed_list: Optional[List[int]] = None):
        """Resets all N environments to step 0 with deterministic noise blocks."""
        if seed_list is not None:
            self.N = len(seed_list)
            self.seeds = np.array(seed_list, dtype=np.int64)
            self.rng_states = [np.random.RandomState(int(s)) for s in self.seeds]
            
            # Re-allocate if N changed
            self.money = np.full((self.N, 2), 3000.0, dtype=np.float32)
            self.land_count = np.full((self.N, 2), 1, dtype=np.int32)
            self.shed_cows = np.zeros((self.N, 2), dtype=np.int32)
            self.shed_sheep = np.zeros((self.N, 2), dtype=np.int32)
            self.active_cows = np.zeros((self.N, 2), dtype=np.int32)
            self.active_sheep = np.zeros((self.N, 2), dtype=np.int32)
            self.pastures_count = np.zeros((self.N, 2), dtype=np.int32)
            self.carrying_cows = np.zeros((self.N, 2), dtype=np.int32)
            self.carrying_sheep = np.zeros((self.N, 2), dtype=np.int32)
            self.cows = np.full((self.N, 2), 2, dtype=np.int32)
            self.sheep = np.full((self.N, 2), 0, dtype=np.int32)
            self.workers = np.full((self.N, 2), 0, dtype=np.int32)
            self.inventory = np.zeros((self.N, 2, self.COMMODITY_COUNT), dtype=np.float32)
            self.market_prices = np.tile(self.BASE_PRICES, (self.N, 1)).astype(np.float32)
            self.sell_orders = np.zeros((self.N, 2, self.COMMODITY_COUNT), dtype=np.float32)
            self.buy_land_orders = np.zeros((self.N, 2), dtype=bool)
            self.market_noise = np.empty((self.EPISODE_STEPS, self.N, self.COMMODITY_COUNT), dtype=np.float32)
            self._pregenerate_noise_block()
        else:
            self.money.fill(3000.0)
            self.land_count.fill(1)
            self.shed_cows.fill(0)
            self.shed_sheep.fill(0)
            self.active_cows.fill(0)
            self.active_sheep.fill(0)
            self.pastures_count.fill(0)
            self.carrying_cows.fill(0)
            self.carrying_sheep.fill(0)
            self.cows.fill(2)
            self.sheep.fill(0)
            self.workers.fill(0)
            self.inventory.fill(0.0)
            self.market_prices[:] = self.BASE_PRICES
            self.sell_orders.fill(0.0)
            self.buy_land_orders.fill(False)
            for i, s in enumerate(self.seeds):
                self.rng_states[i] = np.random.RandomState(int(s))
            self._pregenerate_noise_block()
                
        self.step_idx = 0
        self.day_idx = 0
        self.hour_idx = 0

    def step_vectorized(self):
        """Vectorized execution of 1 step across all N environments simultaneously."""
        # 0. Physical Pasture & Animal Deployment Progression
        # Pasture 1 constructed at Step 1
        if self.step_idx == 1:
            self.pastures_count += 1
        # Pasture 2 constructed at Step 260
        if self.step_idx == 260:
            self.pastures_count += 1
            
        # Animals placed by worker physical pickup-and-place script (Steps 2 - 8)
        if self.step_idx == 3:
            # First cow placed from shed to pasture
            self.active_cows = np.minimum(self.cows, 1)
        elif self.step_idx == 7:
            # Second cow placed from shed to pasture
            self.active_cows = np.minimum(self.cows, 2)
        elif self.step_idx == 8:
            # First sheep placed from shed to pasture
            self.active_sheep = np.minimum(self.sheep, 1)

        # 1. Biological Production Cycles
        # Milk production every 6 hours (Hours 0, 6, 12, 18) from PHYSICALLY PLACED active cows
        if self.step_idx % 6 == 0 and self.step_idx > 0:
            self.inventory[:, :, 5] += self.active_cows.astype(np.float32) * 1.0  # MILK
            
        # Wool production every 72 hours (3 days) from PHYSICALLY PLACED active sheep
        if self.step_idx % 72 == 0 and self.step_idx > 0:
            self.inventory[:, :, 6] += self.active_sheep.astype(np.float32) * 2.0  # WOOL
            
        # Daily Worker Wage deductions at Hour 23
        if self.hour_idx == 23:
            self.money -= (self.workers.astype(np.float32) * 10.0)
            
        # 2. Process Land Purchases
        for p in range(2):
            land_mask = self.buy_land_orders[:, p] & (self.money[:, p] >= 1000.0) & (self.land_count[:, p] == 4)
            self.money[land_mask, p] -= 1000.0
            self.land_count[land_mask, p] += 4
        self.buy_land_orders.fill(False)

        # 3. Vectorized Shared Market Order Book Clearing with Non-Linear Slippage
        # Aggregate total sell volume per commodity across both players: [N, 7]
        tot_vol = self.sell_orders[:, 0, :] + self.sell_orders[:, 1, :]
        
        # Power-law price slippage: min(0.30, 0.005 * V^0.75)
        slippage = np.minimum(0.30, 0.005 * np.power(tot_vol, 0.75))
        clearing_prices = np.maximum(1.0, self.market_prices * (1.0 - slippage))
        
        # Fills, Revenue, and Inventory Updates for both players
        for p in range(2):
            actual_qty = np.minimum(self.inventory[:, p, :], self.sell_orders[:, p, :])
            revenue = np.sum(actual_qty * clearing_prices, axis=-1)
            self.money[:, p] += revenue
            self.inventory[:, p, :] -= actual_qty
        self.sell_orders.fill(0.0)
        
        # 4. Vectorized Market Price Mean Reversion with Zero-Copy Slice
        noise = self.market_noise[self.step_idx]
        reversion = (self.BASE_PRICES - self.market_prices) * 0.015
        self.market_prices = np.maximum(1.0, self.market_prices + reversion + (self.BASE_PRICES * noise))
        
        self.step_idx += 1
        self.day_idx = self.step_idx // self.STEPS_PER_DAY
        self.hour_idx = self.step_idx % self.STEPS_PER_DAY
        done = (self.step_idx >= self.EPISODE_STEPS)
        return done

    def run_paired_batch(
        self,
        policy_cand: Callable[[Dict[str, np.ndarray], int], None],
        policy_base: Callable[[Dict[str, np.ndarray], int], None],
        seeds: List[int]
    ) -> Dict[str, Any]:
        """
        Executes paired simulation across all seeds simultaneously:
        - Match A: Player 0 = Candidate, Player 1 = Baseline
        - Match B: Player 0 = Baseline, Player 1 = Candidate (Seat Swap)
        Returns averaged MCV, win rate, delta, and tail p05 metrics.
        """
        N = len(seeds)
        # =========================================================================
        # MATCH A: Candidate = Player 0, Baseline = Player 1
        # =========================================================================
        self.reset(seeds)
        t0 = time.time()
        for step in range(self.EPISODE_STEPS):
            # Evaluate Candidate (Seat 0)
            state_p0 = {
                "step": self.step_idx, "day": self.day_idx, "hour": self.hour_idx,
                "money": self.money[:, 0], "land": self.land_count[:, 0],
                "inventory": self.inventory[:, 0, :], "market_prices": self.market_prices,
                "opp_money": self.money[:, 1], "opp_land": self.land_count[:, 1],
                "sell_orders": self.sell_orders[:, 0, :], "buy_land": self.buy_land_orders[:, 0]
            }
            policy_cand(state_p0, 0)
            
            # Evaluate Baseline (Seat 1)
            state_p1 = {
                "step": self.step_idx, "day": self.day_idx, "hour": self.hour_idx,
                "money": self.money[:, 1], "land": self.land_count[:, 1],
                "inventory": self.inventory[:, 1, :], "market_prices": self.market_prices,
                "opp_money": self.money[:, 0], "opp_land": self.land_count[:, 0],
                "sell_orders": self.sell_orders[:, 1, :], "buy_land": self.buy_land_orders[:, 1]
            }
            policy_base(state_p1, 1)
            
            self.step_vectorized()
            
        cand_mcv_a = self.money[:, 0].copy()
        base_mcv_a = self.money[:, 1].copy()

        # =========================================================================
        # MATCH B: Baseline = Player 0, Candidate = Player 1 (SEAT SWAPPED)
        # =========================================================================
        self.reset(seeds)
        for step in range(self.EPISODE_STEPS):
            # Evaluate Baseline (Seat 0)
            state_p0 = {
                "step": self.step_idx, "day": self.day_idx, "hour": self.hour_idx,
                "money": self.money[:, 0], "land": self.land_count[:, 0],
                "inventory": self.inventory[:, 0, :], "market_prices": self.market_prices,
                "opp_money": self.money[:, 1], "opp_land": self.land_count[:, 1],
                "sell_orders": self.sell_orders[:, 0, :], "buy_land": self.buy_land_orders[:, 0]
            }
            policy_base(state_p0, 0)
            
            # Evaluate Candidate (Seat 1)
            state_p1 = {
                "step": self.step_idx, "day": self.day_idx, "hour": self.hour_idx,
                "money": self.money[:, 1], "land": self.land_count[:, 1],
                "inventory": self.inventory[:, 1, :], "market_prices": self.market_prices,
                "opp_money": self.money[:, 0], "opp_land": self.land_count[:, 0],
                "sell_orders": self.sell_orders[:, 1, :], "buy_land": self.buy_land_orders[:, 1]
            }
            policy_cand(state_p1, 1)
            
            self.step_vectorized()
            
        base_mcv_b = self.money[:, 0].copy()
        cand_mcv_b = self.money[:, 1].copy()
        
        wall_time = time.time() - t0
        
        # Paired Metrics Computation
        cand_mcv_paired = (cand_mcv_a + cand_mcv_b) / 2.0
        base_mcv_paired = (base_mcv_a + base_mcv_b) / 2.0
        delta_mcv_paired = cand_mcv_paired - base_mcv_paired
        
        is_tie_a = np.isclose(cand_mcv_a, base_mcv_a, atol=1e-2)
        is_tie_b = np.isclose(cand_mcv_b, base_mcv_b, atol=1e-2)
        wins_a = (cand_mcv_a > (base_mcv_a + 1e-2)).astype(np.float32) + 0.5 * is_tie_a.astype(np.float32)
        wins_b = (cand_mcv_b > (base_mcv_b + 1e-2)).astype(np.float32) + 0.5 * is_tie_b.astype(np.float32)
        paired_wr = float(np.mean((wins_a + wins_b) / 2.0))
        
        total_steps = N * 2 * self.EPISODE_STEPS
        steps_per_sec = total_steps / wall_time
        paired_matches_per_sec = N / wall_time
        
        return {
            "batch_size_seeds": N,
            "total_matches": N * 2,
            "wall_time_seconds": round(wall_time, 4),
            "throughput_steps_per_sec": round(steps_per_sec, 0),
            "throughput_paired_matches_per_sec": round(paired_matches_per_sec, 1),
            "paired_win_rate": round(paired_wr, 4),
            "mean_cand_mcv": round(float(np.mean(cand_mcv_paired)), 2),
            "mean_base_mcv": round(float(np.mean(base_mcv_paired)), 2),
            "delta_mean_mcv": round(float(np.mean(delta_mcv_paired)), 2),
            "median_cand_mcv": round(float(np.median(cand_mcv_paired)), 2),
            "p05_cand_mcv": round(float(np.percentile(cand_mcv_paired, 5)), 2),
            "p05_base_mcv": round(float(np.percentile(base_mcv_paired, 5)), 2),
            "p01_cand_mcv": round(float(np.percentile(cand_mcv_paired, 1)), 2),
            "cand_mcv_a_mean": round(float(np.mean(cand_mcv_a)), 2),
            "cand_mcv_b_mean": round(float(np.mean(cand_mcv_b)), 2)
        }
