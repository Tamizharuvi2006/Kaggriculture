"""L+ APEX 2.5-E: Policy Engine for Single Safe Policy Divergence Execution.
"""

from __future__ import annotations
from typing import Dict, List, Any, Optional
from apex.world_model import WorldState
from apex.expert import LPlusExpert
from apex.meta_model import MetaDetector, MetaSignature
from apex.opponent_model import OpponentModel, OpponentSignature
from apex.strategy_adapter import StrategyAdapter, StrategyState
from apex.experience_memory import ExperienceMemory
from apex.planner import ActionPlanner
from apex.action_safety import ActionSafetyGate
from apex.counterfactual import CounterfactualSimulator, CandidateRejectionTelemetry
from apex.shadow_simulator import ShadowSimulator
from apex.divergence_controller import DivergenceController, DivergenceCandidateRank

class DivergenceFeatureAttribution:
    def __init__(self, transit_adv: float, market_adv: float, downstream_adv: float, terminal_adv: float):
        self.transit_adv = transit_adv
        self.market_adv = market_adv
        self.downstream_adv = downstream_adv
        self.terminal_adv = terminal_adv
        self.total_predicted = transit_adv + market_adv + downstream_adv + terminal_adv

class DivergenceTelemetryRecord:
    def __init__(
        self,
        step: int,
        state_signature: str,
        expert_action: Dict[str, Any],
        apex_action: Dict[str, Any],
        reasoning: str,
        predicted_delta: float,
        confidence: float,
        attribution: DivergenceFeatureAttribution,
        action_key: str
    ):
        self.step = step
        self.state_signature = state_signature
        self.expert_action = expert_action
        self.apex_action = apex_action
        self.reasoning = reasoning
        self.predicted_delta = predicted_delta
        self.confidence = confidence
        self.attribution = attribution
        self.action_key = action_key
        self.actual_margin_delta: float = 0.0

