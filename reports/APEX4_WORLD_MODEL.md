# 🌐 APEX 4.0: WORLD MODEL SPECIFICATION

> **Module**: `apex_next/apex4/world_model/world_model.py`  
> **Role**: Live Observation-Driven State Estimator

---

## 📋 State Subsystems
1. **Spatial Subsystem**: Tracks coordinates $(r, c)$ of all 8 workers and farmer, calculating Manhattan distance matrices to all active target tiles.
2. **Infrastructure Subsystem**: Tracks unlocked quadrants (`[0]`, `[0, 2]`), pasture construction status, animal capacity limits, and fence perimeters.
3. **Agricultural Subsystem**: Tracks crop species, growth stage (`SEED`, `GROWING`, `RIPE`), soil moisture (`needs_water`), and maturity deadlines.
4. **Livestock Subsystem**: Tracks animal counts (`COW`, `SHEEP`), feeding history, pasture placements, and milk/wool accumulation cycles.
5. **Economic Subsystem**: Tracks available cash, shed inventory balances, spot market prices, and pending order book commitments.
6. **Public Opponent Subsystem**: Tracks publicly visible opponent cash, unlocked quadrants, crop tiles, and active livestock.
