"""Compress backup outputs into tar.gz archives."""

from __future__ import annotations

import logging
import shutil
import tarfile
from pathlib import Path

logger = logging.getLogger(__name__)


def compress_directory(source: Path, dest_archive: Path) -> Path:
    """Compress *source* directory into a ``.tar.gz`` archive at *dest_archive*.

    After successful compression the original directory is removed.
    Returns the path to the created archive.
    """
    # Safety: ensure source doesn't escape the archive destination's parent tree
    try:
        source.resolve().relative_to(dest_archive.parent.resolve())
    except ValueError:
        raise ValueError(
            f"Refusing to compress/delete '{source}': it is not under '{dest_archive.parent}'"
        )

    if not str(dest_archive).endswith(".tar.gz"):
        dest_archive = Path(str(dest_archive) + ".tar.gz")
    dest_archive.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(dest_archive, "w:gz") as tar:
        tar.add(str(source), arcname=source.name)

    # Verify the archive is readable before deleting the source
    try:
        with tarfile.open(dest_archive, "r:gz") as tar:
            tar.getmembers()
    except (tarfile.TarError, OSError) as exc:
        raise OSError(
            f"Archive verification failed for '{dest_archive}': {exc}"
        ) from exc

    shutil.rmtree(source)
    logger.info("Compressed '%s' → %s", source.name, dest_archive)
    return dest_archive


def compress_repos(projects_dir: Path) -> int:
    """Compress each individual git mirror-clone directory under every project.

    Looks for ``{project}/git/{repo}/`` directories and replaces each with
    ``{repo}.tar.gz``.  Returns the number of archives created.
    """
    count = 0
    if not projects_dir.exists():
        return count
    for project_dir in sorted(projects_dir.iterdir()):
        git_dir = project_dir / "git"
        if not git_dir.is_dir():
            continue
        for entry in sorted(git_dir.iterdir()):
            if entry.is_dir():
                compress_directory(entry, git_dir / f"{entry.name}.tar.gz")
                count += 1
    return count


def compress_projects(projects_dir: Path) -> int:
    """Compress each project directory into ``{project}.tar.gz``.

    Returns the number of archives created.
    """
    count = 0
    if not projects_dir.exists():
        return count
    for entry in sorted(projects_dir.iterdir()):
        if entry.is_dir():
            compress_directory(entry, projects_dir / f"{entry.name}.tar.gz")
            count += 1
    return count


def compress_all(base_dir: Path) -> Path:
    """Compress the entire backup directory into a single archive.

    Creates ``{base_dir}.tar.gz`` alongside *base_dir* and removes the
    original directory.
    """
    return compress_directory(base_dir, base_dir.parent / f"{base_dir.name}.tar.gz")
