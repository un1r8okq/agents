import importlib.util
import tarfile
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "migrate_daily_nesting", Path(__file__).parent / "migrate-daily-nesting.py"
)
mdn = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mdn)


def _fixture(tmp_path: Path) -> Path:
    v = tmp_path / "vault"
    (v / "daily").mkdir(parents=True)
    (v / "daily" / "detail").mkdir()
    (v / "daily" / "transcripts").mkdir()
    (v / "daily" / "2026-05-01.md").write_text("# Notes\n")
    (v / "daily" / "2026-06-02.md").write_text("# Notes\n")
    (v / "daily" / "template.md").write_text("# Notes\n")
    (v / "daily" / "detail" / "2026-05-01-topic.md").write_text("x\n")
    (v / "daily" / "transcripts" / "2026-06-02-mtg-transcript.md").write_text("x\n")
    return v


def test_plan_moves_maps_to_month_folders(tmp_path):
    v = _fixture(tmp_path)
    moves = mdn.plan_moves(v)
    pairs = {(src.relative_to(v).as_posix(), dst.relative_to(v).as_posix()) for src, dst in moves}
    assert ("daily/2026-05-01.md", "daily/2026-05/2026-05-01.md") in pairs
    assert ("daily/2026-06-02.md", "daily/2026-06/2026-06-02.md") in pairs
    assert ("daily/detail/2026-05-01-topic.md", "daily/detail/2026-05/2026-05-01-topic.md") in pairs
    assert (
        "daily/transcripts/2026-06-02-mtg-transcript.md",
        "daily/transcripts/2026-06/2026-06-02-mtg-transcript.md",
    ) in pairs


def test_plan_moves_skips_template_and_nested(tmp_path):
    v = _fixture(tmp_path)
    # already-nested file must not be re-planned (idempotency)
    (v / "daily" / "2026-05").mkdir(exist_ok=True)
    (v / "daily" / "2026-05" / "2026-05-09.md").write_text("# Notes\n")
    srcs = {src.relative_to(v).as_posix() for src, _ in mdn.plan_moves(v)}
    assert "daily/template.md" not in srcs
    assert "daily/2026-05/2026-05-09.md" not in srcs


def test_apply_moves_files_and_verifies(tmp_path):
    v = _fixture(tmp_path)
    moves = mdn.plan_moves(v)
    mdn.apply_moves(moves)
    assert (v / "daily" / "2026-05" / "2026-05-01.md").exists()
    assert not (v / "daily" / "2026-05-01.md").exists()
    assert (v / "daily" / "template.md").exists()  # untouched
    # idempotent: re-planning after apply yields nothing
    assert mdn.plan_moves(v) == []


def test_backup_creates_archive_containing_daily(tmp_path):
    v = _fixture(tmp_path)
    arc = mdn.backup(v)
    assert arc.exists()
    assert arc.parent == v.parent  # archive lives OUTSIDE the vault
    with tarfile.open(arc) as t:
        names = t.getnames()
    assert any(n.startswith("daily/") for n in names)


def test_unparseable_reports_non_dated_non_template(tmp_path):
    v = _fixture(tmp_path)
    (v / "daily" / "notes.md").write_text("x\n")
    names = [p.name for p in mdn.unparseable(v)]
    assert "notes.md" in names
    assert "template.md" not in names


def test_month_of_rejects_impossible_date():
    assert mdn._month_of("2026-02-30-x.md") is None
    assert mdn._month_of("2026-05-01-x.md") == "2026-05"
