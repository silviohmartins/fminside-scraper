"""
CLI legado — use preferencialmente:

  python -m fminside.cli --club "Real Madrid"
  python -m fminside.cli --league "Premier League"

Ou a app web:

  uvicorn app.main:app --reload
"""

from __future__ import annotations

import sys

from fminside.cli import main

if __name__ == "__main__":
    sys.exit(main())