class ApexPolicy:
    """APEX 2.5-E Policy Engine:
    Forces execution of EXACTLY ONE safe zero-cost policy deviation per episode (Steps 100-600).
    """

    def __init__(self, mode: str = "advisor_guided", exploration_level: str = "SINGLE_DEVIATION_E"):
        self.mode = mode
        self.exploration_level = exploration_level
        self.expert = LPlusExpert()
        self.experience_memory = ExperienceMemory()
        self.divergence_controller = DivergenceController(max_deviations_per_episode=1)
        
        self.telemetry_traces: List[DivergenceTelemetryRecord] = []
        self.total_decisions = 0
        self.agreements = 0
        self.divergences = 0
        self.successful_divergences = 0
        self.neutral_divergences = 0
        self.failed_divergences = 0

        self.last_meta: Optional[MetaSignature] = None
        self.last_opp: Optional[OpponentSignature] = None
        self.last_strategy: Optional[StrategyState] = None

    def reset_episode(self):
        """Reset per-episode state in DivergenceController."""
        self.divergence_controller.reset_episode()

    def select_action(self, obs: Dict[str, Any], state: WorldState) -> Dict[str, Any]:
        self.total_decisions += 1

        # Reset episode tracker on step 0
        if state.step == 0:
            self.reset_episode()
        
        # 1. Real-Time Sensing & Strategy Adaptation
        meta_sig = MetaDetector.detect_regime(state)
        opp_sig = OpponentModel.analyze_opponent(state)
        strat_state = StrategyAdapter.select_active_strategy(state, meta_sig, opp_sig)

        self.last_meta = meta_sig
        self.last_opp = opp_sig
        self.last_strategy = strat_state

        # 2. Query L+ Expert Baseline
        expert_act = self.expert.decide(obs)
        expert_market = list(expert_act.get("market", []))

        if self.mode == "expert_pure" or state.remaining_steps <= 24:
            self.agreements += 1
            return expert_act

        # 3. UCB Candidate Generation & Counterfactual Simulation
        candidates = ActionPlanner.generate_market_candidates(state, expert_act)
        approved_candidates = []

        for cand in candidates:
            approved, cand_score, reason = CounterfactualSimulator.evaluate_exploration_candidate(
                cand, expert_act, state, confidence_threshold=0.10
            )
            if approved:
                approved_candidates.append((cand_score, cand, reason))

        # 4. Query DivergenceController for Controlled Single Deviation Selection
        chosen_rank = self.divergence_controller.select_controlled_deviation(approved_candidates, state)

        if chosen_rank is not None:
            first_ord = chosen_rank.candidate[0] if isinstance(chosen_rank.candidate, list) and len(chosen_rank.candidate) > 0 else chosen_rank.candidate
            if isinstance(first_ord, list) and len(first_ord) > 0 and isinstance(first_ord[0], list):
                first_ord = first_ord[0]

            item = first_ord[1] if len(first_ord) > 1 else "WHEAT"
            qty = first_ord[2] if len(first_ord) > 2 else 1
            price = float(state.prices.get(item, 10.0))

            # REPLACE expert sell orders for this item to enforce genuine divergence
            final_market = [ord for ord in expert_market if not (len(ord) > 1 and ord[0] == "SELL" and ord[1] == item)]
            final_market.insert(0, first_ord)

            # Verify Divergent Plan via ShadowSimulator
            sim_res = ShadowSimulator.simulate_plan(final_market, state)
            if not sim_res.is_valid:
                self.agreements += 1
                return expert_act

            self.divergences += 1
            
            attr = DivergenceFeatureAttribution(
                transit_adv=15.0,
                market_adv=qty * price * 0.05,
                downstream_adv=15.0,
                terminal_adv=10.0
            )
            
            sig = f"Step_{state.step}_Money_{int(state.money)}_Regime_{meta_sig.regime}"
            self.telemetry_traces.append(DivergenceTelemetryRecord(
                step=state.step,
                state_signature=sig,
                expert_action=expert_act,
                apex_action={"market": final_market[:10]},
                reasoning=chosen_rank.reason,
                predicted_delta=chosen_rank.score,
                confidence=min(1.0, chosen_rank.score / 200.0),
                attribution=attr,
                action_key=chosen_rank.action_key
            ))
            
            selected_action = dict(expert_act)
            selected_action["market"] = final_market[:10]
            return selected_action

        self.agreements += 1
        return expert_act

    def record_match_outcome(self, margin_delta: float):
        """Telemetry recorder for match outcome margin attribution."""
        if self.divergences > 0:
            for trace in self.telemetry_traces:
                trace.actual_margin_delta = margin_delta
                regime = self.last_meta.regime if self.last_meta else "BALANCED"
                self.experience_memory.add_experience(
                    step=trace.step,
                    action_key=trace.action_key,
                    regime=regime,
                    predicted_value=trace.predicted_delta,
                    actual_delta=margin_delta,
                    situation_features={"step": float(trace.step), "confidence": trace.confidence},
                    confidence=0.20
                )
            if margin_delta > 0.0:
                self.successful_divergences += 1
            elif margin_delta == 0.0:
                self.neutral_divergences += 1
            else:
                self.failed_divergences += 1

    def get_metrics(self) -> Dict[str, Any]:
        total = max(1, self.total_decisions)
        agree_pct = (self.agreements / total) * 100.0
        disagree_pct = (self.divergences / total) * 100.0
        total_devs = max(1, self.divergences)
        success_rate = (self.successful_divergences / total_devs) * 100.0 if self.divergences > 0 else 0.0

        audit = CounterfactualSimulator.REJECTION_TELEMETRY.get_audit_summary()

        return {
            "exploration_level": self.exploration_level,
            "total_decisions": self.total_decisions,
            "agreements": self.agreements,
            "divergences": self.divergences,
            "agreement_rate_pct": agree_pct,
            "divergence_rate_pct": disagree_pct,
            "successful_divergences": self.successful_divergences,
            "neutral_divergences": self.neutral_divergences,
            "failed_divergences": self.failed_divergences,
            "divergence_success_rate_pct": success_rate,
            "total_telemetry_traces": len(self.telemetry_traces),
            "rejection_audit": audit,
            "active_strategy": self.last_strategy.name if self.last_strategy else "UNKNOWN",
            "detected_regime": self.last_meta.regime if self.last_meta else "UNKNOWN",
            "opponent_archetype": self.last_opp.archetype if self.last_opp else "UNKNOWN"
        }
