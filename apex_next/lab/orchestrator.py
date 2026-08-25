"""
11. Master Research & Validation Orchestrator
Coordinates the 16-stage autonomous pipeline deterministically:
Priority Engine -> Hypothesis Memory -> Genealogy -> Candidate -> 4 Gates ->
Statistical Judge -> Champion Registry. Maintains strict physical separation
between read-only production and the research lab.
"""
import sys
import os

# Make the lab importable regardless of the current working directory.
# apex_next/ is the new agent root; CWD-independent execution is required.
_APEX_NEXT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _APEX_NEXT_ROOT not in sys.path:
    sys.path.insert(0, _APEX_NEXT_ROOT)

from lab.telemetry_ingestor import TelemetryIngestor
from lab.diagnostics_analyzer import DiagnosticsAnalyzer
from lab.hypothesis_generator import HypothesisGenerator
from lab.candidate_builder import CandidateBuilder
from lab.exact_replay_engine import ExactReplayEngine
from lab.historical_suite_engine import HistoricalSuiteEngine
from lab.frozen_holdout_engine import FrozenHoldoutEngine
from lab.statistical_judge import StatisticalJudge
from lab.audit_ledger import AuditLedger
from lab.release_manager import ReleaseManager
from lab.experiment_memory import ExperimentMemory
from lab.priority_engine import PriorityEngine
from lab.regime_detector import RegimeDetector
from lab.artifact_hasher import ArtifactHasher
from lab.regression_sentinel import RegressionSentinel
from lab.champion_registry import ChampionRegistry


