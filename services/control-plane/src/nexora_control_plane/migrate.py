"""Run database migrations: ``python -m nexora_control_plane.migrate [revision]``.

Reads only ``NEXORA_DATABASE_URL`` (so the migration Job needs no API token).
Idempotent: running at ``head`` is a no-op.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config

from nexora_control_plane.db import create_db_engine

_MIGRATIONS_DIR = Path(__file__).parent / "migrations"


def upgrade(url: str, revision: str = "head") -> None:
    cfg = Config()
    cfg.set_main_option("script_location", str(_MIGRATIONS_DIR))
    engine = create_db_engine(url)
    try:
        with engine.begin() as connection:
            cfg.attributes["connection"] = connection
            command.upgrade(cfg, revision)
    finally:
        engine.dispose()


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    url = os.environ.get("NEXORA_DATABASE_URL")
    if not url:
        sys.stderr.write("NEXORA_DATABASE_URL is required\n")
        return 2
    upgrade(url, args[0] if args else "head")
    sys.stdout.write("migrations applied\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
