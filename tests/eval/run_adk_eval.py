from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from prepare_eval_assets import main as prepare_eval_assets

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EVALSET_PATH = Path("tests/eval/generated/core_historians.evalset.json")
CONFIG_PATH = Path("tests/eval/eval_config.json")
EVAL_IDS = ["recent_history", "symbol_intent", "keyword_evolution"]


def run_eval(eval_id: str) -> int:
    print(f"\n=== Running eval: {eval_id} ===")
    result = subprocess.run(
        [
            "uv",
            "run",
            "adk",
            "eval",
            "./app",
            f"{EVALSET_PATH}:{eval_id}",
            f"--config_file_path={CONFIG_PATH}",
            "--print_detailed_results",
        ],
        cwd=PROJECT_ROOT,
        check=False,
    )
    return result.returncode


def main() -> None:
    prepare_eval_assets()

    failures = []
    for eval_id in EVAL_IDS:
        exit_code = run_eval(eval_id)
        if exit_code != 0:
            failures.append(eval_id)

    if failures:
        print(f"\nEval failures: {', '.join(failures)}", file=sys.stderr)
        raise SystemExit(1)

    print("\nAll ADK eval cases passed.")


if __name__ == "__main__":
    main()