class LabOrchestrator:
    def __init__(self, baseline_id: str = "APEX-3.5-PROD"):
        self.baseline_id = baseline_id
        self.telemetry_ingestor = TelemetryIngestor()
        self.diagnostics_analyzer = DiagnosticsAnalyzer()
        self.hypothesis_gen = HypothesisGenerator()
        self.candidate_builder = CandidateBuilder()
        self.exact_replay = ExactReplayEngine()
        self.historical_suite = HistoricalSuiteEngine()
        self.frozen_holdout = FrozenHoldoutEngine()
        self.statistical_judge = StatisticalJudge()
        self.audit_ledger = AuditLedger()
        self.release_manager = ReleaseManager()
        self.experiment_memory = ExperimentMemory()
        self.priority_engine = PriorityEngine()
        self.regime_detector = RegimeDetector()
        self.artifact_hasher = ArtifactHasher()
        self.champion_registry = ChampionRegistry()

    def _run_memory_gate(
        self,
        diagnostic_package: dict,
        variable_family: str,
        proposed_mechanism: str
    ) -> dict:
        """
        Hypothesis Memory gate: before a new hypothesis is generated, search the
        experiment ledger. If the same family/archetype/mechanism was already
        falsified, return LEARN (blocked) instead of re-running the dead end.
        """
        lookup = self.experiment_memory.search_hypothesis(
            variable_family=variable_family,
            target_archetype=diagnostic_package.get("primary_archetype"),
            mechanism=proposed_mechanism
        )
        if lookup["verdict"] == "LEARN":
            print(f"[Memory Gate] BLOCKED: identical hypothesis already falsified.")
            for prior in lookup["prior_attempts"]:
                print(f"  Prior {prior['experiment_id']} (score {prior['score']}): {prior.get('hypothesis', '')[:80]}")
            return {
                "status": "BLOCKED",
                "reasons": lookup["reasons"],
                "prior_attempts": lookup["prior_attempts"]
            }
        return {"status": "CLEARED", "prior_attempts": lookup["prior_attempts"]}

    def run_experiment_pipeline(
        self,
        diagnostic_package: dict,
        proposed_mechanism: str,
        variable_family: str,
        candidate_code_content: str,
        baseline_file: str = "submission.py",
        auto_promote: bool = False,
        new_version_tag: str = "APEX-3.6-PROD"
    ) -> dict:
        """Executes the full memory-guided verification and release loop."""
        print(f"\n=======================================================")
        print(f"[PIPELINE] INITIATING APEX RESEARCH PIPELINE (Baseline: {self.baseline_id})")
        print(f"=======================================================\n")

        # Stage 0a: Priority Engine -- pick the ONE archetype worth attacking
        archetype = diagnostic_package.get("primary_archetype")
        if not archetype:
            selection = self.priority_engine.select_next_experiment(
                diagnostics_aggregate=diagnostic_package,
                attempt_penalty=None
            )
            archetype = selection.get("selected_archetype")
            print(f"[Stage 0: Priority] Highest-value archetype: {archetype}")
            if not archetype:
                return {"experiment_id": None, "verdict": "NO_FAILURES_TO_ATTACK"}

        # Stage 0b: Hypothesis Memory -- never re-run a falsified dead end
        memory_gate = self._run_memory_gate(diagnostic_package, variable_family, proposed_mechanism)
        if memory_gate["status"] == "BLOCKED":
            return {
                "experiment_id": None,
                "verdict": "BLOCKED_BY_MEMORY",
                "prior_attempts": memory_gate["prior_attempts"]
            }

        # Stage 0c: Genealogy -- attach the parent from the same lineage
        parent_exp_id = self.experiment_memory.assign_parent(
            variable_family=variable_family,
            target_archetype=archetype
        )
        if parent_exp_id:
            print(f"[Stage 0c: Genealogy] Parent lineage: {parent_exp_id} -> new experiment")

        # 1. Hypothesis Formulation
        hypothesis = self.hypothesis_gen.generate_hypothesis(
            diagnostic_package=diagnostic_package,
            proposed_mechanism=proposed_mechanism,
            variable_family=variable_family
        )
        exp_id = hypothesis["experiment_id"]
        print(f"[Stage 3: Hypothesis] Generated {exp_id} | Family: {variable_family}")
        print(f"                      Mechanism: {proposed_mechanism}")

        # 2. Candidate Branch Building
        candidate_meta = self.candidate_builder.create_candidate_branch(
            hypothesis_spec=hypothesis,
            baseline_file=baseline_file,
            candidate_code_content=candidate_code_content
        )
        print(f"[Stage 4: Candidate] Branch built in experiments/{exp_id}/ (SHA256: {candidate_meta['candidate_hash'][:8]})")

        # 3. Gate 1: Exact Loss Replay
        motivating_seed = diagnostic_package.get("motivating_seed")
        seeds = [motivating_seed] if motivating_seed else [42, 107, 504110]
        exact_res = self.exact_replay.run_exact_replay(candidate_meta, seeds)
        print(f"[Gate 1: Replay] Status: {exact_res['status']} | WinRate: {exact_res['win_rate']:.1%}")

        if not exact_res["passed"]:
            print(f"[FAIL] Gate 1 FAILED. Candidate did not eliminate motivating loss. Falsifying.")
            self._log_and_archive(
                exp_id, candidate_meta, hypothesis, exact_res, {}, {},
                {"promotable": False, "failed_reasons": ["Gate 1 Exact Replay Failed"]},
                parent_exp_id=parent_exp_id,
                diagnostic_package=diagnostic_package
            )
            return {"experiment_id": exp_id, "verdict": "FALSIFIED_GATE_1"}

        # 4. Gate 2: Historical Loss Suite (N=50)
        hist_res = self.historical_suite.run_suite(candidate_meta)
        print(f"[Gate 2: History] Status: {hist_res['status']} | Overall WR: {hist_res['overall_win_rate']:.1%}")

        if not hist_res["passed"]:
            print(f"[FAIL] Gate 2 FAILED. Regression observed across historical suite. Falsifying.")
            self._log_and_archive(
                exp_id, candidate_meta, hypothesis, exact_res, hist_res, {},
                {"promotable": False, "failed_reasons": ["Gate 2 Historical Regression"]},
                parent_exp_id=parent_exp_id,
                diagnostic_package=diagnostic_package
            )
            return {"experiment_id": exp_id, "verdict": "FALSIFIED_GATE_2"}

        # 5. Gate 3: Frozen Blind Holdout (N=100)
        print(f"[Gate 3: Holdout] Running single-shot evaluation against {self.frozen_holdout.HOLDOUT_SUITE_VERSION} (N=100)...")
        holdout_res = self.frozen_holdout.run_holdout(candidate_meta)
        print(f"                  Candidate WR: {holdout_res['win_rate']:.1%} | Mean MCV: {holdout_res['candidate_mean_mcv']:.0f} (vs {holdout_res['baseline_mean_mcv']:.0f})")

        # 6. Gate 4: Deterministic Statistical Judge
        judge_verdict = self.statistical_judge.evaluate(holdout_res)
        print(f"[Gate 4: Judge] Verdict: {judge_verdict['verdict']}")

        promoted = False
        if judge_verdict["promotable"]:
            print(f"\n[SUCCESS] ALL GATES CLEARED! Challenger approved for promotion.")
            if auto_promote:
                rel_res = self.release_manager.prepare_release(
                    candidate_meta=candidate_meta,
                    judge_verdict=judge_verdict,
                    new_version_tag=new_version_tag
                )
                promoted = (rel_res.get("status") == "RELEASE_READY")
                if promoted:
                    print(f"[Stage 10: Release] Deployed to {self.release_manager.submission_target} as {new_version_tag}")
                    registry_res = self.champion_registry.promote_challenger(
                        challenger_meta=candidate_meta,
                        judge_verdict=judge_verdict,
                        holdout_res=holdout_res,
                        version_tag=new_version_tag,
                        release_confirmed=True
                    )
                    print(f"[Champion Registry] {registry_res['status']} -> {new_version_tag}")
        else:
            print(f"\n[FAIL] Gate 4 FAILED. Reasons: {judge_verdict['failed_reasons']}")

        # 7. Immutable Audit Log (with provenance + genealogy + regime)
        self._log_and_archive(
            exp_id, candidate_meta, hypothesis, exact_res, hist_res, holdout_res,
            judge_verdict, promoted=promoted,
            parent_exp_id=parent_exp_id,
            diagnostic_package=diagnostic_package
        )

        return {
            "experiment_id": exp_id,
            "verdict": judge_verdict["verdict"],
            "promoted": promoted,
            "metrics": judge_verdict.get("metrics", {})
        }

    def _log_and_archive(
        self,
        exp_id,
        candidate_meta,
        hypothesis,
        exact_res,
        hist_res,
        holdout_res,
        judge_verdict,
        promoted=False,
        parent_exp_id=None,
        diagnostic_package=None
    ):
        """Builds provenance, regime tags, priority score and appends the record."""
        # Artifact provenance: code + baseline + config + holdout + result hashes
        provenance = self.artifact_hasher.build_provenance(
            candidate_file=candidate_meta.get("candidate_file", ""),
            baseline_file="submission.py",
            config=candidate_meta.get("config", {}),
            holdout_seeds=self.frozen_holdout.FROZEN_SEEDS_N100,
            results=judge_verdict.get("metrics", {}) if judge_verdict else {}
        )

        # Regime tags from the motivating telemetry's real market events
        regime_tags = None
        if diagnostic_package:
            trajectory_rows = diagnostic_package.get("trajectory_rows")
            if trajectory_rows:
                regime = self.regime_detector.classify_trajectory(trajectory_rows)
                regime_tags = [regime["regime"], regime.get("product")]
            elif diagnostic_package.get("market_events"):
                regime = self.regime_detector.classify_series(diagnostic_package["market_events"])
                regime_tags = [regime["regime"]]

        # Priority score of the attacked archetype (attempt penalty from memory)
        priority_score = None
        if diagnostic_package and diagnostic_package.get("primary_archetype"):
            attempts = self.experiment_memory.attempt_count_for_archetype(
                target_archetype=diagnostic_package["primary_archetype"],
                variable_family=hypothesis.get("variable_family")
            )
            score = self.priority_engine.score_archetype(
                archetype=diagnostic_package["primary_archetype"],
                frequency=0.5, impact=0.5, confidence=0.5, fixability=0.5
            )
            score["prior_attempts"] = attempts
            score["penalized_score"] = round(score["priority_score"] * (0.75 ** attempts), 2)
            priority_score = score["penalized_score"]

        # Population-level distribution metrics from the holdout run
        population_metrics = None
        if holdout_res:
            population_metrics = {
                "win_rate": holdout_res.get("win_rate"),
                "baseline_mean_mcv": holdout_res.get("baseline_mean_mcv"),
                "candidate_mean_mcv": holdout_res.get("candidate_mean_mcv"),
                "baseline_std_mcv": holdout_res.get("baseline_std_mcv"),
                "candidate_std_mcv": holdout_res.get("candidate_std_mcv"),
                "baseline_p05_mcv": holdout_res.get("baseline_p05_mcv"),
                "candidate_p05_mcv": holdout_res.get("candidate_p05_mcv"),
                "avg_pass_turns": holdout_res.get("avg_pass_turns"),
                "max_pass_turns": holdout_res.get("max_pass_turns")
            }

        record = self.audit_ledger.append_record(
            experiment_id=exp_id,
            baseline_id=self.baseline_id,
            candidate_meta=candidate_meta,
            hypothesis_spec=hypothesis,
            exact_replay_res=exact_res,
            historical_res=hist_res,
            holdout_res=holdout_res,
            judge_verdict=judge_verdict,
            promoted=promoted,
            parent_exp_id=parent_exp_id,
            provenance=provenance,
            regime_tags=regime_tags,
            priority_score=priority_score,
            population_metrics=population_metrics
        )
        print(f"[Audit Ledger] Appended immutable record {exp_id} -> {self.audit_ledger.ledger_filepath}")
        return record

    def watch_live_performance(
        self,
        expected_wr: float,
        expected_mean_mcv: float,
        expected_std_mcv: float,
        live_matches: list
    ) -> dict:
        """
        Regression Sentinel entry point: feeds the first N live matches of the
        newly promoted champion and returns the deterministic state + recommendation.
        The sentinel never reverts; the release controller owns fallback.
        """
        sentinel = RegressionSentinel(
            expected_wr=expected_wr,
            expected_mean_mcv=expected_mean_mcv,
            expected_std_mcv=expected_std_mcv
        )
        for match in live_matches:
            sentinel.observe(match.get("result"), match.get("our_mcv", 0))
        verdict = sentinel.evaluate()
        print(f"[Regression Sentinel] State: {verdict['state']} | "
              f"Recommendation: {verdict['recommendation']} | Matches: {verdict['matches_observed']}")
        return verdict


if __name__ == "__main__":
    # Self-test smoke test
    orchestrator = LabOrchestrator()
    dummy_diag = {
        "match_id": "ep-90744327",
        "primary_archetype": "LIQUIDITY_SHOCK",
        "motivating_seed": 504110,
        "evidence_chain": ["Cash reserve floor hit zero on Day 12."],
        "market_events": [100, 98, 96, 90, 85]
    }
    dummy_code = "# APEX Candidate Agent\ndef agent(obs, conf):\n    return {}\n"
    res = orchestrator.run_experiment_pipeline(
        diagnostic_package=dummy_diag,
        proposed_mechanism="Maintain minimum cash reserve buffer of $150 prior to Day 14.",
        variable_family="Inventory_Liquidity",
        candidate_code_content=dummy_code,
        auto_promote=False
    )
    print("\nOrchestrator Test Run Completed:", res)