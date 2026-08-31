"""
EXP203.5 — Vectorized GPU Full-Game Resident Simulator Prototype (NVIDIA RTX 4050).
Simulates N complete 720-step 2-player Kaggriculture matches entirely in GPU VRAM
without any per-step host-device synchronization.
"""

import os
import sys
import time
import numpy as np
import torch
import torch.nn.functional as F

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Product indices: 0: CARROT, 1: WHEAT, 2: TOMATO, 3: STRAWBERRY, 4: MELON, 5: EGG, 6: MILK, 7: WOOL, 8: FERTILIZER
BASE_PRICES = torch.tensor([30.0, 30.0, 50.0, 120.0, 250.0, 40.0, 160.0, 180.0, 80.0], dtype=torch.float32)

class GPUVectorizedGameEnv:
    def __init__(self, num_games=1000, device="cuda"):
        self.device = torch.device(device if torch.cuda.is_available() else "cpu")
        self.N = num_games
        
        # Allocate all game state tensors in GPU VRAM
        # Shape: [N, 2] for 2 players
        self.money = torch.full((self.N, 2), 3000.0, dtype=torch.float32, device=self.device)
        self.workers = torch.zeros((self.N, 2), dtype=torch.int32, device=self.device)
        self.unlocked_quads = torch.ones((self.N, 2), dtype=torch.int32, device=self.device) # 1 quadrant (25 tiles)
        
        # Shed Inventory: [N, 2, 9] products
        self.shed = torch.zeros((self.N, 2, 9), dtype=torch.int32, device=self.device)
        self.shed[:, :, 1] = 12 # 12 starter wheat feed
        
        # Animals: [N, 2] cows and sheep counts
        self.cows = torch.full((self.N, 2), 3, dtype=torch.int32, device=self.device)
        self.sheep = torch.zeros((self.N, 2), dtype=torch.int32, device=self.device)
        
        # Crop counts: [N, 2, 4] for Carrot, Wheat, Strawberry, Melon
        self.planted_crops = torch.zeros((self.N, 2, 4), dtype=torch.int32, device=self.device)
        self.planted_crops[:, :, 0] = 8 # 8 starter carrots
        
        # Market prices: [N, 9]
        self.prices = BASE_PRICES.unsqueeze(0).repeat(self.N, 1).to(self.device)
        
        self.step_idx = 0
        self.day = 0
        self.hour = 0

    def step(self):
        """Advances all N games by 1 step in parallel on GPU."""
        self.step_idx += 1
        self.hour = self.step_idx % 24
        self.day = self.step_idx // 24
        
        is_hour_0 = (self.hour == 0)
        
        # 1. Start-of-Day Economics (Hour 0)
        if is_hour_0:
            # Cow Production: 1 Milk + 1 Fertilizer per cow (if fed with wheat)
            has_wheat = (self.shed[:, :, 1] >= self.cows)
            fed_cows = torch.where(has_wheat, self.cows, torch.zeros_like(self.cows))
            self.shed[:, :, 1] -= fed_cows # Deduct wheat feed
            self.shed[:, :, 6] += fed_cows # Add Milk
            self.shed[:, :, 8] += fed_cows # Add Fertilizer
            
            # Sheep Production: 1 Wool per sheep (if Day >= 8)
            if self.day >= 8:
                self.shed[:, :, 7] += self.sheep
                
            # Worker Wages: $40/day per worker
            wage_costs = self.workers.float() * 40.0
            self.money -= wage_costs
            
        # 2. Automated Adaptive Strategy Rules (Native GPU Vectorized Dispatch)
        # Day 0-3: Harvest and sell carrots on Day 3
        if self.day == 3 and self.hour == 6:
            p_carrot = self.prices[:, 0].unsqueeze(1) # [N, 1]
            carrot_revenue = self.planted_crops[:, :, 0].float() * p_carrot * 3.0
            self.money += carrot_revenue
            self.planted_crops[:, :, 0] = 0
            
        # Day 6: Hire worker 1 if money >= 50
        if self.day == 6 and self.hour == 0:
            can_hire = (self.money >= 50.0) & (self.workers < 1)
            self.workers += can_hire.int()
            self.money -= torch.where(can_hire, 40.0, 0.0)
            
        # Day 8: Buy 4 Sheep if money >= 2400
        if self.day == 8 and self.hour == 4:
            can_buy_4_sheep = (self.money >= 2400.0)
            self.sheep += torch.where(can_buy_4_sheep, 4, 0)
            self.money -= torch.where(can_buy_4_sheep, 2400.0, 0.0)
            
        # Middle-to-Late Game Continuous Milk & Wool Liquidation (Days 8-29)
        if self.day >= 8 and self.hour % 6 == 0:
            # Liquidate accumulated Milk
            p_milk = self.prices[:, 6].unsqueeze(1)
            milk_qty = self.shed[:, :, 6].float()
            milk_rev = milk_qty * p_milk
            self.money += milk_rev
            self.shed[:, :, 6] = 0
            
            # Liquidate accumulated Wool
            p_wool = self.prices[:, 7].unsqueeze(1)
            wool_qty = self.shed[:, :, 7].float()
            wool_rev = wool_qty * p_wool
            self.money += wool_rev
            self.shed[:, :, 7] = 0
            
            # Liquidate accumulated Fertilizer
            p_fert = self.prices[:, 8].unsqueeze(1)
            fert_qty = self.shed[:, :, 8].float()
            fert_rev = fert_qty * p_fert
            self.money += fert_rev
            self.shed[:, :, 8] = 0

        # Late-Game Crop Cycles (Strawberries Days 10-29)
        if self.day >= 10 and is_hour_0:
            p_straw = self.prices[:, 3].unsqueeze(1)
            straw_revenue = 16.0 * p_straw * 1.5
            self.money += straw_revenue

        # End of Match (Step 720) - Liquidate everything
        if self.step_idx == 720:
            p_milk = self.prices[:, 6].unsqueeze(1)
            p_wool = self.prices[:, 7].unsqueeze(1)
            total_milk = self.shed[:, :, 6].float() * p_milk
            total_wool = self.shed[:, :, 7].float() * p_wool
            self.money += total_milk + total_wool


    def run_full_game(self):
        """Simulates all 720 steps entirely in GPU memory."""
        for _ in range(720):
            self.step()
        return self.money

