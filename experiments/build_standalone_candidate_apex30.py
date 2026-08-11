"""Build Monolithic 100% Standalone APEX 3.0 Kaggle Submission Artifact.

Integrates:
1. Frozen L+ 4.1 Master Strategy Core (kaitofukami-v18.py)
2. WorldState & CashFlowState dynamic parsing
3. State-Conditioned Empirical MCV Evaluator (EmpiricalMarginalEvaluator)
4. ActionSafetyGate (Zero-Capital-Cost Curriculum Invariant)
5. ActionPlanner (Zero-Cost Sell Batch & Market Substitution)
6. CounterfactualSimulator & DivergenceController (Single-Deviation Policy)
7. Standalone Monolithic Execution Entrypoint (agent(obs, conf))

Outputs: generalization_pipeline/submission_candidate_apex30.py
"""

from __future__ import annotations
import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

V18_PATH = os.path.join(BASE_DIR, "baseline", "kaitofukami-v18.py")
OUT_PATH = os.path.join(BASE_DIR, "generalization_pipeline", "submission_candidate_apex30.py")

with open(V18_PATH, "r", encoding="utf-8") as f:
    v18_code = f.read()

# Rename base agent entrypoint in v18 code so APEX 3.0 wraps it as agent(obs, configuration)
v18_code = v18_code.replace("def agent(obs):", "def _base_agent(obs, configuration=None):")


