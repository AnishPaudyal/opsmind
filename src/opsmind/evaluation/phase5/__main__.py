"""Command-line entry point for governed Phase 5 evaluation."""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from opsmind.evaluation.phase5.evaluation import evaluate_phase5_scenarios
from opsmind.evaluation.phase5.reporting import render_json, render_markdown
from opsmind.evaluation.phase5.scenarios import DATASET_VERSION, build_phase5_scenarios

JSON_FILENAME = "phase5-evaluation.json"
MARKDOWN_FILENAME = "phase5-evaluation.md"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate the governed deterministic Phase 5 stockout and reorder "
            "scenario dataset."
        )
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        type=Path,
        help="Directory in which deterministic evaluation artifacts are written.",
    )
    return parser


def _write_artifacts(
    *,
    output_dir: Path,
    json_text: str,
    markdown_text: str,
) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / JSON_FILENAME
    markdown_path = output_dir / MARKDOWN_FILENAME
    existing = [path for path in (json_path, markdown_path) if path.exists()]
    if existing:
        names = ", ".join(path.name for path in existing)
        raise FileExistsError(
            f"refusing to overwrite existing Phase 5 artifact(s): {names}"
        )
    json_path.write_text(json_text, encoding="utf-8")
    markdown_path.write_text(markdown_text, encoding="utf-8")
    return json_path, markdown_path


def main(argv: Sequence[str] | None = None) -> int:
    """Run the deterministic Phase 5 scenario-conformance evaluation."""

    args = _parser().parse_args(argv)
    try:
        result = evaluate_phase5_scenarios(
            dataset_version=DATASET_VERSION,
            scenarios=build_phase5_scenarios(),
        )
        json_path, markdown_path = _write_artifacts(
            output_dir=args.output_dir,
            json_text=render_json(result),
            markdown_text=render_markdown(result),
        )
    except (FileExistsError, ValueError) as error:
        print(f"Phase 5 evaluation failed: {error}", file=sys.stderr)
        return 2

    print(json_path)
    print(markdown_path)
    return 0 if result.summary.failed_scenario_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
