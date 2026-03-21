"""Netlify Function entry point — wraps the FastAPI app via Mangum (ASGI-to-Lambda adapter).

This file is the AWS Lambda / Netlify Function handler for the Iris API.
The backend Python package is bundled via netlify.toml `included_files`.

See docs/deployment-netlify-supabase.md for deployment instructions.
"""

from __future__ import annotations

import os
import sys

# Add the bundled backend package to the module search path.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../backend"))

from mangum import Mangum  # noqa: E402 (import after sys.path modification)

from app.main import create_app  # noqa: E402

# Mangum adapts ASGI (FastAPI) to the AWS Lambda / Netlify Function event format.
# lifespan="auto" runs FastAPI startup/shutdown events on first invocation / container recycle.
handler = Mangum(create_app(), lifespan="auto")
