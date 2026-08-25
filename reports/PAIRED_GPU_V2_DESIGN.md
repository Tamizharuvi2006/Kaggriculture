# ⚡ PAIRED_GPU_V2: PAIRED ACCELERATOR ARCHITECTURE & DESIGN SPECIFICATION

> **Purpose**: Transform the GPU screening engine from an isolated solo simulator into a **paired 2-player co-simulation accelerator** that accurately reproduces competitive ladder dynamics against the frozen `APEX-3.5-PROD` champion.  
> **Authority Contract**: PAIRED_GPU_V2 is strictly a **search accelerator**. The official `kaggle_environments v1.32.6` reference runner remains the sole authority for promotion gates.

---

## 🏛️ Core Architecture Principles

```
                       [RESEARCH CANDIDATE]
                                │
                                ▼
         ┌─────────────────────────────────────────────┐
         │       PAIRED_GPU_V2 SIMULATION ENGINE       │
         │                                             │
         │  ┌─────────────────┐   ┌─────────────────┐  │
         │  │   Candidate     │   │  APEX 3.5 (PROD)│  │
         │  │   (Player 0)    │   │   (Player 1)    │  │
         │  └────────┬────────┘   └────────┬────────┘  │
         │           │                     │           │
         │           ▼                     ▼           │
         │   [SHARED IN-MEMORY 10x10 GAME STATE]       │
         │   [SHARED MARKET ORDER BOOK & SLIPPAGE]     │
         │                                             │
         │   • Seed S: Match 0 (Cand=0, Base=1)        │
         │   • Seed S: Match 1 (Base=0, Cand=1)        │
         └──────────────────────┬──────────────────────┘
                                │
                                ▼
                [PAIRED STATISTICAL EVALUATION]
                                │
               Cleared WR >= 55% & Delta MCV > 0?
                     ┌──────────┴──────────┐
                    YES                    NO
                     │                      │
                     ▼                      ▼
           [OFFICIAL REFERENCE]         [HALT / FALSIFY]
           kaggle_environments
            Gate 1 -> 2 -> 3 -> 4
```

---

## 🔑 Key Engineering Specifications

### 1. 🪞 Paired Co-Simulation & Seat Swapping
* For every screening seed $s$, execute **exactly two matches**:
  * Match A: `Player 0 = Candidate`, `Player 1 = Baseline (APEX 3.5)`
  * Match B: `Player 0 = Baseline (APEX 3.5)`, `Player 1 = Candidate`
* Compute paired win score:
  $$	ext{Score}(s) = egin{cases} 1.0 & 	ext{if Candidate wins both seats} \ 0.5 & 	ext{if Candidate splits 1-1} \ 0.0 & 	ext{if Candidate loses both seats} \end{cases}$$
* **Invariant**: Completely eliminates first-mover seat bias.

### 2. 📉 Shared Market Order Book with Price Slippage
* Both agents submit market orders into the **same town market engine**.
* Aggregate order volume $V = V_{	ext{cand}} + V_{	ext{base}}$ determines execution price:
  $$P_{	ext{fill}}(p) = P_{	ext{market}}(p) \cdot \left(1.0 - \kappa \cdot V^{\gamma}ight)$$
* Eliminates the "solo-engine illusion" where candidates assume infinite liquidity at peak prices.

### 3. 🎯 Validated Multi-Objective Screening Score
To prevent optimizing arbitrary synthetic metrics, screening ranking follows a **gated hierarchy**:
1. **Primary Gate**: Paired Win Rate $	ext{WR}_{	ext{paired}} \ge 55.0\%$ (Must beat Baseline head-to-head).
2. **Secondary Gate**: Mean MCV Lift $\Delta\mu_{	ext{MCV}} \ge +\$1{,}000$.
3. **Tertiary Gate**: Downside Tail $\Delta p05 \ge \$0.00$.
4. **Guardrail Penalty**: Any excess PASS turns ($\Delta	ext{PASS} > 0$) or life-support failure triggers immediate disqualification.

---

## 🚫 Explicit Limitations & Boundaries
1. **Never a Second Source of Truth**: Candidate promotion to production is **strictly prohibited** on GPU screening alone.
2. **Deterministic Parity Wall**: If a candidate achieves $	ext{WR} \ge 55\%$ in PAIRED_GPU_V2, it must immediately undergo **Gate 1 Exact Replay on `kaggle_environments v1.32.6`** before any subsequent gate.
