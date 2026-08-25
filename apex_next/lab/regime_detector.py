"""
13. Market Regime Detector
Classifies the match economy into concrete market regimes and measures the
champion's (and candidate's) win rate per regime. This replaces "APEX loses"
with "APEX loses specifically during liquidity shocks" -- the actionable form.

Consumes the REAL telemetry formats:
  - mcv_replay_dataset.json rows: {file, player_idx, step, day, cash,
    market_prices: {PRODUCT: price}, executed_market_action, final_wealth,
    won_match}
  - Kaggle episode JSONs (reports/live_match_telemetry/submission_*.json):
    {episodes: [{agents: [{submissionId, reward, index}], ...}]}

Regimes:
    STABLE            - prices inside normal band, low volatility
    INFLATION         - sustained upward price drift
    LIQUIDITY_SHOCK   - fast collapse of a commodity price / cash crunch
    DEMAND_SPIKE      - rapid price surge of a sellable product
    SUPPLY_COLLAPSE   - one product supply saturates and price crashes to floor
    OPPONENT_PRESSURE - opponent dumps inventory into our price bands
"""
import json
import os
import numpy as np
from typing import Dict, Any, List, Optional

# Products whose price dynamics define the competitive economy (MILK/WOOL are
# livestock revenue, STRAWBERRY/MELON are the crop pipeline, WHEAT is the
# cash-flow cycle). FERTILIZER is an input cost, not a sellable.
DECISIVE_PRODUCTS = ("MILK", "WOOL", "STRAWBERRY", "MELON", "TOMATO", "CARROT", "WHEAT")


