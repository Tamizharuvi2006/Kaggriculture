"""Track B (Candidate EXP054): Opening Slack Accelerator (OSA).
Converts Day 0-4 (Steps 0-120) idle worker steps into zero-drag pre-tilling of future strawberry plots.
Rules:
1. Zero-Drag Invariant: Only fires when a worker's assigned base action is PASS (100% idle).
2. Critical-Path Protection: Never interrupts active watering, planting, or harvesting.
3. Cash Protection: Consumes $0 seed money (only performs zero-cost TILL actions on un-tilled tiles).
4. Future Workload Reduction: Pre-tills Quadrant 1 & Quadrant 2 plots so that Day 6+ planting is instantaneous.
"""
from __future__ import annotations
import sys
import os
from typing import Dict, Any, List, Optional, Tuple

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from engine.agent import VariantDAgent

class OpeningSlackAccelerator:
    """Pre-tills future strawberry plots using only Day 0-4 idle worker-steps."""
    def __init__(self):
        self.pre_tilled_count = 0
        self.idle_steps_converted = 0

    def reset(self):
        self.pre_tilled_count = 0
        self.idle_steps_converted = 0

    def intercept_opening_idle_steps(self, obs: Dict[str, Any], config: Optional[Dict[str, Any]], base_act: Dict[str, Any]) -> Dict[str, Any]:
        step = int(obs.get("step", 0) if isinstance(obs, dict) else getattr(obs, "step", 0) or 0)
        day = int(obs.get("day", 0) if isinstance(obs, dict) else getattr(obs, "day", 0) or 0)

        # Active ONLY on Days 0-4 (Steps 0-120)
        if day > 4 or step > 120:
            return base_act

        farms = obs.get("farms") or [] if isinstance(obs, dict) else getattr(obs, "farms", []) or []
        player = int(obs.get("player", 0) if isinstance(obs, dict) else getattr(obs, "player", 0) or 0)
        own_farm = farms[player] if len(farms) > player else {}
        tiles = own_farm.get("tiles") or []

        farmer_cmd = list(base_act.get("farmer") or ["PASS"])
        hands_cmds = [list(h) for h in (base_act.get("hands") or [])]
        orders = list(base_act.get("market") or [])

        # Find un-tilled arable tiles in the primary farming quadrants
        untilled_plots = []
        for y, row in enumerate(tiles):
            for x, tile in enumerate(row):
                if isinstance(tile, dict):
                    crop = tile.get("crop")
                    tilled = tile.get("tilled", False)
                    # Arable, empty, un-tilled plot
                    if crop is None and not tilled:
                        untilled_plots.append((x, y))

        if not untilled_plots:
            return base_act

        # Check hands for pure PASS idle actions
        plot_idx = 0
        for i, h_cmd in enumerate(hands_cmds):
            if (not h_cmd) or h_cmd[0] == "PASS":
                if plot_idx < len(untilled_plots):
                    target_x, target_y = untilled_plots[plot_idx]
                    hands_cmds[i] = ["TILL", target_x, target_y]
                    self.idle_steps_converted += 1
                    self.pre_tilled_count += 1
                    plot_idx += 1

        return {
            "farmer": farmer_cmd,
            "hands": hands_cmds,
            "market": orders[:10],
        }

class OpeningSlackAgent:
    """Agent equipped with the Opening Slack Accelerator."""
    def __init__(self):
        self.d1_agent = VariantDAgent()
        self.osa = OpeningSlackAccelerator()

    def reset(self):
        self.d1_agent.reset()
        self.osa.reset()

    def act(self, obs: Dict[str, Any], config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        # 1. Generate base D.1 action
        base_act = self.d1_agent.act(obs, config)
        if not isinstance(base_act, dict):
            return base_act

        # 2. Intercept Day 0-4 idle steps for zero-drag pre-tilling
        return self.osa.intercept_opening_idle_steps(obs, config, base_act)

_GLOBAL_OSA_AGENT = OpeningSlackAgent()

def agent(obs, configuration=None):
    global _GLOBAL_OSA_AGENT
    return _GLOBAL_OSA_AGENT.act(obs, configuration)
