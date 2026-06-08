import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import validate_vault as vv


def _vault(tmp_path: Path) -> Path:
    """A minimal, valid vault: a few non-empty notes in typical dirs."""
    (tmp_path / "people").mkdir()
    (tmp_path / "misc").mkdir()
    (tmp_path / "people" / "Real Person.md").write_text("# Real Person\nbody\n")
    (tmp_path / "misc" / "A Note.md").write_text("content\n")
    return tmp_path


def test_find_empty_notes_flags_zero_byte_note(tmp_path):
    vault = _vault(tmp_path)
    (vault / "people" / "Empty.md").write_text("")
    found = vv.find_empty_notes(vault)
    assert vault / "people" / "Empty.md" in found


def test_find_empty_notes_flags_whitespace_only_note(tmp_path):
    vault = _vault(tmp_path)
    (vault / "misc" / "Blank.md").write_text("   \n\t\n")
    found = vv.find_empty_notes(vault)
    assert vault / "misc" / "Blank.md" in found


def test_find_empty_notes_ignores_nonempty_and_dotdirs(tmp_path):
    vault = _vault(tmp_path)
    (vault / ".obsidian").mkdir()
    (vault / ".obsidian" / "Empty In Dotdir.md").write_text("")  # excluded
    found = vv.find_empty_notes(vault)
    assert found == []
    assert vault / ".obsidian" / "Empty In Dotdir.md" not in found


def test_find_duplicate_basenames_flags_collision(tmp_path):
    vault = _vault(tmp_path)
    (vault / "engagements").mkdir()
    (vault / "engagements" / "Dup.md").write_text("stub\n")
    (vault / "misc" / "Dup.md").write_text("rich\n")
    dups = vv.find_duplicate_basenames(vault)
    names = [name for name, _ in dups]
    assert names == ["Dup.md"]
    paths = dict(dups)["Dup.md"]
    assert (vault / "engagements" / "Dup.md") in paths
    assert (vault / "misc" / "Dup.md") in paths


def test_find_duplicate_basenames_ignores_unique(tmp_path):
    vault = _vault(tmp_path)  # _vault basenames ("Real Person.md", "A Note.md") are all unique
    assert vv.find_duplicate_basenames(vault) == []


def test_find_duplicate_basenames_ignores_dotdirs(tmp_path):
    vault = _vault(tmp_path)
    (vault / ".obsidian").mkdir()
    (vault / ".obsidian" / "A Note.md").write_text("config copy\n")  # collides by name but is in a dot-dir
    assert vv.find_duplicate_basenames(vault) == []