class RegimeDetector:
    REGIMES = ["STABLE", "INFLATION", "LIQUIDITY_SHOCK", "DEMAND_SPIKE",
               "SUPPLY_COLLAPSE", "OPPONENT_PRESSURE"]

    # Deterministic thresholds
    PRICE_VOL_SINGLE_STEP = 0.08          # |p(t) - p(t-1)| / p(t-1) crossing = event
    SPIKE_DRIFT_THRESHOLD = 0.30          # cumulative 3-step drift for spike/collapse
    INFLATION_MIN_DRIFT = 0.20            # cumulative drift over the window
    LIQUIDITY_CASH_FLOOR = 150            # cash reserve collapse line (contract)
    LIQUIDITY_ZERO_CASH = 0.0             # absolute cash exhaustion line
    LIQUIDITY_PRICE_COLLAPSE = -0.15      # 3-step price drop needed with zero cash
    MIN_STEPS = 12                        # minimum trajectory length to classify

    def classify_series(self, price_series: List[float], cash_series: List[float] = None) -> Dict[str, Any]:
        """
        price_series: per-step price observations for a single product.
        cash_series : optional per-step cash reserve observations.
        Returns a single regime label plus the evidence used.
        """
        prices = np.asarray([float(p) for p in price_series if p is not None], dtype=float)
        if prices.size < 3:
            return {"regime": "STABLE", "evidence": {}, "reason": "Insufficient price history."}

        # Normalize to relative moves
        rel = np.diff(prices) / np.maximum(np.abs(prices[:-1]), 1e-9)

        # 1. Liquidity shock: real cash exhaustion that coincides with a price
        #    collapse. Zero cash is the NORM for this reinvestment strategy
        #    (median min-cash ~$10 in the 86-trajectory population), so cash
        #    alone cannot discriminate -- it needs the price crash context.
        if cash_series is not None:
            min_cash = float(min(cash_series))
            if min_cash <= self.LIQUIDITY_ZERO_CASH:
                for i in range(len(rel) - 2):
                    window = rel[i:i + 3].sum()
                    if window <= self.LIQUIDITY_PRICE_COLLAPSE:
                        return {"regime": "LIQUIDITY_SHOCK",
                                "evidence": {"min_cash": min_cash, "price_collapse": round(float(window), 4), "step": i},
                                "reason": f"Cash exhausted (${min_cash:.0f}) while price collapsed -{abs(window):.0%} over 3 steps."}

        # 2. Demand spike / supply collapse: 3-step directional event
        for i in range(len(rel) - 2):
            window = rel[i:i + 3].sum()
            if window >= self.SPIKE_DRIFT_THRESHOLD:
                return {"regime": "DEMAND_SPIKE",
                        "evidence": {"drift": round(float(window), 4), "step": i},
                        "reason": f"Price surged +{window:.0%} over 3 steps."}
            if window <= -self.SPIKE_DRIFT_THRESHOLD:
                return {"regime": "SUPPLY_COLLAPSE",
                        "evidence": {"drift": round(float(window), 4), "step": i},
                        "reason": f"Price collapsed -{abs(window):.0%} over 3 steps."}

        # 3. Sustained inflation: total drift over the window
        total_drift = (prices[-1] - prices[0]) / max(abs(prices[0]), 1e-9)
        if total_drift >= self.INFLATION_MIN_DRIFT:
            return {"regime": "INFLATION",
                    "evidence": {"total_drift": round(float(total_drift), 4)},
                    "reason": f"Market drifted +{total_drift:.0%} across the window."}

        # 4. Opponent pressure: high single-step volatility without direction
        max_abs_step = float(np.max(np.abs(rel)))
        if max_abs_step >= self.PRICE_VOL_SINGLE_STEP:
            return {"regime": "OPPONENT_PRESSURE",
                    "evidence": {"max_single_step": round(max_abs_step, 4)},
                    "reason": "High-frequency two-sided price churn, consistent with dumping."}

        return {"regime": "STABLE",
                "evidence": {"max_single_step": round(max_abs_step, 4), "total_drift": round(float(total_drift), 4)},
                "reason": "Prices inside normal band with low volatility."}

    def classify_trajectory(self, trajectory_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Classifies a REAL full-trajectory telemetry stream (mcv_replay_dataset
        rows for one (file, player_idx)). Builds per-product price series and
        cash series from the real fields, classifies each decisive product,
        and returns the dominant (highest-severity) regime with evidence.
        """
        if not trajectory_rows:
            return {"regime": "STABLE", "evidence": {}, "reason": "Empty trajectory."}

        rows = sorted(trajectory_rows, key=lambda r: r.get("step", 0))
        if len(rows) < self.MIN_STEPS:
            return {"regime": "STABLE", "evidence": {},
                    "reason": f"Trajectory too short ({len(rows)} steps < {self.MIN_STEPS})."}

        cash_series = [r.get("cash", 0.0) for r in rows]

        per_product = {}
        for product in DECISIVE_PRODUCTS:
            series = []
            present = False
            for r in rows:
                prices = r.get("market_prices") or {}
                if product in prices:
                    series.append(prices[product])
                    present = True
                elif series:
                    series.append(series[-1])  # carry forward within same trajectory
            if present and len(series) >= 3:
                per_product[product] = self.classify_series(series, cash_series)

        if not per_product:
            return {"regime": "STABLE", "evidence": {}, "reason": "No decisive product price history."}

        # Dominant regime = highest severity ordering: liquidity/volatility
        # events outrank drift, drift outranks stability.
        severity = {"LIQUIDITY_SHOCK": 5, "DEMAND_SPIKE": 4, "SUPPLY_COLLAPSE": 4,
                    "OPPONENT_PRESSURE": 3, "INFLATION": 2, "STABLE": 1}

        ranked = sorted(per_product.items(),
                        key=lambda kv: (severity.get(kv[1]["regime"], 1), len(kv[0])),
                        reverse=True)
        product, classification = ranked[0]

        return {
            "regime": classification["regime"],
            "product": product,
            "evidence": classification["evidence"],
            "reason": f"{product}: {classification['reason']}",
            "per_product": {p: c["regime"] for p, c in per_product.items()}
        }

    def evaluate_by_regime(self, dataset_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        REAL population evaluation: groups mcv_replay_dataset rows by
        (file, player_idx), classifies each trajectory, and computes win rate,
        mean MCV, and p05 tail per regime -- the actionable weakness map.
        """
        trajectories: Dict[tuple, List[Dict[str, Any]]] = {}
        for row in dataset_rows:
            key = (row.get("file"), row.get("player_idx"))
            trajectories.setdefault(key, []).append(row)

        buckets = {regime: {"wins": 0, "losses": 0, "mcvs": []} for regime in self.REGIMES}
        classified = []

        for (filepath, player_idx), rows in trajectories.items():
            classification = self.classify_trajectory(rows)
            regime = classification["regime"]
            final_wealth = rows[-1].get("final_wealth", 0.0)
            won = bool(rows[-1].get("won_match", False))

            bucket = buckets.setdefault(regime, {"wins": 0, "losses": 0, "mcvs": []})
            bucket["wins"] += int(won)
            bucket["losses"] += int(not won)
            bucket["mcvs"].append(final_wealth)
            classified.append({
                "file": filepath,
                "player_idx": player_idx,
                "regime": regime,
                "product": classification.get("product"),
                "won_match": won,
                "final_wealth": final_wealth
            })

        regime_stats = {}
        for regime, bucket in buckets.items():
            n = bucket["wins"] + bucket["losses"]
            if n == 0:
                regime_stats[regime] = {"matches": 0}
                continue
            arr = np.asarray(bucket["mcvs"], dtype=float)
            regime_stats[regime] = {
                "matches": n,
                "win_rate": round(bucket["wins"] / n, 4),
                "mean_mcv": round(float(np.mean(arr)), 1),
                "p05_mcv": round(float(np.percentile(arr, 5)), 1)
            }

        weakest = min(
            ((r, s) for r, s in regime_stats.items() if s.get("matches", 0) >= 3),
            key=lambda rs: rs[1]["win_rate"],
            default=(None, None)
        )

        return {
            "total_trajectories": len(trajectories),
            "by_regime": regime_stats,
            "classified": classified,
            "weakest_regime": weakest[0] if weakest[0] else None,
            "weakest_win_rate": weakest[1]["win_rate"] if weakest[1] else None,
            "diagnosis": f"Agent is weakest during {weakest[0] or 'n/a'} "
                         f"({weakest[1]['win_rate']:.0%} WR over {weakest[1]['matches']} matches)."
        }

    def load_real_dataset(self, dataset_path: str = "data/replay/mcv_replay_dataset.json") -> List[Dict[str, Any]]:
        """Loads the real per-step replay dataset used by the research pipeline."""
        if not os.path.exists(dataset_path):
            return []
        with open(dataset_path, "r", encoding="utf-8") as f:
            return json.load(f)


if __name__ == "__main__":
    detector = RegimeDetector()
    real_rows = detector.load_real_dataset()
    if real_rows:
        result = detector.evaluate_by_regime(real_rows)
        print(f"Real population: {result['total_trajectories']} trajectories")
        for regime, stats in result["by_regime"].items():
            print(f"  {regime:<20} {stats}")
        print("Weakest regime:", result["weakest_regime"], result["diagnosis"])
    else:
        print("data/replay/mcv_replay_dataset.json not found; running fixture fallback.")
        fake_trajectory = [
            {"step": s, "cash": 500 - 30 * s, "market_prices": {"MILK": 160 - 4 * s}, "final_wealth": 0, "won_match": False}
            for s in range(20)
        ]
        print("Trajectory regime:", detector.classify_trajectory(fake_trajectory)["regime"])
