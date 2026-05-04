"""Regenerate `iris_client.models.generated` from a running backend's OpenAPI.

Invoked via `uv run iris-client-regen`. See SPEC-132-A.

Requires the `dev` extra to be installed (for `datamodel-code-generator`).
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    url = os.environ.get("IRIS_URL", "http://localhost:8000")
    schema_url = f"{url.rstrip('/')}/api/openapi.json"

    output = Path(__file__).resolve().parent.parent / "models" / "generated.py"
    output.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "datamodel-codegen",
        "--url", schema_url,
        "--output", str(output),
        "--output-model-type", "pydantic_v2.BaseModel",
        "--target-python-version", "3.12",
        "--use-standard-collections",
        "--use-union-operator",
        "--disable-timestamp",
    ]
    print(f"Regenerating {output} from {schema_url}")
    try:
        subprocess.run(cmd, check=True)
    except FileNotFoundError:
        print(
            "datamodel-codegen not found. Install the dev extra:\n"
            "  uv sync --extra dev\n",
            file=sys.stderr,
        )
        return 2
    except subprocess.CalledProcessError as exc:
        print(f"datamodel-codegen failed: {exc}", file=sys.stderr)
        return exc.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
