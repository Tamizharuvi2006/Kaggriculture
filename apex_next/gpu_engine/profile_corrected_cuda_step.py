"""Profile the corrected CUDA step without changing simulator semantics."""

from __future__ import annotations

import argparse
import cProfile
import io
import json
import pstats
import re
import sys
import time
from pathlib import Path

import torch

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from apex_next.gpu_engine.paired_gpu_v25.corrected_cuda_engine import CorrectedCudaPairedEngine  # noqa: E402


DEFAULT_TRACE = PROJECT_ROOT / "reports" / "step3h" / "traces" / "step3h_real_action_traces" / "real_action_trace_seed_39000_steps_720.json"
DEFAULT_REPORT = PROJECT_ROOT / "reports" / "step3h" / "profiles" / "STEP3H8M_CORRECTED_CUDA_STEP_PROFILE.json"
ENGINE_PATH = PROJECT_ROOT / "apex_next" / "gpu_engine" / "paired_gpu_v25" / "corrected_cuda_engine.py"


def _load_actions(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    actions = payload["actions"]
    if len(actions) < 24:
        raise ValueError("Profile trace must contain at least 24 actions")
    return actions


def _static_hotspots() -> dict[str, object]:
    text = ENGINE_PATH.read_text(encoding="utf-8").splitlines()
    patterns = {
        "python_for_loops": r"\bfor\s+",
        "tensor_item_calls": r"\.item\(\)",
        "tensor_cpu_calls": r"\.cpu\(\)",
        "tensor_to_calls": r"\.to\(",
        "tensor_allocations": r"torch\.(tensor|zeros|ones|full|arange|stack|cat|maximum|minimum)\(",
        "cuda_sync_calls": r"cuda\.synchronize|synchronize\(",
    }
    matches: dict[str, list[int]] = {}
    for label, pattern in patterns.items():
        matches[label] = [idx + 1 for idx, line in enumerate(text) if re.search(pattern, line)]
    return {
        "engine_file": str(ENGINE_PATH),
        "counts": {label: len(lines) for label, lines in matches.items()},
        "line_numbers": matches,
    }


def _profile(batch_size: int, steps: int, actions: list[dict]) -> dict[str, object]:
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is unavailable; refusing to profile a CPU fallback")
    device = torch.device("cuda:0")
    engine = CorrectedCudaPairedEngine(batch_size=batch_size, base_seed=39000, device=device)
    engine.reset(list(range(39000, 39000 + batch_size)))
    batch_actions = [actions[idx] for idx in range(steps)]

    profile = cProfile.Profile()
    if engine.actual_cuda_used:
        torch.cuda.synchronize(device)
    started = time.perf_counter()
    profile.enable()
    for action in batch_actions:
        p0 = [action["p0"] for _ in range(batch_size)]
        p1 = [action["p1"] for _ in range(batch_size)]
        engine.step_integrated(p0, p1)
    profile.disable()
    if engine.actual_cuda_used:
        torch.cuda.synchronize(device)
    elapsed = time.perf_counter() - started

    stream = io.StringIO()
    stats = pstats.Stats(profile, stream=stream).strip_dirs().sort_stats("cumtime")
    stats.print_stats(40)
    return {
        "batch_size": batch_size,
        "steps_profiled": steps,
        "total_steps": batch_size * steps,
        "wall_time_seconds": round(elapsed, 6),
        "steps_per_second": round(batch_size * steps / elapsed, 3),
        "actual_cuda_used": bool(engine.actual_cuda_used),
        "tensor_device": str(engine.money.device),
        "cprofile_top_40_cumulative": stream.getvalue(),
        "cuda_memory_allocated_mb": round(torch.cuda.memory_allocated(device) / (1024 * 1024), 3),
        "cuda_max_memory_allocated_mb": round(torch.cuda.max_memory_allocated(device) / (1024 * 1024), 3),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace", type=Path, default=DEFAULT_TRACE)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--steps", type=int, default=24)
    args = parser.parse_args()

    actions = _load_actions(args.trace)
    report = {
        "status": "PASS",
        "step": "STEP 3H-8M - Corrected CUDA step profile",
        "scope": "short diagnostic profile only; no semantics changed; no PPO rollout",
        "cuda_available": torch.cuda.is_available(),
        "cuda_device_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        "static_hotspots": _static_hotspots(),
        "runtime": _profile(args.batch_size, args.steps, actions),
        "recommendation": "Optimize the highest cumulative-time Python/object paths, then rerun cached 20-seed parity before benchmarking again.",
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"status": report["status"], "report": str(args.report), "wall_time_seconds": report["runtime"]["wall_time_seconds"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
