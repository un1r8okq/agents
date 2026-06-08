import io
import os
import subprocess
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


def test_find_duplicate_basenames_ignores_readme(tmp_path):
    vault = _vault(tmp_path)
    (vault / "meta").mkdir()
    (vault / "README.md").write_text("root readme\n")
    (vault / "meta" / "README.md").write_text("meta readme\n")
    assert vv.find_duplicate_basenames(vault) == []


def test_read_cwd_parses_json(tmp_path):
    assert vv.read_cwd('{"cwd": "/c/notes"}') == "/c/notes"


def test_read_cwd_falls_back_to_getcwd_on_garbage(monkeypatch):
    monkeypatch.chdir("/")
    assert vv.read_cwd("not json") == os.getcwd()
    assert vv.read_cwd("") == os.getcwd()


def test_in_scope_accepts_inside_vault_rejects_outside(tmp_path):
    vault = tmp_path / "vault"
    repo = tmp_path / "repo"
    other = tmp_path / "other"
    for d in (vault, repo, other):
        d.mkdir()
    (vault / "daily").mkdir()
    assert vv.in_scope(str(vault), vault, repo) is True            # vault root
    assert vv.in_scope(str(vault / "daily"), vault, repo) is True  # inside vault
    assert vv.in_scope(str(repo / "skills"), vault, repo) is True  # inside skills repo
    assert vv.in_scope(str(other), vault, repo) is False           # outside both
    assert vv.in_scope(str(repo), vault, repo) is True             # skills repo root


def test_resolve_vault_from_env(tmp_path, monkeypatch):
    monkeypatch.setenv("OBSIDIAN_VAULT", str(tmp_path))
    monkeypatch.delenv("CLAUDE_ENV_FILE", raising=False)
    assert vv.resolve_vault() == tmp_path


def test_resolve_vault_none_when_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("OBSIDIAN_VAULT", str(tmp_path / "nope"))
    monkeypatch.delenv("CLAUDE_ENV_FILE", raising=False)
    assert vv.resolve_vault() is None


def test_resolve_vault_from_claude_env_file(tmp_path, monkeypatch):
    vault = tmp_path / "v"
    vault.mkdir()
    env_file = tmp_path / "persist.sh"
    env_file.write_text(f'export OBSIDIAN_VAULT="{vault}"\n')
    monkeypatch.delenv("OBSIDIAN_VAULT", raising=False)
    monkeypatch.setenv("CLAUDE_ENV_FILE", str(env_file))
    assert vv.resolve_vault() == vault


def test_format_report_empty_when_clean(tmp_path):
    assert vv.format_report([], [], tmp_path) == ""


def test_format_report_lists_findings(tmp_path):
    (tmp_path / "people").mkdir()
    empty = tmp_path / "people" / "Empty.md"
    empty.write_text("")
    report = vv.format_report(
        [empty], [("Dup.md", [tmp_path / "misc" / "Dup.md", tmp_path / "engagements" / "Dup.md"])], tmp_path
    )
    assert "people/Empty.md" in report
    assert 'Duplicate basename "Dup.md"' in report
    assert "do NOT auto-edit" in report
    assert "no content" in report
    assert "0 bytes" not in report


def test_read_cwd_falls_back_when_json_is_not_object(monkeypatch):
    monkeypatch.chdir("/")
    assert vv.read_cwd("[]") == os.getcwd()
    assert vv.read_cwd("42") == os.getcwd()


HOOK = os.path.join(os.path.dirname(__file__), "validate_vault.py")


def _run(stdin_text, env_extra):
    env = dict(os.environ)
    env.pop("OBSIDIAN_VAULT", None)
    env.pop("CLAUDE_ENV_FILE", None)
    env.update(env_extra)
    return subprocess.run(
        [sys.executable, HOOK],
        input=stdin_text, capture_output=True, text=True, env=env,
    )


def test_hook_reports_findings_when_cwd_in_vault(tmp_path):
    (tmp_path / "people").mkdir()
    (tmp_path / "people" / "Empty.md").write_text("")
    r = _run(f'{{"cwd": "{tmp_path}"}}', {"OBSIDIAN_VAULT": str(tmp_path)})
    assert r.returncode == 0
    assert "people/Empty.md" in r.stdout
    assert r.stderr == ""


def test_hook_silent_when_cwd_outside_scope(tmp_path):
    (tmp_path / "people").mkdir()
    (tmp_path / "people" / "Empty.md").write_text("")
    outside = tmp_path.parent
    r = _run(f'{{"cwd": "{outside}"}}', {"OBSIDIAN_VAULT": str(tmp_path)})
    assert r.returncode == 0
    assert r.stdout == ""


def test_hook_silent_when_clean(tmp_path):
    (tmp_path / "misc").mkdir()
    (tmp_path / "misc" / "Fine.md").write_text("ok\n")
    r = _run(f'{{"cwd": "{tmp_path}"}}', {"OBSIDIAN_VAULT": str(tmp_path)})
    assert r.returncode == 0
    assert r.stdout == ""


def test_hook_exit_zero_with_fallback_cwd_when_stdin_malformed(tmp_path):
    # malformed stdin -> read_cwd falls back to os.getcwd(); still exits 0
    r = _run("not json at all", {"OBSIDIAN_VAULT": str(tmp_path)})
    assert r.returncode == 0
    assert r.stdout == ""


def test_hook_exit_zero_when_vault_unset(tmp_path):
    r = _run(f'{{"cwd": "{tmp_path}"}}', {})
    assert r.returncode == 0
    assert r.stdout == ""


def test_main_returns_zero_when_a_check_raises(tmp_path, monkeypatch):
    # Force an exception inside main()'s body; the never-fail guard must still return 0.
    def _boom(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setenv("OBSIDIAN_VAULT", str(tmp_path))
    monkeypatch.delenv("CLAUDE_ENV_FILE", raising=False)
    monkeypatch.setattr(vv, "find_empty_notes", _boom)
    monkeypatch.setattr("sys.stdin", io.StringIO(f'{{"cwd": "{tmp_path}"}}'))
    assert vv.main() == 0
