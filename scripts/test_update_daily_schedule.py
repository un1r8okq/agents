import datetime
import importlib.util
import os
from pathlib import Path

os.environ.setdefault("OBSIDIAN_VAULT", "/tmp/uds-test-vault")

spec = importlib.util.spec_from_file_location(
    "update_daily_schedule", Path(__file__).parent / "update-daily-schedule.py"
)
uds = importlib.util.module_from_spec(spec)
spec.loader.exec_module(uds)


def test_daily_note_path_is_month_nested():
    vault = Path("/tmp/some-vault")
    day = datetime.date(2026, 6, 9)
    assert uds.daily_note_path(vault, day) == vault / "daily" / "2026-06" / "2026-06-09.md"
