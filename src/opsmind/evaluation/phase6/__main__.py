"""CLI for reproducible Phase 6 deterministic workflow evaluation."""

import argparse
from collections.abc import Sequence
from pathlib import Path

from opsmind.evaluation.phase6.evaluation import evaluate_phase6
from opsmind.evaluation.phase6.reporting import render_json, render_markdown

JSON_FILENAME = "phase6-evaluation.json"
MARKDOWN_FILENAME = "phase6-evaluation.md"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate the governed deterministic Phase 6 recommendation workflow."
        )
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Directory for deterministic JSON and Markdown artifacts.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Permit replacement of existing Phase 6 evaluation artifacts.",
    )
    return parser


def _write_artifacts(
    output_dir: Path,
    *,
    json_text: str,
    markdown_text: str,
    overwrite: bool,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / JSON_FILENAME
    markdown_path = output_dir / MARKDOWN_FILENAME

    existing = tuple(path for path in (json_path, markdown_path) if path.exists())
    if existing and not overwrite:
        names = ", ".join(path.name for path in existing)
        raise FileExistsError(
            f"Refusing to overwrite existing evaluation artifact(s): {names}"
        )

    json_path.write_text(json_text, encoding="utf-8")
    markdown_path.write_text(markdown_text, encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    """Run the deterministic Phase 6 evaluator."""
    args = _parser().parse_args(argv)
    evaluation = evaluate_phase6()
    try:
        _write_artifacts(
            args.output_dir,
            json_text=render_json(evaluation),
            markdown_text=render_markdown(evaluation),
            overwrite=args.overwrite,
        )
    except (OSError, ValueError) as error:
        print(f"Phase 6 evaluation failed: {error}")
        return 2

    return 0 if evaluation.failed_scenarios == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
