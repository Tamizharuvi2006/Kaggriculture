"""
15. Regression Sentinel
Watches the first N live matches after a new champion goes live and compares
them against the previous champion's expectations. It never auto-reverts on a
tiny sample: it uses a predefined emergency threshold AND a minimum sample
size. Its output is a recommendation consumed by the deterministic release
controller -- the sentinel itself has no write authority.

States:
    NORMAL       - live performance within expected band
    SUSPICIOUS   - performance drifting below expectation, keep watching
    REGRESSION   - emergency threshold breached at/after the minimum sample
    FREEZE       - sustained regression; recommend fallback to previous champion
"""
import numpy as np
from typing import Dict, Any, List


class RegressionSentinel:
    def __init__(
        self,
        expected_wr: float,
        expected_mean_mcv: float,
        expected_std_mcv: float,
        min_sample_size: int = 20,
        wr_emergency_delta: float = -0.15,
        mcv_emergency_delta: float = -12000.0,
        suspicious_z: float = 1.5,
        regression_streak: int = 3
    ):
        self.expected_wr = expected_wr
        self.expected_mean_mcv = expected_mean_mcv
        self.expected_std_mcv = expected_std_mcv
        self.min_sample_size = min_sample_size
        self.wr_emergency_delta = wr_emergency_delta
        self.mcv_emergency_delta = mcv_emergency_delta
        self.suspicious_z = suspicious_z
        self.regression_streak = regression_streak
        self._observed_wr = []
        self._observed_mcvs = []

    def observe(self, result: str, our_mcv: float) -> None:
        """Feeds one live match into the sentinel. WIN/LOSS plus final MCV."""
        self._observed_wr.append(1.0 if result == "WIN" else 0.0)
        self._observed_mcvs.append(float(our_mcv))

    def _z_score(self) -> float:
        if not self._observed_mcvs:
            return 0.0
        arr = np.asarray(self._observed_mcvs)
        se = self.expected_std_mcv / np.sqrt(len(arr))
        if se <= 0:
            return 0.0
        return float((np.mean(arr) - self.expected_mean_mcv) / se)

    def evaluate(self) -> Dict[str, Any]:
        """Deterministic state machine evaluation based on accumulated evidence."""
        n = len(self._observed_wr)
        if n == 0:
            return {"state": "NORMAL", "matches_observed": 0,
                    "note": "No live matches observed yet."}

        live_wr = np.mean(self._observed_wr)
        live_mcv = np.mean(self._observed_mcvs)
        z = self._z_score()

        wr_delta = live_wr - self.expected_wr
        mcv_delta = live_mcv - self.expected_mean_mcv

        emergency_breached = (
            wr_delta <= self.wr_emergency_delta or mcv_delta <= self.mcv_emergency_delta
        )

        # Below minimum sample: never classify as REGRESSION or FREEZE.
        if n < self.min_sample_size:
            state = "SUSPICIOUS" if emergency_breached else "NORMAL"
            return {
                "state": state,
                "matches_observed": n,
                "min_sample_size": self.min_sample_size,
                "live_wr": round(float(live_wr), 4),
                "live_mean_mcv": round(float(live_mcv), 1),
                "wr_delta": round(float(wr_delta), 4),
                "mcv_delta": round(float(mcv_delta), 1),
                "z_score": round(z, 2),
                "emergency_breached": emergency_breached,
                "recommendation": "CONTINUE_OBSERVING" if not emergency_breached else "ESCALATE_TO_SUSPICIOUS",
                "note": "Sample below minimum; no reversion decision allowed."
            }

        # At or above minimum sample: emergency breach means REGRESSION.
        if emergency_breached:
            return {
                "state": "REGRESSION",
                "matches_observed": n,
                "min_sample_size": self.min_sample_size,
                "live_wr": round(float(live_wr), 4),
                "live_mean_mcv": round(float(live_mcv), 1),
                "wr_delta": round(float(wr_delta), 4),
                "mcv_delta": round(float(mcv_delta), 1),
                "z_score": round(z, 2),
                "emergency_breached": True,
                "recommendation": "FREEZE_AND_EVALUATE_FALLBACK",
                "note": "Emergency threshold breached at minimum sample. Release controller should prepare fallback."
            }

        # Drift without emergency breach: statistical deviation check.
        if z <= -self.suspicious_z:
            return {
                "state": "SUSPICIOUS",
                "matches_observed": n,
                "min_sample_size": self.min_sample_size,
                "live_wr": round(float(live_wr), 4),
                "live_mean_mcv": round(float(live_mcv), 1),
                "wr_delta": round(float(wr_delta), 4),
                "mcv_delta": round(float(mcv_delta), 1),
                "z_score": round(z, 2),
                "emergency_breached": False,
                "recommendation": "CONTINUE_OBSERVING",
                "note": "Statistically suspicious drift. No action yet; keep sampling."
            }

        return {
            "state": "NORMAL",
            "matches_observed": n,
            "min_sample_size": self.min_sample_size,
            "live_wr": round(float(live_wr), 4),
            "live_mean_mcv": round(float(live_mcv), 1),
            "wr_delta": round(float(wr_delta), 4),
            "mcv_delta": round(float(mcv_delta), 1),
            "z_score": round(z, 2),
            "emergency_breached": False,
            "recommendation": "CONTINUE_NORMAL",
            "note": "Performance within expected band."
        }


if __name__ == "__main__":
    sentinel = RegressionSentinel(expected_wr=0.79, expected_mean_mcv=142850.0, expected_std_mcv=22000.0)
    for i in range(25):
        sentinel.observe("WIN" if i % 3 else "LOSS", 110000.0 if i % 3 == 0 else 145000.0)
    print("Sentinel state:", sentinel.evaluate()["state"])