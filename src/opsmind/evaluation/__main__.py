"""Command-line entry point for reproducible forecast evaluation."""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import cast

from opsmind.evaluation.datasets import DATASET_VERSION, build_phase4_dataset
from opsmind.evaluation.forecast import (
    EvaluationConfiguration,
    evaluate_baseline_forecast,
)
from opsmind.evaluation.reporting import render_json, render_markdown

JSON_FILENAME = "evaluation.json"
MARKDOWN_FILENAME = "evaluation.md"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate the deterministic OpsMind simple-mean forecast against "
            "the governed synthetic Phase 4 dataset."
        )
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Directory for evaluation.json and evaluation.md.",
    )
    parser.add_argument(
        "--lookback-observations",
        type=int,
        default=7,
    )
    parser.add_argument(
        "--horizon-days",
        type=int,
        default=7,
    )
    parser.add_argument(
        "--minimum-training-observations",
        type=int,
        default=7,
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace existing evaluation artifacts.",
    )
    return parser


def _write_artifacts(
    *,
    output_dir: Path,
    json_text: str,
    markdown_text: str,
    force: bool,
) -> tuple[Path, Path]:
    json_path = output_dir / JSON_FILENAME
    markdown_path = output_dir / MARKDOWN_FILENAME
    existing = tuple(path for path in (json_path, markdown_path) if path.exists())
    if existing and not force:
        joined = ", ".join(str(path) for path in existing)
        raise FileExistsError(
            f"refusing to overwrite existing evaluation artifacts: {joined}"
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    json_temp = output_dir / f".{JSON_FILENAME}.tmp"
    markdown_temp = output_dir / f".{MARKDOWN_FILENAME}.tmp"

    try:
        json_temp.write_text(json_text, encoding="utf-8")
        markdown_temp.write_text(markdown_text, encoding="utf-8")
        json_temp.replace(json_path)
        markdown_temp.replace(markdown_path)
    finally:
        json_temp.unlink(missing_ok=True)
        markdown_temp.unlink(missing_ok=True)

    return json_path, markdown_path


def main(argv: Sequence[str] | None = None) -> int:
    """Run the governed synthetic evaluation and write its artifacts."""
    namespace = _parser().parse_args(argv)
    output_dir = cast(Path, namespace.output_dir)
    force = cast(bool, namespace.force)

    try:
        configuration = EvaluationConfiguration(
            lookback_observations=cast(
                int,
                namespace.lookback_observations,
            ),
            horizon_days=cast(int, namespace.horizon_days),
            minimum_training_observations=cast(
                int,
                namespace.minimum_training_observations,
            ),
        )
        result = evaluate_baseline_forecast(
            dataset_version=DATASET_VERSION,
            series=build_phase4_dataset(),
            configuration=configuration,
        )
        json_path, markdown_path = _write_artifacts(
            output_dir=output_dir,
            json_text=render_json(result),
            markdown_text=render_markdown(result),
            force=force,
        )
    except (OSError, TypeError, ValueError) as error:
        print(f"Evaluation failed: {error}", file=sys.stderr)
        return 2

    print(json_path)
    print(markdown_path)
    if result.valid_windows == 0:
        print(
            "Evaluation produced zero valid windows and cannot support "
            "Phase 4 completion.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
