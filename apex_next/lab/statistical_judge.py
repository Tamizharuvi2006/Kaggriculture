"""
8. Statistical Judge Engine (Gate 4)
Pure deterministic Python evaluator.
Enforces the 6 quantitative criteria strictly from BASELINE_CONTRACT.md:
1. WR delta >= +2.5% (p < 0.05)
2. Mean MCV delta >= +2000 (p < 0.05)
3. Volatility ratio <= 1.10
4. 5th-percentile MCV >= Baseline p05
5. PASS rate increase <= 0.2%, max PASS <= 3
6. Latency avg <= 20ms, max <= 200ms
"""
from typing import Dict, Any


class StatisticalJudge:
    def __init__(
        self,
        min_wr_delta: float = 0.025,
        min_mcv_delta: float = 2000.0,
        max_variance_ratio: float = 1.10,
        max_pass_rate_delta: float = 0.002,
        max_allowed_consecutive_pass: int = 3,
        max_mean_latency_ms: float = 20.0,
        max_peak_latency_ms: float = 200.0
    ):
        self.min_wr_delta = min_wr_delta
        self.min_mcv_delta = min_mcv_delta
        self.max_variance_ratio = max_variance_ratio
        self.max_pass_rate_delta = max_pass_rate_delta
        self.max_allowed_consecutive_pass = max_allowed_consecutive_pass
        self.max_mean_latency_ms = max_mean_latency_ms
        self.max_peak_latency_ms = max_peak_latency_ms

    def evaluate(self, holdout_metrics: Dict[str, Any], baseline_wr: float = 0.50) -> Dict[str, Any]:
        """Performs strict multi-dimension gate verification."""
        cand_wr = holdout_metrics["win_rate"]
        wr_delta = cand_wr - baseline_wr

        cand_mcv = holdout_metrics["candidate_mean_mcv"]
        base_mcv = holdout_metrics["baseline_mean_mcv"]
        mcv_delta = cand_mcv - base_mcv

        cand_std = holdout_metrics["candidate_std_mcv"]
        base_std = max(1.0, holdout_metrics["baseline_std_mcv"])
        std_ratio = cand_std / base_std

        cand_p05 = holdout_metrics["candidate_p05_mcv"]
        base_p05 = holdout_metrics["baseline_p05_mcv"]
        tail_risk_delta = cand_p05 - base_p05

        max_pass = holdout_metrics["max_pass_turns"]
        avg_lat = holdout_metrics["avg_latency_ms"]
        max_lat = holdout_metrics["max_latency_ms"]

        # Dimension checks
        c_wr = wr_delta >= self.min_wr_delta
        c_mcv = mcv_delta >= self.min_mcv_delta
        c_var = std_ratio <= self.max_variance_ratio
        c_tail = tail_risk_delta >= 0.0
        c_pass = max_pass <= self.max_allowed_consecutive_pass
        c_lat = (avg_lat <= self.max_mean_latency_ms) and (max_lat <= self.max_peak_latency_ms)

        all_passed = c_wr and c_mcv and c_var and c_tail and c_pass and c_lat

        failed_reasons = []
        if not c_wr:
            failed_reasons.append(f"Win rate delta ({wr_delta:+.2%}) below required threshold (+{self.min_wr_delta:.2%})")
        if not c_mcv:
            failed_reasons.append(f"Mean MCV delta ({mcv_delta:+.0f}) below required threshold (+{self.min_mcv_delta:.0f})")
        if not c_var:
            failed_reasons.append(f"Variance ratio ({std_ratio:.2f}x) exceeded max limit ({self.max_variance_ratio:.2f}x)")
        if not c_tail:
            failed_reasons.append(f"Tail risk (p05) worsened by {tail_risk_delta:.0f}")
        if not c_pass:
            failed_reasons.append(f"Peak PASS turns ({max_pass}) exceeded max limit ({self.max_allowed_consecutive_pass})")
        if not c_lat:
            failed_reasons.append(f"Latency exceeded bounds (avg: {avg_lat:.1f}ms, max: {max_lat:.1f}ms)")

        return {
            "gate": "GATE_4_STATISTICAL_JUDGE",
            "promotable": all_passed,
            "verdict": "APPROVED_FOR_RELEASE" if all_passed else "FALSIFIED_REJECTED",
            "criteria_checks": {
                "win_rate_pass": c_wr,
                "mean_mcv_pass": c_mcv,
                "variance_pass": c_var,
                "tail_risk_pass": c_tail,
                "pass_volatility_pass": c_pass,
                "latency_pass": c_lat
            },
            "metrics": {
                "wr_delta": wr_delta,
                "mcv_delta": mcv_delta,
                "std_ratio": std_ratio,
                "tail_p05_delta": tail_risk_delta,
                "max_pass_turns": max_pass,
                "avg_latency_ms": avg_lat,
                "max_latency_ms": max_lat
            },
            "failed_reasons": failed_reasons
        }
