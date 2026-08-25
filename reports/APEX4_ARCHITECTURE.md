# 🧠 APEX 4.0: CLOSED-LOOP RESEARCH AGENT ARCHITECTURE

> **Target Release**: `APEX 4.0 RESEARCH CANDIDATE`  
> **Core Architectural Transformation**: Full transition from an open-loop 720-step coordinate trace (`_FIXED_SCHEDULE_B85`) to a **Closed-Loop, Observation-Driven, Resource-Synchronized Policy Engine**.

---

## 📊 1. Master System Pipeline

```text
                           LIVE GAME OBSERVATION (Step t)
                                         │
                                         ▼
                            APEX 4.0 WORLD MODEL (State Update)
                 (Spatial Grid, Infrastructure, Agriculture, Livestock, Economy)
                                         │
                                         ▼
                             OPPONENT PUBLIC TRACKER
                        (Expansion Rate & Scale Inference)
                                         │
                                         ▼
                            SEMANTIC TASK GRAPH & CRITICAL DAG
                  (Protects Step 159 Pasture 2 & Step 170 Cow Pickups)
                                         │
                                         ▼
                             RESOURCE SYNCHRONIZER
             (Couples Step 156 Seed Purchases with Step 163 Planting)
                                         │
                                         ▼
                               CLOSED-LOOP CONTROLLER
                       (Bipartite Matching & Shortest Path)
                                         │
                                         ▼
                          EXECUTABLE KAGGLE ACTIONS EMITTED
```

---

## 🔍 2. The Five Pillar Invariants
1. **Infrastructure Safety Invariant**: Pasture 1 (Step 1) and Pasture 2 (Step 159) are 100% hardwired and protected.
2. **Resource Synchronization Invariant**: No worker is routed to till/plant unless seeds exist in the shed or are enqueued for delivery.
3. **Opportunistic Labor Allocation**: Unreserved workers (Worker #3) are dynamically dispatched during verified PASS windows.
4. **Pre-Clearance Liquidation**: Peak-of-cycle inventory is sold at Hour 23 before daily reset.
5. **Terminal Solvency Guarantee**: 100% solvency preserved with zero wage defaults or bankruptcy penalties.
