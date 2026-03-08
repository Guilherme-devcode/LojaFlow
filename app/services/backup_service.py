"""Database backup service."""
from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

from app.database import get_db_path


def create_backup(destination_dir: Path | None = None) -> Path:
    """Copy the SQLite database to destination_dir with a timestamp filename.

    Returns the path of the created backup file.
    """
    db_path = get_db_path()
    if not db_path.exists():
        raise FileNotFoundError(f"Banco de dados não encontrado: {db_path}")

    if destination_dir is None:
        destination_dir = db_path.parent / "backups"

    destination_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"lojaflow_backup_{timestamp}.db"
    backup_path = destination_dir / backup_name

    shutil.copy2(db_path, backup_path)
    return backup_path


def list_backups(backup_dir: Path | None = None) -> list[Path]:
    """Return existing backup files sorted by modification time (newest first)."""
    if backup_dir is None:
        backup_dir = get_db_path().parent / "backups"

    if not backup_dir.exists():
        return []

    return sorted(backup_dir.glob("lojaflow_backup_*.db"), key=lambda p: p.stat().st_mtime, reverse=True)
