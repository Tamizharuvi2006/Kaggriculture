"""Step 3H-7 vector-port parity audit.

Gate 3H-7A validates that the corrected V25-style vector state starts from the
same public/private world as real Kaggriculture and PairedSimV2. Transition
ports must be added in later gates only after this initial-state contract holds.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import kaggle_environments

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from apex_next.gpu_engine.paired_gpu_v25.corrected_vector_engine import CorrectedVectorPairedEngine  # noqa: E402
from apex_next.gpu_engine.paired_sim_v2 import PairedSimV2Engine  # noqa: E402
from apex_next.gpu_engine.step3h_parity_audit import (  # noqa: E402
    _compare_value,
    _first_divergence,
    _land_count,
    _observation,
    _replay_in_paired_sim,
    _run_real_kaggle,
    _snapshot_sim,
)


DEFAULT_REPORT = PROJECT_ROOT / "reports" / "step3h" / "vector" / "STEP3H7_VECTOR_PORT_AUDIT.json"
DEFAULT_MARKET_REPORT = PROJECT_ROOT / "reports" / "step3h" / "vector" / "STEP3H7_MARKET_PORT_AUDIT.json"


def run_initial_state_audit(
    seeds: list[int],
    report_path: Path = DEFAULT_REPORT,
) -> dict[str, Any]:
    started = time.perf_counter()
    engine = CorrectedVectorPairedEngine(batch_size=len(seeds), base_seed=seeds[0] if seeds else 0)
    engine.reset(seeds)
    seed_reports = []

    for env_idx, seed in enumerate(seeds):
        real = _real_initial(seed)
        paired = _paired_initial(seed)
        vector = _vector_initial(engine, env_idx)
        real_vs_paired = _compare_value(real, paired, path="")
        paired_vs_vector = _compare_value(paired, vector, path="")
        status = "PASS" if real_vs_paired is None and paired_vs_vector is None else "FAIL"
        seed_reports.append(
            {
                "seed": seed,
                "status": status,
                "real_vs_paired_divergence": real_vs_paired,
                "paired_vs_vector_divergence": paired_vs_vector,
            }
        )
        print(
            f"seed={seed} status={status} "
            f"real_vs_paired={real_vs_paired} paired_vs_vector={paired_vs_vector}",
            flush=True,
        )

    passed = sum(1 for item in seed_reports if item["status"] == "PASS")
    report = {
        "status": "PASS" if passed == len(seed_reports) else "FAIL",
        "step": "STEP 3H-7A - Corrected vector initial-state parity",
        "scope": "initial state only; no market/action/lifecycle transition port yet",
        "backend": "CorrectedVectorPairedEngine NumPy/Python batch state",
        "actual_cuda_used": False,
        "seeds_tested": len(seed_reports),
        "seeds_passed": passed,
        "seeds_failed": len(seed_reports) - passed,
        "seed_reports": seed_reports,
        "recommendation": _recommendation(passed, len(seed_reports)),
        "elapsed_seconds": round(time.perf_counter() - started, 6),
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def run_market_transition_audit(
    seeds: list[int],
    steps: int = 1,
    report_path: Path = DEFAULT_MARKET_REPORT,
    include_physical: bool = False,
) -> dict[str, Any]:
    started = time.perf_counter()
    seed_reports = []

    engine = CorrectedVectorPairedEngine(batch_size=len(seeds), base_seed=seeds[0] if seeds else 0)
    engine.reset(seeds)
    batched_actions: list[tuple[list[dict[str, Any]], list[dict[str, Any]]]] = []

    for seed in seeds:
        actions, real_snapshots = _run_real_kaggle(seed=seed, steps=steps)
        paired_snapshots = _replay_in_paired_sim(seed=seed, actions=actions)
        real_vs_paired = _first_divergence(real_snapshots, paired_snapshots)
        if len(actions) != steps:
            real_vs_paired = real_vs_paired or {
                "field": "action_trace_length",
                "real": steps,
                "sim": len(actions),
            }
        seed_reports.append(
            {
                "seed": seed,
                "status": "PENDING_VECTOR",
                "real_vs_paired_divergence": real_vs_paired,
                "paired_vs_vector_divergence": None,
                "market_prices": None,
            }
        )
        batched_actions.append(([pair["p0"] for pair in actions], [pair["p1"] for pair in actions]))

    for step_idx in range(steps):
        actions_p0 = [trace[0][step_idx] for trace in batched_actions]
        actions_p1 = [trace[1][step_idx] for trace in batched_actions]
        if include_physical:
            engine.step(actions_p0, actions_p1)
        else:
            engine.step_market_only(actions_p0, actions_p1)

    for env_idx, seed in enumerate(seeds):
        actions = [
            {"p0": batched_actions[env_idx][0][idx], "p1": batched_actions[env_idx][1][idx]}
            for idx in range(steps)
        ]
        sim = PairedSimV2Engine(seed=seed)
        sim.reset(seed)
        for pair in actions:
            sim.step(pair["p0"], pair["p1"])
        paired = _projection_from_sim_snapshot(_snapshot_sim(sim, step=steps), sim)
        vector = _vector_initial(engine, env_idx)
        paired_vs_vector = _compare_value(paired, vector, path="")
        seed_reports[env_idx]["paired_vs_vector_divergence"] = paired_vs_vector
        seed_reports[env_idx]["status"] = (
            "PASS"
            if seed_reports[env_idx]["real_vs_paired_divergence"] is None and paired_vs_vector is None
            else "FAIL"
        )
        seed_reports[env_idx]["market_prices"] = vector["market"]["prices"]
        print(
            f"seed={seed} status={seed_reports[env_idx]['status']} "
            f"real_vs_paired={seed_reports[env_idx]['real_vs_paired_divergence']} "
            f"paired_vs_vector={paired_vs_vector}",
            flush=True,
        )

    passed = sum(1 for item in seed_reports if item["status"] == "PASS")
    report = {
        "status": "PASS" if passed == len(seed_reports) else "FAIL",
        "step": "STEP 3H-7C - Corrected vector physical-transition parity"
        if include_physical
        else "STEP 3H-7B - Corrected vector market-transition parity",
        "scope": f"{steps} real action step(s); full physical/market transition"
        if include_physical
        else f"{steps} real action step(s); market/order/time transition only",
        "backend": "CorrectedVectorPairedEngine NumPy/Python batch state",
        "actual_cuda_used": False,
        "seeds_tested": len(seed_reports),
        "seeds_passed": passed,
        "seeds_failed": len(seed_reports) - passed,
        "seed_reports": seed_reports,
        "recommendation": _physical_recommendation(passed, len(seed_reports))
        if include_physical
        else _market_recommendation(passed, len(seed_reports)),
        "elapsed_seconds": round(time.perf_counter() - started, 6),
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def _real_initial(seed: int) -> dict[str, Any]:
    env = kaggle_environments.make(
        "kaggriculture",
        configuration={"episodeSteps": 720, "townCenterSellInterval": 24, "seed": seed},
    )
    state = env.reset(num_agents=2)
    obs0 = _observation(state[0])
    return _projection(
        step=obs0.get("step", 0),
        day=obs0.get("day", 0),
        hour=obs0.get("hour", 0),
        farms=obs0.get("farms", []),
        market=obs0.get("market", {}),
        town=obs0.get("town", {}),
        privates=[_private(state[0]), _private(state[1])],
    )


def _paired_initial(seed: int) -> dict[str, Any]:
    sim = PairedSimV2Engine(seed=seed)
    sim.reset(seed)
    return _projection_from_sim_snapshot(_snapshot_sim(sim, step=0), sim)


def _vector_initial(engine: CorrectedVectorPairedEngine, env_idx: int) -> dict[str, Any]:
    obs = engine.observation(env_idx, 0)
    return _projection(
        step=obs.get("step", 0),
        day=obs.get("day", 0),
        hour=obs.get("hour", 0),
        farms=obs.get("farms", []),
        market=obs.get("market", {}),
        town=obs.get("town", {}),
        privates=[engine.private_observation(env_idx, 0), engine.private_observation(env_idx, 1)],
    )


def _projection_from_sim_snapshot(snapshot: dict[str, Any], sim: PairedSimV2Engine) -> dict[str, Any]:
    farms = []
    for idx, player in enumerate(snapshot["players"]):
        farms.append(
            {
                "money": player["money"],
                "land": player["land_count"],
                "farmer": player["farmer"],
                "hands": player["hands"],
                "unlocked_quadrants": player["unlocked_quadrants"],
                "tiles": sim.tiles[idx],
                "inventory": player["inventory"],
            }
        )
    market = {
        "inventory": dict(sim.market_inventory),
        "prices": snapshot["market_prices"],
    }
    return _projection(
        step=snapshot["step"],
        day=sim.day_idx,
        hour=sim.hour_idx,
        farms=farms,
        market=market,
        town={"unlocked_shops": list(sim.town_shops)},
        privates=[
            {"shed": sim.private_shed[0], "inventories": sim.private_inventories[0], "seeds": sim.seeds[0]},
            {"shed": sim.private_shed[1], "inventories": sim.private_inventories[1], "seeds": sim.seeds[1]},
        ],
    )


def _projection(
    *,
    step: int,
    day: int,
    hour: int,
    farms: Any,
    market: dict[str, Any],
    town: dict[str, Any],
    privates: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "step": int(step),
        "day": int(day),
        "hour": int(hour),
        "players": [_farm_projection(farms[idx], privates[idx]) for idx in range(2)],
        "market": {
            "inventory": _ordered_numbers((market or {}).get("inventory", {}), CorrectedVectorPairedEngine.PRODUCTS),
            "prices": _ordered_numbers((market or {}).get("prices", {}), CorrectedVectorPairedEngine.PRODUCTS),
        },
        "town": {"unlocked_shops": list((town or {}).get("unlocked_shops", []))},
    }


def _farm_projection(farm: dict[str, Any], private: dict[str, Any]) -> dict[str, Any]:
    return {
        "money": float(farm.get("money", 0.0)),
        "land": _land_count(farm),
        "farmer": list(farm.get("farmer", [])),
        "hands": list(farm.get("hands", [])),
        "unlocked_quadrants": list(farm.get("unlocked_quadrants", [])),
        "tile_signature": _tile_signature(farm.get("tiles")),
        "inventory": _ordered_numbers(farm.get("inventory", {}), CorrectedVectorPairedEngine.PRODUCTS),
        "private": {
            "shed": _ordered_numbers(private.get("shed", {}), CorrectedVectorPairedEngine.PRODUCTS + CorrectedVectorPairedEngine.ANIMALS),
            "inventories": list(private.get("inventories", [])),
            "seeds": _ordered_numbers(private.get("seeds", {}), CorrectedVectorPairedEngine.CROPS),
        },
    }


def _tile_signature(tiles: Any) -> dict[str, int]:
    signature = {"locked": 0, "empty": 0, "plant": 0, "pasture": 0, "other": 0}
    if not isinstance(tiles, list):
        return signature
    for row in tiles:
        if not isinstance(row, list):
            signature["other"] += 1
            continue
        for tile in row:
            if tile == "LOCKED":
                signature["locked"] += 1
            elif tile is None:
                signature["empty"] += 1
            elif isinstance(tile, dict) and tile.get("kind") == "PLANT":
                signature["plant"] += 1
            elif isinstance(tile, dict) and tile.get("kind") == "PASTURE":
                signature["pasture"] += 1
            else:
                signature["other"] += 1
    return signature


def _ordered_numbers(mapping: Any, keys: list[str]) -> dict[str, float]:
    result = {}
    for key in keys:
        value = 0.0
        if isinstance(mapping, dict):
            value = mapping.get(key, mapping.get(key.lower(), 0.0))
        result[key] = float(value)
    return result


def _private(agent_state: Any) -> dict[str, Any]:
    obs = _observation(agent_state)
    private = obs.get("private", {}) if isinstance(obs, dict) else {}
    return private if isinstance(private, dict) else {}


def _recommendation(passed: int, total: int) -> str:
    if passed == total:
        return "3H-7A initial-state parity is closed. Next port market transition semantics into the corrected vector architecture."
    return "Initial-state parity failed. Fix the corrected vector reset/schema before porting any transition mechanics."


def _market_recommendation(passed: int, total: int) -> str:
    if passed == total:
        return "3H-7B market-transition parity is closed for the audited window. Next port physical action interpreter semantics."
    return "Market-transition parity failed. Fix market/order/time semantics before porting physical mechanics."


def _physical_recommendation(passed: int, total: int) -> str:
    if passed == total:
        return "3H-7C physical-transition parity is closed for the audited window. Next expand the vector replay window toward full-trajectory parity."
    return "Physical-transition parity failed. Fix the first divergent action/lifecycle mechanic before expanding the replay window."


def _parse_seeds(args: argparse.Namespace) -> list[int]:
    if args.seeds:
        return [int(part.strip()) for part in args.seeds.split(",") if part.strip()]
    return list(range(args.seed_start, args.seed_start + args.count))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Step 3H-7 vector-port parity audit.")
    parser.add_argument("--mode", choices=["initial", "market", "physical"], default="initial")
    parser.add_argument("--seed-start", type=int, default=39000)
    parser.add_argument("--count", type=int, default=20)
    parser.add_argument("--seeds", type=str, default="")
    parser.add_argument("--steps", type=int, default=1)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    seeds = _parse_seeds(args)
    if args.mode == "market":
        report_path = args.report if args.report != DEFAULT_REPORT else DEFAULT_MARKET_REPORT
        report = run_market_transition_audit(seeds, steps=args.steps, report_path=report_path)
    elif args.mode == "physical":
        report_path = args.report if args.report != DEFAULT_REPORT else PROJECT_ROOT / "reports" / "step3h" / "vector" / "STEP3H7_PHYSICAL_PORT_AUDIT.json"
        report = run_market_transition_audit(seeds, steps=args.steps, report_path=report_path, include_physical=True)
    else:
        report = run_initial_state_audit(seeds, report_path=args.report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
