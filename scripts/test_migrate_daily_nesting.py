import importlib.util
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
