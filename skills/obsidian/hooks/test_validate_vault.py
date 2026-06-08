import io
import os
import re
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
    (tmp_path / "misc" / "Fine.md").write_text("---\ndescription: all good\n---\nok\n")
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


def test_read_frontmatter_parses_top_level_keys(tmp_path):
    p = tmp_path / "n.md"
    p.write_text('---\nrole: Lead Engineer\norganisation: "[[ClearPoint]]"\naliases:\n  - Will\n  - Will V\n---\n# Body\n')
    fm = vv._read_frontmatter(p)
    assert fm["role"] == "Lead Engineer"
    assert fm["organisation"] == '"[[ClearPoint]]"'
    assert fm["aliases"] == ""        # key present; its list items are not parsed
    assert "Will" not in fm           # list items never become keys


def test_read_frontmatter_empty_when_no_block(tmp_path):
    p = tmp_path / "n.md"
    p.write_text("# Just a heading\nbody\n")
    assert vv._read_frontmatter(p) == {}


def test_requires_description_by_directory():
    from pathlib import Path as P
    assert vv._requires_description(P("people/Foo.md")) is True
    assert vv._requires_description(P("orgs/Bar.md")) is True
    assert vv._requires_description(P("glossary/x.md")) is True
    assert vv._requires_description(P("misc/y.md")) is True
    assert vv._requires_description(P("engagements/DSO2/context.md")) is True
    assert vv._requires_description(P("daily/detail/2026-01-01-x.md")) is True
    assert vv._requires_description(P("daily/2026-01-01.md")) is False
    assert vv._requires_description(P("daily/transcripts/x.md")) is False
    assert vv._requires_description(P("meta/architecture.md")) is False
    assert vv._requires_description(P("README.md")) is False


def test_read_frontmatter_unclosed_fence_returns_empty(tmp_path):
    p = tmp_path / "n.md"
    p.write_text("---\ntitle: Foo\ndescription: this is body text, not frontmatter\nmore body\n")
    assert vv._read_frontmatter(p) == {}


def test_find_missing_description_flags_entity_without_it(tmp_path):
    (tmp_path / "people").mkdir()
    (tmp_path / "people" / "NoDesc.md").write_text("---\nrole: x\n---\n# body\n")
    (tmp_path / "people" / "HasDesc.md").write_text("---\ndescription: a real person\n---\n# body\n")
    found = vv.find_missing_description(tmp_path)
    assert (tmp_path / "people" / "NoDesc.md") in found
    assert (tmp_path / "people" / "HasDesc.md") not in found


def test_find_missing_description_excludes_daily_and_transcripts(tmp_path):
    (tmp_path / "daily").mkdir()
    (tmp_path / "daily" / "detail").mkdir()
    (tmp_path / "daily" / "transcripts").mkdir()
    (tmp_path / "daily" / "2026-01-01.md").write_text("# Notes\n")
    (tmp_path / "daily" / "transcripts" / "t.md").write_text("raw transcript\n")
    (tmp_path / "daily" / "detail" / "2026-01-01-x.md").write_text("notes\n")
    found = vv.find_missing_description(tmp_path)
    assert (tmp_path / "daily" / "2026-01-01.md") not in found
    assert (tmp_path / "daily" / "transcripts" / "t.md") not in found
    assert (tmp_path / "daily" / "detail" / "2026-01-01-x.md") in found


def test_find_missing_description_uppercase_counts_as_missing(tmp_path):
    (tmp_path / "people").mkdir()
    (tmp_path / "people" / "Upper.md").write_text("---\nDescription: capitalized key\n---\n")
    assert (tmp_path / "people" / "Upper.md") in vv.find_missing_description(tmp_path)


def test_find_uppercase_frontmatter_keys_flags_capitalized(tmp_path):
    (tmp_path / "people").mkdir()
    (tmp_path / "people" / "Drift.md").write_text('---\nRole: x\nOrganisation: "[[Y]]"\ndescription: ok\n---\n')
    found = dict(vv.find_uppercase_frontmatter_keys(tmp_path))
    assert (tmp_path / "people" / "Drift.md") in found
    assert set(found[tmp_path / "people" / "Drift.md"]) == {"Role", "Organisation"}


