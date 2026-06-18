#!/usr/bin/env python3
"""Migrate flat daily/detail/transcript notes into YYYY-MM/ month folders.

The vault is NOT a git repo, so this is the safety net:
  * defaults to --dry-run (prints planned moves, changes nothing)
  * --apply performs the moves, after writing a tarball backup OUTSIDE the vault
  * verifies in-count == out-count and reports leftovers
Idempotent: already-nested files and template.md are skipped, so re-runs are safe.
"""
import argparse
import datetime
import os
import re
import sys
import tarfile
from pathlib import Path

DATE_PREFIX = re.compile(r"(\d{4})-(\d{2})-(\d{2})")
# Directories whose dated *.md files get nested. Each is relative to the vault.
SCAN_DIRS = ("daily", "daily/detail", "daily/transcripts")


def _month_of(name: str) -> str | None:
    """Return 'YYYY-MM' from a filename starting with a YYYY-MM-DD date, else None."""
    m = DATE_PREFIX.match(name)
    if not m:
        return None
    try:
        datetime.date(int(m[1]), int(m[2]), int(m[3]))
    except ValueError:
        return None
    return f"{m[1]}-{m[2]}"


def plan_moves(vault: Path) -> list[tuple[Path, Path]]:
    """Return (src, dst) pairs for dated .md files not yet in their month folder."""
    moves = []
    for rel in SCAN_DIRS:
        d = vault / rel
        if not d.is_dir():
            continue
        for child in sorted(d.iterdir()):
            if not child.is_file() or child.suffix != ".md":
                continue
            month = _month_of(child.name)
            if month is None:
                continue  # template.md, non-dated files: leave in place
            dst = d / month / child.name
            if child.resolve() == dst.resolve():
                continue
            moves.append((child, dst))
    return moves


def unparseable(vault: Path) -> list[Path]:
    """Dated-dir .md files at the flat root whose names lack a YYYY-MM-DD prefix."""
    out = []
    for rel in SCAN_DIRS:
        d = vault / rel
        if not d.is_dir():
            continue
        for child in sorted(d.iterdir()):
            if child.is_file() and child.suffix == ".md" and _month_of(child.name) is None:
                if child.name != "template.md":
                    out.append(child)
    return out


def apply_moves(moves: list[tuple[Path, Path]]) -> None:
    """Create month subdirs and rename each (src, dst) pair; raises FileExistsError on collision."""
    for src, dst in moves:
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists():
            raise FileExistsError(f"refusing to overwrite {dst}")
        src.rename(dst)


def backup(vault: Path, backup_dir: Path) -> Path:
    """Tar the daily/ tree to a timestamped archive in backup_dir (which must be
    OUTSIDE the indexed vault and writable). Returns the archive path."""
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y-%m-%d-%H%M%S")
    archive = backup_dir / f"{vault.name}-daily-bak-{stamp}.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        tar.add(vault / "daily", arcname="daily")
    return archive


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true", help="perform moves (default: dry-run)")
    ap.add_argument("--vault", default=os.environ.get("OBSIDIAN_VAULT"))
    ap.add_argument(
        "--backup-dir",
        default=str(Path.home()),
        help="where to write the pre-migration backup tarball (must be outside the vault; default: home dir)",
    )
    args = ap.parse_args(argv)
    if not args.vault:
        print("OBSIDIAN_VAULT not set and --vault not given", file=sys.stderr)
        return 2
    vault = Path(args.vault)
    if not (vault / "daily").is_dir():
        print(f"{vault}/daily not found", file=sys.stderr)
        return 2

    moves = plan_moves(vault)
    skipped = unparseable(vault)
    print(f"Planned moves: {len(moves)}")
    for src, dst in moves:
        print(f"  {src.relative_to(vault)}  ->  {dst.relative_to(vault)}")
    if skipped:
        print(f"Left in place (no YYYY-MM-DD prefix): {len(skipped)}")
        for p in skipped:
            print(f"  {p.relative_to(vault)}")

    if not args.apply:
        print("\nDRY RUN — nothing changed. Re-run with --apply to migrate.")
        return 0

    before = sum(1 for _ in (vault / "daily").rglob("*.md"))
    archive = backup(vault, Path(args.backup_dir))
    print(f"\nBackup written: {archive}")
    apply_moves(moves)
    after = sum(1 for _ in (vault / "daily").rglob("*.md"))
    leftovers = [src for src, _ in plan_moves(vault)]  # should be empty now
    print(f"Moved {len(moves)} file(s). daily/ .md count before={before} after={after}.")
    if before != after:
        print("ERROR: file count changed — investigate against the backup!", file=sys.stderr)
        return 1
    if leftovers:
        print(f"ERROR: {len(leftovers)} file(s) still un-nested — investigate.", file=sys.stderr)
        return 1
    print("OK — counts match, no leftovers.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
