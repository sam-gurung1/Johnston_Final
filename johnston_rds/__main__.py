"""Allow ``python -m johnston_rds`` to launch the experiment."""
from __future__ import annotations

from .cli import main


if __name__ == "__main__":  # pragma: no cover - module level CLI hook
    main()
    