"""Export the canonical FastAPI OpenAPI document deterministically."""

import argparse
import json
from pathlib import Path

from opsmind.application import create_app


def export_openapi(output: Path) -> None:
    """Write a stable UTF-8 OpenAPI document from the application factory."""
    document = create_app().openapi()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    """Parse the bounded output location and export the schema."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("frontend/openapi/openapi.json"),
    )
    arguments = parser.parse_args()
    export_openapi(arguments.output)


if __name__ == "__main__":
    main()