# APEX 3.0 Standalone Runtime Addition
APEX_30_EMBEDDED_CODE = '''

# ====================================================================================================
# 🏛️ APEX 3.0 STANDALONE MONOLITHIC RUNTIME ENGINE (EMPIRICAL MCV EVALUATOR)
# ====================================================================================================

import math

class WorldState:

    def __init__(self, obs: dict):
        self.day = int(obs.get("day", 0))
        self.hour = int(obs.get("hour", 0))
        self.step = int(obs.get("step", self.day * 24 + self.hour))
        self.total_steps = 720
        self.remaining_steps = max(0, self.total_steps - self.step)
        self.player_idx = int(obs.get("player", 0))
        self.opp_idx = 1 - self.player_idx

        market = obs.get("market", {}) or {}
        self.prices = market.get("prices", {}) or {}

        farms = obs.get("farms", []) or []
        if len(farms) > self.player_idx:
            my_farm = farms[self.player_idx]
            self.money = float(my_farm.get("money", 0.0))
            self.unlocked_quadrants = list(my_farm.get("unlocked_quadrants", []) or [])
            self.inventory = dict(my_farm.get("inventory", {}) or {})
            self.tiles = [t for row in (my_farm.get("tiles", []) or []) for t in row if isinstance(t, dict)]
            self.workers = list(my_farm.get("workers", []) or [])
        else:
            self.money = 0.0
            self.unlocked_quadrants = []
            self.inventory = {}
            self.tiles = []
            self.workers = []

        self.ready_harvests = [t for t in self.tiles if t.get("crop") is not None and t.get("yield", 0) > 0]

class EmpiricalMarginalEvaluator:
    @staticmethod
    def calculate_marginal_value(candidate, expert_action, state):
        first_cand = candidate[0] if isinstance(candidate, list) and len(candidate) > 0 else candidate
        if isinstance(first_cand, list) and len(first_cand) > 0 and isinstance(first_cand[0], list):
            first_cand = first_cand[0]

        expert_market = list(expert_action.get("market", [])) if isinstance(expert_action, dict) else []

        cand_cmd = first_cand[0] if len(first_cand) > 0 else "PASS"
        cand_item = first_cand[1] if len(first_cand) > 1 else "WHEAT"
        cand_qty = first_cand[2] if len(first_cand) > 2 else 1
        cand_price = float(state.prices.get(cand_item, 10.0))

        expert_qty = 0
        for ord in expert_market:
            if len(ord) > 1 and ord[0] == cand_cmd and ord[1] == cand_item:
                expert_qty = ord[2] if len(ord) > 2 else 1
                break

        delta_qty = cand_qty - expert_qty
        raw_cash_delta = delta_qty * cand_price

        step = state.step
        current_money = state.money
        num_tiles = max(1, len(state.tiles))

        total_inv_count = sum(state.inventory.values())
        congestion_ratio = min(1.0, total_inv_count / max(1.0, float(num_tiles * 2)))

        operating_reserve = 300.0 if state.day <= 20 else 150.0
        disposable_before = max(0.0, current_money - operating_reserve)
        disposable_after = max(0.0, (current_money + raw_cash_delta) - operating_reserve)

        unlocks_hire = (disposable_before < 100 <= disposable_after)
        unlocks_seed = (disposable_before < 50 <= disposable_after)
        unlocks_land = (disposable_before < 500 <= disposable_after)

        if unlocks_hire:
            capital_multiplier = 0.50
        elif unlocks_seed:
            capital_multiplier = 0.35
        elif unlocks_land:
            capital_multiplier = 0.25
        else:
            if current_money < 300.0:
                capital_multiplier = 0.005 # Low cash distress penalty
            elif 300.0 <= current_money < 1500.0:
                capital_multiplier = 0.025
            else:
                capital_multiplier = 0.045

            if cand_item == "FERTILIZER":
                if step < 200:
                    capital_multiplier = min(capital_multiplier, 0.005)
                elif step >= 500:
                    capital_multiplier = max(capital_multiplier, 0.05)

        marginal_cash_value = raw_cash_delta * capital_multiplier

        if cand_cmd == "SELL" and cand_item in ("WHEAT", "CARROT", "TOMATO") and expert_qty == 0:
            if congestion_ratio > 0.4 and current_money >= 300.0:
                congestion_relief_adv = 3.50 * congestion_ratio
            else:
                congestion_relief_adv = 0.0
        else:
            congestion_relief_adv = 0.0

        mcv = marginal_cash_value + congestion_relief_adv
        return mcv, {"total_mcv": mcv}

class ActionSafetyGate:
    @staticmethod
    def is_action_safe(candidate_action, state):
        FORBIDDEN = {"BUY_SEED", "BUY_LAND", "HIRE", "BUY_ANIMAL"}
        first_ord = candidate_action[0] if isinstance(candidate_action, list) and len(candidate_action) > 0 else candidate_action
        if isinstance(first_ord, list) and len(first_ord) > 0 and isinstance(first_ord[0], list):
            first_ord = first_ord[0]

        if len(first_ord) > 0 and first_ord[0] in FORBIDDEN:
            return False, "REJECT_CAPITAL_EXPLORATION"
        return True, "SAFE"

class ActionPlanner:
    @staticmethod
    def generate_market_candidates(state, expert_act):
        candidates = []
        if expert_act and "market" in expert_act:
            for ord in expert_act["market"]:
                if len(ord) > 1 and ord[0] == "SELL":
                    item = ord[1]
                    expert_qty = ord[2] if len(ord) > 2 else 1
                    alt_qtys = {max(1, int(expert_qty * 0.5)), max(1, expert_qty + 1), max(1, expert_qty - 1)}
                    for q in alt_qtys:
                        if q != expert_qty:
                            candidates.append([["SELL", item, q]])

        for item in ("STRAWBERRY", "MELON", "MILK", "WOOL", "WHEAT", "CARROT", "TOMATO"):
            inv_qty = state.inventory.get(item, 0)
            ready_qty = sum(t.get("yield", 0) for t in state.ready_harvests if t.get("crop") == item)
            total_avail = inv_qty + ready_qty

            if total_avail > 0:
                for pct in [0.25, 0.50, 0.75, 1.00]:
                    batch_qty = max(1, int(total_avail * pct))
                    candidates.append([["SELL", item, batch_qty]])

        if not candidates and 100 <= state.step <= 600:
            candidates.append([["SELL", "WHEAT", 1]])

        return candidates

class DivergenceController:
    def __init__(self, max_deviations=1):
        self.max_deviations = max_deviations
        self.executed_count = 0

    def reset_episode(self):
        self.executed_count = 0

    def select_controlled_deviation(self, approved_candidates, state):
        if self.executed_count >= self.max_deviations or not approved_candidates:
            return None
        if state.step < 100 or state.step > 600:
            return None

        approved_candidates.sort(key=lambda x: x[0], reverse=True)
        top_cand = approved_candidates[0]
        self.executed_count += 1

        class Choice:
            def __init__(self, candidate, score):
                self.candidate = candidate
                self.score = score
        return Choice(top_cand[1], top_cand[0])

# Global APEX 3.0 State Instance
_APEX_CONTROLLER = DivergenceController()

def agent(obs, configuration=None):
    # 1. Base Expert Decision
    base_action = _base_agent(obs, configuration)

    # 2. State Sensing & Optimization
    wstate = WorldState(obs)
    if wstate.step == 0:
        _APEX_CONTROLLER.reset_episode()

    if wstate.remaining_steps <= 24 or wstate.step < 100 or wstate.step > 600:
        return base_action

    candidates = ActionPlanner.generate_market_candidates(wstate, base_action)
    approved = []

    for cand in candidates:
        safe, reason = ActionSafetyGate.is_action_safe(cand, wstate)
        if safe:
            mcv_score, _ = EmpiricalMarginalEvaluator.calculate_marginal_value(cand, base_action, wstate)
            if mcv_score >= 1.0:
                approved.append((mcv_score, cand, "APPROVED"))

    chosen = _APEX_CONTROLLER.select_controlled_deviation(approved, wstate)
    if chosen is not None:
        first_ord = chosen.candidate[0] if isinstance(chosen.candidate, list) and len(chosen.candidate) > 0 else chosen.candidate
        if isinstance(first_ord, list) and len(first_ord) > 0 and isinstance(first_ord[0], list):
            first_ord = first_ord[0]

        alt_market = list(base_action.get("market", [])) + [first_ord]
        apex_action = dict(base_action)
        apex_action["market"] = alt_market
        return apex_action

    return base_action
'''

# Merge Base Engine + APEX 3.0 Engine
final_code = v18_code + "\n" + APEX_30_EMBEDDED_CODE


with open(OUT_PATH, "w", encoding="utf-8") as f:
    f.write(final_code)

print(f"Successfully generated standalone APEX 3.0 Monolithic Artifact at:\n  {OUT_PATH}")
print(f"File Size: {os.path.getsize(OUT_PATH)} bytes")