def test_find_uppercase_frontmatter_keys_ignores_lowercase_and_aliases(tmp_path):
    (tmp_path / "people").mkdir()
    (tmp_path / "people" / "Good.md").write_text('---\nrole: x\ndescription: y\naliases:\n  - Will\n---\n')
    assert vv.find_uppercase_frontmatter_keys(tmp_path) == []


def test_format_report_includes_missing_desc_and_bad_keys(tmp_path):
    (tmp_path / "people").mkdir()
    nodesc = tmp_path / "people" / "NoDesc.md"
    nodesc.write_text("---\nrole: x\n---\n")
    drift = tmp_path / "people" / "Drift.md"
    drift.write_text("---\nRole: x\n---\n")
    report = vv.format_report([], [], tmp_path, missing_desc=[nodesc], bad_keys=[(drift, ["Role"])])
    assert "Missing description: people/NoDesc.md" in report
    assert "Non-lowercase frontmatter keys: people/Drift.md (Role)" in report


def test_format_report_empty_with_all_kwargs_empty(tmp_path):
    assert vv.format_report([], [], tmp_path, missing_desc=[], bad_keys=[]) == ""


def test_hook_reports_missing_description(tmp_path):
    (tmp_path / "people").mkdir()
    (tmp_path / "people" / "NoDesc.md").write_text("---\nrole: x\n---\n")
    r = _run(f'{{"cwd": "{tmp_path}"}}', {"OBSIDIAN_VAULT": str(tmp_path)})
    assert r.returncode == 0
    assert "Missing description: people/NoDesc.md" in r.stdout


def _skill_md_required_rows():
    """Map each `dir`-cell -> Required-cell from SKILL.md's frontmatter table.

    Treats escaped pipes (\\|) inside cells as literal, not column separators.
    Only parses the table that immediately follows 'Required fields per directory'
    to avoid picking up rows from other tables (e.g. the vault-structure table).
    """
    repo = Path(vv.__file__).resolve().parents[3]
    skill = (repo / "skills" / "obsidian" / "SKILL.md").read_text(encoding="utf-8")
    assert "Required fields per directory" in skill
    # Isolate only the lines that belong to the "Required fields" table.
    lines = skill.splitlines()
    in_section = False
    table_lines = []
    for line in lines:
        if "Required fields per directory" in line:
            in_section = True
            continue
        if in_section:
            stripped = line.lstrip()
            if stripped.startswith("|"):
                table_lines.append(line)
            elif table_lines:
                # First non-pipe line after table rows signals end of table.
                break
    rows = {}
    for line in table_lines:
        safe = line.replace(r"\|", "\x00")
        cells = [c.replace("\x00", "|").strip() for c in safe.strip().strip("|").split("|")]
        if len(cells) >= 2 and cells[0].startswith("`"):
            rows[cells[0]] = cells[1]
    return skill, rows


def test_description_required_dirs_match_skill_md():
    skill, rows = _skill_md_required_rows()

    def required_cells_for(token):
        return [req for dircell, req in rows.items() if token in dircell]

    for d in vv.DESCRIPTION_REQUIRED_DIRS:
        cells = required_cells_for(f"`{d}/")
        assert cells, f"no SKILL.md row for {d}/"
        assert all("description:" in c for c in cells), f"{d}/ row(s) no longer require description: in SKILL.md"
    detail = required_cells_for("`daily/detail/`")
    assert detail and all("description:" in c for c in detail), "daily/detail/ must require description:"

    daily_top = rows.get("`daily/`")
    assert daily_top is not None, "no `daily/` row found in SKILL.md table"
    assert "description:" not in daily_top, "daily/ must not require description:"

    assert re.search(r"All keys.*lowercase", skill), "SKILL.md lowercase-keys rule missing"


def test_hook_reports_uppercase_keys(tmp_path):
    (tmp_path / "people").mkdir()
    (tmp_path / "people" / "Drift.md").write_text('---\nRole: x\ndescription: ok\n---\n')
    r = _run(f'{{"cwd": "{tmp_path}"}}', {"OBSIDIAN_VAULT": str(tmp_path)})
    assert r.returncode == 0
    assert "Non-lowercase frontmatter keys: people/Drift.md (Role)" in r.stdout