def benchmark_gpu_resident_simulator():
    print("=" * 85)
    print("EXP203.5 -- GPU-RESIDENT VECTORIZED FULL-GAME SIMULATOR BENCHMARK (RTX 4050)")
    print("=" * 85)
    
    device_name = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU"
    print(f"Executing on device: {device_name}")
    
    test_scales = [1000, 10000, 100000]
    
    # Warmup
    warmup_env = GPUVectorizedGameEnv(num_games=500)
    _ = warmup_env.run_full_game()
    torch.cuda.synchronize()
    
    results = []
    
    for n_games in test_scales:
        torch.cuda.synchronize()
        t0 = time.perf_counter()
        
        env = GPUVectorizedGameEnv(num_games=n_games)
        final_money = env.run_full_game()
        
        torch.cuda.synchronize()
        elapsed_s = time.perf_counter() - t0
        
        matches_per_sec = n_games / elapsed_s
        steps_per_sec = (n_games * 720) / elapsed_s
        vram_mb = torch.cuda.memory_allocated() / (1024 * 1024)
        
        mean_p0_wealth = final_money[:, 0].mean().item()
        mean_p1_wealth = final_money[:, 1].mean().item()
        
        results.append({
            "num_games": n_games,
            "elapsed_s": elapsed_s,
            "matches_per_sec": matches_per_sec,
            "steps_per_sec": steps_per_sec,
            "vram_mb": vram_mb,
            "mean_wealth": mean_p0_wealth
        })
        
        print(f"Batch Scale: {n_games:>7,d} Matches | Time: {elapsed_s:6.3f}s | Throughput: {matches_per_sec:>9,.1f} matches/sec ({steps_per_sec:>12,.0f} steps/s) | VRAM: {vram_mb:5.1f} MB | Mean Wealth: ${mean_p0_wealth:>8,.1f}")
        
    print("=" * 85)
    return results

if __name__ == "__main__":
    benchmark_gpu_resident_simulator()
