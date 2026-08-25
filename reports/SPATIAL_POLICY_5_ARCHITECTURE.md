# 🧠 SPATIAL_POLICY-5: PURE CLOSED-LOOP RESEARCH ENGINE ARCHITECTURE

> **Core Objective**: Transition from fixed-schedule replay patching to a **Pure Closed-Loop Goal-Oriented Policy Engine**.  
> **Key Innovation**: Replaces `_FIXED_SCHEDULE_B85` as the execution master with an **Observation-Driven Task Dependency Graph**, while keeping critical infrastructure milestones (242 registered events) strictly protected.

---

## 📊 1. System Architecture Diagram

```text
                           LIVE GAME OBSERVATION (Step t)
                                         │
                                         ▼
                             DYNAMIC WORLD-STATE MODEL
               (Grid Tiles, Unlocked Quadrants, Ripe Crops, Animal Status)
                                         │
                                         ▼
                            SEMANTIC TASK GRAPH & PREREQUISITES
             ┌───────────────────────────┼───────────────────────────┐
             ▼                           ▼                           ▼
      Crop Lifecycle           Livestock Lifecycle          Capital & Land
    (Plant, Water, Harvest)    (Pasture, Feed, Milk)     (Land Unlock, Expansion)
             │                           │                           │
             └───────────────────────────┼───────────────────────────┘
                                         ▼
                            CRITICAL MILESTONE PROTECTOR
                    (Guarantees Step 159 Pasture 2 & Cow Pickups)
                                         │
                                         ▼
                              WORKER TASK ALLOCATOR
                      (Bipartite Matching & Shortest Path)
                                         │
                                         ▼
                            CLOSED-LOOP ACTIONS EMITTED
```

---

## 🔍 2. The Four Pillar Invariants
1. **Critical Infrastructure Invariant**: Pasture 2 construction (Step 159) and Cow Pickups (Step 170) are hardwired in `CRITICAL_TASK_REGISTRY` and can NEVER be preempted by farming tasks.
2. **Dynamic Opportunistic Cultivation**: Whenever new land is unlocked, unreserved workers immediately till and plant high-value crops without waiting for static schedule timing.
3. **Pre-Clearance Logistics**: Workers carrying ripe inventory execute `DROP` at Hour 22 to capture top-of-cycle commodity prices at Hour 23 clearance.
4. **Terminal Solvency Guarantee**: Feed purchases halt when shed reserves suffice, preserving cash capital into terminal valuation.
