"""Create immutable source snapshots and evidence manifests for CUDA engine stages."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE = PROJECT_ROOT / "apex_next" / "gpu_engine" / "paired_gpu_v25" / "corrected_cuda_engine.py"
DEFAULT_OUTPUT = PROJECT_ROOT / "reports" / "step3h" / "source_snapshots"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def command_output(*args: str) -> str | None:
    try:
        return subprocess.check_output(args, cwd=PROJECT_ROOT, text=True, stderr=subprocess.STDOUT).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def runtime_info() -> dict[str, object]:
    info: dict[str, object] = {
        "python_version": sys.version,
        "platform": platform.platform(),
        "pytorch_version": None,
        "cuda_version": None,
        "cuda_available": False,
        "gpu_name": None,
    }
    try:
        import torch

        info["pytorch_version"] = torch.__version__
        info["cuda_version"] = torch.version.cuda
        info["cuda_available"] = bool(torch.cuda.is_available())
        if torch.cuda.is_available():
            info["gpu_name"] = torch.cuda.get_device_name(0)
    except Exception as exc:  # Snapshotting must still work in a CPU-only shell.
        info["runtime_probe_error"] = f"{type(exc).__name__}: {exc}"
    return info


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--label", required=True, help="Immutable filename label, e.g. GOLDEN_0p668")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--optimization-stage", default="unspecified")
    parser.add_argument("--parent-sha256")
    parser.add_argument("--parity-report")
    parser.add_argument("--performance-report")
    parser.add_argument("--benchmark-parameters")
    parser.add_argument("--status", choices=["golden", "recovery-only", "candidate"], default="candidate")
    args = parser.parse_args()

    source = args.source.resolve()
    output_dir = args.output_dir.resolve()
    if not source.is_file():
        raise SystemExit(f"Source file does not exist: {source}")
    output_dir.mkdir(parents=True, exist_ok=True)

    snapshot = output_dir / f"corrected_cuda_engine_{args.label}.py"
    manifest = output_dir / f"corrected_cuda_engine_{args.label}.json"
    if snapshot.exists() or manifest.exists():
        raise SystemExit(f"Refusing to overwrite existing snapshot: {snapshot}")

    source_hash = sha256(source)
    shutil.copy2(source, snapshot)
    manifest_data = {
        "status": args.status,
        "source_path": str(source),
        "snapshot_path": str(snapshot),
        "sha256": source_hash,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "optimization_stage": args.optimization_stage,
        "parent_snapshot_sha256": args.parent_sha256,
        "parity_report_path": args.parity_report,
        "performance_report_path": args.performance_report,
        "benchmark_parameters": args.benchmark_parameters,
        "runtime": runtime_info(),
        "git_status": command_output("git", "status", "--short"),
        "git_commit": command_output("git", "rev-parse", "HEAD"),
    }
    manifest.write_text(json.dumps(manifest_data, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"snapshot": str(snapshot), "manifest": str(manifest), "sha256": source_hash}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
