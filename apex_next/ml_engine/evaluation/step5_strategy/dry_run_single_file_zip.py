"""Clean import and one-game dry-run for the single-file ZIP."""

from __future__ import annotations

import argparse
import importlib.util
import json
import tempfile
import zipfile
from pathlib import Path


def _load(path: Path):
    spec = importlib.util.spec_from_file_location("single_zip_entrypoint", path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--zip", type=Path, required=True)
    args = parser.parse_args()
    import kaggle_environments

    with tempfile.TemporaryDirectory(prefix="single_zip_dryrun_") as temp:
        root = Path(temp)
        with zipfile.ZipFile(args.zip) as archive:
            names = archive.namelist()
            archive.extractall(root)
        entry = root / "APEX4_PPO_FINAL_SINGLE.py"
        module = _load(entry)
        env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": 79000})
        noop = lambda observation, configuration=None: {"farmer": ["PASS"], "hands": [], "market": []}
        errors = []
        try:
            env.run([module.agent, noop])
        except Exception as exc:
            errors.append(repr(exc))
        print(json.dumps({
            "status": "PASS" if len(names) == 1 and len(env.steps) == 720 and not errors else "FAIL",
            "zip_entries": names,
            "torch_required": False,
            "steps": len(env.steps),
            "errors": errors,
        }, indent=2))


if __name__ == "__main__":
    main()
