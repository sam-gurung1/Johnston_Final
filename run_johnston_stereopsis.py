"""Entry point script for the Johnston (1991) stereopsis task.

This small wrapper simply dispatches to :mod:`johnston_rds.cli`.  Keeping the
actual logic in the package makes it possible to launch the experiment via
``python -m johnston_rds`` *or* by executing this file directly.  The indirection
also prevents path issues that some students encountered when running the script
from a different working directory.
"""
from __future__ import annotations

from johnston_rds.cli import main


if __name__ == "__main__":
    main()
    