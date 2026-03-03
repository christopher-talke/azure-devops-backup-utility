"""Allow running via ``python src/cli.py`` or as a module entry point."""

import sys

from cli import main

sys.exit(main())
