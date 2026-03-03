"""Allow running as ``python -m ado_backup``."""

import sys

from .cli import main

sys.exit(main())
