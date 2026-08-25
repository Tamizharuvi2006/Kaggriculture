"""Step 3H parity audit for the fast Kaggriculture simulator.

This script is diagnostic only. It does not use the fast simulator as training
truth; it replays identical legal actions against real kaggle_environments and
the current vector simulator, then reports the first state divergence.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import kaggle_environments
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from apex_next.gpu_engine.paired_sim_v2 import PairedSimV2Engine
from apex_next.gpu_engine.paired_gpu_v25.paired_engine_v25 import VectorizedPairedEngineV25
from apex_next.ml_engine.env_wrapper import call_agent, sanitize_action


DEFAULT_REPORT = PROJECT_ROOT / "reports" / "step3h" / "parity" / "STEP3H_GPU_ENGINE_PARITY_AUDIT.json"
APEX4_PATH = PROJECT_ROOT / "APEX4_SUBMISSION_FINAL.py"
BASELINE_PATH = PROJECT_ROOT / "submission.py"
PRODUCTS = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER"]
MARKET_PRODUCTS = PRODUCTS


def run_step3h_parity_audit(
    seed: int = 39000,
    steps: int = 40,
    batch_size: int = 4096,
    report_path: Path = DEFAULT_REPORT,
) -> dict[str, Any]:
    """Run deterministic real-vs-vector replay and throughput audit."""

    started = time.perf_counter()
    actions, real_snapshots = _run_real_kaggle(seed=seed, steps=steps)
    sim_snapshots = _replay_in_paired_sim(seed=seed, actions=actions)
    divergence = _first_divergence(real_snapshots, sim_snapshots)
    benchmark = _benchmark_v25(batch_size=batch_size)
    report = {
        "status": "PASS" if divergence is None else "FAIL_EXPECTED",
        "step": "STEP 3H - Simulator parity audit",
        "scope": "diagnostic only; fast simulator is not approved for Step 5B training truth",
        "seed": seed,
        "steps_requested": steps,
        "real_steps_recorded": len(real_snapshots) - 1,
        "sim_steps_replayed": len(sim_snapshots) - 1,
        "action_source": {
            "p0": str(APEX4_PATH),
            "p1": str(BASELINE_PATH),
            "sanitized_before_replay": True,
        },
        "known_contract": {
            "real_kaggle_environment_is_truth": True,
            "fast_engine_currently_untrusted_for_training": True,
            "identical_actions_replayed": True,
        },
        "parity": {
            "passed": divergence is None,
            "first_divergence": divergence,
            "compared_fields": [
                "money",
                "worker_count",
                "land_count",
                "active_cows",
                "active_sheep",
                "shed_cows",
                "shed_sheep",
                "farmer",
                "hands",
                "unlocked_quadrants",
                "tile_signature",
                "inventory",
                "market_prices",
            ],
            "real_initial": real_snapshots[0],
            "sim_initial": sim_snapshots[0],
        },
        "unsupported_action_summary": _unsupported_action_summary(actions),
        "benchmark": benchmark,
        "recommendation": _recommendation(divergence),
        "elapsed_seconds": round(time.perf_counter() - started, 6),
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def _run_real_kaggle(seed: int, steps: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    env = kaggle_environments.make(
        "kaggriculture",
        configuration={"episodeSteps": 720, "townCenterSellInterval": 24, "seed": seed},
    )
    agents = [_load_agent(APEX4_PATH), _load_agent(BASELINE_PATH)]
    state = env.reset(num_agents=2)
    actions: list[dict[str, Any]] = []
    snapshots = [_snapshot_real(state, step=0)]
    for _ in range(steps):
        obs0 = _observation(state[0])
        obs1 = _observation(state[1])
        act0 = sanitize_action(call_agent(agents[0], obs0, env.configuration))
        act1 = sanitize_action(call_agent(agents[1], obs1, env.configuration))
        actions.append({"p0": act0, "p1": act1})
        state = env.step([act0, act1])
        snapshots.append(_snapshot_real(state, step=len(snapshots)))
        if _is_done(state):
            break
    return actions, snapshots


def _replay_in_paired_sim(seed: int, actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sim = PairedSimV2Engine(seed=seed)
    sim.reset(seed)
    snapshots = [_snapshot_sim(sim, step=0)]
    for action_pair in actions:
        sim.step(action_pair["p0"], action_pair["p1"])
        snapshots.append(_snapshot_sim(sim, step=len(snapshots)))
    return snapshots


def _snapshot_real(state: list[Any], step: int) -> dict[str, Any]:
    obs0 = _observation(state[0])
    farms = obs0.get("farms", []) if isinstance(obs0, dict) else []
    return {
        "step": step,
        "players": [_farm_projection(farms, idx) for idx in range(2)],
        "market_prices": _market_prices(obs0),
        "done": _is_done(state),
        "reward": _safe_list(getattr(state[0], "reward", None), getattr(state[1], "reward", None)),
    }


def _snapshot_sim(sim: PairedSimV2Engine, step: int) -> dict[str, Any]:
    return {
        "step": step,
        "players": [
            {
                "money": round(float(sim.money[idx]), 4),
                "worker_count": int(sim.workers[idx]),
                "land_count": int(sim.land_count[idx]),
                "farmer": list(sim.farmers[idx]),
                "hands": list(sim.hands[idx]),
                "unlocked_quadrants": list(sim.unlocked_quadrants[idx]),
                "tile_signature": _tile_signature(sim.tiles[idx]),
                "active_cows": int(sim.active_cows[idx]),
                "active_sheep": int(sim.active_sheep[idx]),
                "shed_cows": int(sim.shed_cows[idx]),
                "shed_sheep": int(sim.shed_sheep[idx]),
                "inventory": {
                    product: round(float(sim.inventory[idx, prod_idx]), 4)
                    for prod_idx, product in enumerate(PRODUCTS)
                },
            }
            for idx in range(2)
        ],
        "market_prices": _sim_market_prices(sim),
        "done": bool(sim.step_idx >= sim.TERMINAL_STEP),
        "reward": [0.0, 0.0]
        if sim.step_idx < sim.TERMINAL_STEP
        else [round(float(sim.money[0]), 4), round(float(sim.money[1]), 4)],
    }


def _farm_projection(farms: Any, idx: int) -> dict[str, Any]:
    farm = farms[idx] if isinstance(farms, list) and idx < len(farms) and isinstance(farms[idx], dict) else {}
    recursive = _recursive_counts(farm)
    return {
        "money": round(_number_at(farm, "money", recursive.get("money", 0.0)), 4),
        "worker_count": _worker_count(farm),
        "land_count": _land_count(farm),
        "farmer": list(farm.get("farmer", [])) if isinstance(farm.get("farmer"), list) else [],
        "hands": list(farm.get("hands", [])) if isinstance(farm.get("hands"), list) else [],
        "unlocked_quadrants": list(farm.get("unlocked_quadrants", []))
        if isinstance(farm.get("unlocked_quadrants"), list)
        else [],
        "tile_signature": _tile_signature(farm.get("tiles")),
        "active_cows": recursive.get("active_cows", recursive.get("cows", 0)),
        "active_sheep": recursive.get("active_sheep", recursive.get("sheep", 0)),
        "shed_cows": recursive.get("shed_cows", 0),
        "shed_sheep": recursive.get("shed_sheep", 0),
        "inventory": _inventory_projection(farm),
    }


def _recursive_counts(value: Any) -> dict[str, int]:
    counts: dict[str, int] = {}
    if isinstance(value, dict):
        for key, item in value.items():
            key_text = str(key).lower()
            if key_text in {"cow", "cows"}:
                counts["cows"] = counts.get("cows", 0) + _count_value(item)
            elif key_text in {"sheep"}:
                counts["sheep"] = counts.get("sheep", 0) + _count_value(item)
            elif "shed" in key_text and "cow" in key_text:
                counts["shed_cows"] = counts.get("shed_cows", 0) + _count_value(item)
            elif "shed" in key_text and "sheep" in key_text:
                counts["shed_sheep"] = counts.get("shed_sheep", 0) + _count_value(item)
            for nested_key, nested_count in _recursive_counts(item).items():
                counts[nested_key] = counts.get(nested_key, 0) + nested_count
    elif isinstance(value, list):
        for item in value:
            for nested_key, nested_count in _recursive_counts(item).items():
                counts[nested_key] = counts.get(nested_key, 0) + nested_count
    return counts


def _first_divergence(real: list[dict[str, Any]], sim: list[dict[str, Any]]) -> dict[str, Any] | None:
    for step in range(min(len(real), len(sim))):
        diff = _compare_value(real[step], sim[step], path="")
        if diff is not None:
            diff["step"] = step
            return diff
    if len(real) != len(sim):
        return {"step": min(len(real), len(sim)), "field": "trajectory_length", "real": len(real), "sim": len(sim)}
    return None


def _compare_value(real: Any, sim: Any, path: str) -> dict[str, Any] | None:
    if isinstance(real, dict) and isinstance(sim, dict):
        for key in sorted(set(real) | set(sim)):
            diff = _compare_value(real.get(key), sim.get(key), f"{path}.{key}" if path else str(key))
            if diff is not None:
                return diff
        return None
    if isinstance(real, list) and isinstance(sim, list):
        if len(real) != len(sim):
            return {"field": path, "real": real, "sim": sim}
        for idx, (real_item, sim_item) in enumerate(zip(real, sim)):
            diff = _compare_value(real_item, sim_item, f"{path}[{idx}]")
            if diff is not None:
                return diff
        return None
    if _equivalent(real, sim):
        return None
    return {"field": path, "real": real, "sim": sim}


def _equivalent(real: Any, sim: Any) -> bool:
    if isinstance(real, (int, float)) and isinstance(sim, (int, float)):
        return abs(float(real) - float(sim)) <= 1e-3
    return real == sim


def _benchmark_v25(batch_size: int) -> dict[str, Any]:
    before = _resource_snapshot()
    cpu_start = time.process_time()
    wall_start = time.perf_counter()
    engine = VectorizedPairedEngineV25(batch_size=batch_size)
    result = engine.run_paired_batch(_noop_vector_policy, _noop_vector_policy, list(range(41000, 41000 + batch_size)))
    wall_seconds = time.perf_counter() - wall_start
    cpu_seconds = time.process_time() - cpu_start
    after = _resource_snapshot()
    return {
        "engine": "VectorizedPairedEngineV25",
        "actual_cuda_demonstrated": False,
        "implementation_backend": "NumPy CPU vectorization",
        "batch_size": batch_size,
        "wall_seconds": round(wall_seconds, 6),
        "process_cpu_seconds": round(cpu_seconds, 6),
        "approx_process_cpu_util_percent": round((cpu_seconds / max(wall_seconds, 1e-9)) * 100.0 / max(os.cpu_count() or 1, 1), 2),
        "result": result,
        "resources_before": before,
        "resources_after": after,
    }


def _noop_vector_policy(state: dict[str, np.ndarray], seat: int) -> None:
    _ = state
    _ = seat


def _unsupported_action_summary(actions: list[dict[str, Any]]) -> dict[str, Any]:
    commands: dict[str, int] = {}
    unsupported = 0
    total = 0
    supported_market = {"BUY_ANIMAL", "BUY_LAND", "BUY_PRODUCT", "BUY_SEED", "HIRE", "SELL"}
    supported_unit = {
        "BUILD_COOP",
        "BUILD_PASTURE",
        "CARE",
        "COLLECT_FERTILIZER",
        "DIG",
        "DROP",
        "EAST",
        "FEED",
        "FERTILIZE",
        "HARVEST",
        "NORTH",
        "PASS",
        "PICKUP",
        "PLACE",
        "PLANT",
        "SOUTH",
        "WATER",
        "WEST",
    }
    for pair in actions:
        for action in pair.values():
            for channel in ("farmer", "hands"):
                entries = action.get(channel, [])
                if channel == "farmer":
                    entries = [entries]
                for entry in entries:
                    command = _command(entry)
                    if command and command not in supported_unit:
                        unsupported += 1
                        commands[command] = commands.get(command, 0) + 1
                    total += 1
            for order in action.get("market", []):
                command = _command(order)
                if command and command not in supported_market:
                    unsupported += 1
                    commands[command] = commands.get(command, 0) + 1
                total += 1
    return {
        "total_action_entries_seen": total,
        "unsupported_or_ignored_entries": unsupported,
        "unsupported_or_ignored_commands": dict(sorted(commands.items())),
        "paired_sim_v2_supported_market_commands": sorted(supported_market),
        "paired_sim_v2_supported_unit_commands": sorted(supported_unit),
    }


def _recommendation(divergence: dict[str, Any] | None) -> str:
    if divergence is None:
        return (
            "Single-seed deterministic replay has no compared-field divergence. "
            "Next gate is multi-seed deterministic parity before any PPO training use."
        )
    field = divergence.get("field", "unknown")
    step = divergence.get("step", "unknown")
    return (
        f"Keep first-divergence parity hardening. Current first divergence is {field} at step {step}; "
        "isolate that transition before using this simulator for PPO rollouts."
    )


def _resource_snapshot() -> dict[str, Any]:
    return {
        "nvidia_smi": _nvidia_smi(),
        "process_rss_mb": _current_process_rss_mb(),
        "logical_cpu_count": os.cpu_count(),
    }


def _nvidia_smi() -> dict[str, Any] | None:
    query = "utilization.gpu,memory.used,memory.total"
    try:
        proc = subprocess.run(
            ["nvidia-smi", f"--query-gpu={query}", "--format=csv,noheader,nounits"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    parts = [part.strip() for part in proc.stdout.strip().split(",")]
    if len(parts) < 3:
        return {"raw": proc.stdout.strip()}
    return {
        "gpu_util_percent": _safe_float(parts[0]),
        "gpu_memory_used_mb": _safe_float(parts[1]),
        "gpu_memory_total_mb": _safe_float(parts[2]),
    }


def _current_process_rss_mb() -> float | None:
    try:
        import psutil  # type: ignore

        return float(psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024))
    except Exception:
        return None


def _inventory_projection(farm: dict[str, Any]) -> dict[str, float]:
    inventory = farm.get("inventory", farm.get("inventories", farm.get("warehouse", {})))
    result = {product: 0.0 for product in PRODUCTS}
    if isinstance(inventory, dict):
        for product in PRODUCTS:
            result[product] = round(_number_at(inventory, product, 0.0), 4)
    return result


def _market_prices(obs: dict[str, Any]) -> dict[str, float]:
    market = obs.get("market", {}) if isinstance(obs, dict) else {}
    prices = market.get("prices", market) if isinstance(market, dict) else {}
    return {product: round(_number_at(prices, product, 0.0), 4) for product in MARKET_PRODUCTS}


def _sim_market_prices(sim: PairedSimV2Engine) -> dict[str, float]:
    prices = {product: round(float(sim.market_prices[idx]), 4) for idx, product in enumerate(PRODUCTS)}
    return {product: round(float(prices.get(product, 0.0)), 4) for product in MARKET_PRODUCTS}


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


def _worker_count(farm: dict[str, Any]) -> int:
    workers = farm.get("workers", farm.get("hands", []))
    if isinstance(workers, list):
        return len(workers)
    try:
        return int(workers)
    except (TypeError, ValueError):
        return 0


def _land_count(farm: dict[str, Any]) -> int:
    for key in ("land", "land_count"):
        if key in farm:
            try:
                return int(farm[key])
            except (TypeError, ValueError):
                pass
    quadrants = farm.get("unlocked_quadrants")
    if isinstance(quadrants, list):
        return len(quadrants)
    tiles = farm.get("tiles")
    if isinstance(tiles, list):
        return sum(1 for row in tiles if isinstance(row, list) for tile in row if tile is not None)
    return 0


def _count_value(value: Any) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, list):
        return len(value)
    if isinstance(value, dict):
        return int(bool(value))
    return 0


def _number_at(mapping: Any, key: str, default: float) -> float:
    if isinstance(mapping, dict):
        for candidate in (key, key.lower(), key.upper(), key.capitalize()):
            if candidate in mapping:
                try:
                    return float(mapping[candidate])
                except (TypeError, ValueError):
                    return default
    return default


def _command(entry: Any) -> str | None:
    if isinstance(entry, (list, tuple)) and entry:
        return str(entry[0])
    if isinstance(entry, str):
        return entry
    return None


def _load_agent(path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(f"step3h_agent_{path.stem}_{time.time_ns()}", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load agent from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.agent


def _observation(agent_state: Any) -> dict[str, Any]:
    obs = getattr(agent_state, "observation", {})
    return obs if isinstance(obs, dict) else {}


def _is_done(state: list[Any]) -> bool:
    return any(getattr(agent_state, "status", "ACTIVE") != "ACTIVE" for agent_state in state)


def _safe_list(*values: Any) -> list[Any]:
    return [None if value is None else round(float(value), 4) for value in values]


def _safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Step 3H GPU/vector simulator parity audit.")
    parser.add_argument("--seed", type=int, default=39000)
    parser.add_argument("--steps", type=int, default=40)
    parser.add_argument("--batch-size", type=int, default=4096)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    report = run_step3h_parity_audit(
        seed=args.seed,
        steps=args.steps,
        batch_size=args.batch_size,
        report_path=args.report,
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
