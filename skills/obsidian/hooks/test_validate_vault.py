import io
import os
import re
import subprocess
import sys
from datetime import date
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


def _two_engagements_with_context(vault: Path) -> None:
    """Two engagements that each carry a companion context.md (convention-sanctioned
    duplicate basenames) — the setup that makes a bare [[context]] ambiguous."""
    (vault / "engagements" / "Agent OS").mkdir(parents=True)
    (vault / "engagements" / "DSO2").mkdir(parents=True)
    (vault / "engagements" / "Agent OS" / "context.md").write_text("ctx\n")
    (vault / "engagements" / "DSO2" / "context.md").write_text("ctx\n")


def test_find_ambiguous_wikilinks_flags_bare_link_to_dup(tmp_path):
    vault = _vault(tmp_path)
    _two_engagements_with_context(vault)
    (vault / "misc" / "Ref.md").write_text("see [[context]] for priorities\n")
    found = vv.find_ambiguous_wikilinks(vault)
    assert [(p.name, t) for p, t, _ in found] == [("Ref.md", "context")]
    candidates = found[0][2]
    assert len(candidates) == 2
    assert all(c.name == "context.md" for c in candidates)


def test_find_ambiguous_wikilinks_ignores_path_qualified(tmp_path):
    vault = _vault(tmp_path)
    _two_engagements_with_context(vault)
    # already disambiguated with a path prefix -> not flagged
    (vault / "misc" / "Ref.md").write_text("see [[DSO2/context|context]] for priorities\n")
    assert vv.find_ambiguous_wikilinks(vault) == []


def test_find_ambiguous_wikilinks_ignores_unique_stem(tmp_path):
    vault = _vault(tmp_path)
    # [[Real Person]] is a unique stem -> a bare link to it is unambiguous
    (vault / "misc" / "Ref.md").write_text("met [[Real Person]] today\n")
    assert vv.find_ambiguous_wikilinks(vault) == []


def test_find_ambiguous_wikilinks_companion_dups_without_bare_link_ok(tmp_path):
    # Duplicate companion basenames are convention-sanctioned: with no BARE link
    # pointing at the shared name, there is no nondeterministic resolution -> silent.
    vault = _vault(tmp_path)
    for eng in ("Agent OS", "DSO2"):
        (vault / "engagements" / eng).mkdir(parents=True)
        for comp in ("context", "timeline", "decisions", "people"):
            (vault / "engagements" / eng / f"{comp}.md").write_text("body\n")
    (vault / "engagements" / "DSO2" / "DSO2.md").write_text("see [[DSO2/context|context]]\n")
    assert vv.find_ambiguous_wikilinks(vault) == []


def test_find_ambiguous_wikilinks_dedupes_per_note(tmp_path):
    vault = _vault(tmp_path)
    _two_engagements_with_context(vault)
    (vault / "misc" / "Ref.md").write_text("[[context]] then [[context]] then [[context]]\n")
    found = [f for f in vv.find_ambiguous_wikilinks(vault) if f[0].name == "Ref.md"]
    assert len(found) == 1


def test_find_ambiguous_wikilinks_skips_dotdirs(tmp_path):
    vault = _vault(tmp_path)
    _two_engagements_with_context(vault)
    (vault / ".obsidian").mkdir()
    (vault / ".obsidian" / "Cfg.md").write_text("[[context]] in a dot-dir, not scanned\n")
    assert vv.find_ambiguous_wikilinks(vault) == []


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
    ambiguous = [(
        tmp_path / "engagements" / "DSO2" / "DSO2.md",
        "context",
        [tmp_path / "engagements" / "Agent OS" / "context.md",
         tmp_path / "engagements" / "DSO2" / "context.md"],
    )]
    report = vv.format_report([empty], ambiguous, tmp_path)
    assert "people/Empty.md" in report
    assert "Ambiguous wikilink [[context]] in engagements/DSO2/DSO2.md" in report
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


def test_hook_reports_ambiguous_wikilink(tmp_path):
    for eng in ("Agent OS", "DSO2"):
        (tmp_path / "engagements" / eng).mkdir(parents=True)
        (tmp_path / "engagements" / eng / "context.md").write_text("---\ndescription: d\n---\nx\n")
    (tmp_path / "misc").mkdir()
    (tmp_path / "misc" / "Ref.md").write_text("---\ndescription: d\n---\nsee [[context]]\n")
    r = _run(f'{{"cwd": "{tmp_path}"}}', {"OBSIDIAN_VAULT": str(tmp_path)})
    assert r.returncode == 0
    assert "Ambiguous wikilink [[context]] in misc/Ref.md" in r.stdout


def test_hook_silent_when_cwd_outside_scope(tmp_path):
    (tmp_path / "people").mkdir()
    (tmp_path / "people" / "Empty.md").write_text("")
    outside = tmp_path.parent
    r = _run(f'{{"cwd": "{outside}"}}', {"OBSIDIAN_VAULT": str(tmp_path)})
    assert r.returncode == 0
    assert r.stdout == ""


def test_hook_reports_ok_when_clean(tmp_path):
    # Happy path: in scope, scanned, no findings -> positive confirmation with note count.
    (tmp_path / "misc").mkdir()
    (tmp_path / "misc" / "Fine.md").write_text("---\ndescription: all good\n---\nok\n")
    r = _run(f'{{"cwd": "{tmp_path}"}}', {"OBSIDIAN_VAULT": str(tmp_path)})
    assert r.returncode == 0
    assert "vault integrity OK" in r.stdout
    assert "1 note checked" in r.stdout          # singular, exactly one .md note
    assert r.stderr == ""


def test_hook_silent_when_no_notes_to_check(tmp_path):
    # Empty/misconfigured vault: nothing scanned -> no positive message, stays silent.
    r = _run(f'{{"cwd": "{tmp_path}"}}', {"OBSIDIAN_VAULT": str(tmp_path)})
    assert r.returncode == 0
    assert r.stdout == ""


def test_ok_message_count_and_pluralization():
    assert vv._ok_message(142) == "validate-vault: vault integrity OK — 142 notes checked, no issues."
    assert vv._ok_message(1).endswith("1 note checked, no issues.")   # singular
    assert vv._ok_message(0) == ""                                    # nothing scanned -> silent


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


def test_find_wikilinks_in_description_flags_wikilink(tmp_path):
    (tmp_path / "people").mkdir()
    (tmp_path / "people" / "Linked.md").write_text('---\ndescription: "Lead at [[ClearPoint]]"\n---\n# body\n')
    assert (tmp_path / "people" / "Linked.md") in vv.find_wikilinks_in_description(tmp_path)


def test_find_wikilinks_in_description_ignores_plain_and_body_links(tmp_path):
    (tmp_path / "people").mkdir()
    # plain description; the [[ClearPoint]] is in the BODY, which must NOT be flagged
    (tmp_path / "people" / "Plain.md").write_text("---\ndescription: Lead at ClearPoint\n---\n# body [[ClearPoint]]\n")
    assert vv.find_wikilinks_in_description(tmp_path) == []


def test_find_wikilinks_in_description_ignores_no_description(tmp_path):
    (tmp_path / "people").mkdir()
    (tmp_path / "people" / "NoFm.md").write_text("# just body, no frontmatter\n")
    assert vv.find_wikilinks_in_description(tmp_path) == []


def test_format_report_includes_desc_links(tmp_path):
    (tmp_path / "people").mkdir()
    linked = tmp_path / "people" / "Linked.md"
    linked.write_text('---\ndescription: "Lead at [[ClearPoint]]"\n---\n')
    report = vv.format_report([], [], tmp_path, desc_links=[linked])
    assert "Wikilink in description: people/Linked.md" in report


def test_format_report_empty_with_desc_links_empty(tmp_path):
    assert vv.format_report([], [], tmp_path, desc_links=[]) == ""


def test_hook_reports_wikilink_in_description(tmp_path):
    (tmp_path / "people").mkdir()
    (tmp_path / "people" / "Linked.md").write_text('---\ndescription: "Lead at [[ClearPoint]]"\n---\n')
    r = _run(f'{{"cwd": "{tmp_path}"}}', {"OBSIDIAN_VAULT": str(tmp_path)})
    assert r.returncode == 0
    assert "Wikilink in description: people/Linked.md" in r.stdout


def test_find_wikilinks_in_description_ignores_entity_field_wikilinks(tmp_path):
    (tmp_path / "people").mkdir()
    # organisation: legitimately keeps its wikilink; description is plain -> NOT flagged
    (tmp_path / "people" / "Ok.md").write_text('---\norganisation: "[[ClearPoint]]"\ndescription: Lead engineer\n---\n')
    assert vv.find_wikilinks_in_description(tmp_path) == []


def test_required_keys_by_directory():
    from pathlib import Path as P
    assert vv._required_keys(P("people/Foo.md")) == {"organisation", "role"}
    assert vv._required_keys(P("orgs/Bar.md")) == {"relationship"}
    assert vv._required_keys(P("glossary/x.md")) == {"full"}
    assert vv._required_keys(P("engagements/DSO2/DSO2.md")) == {"client", "status"}
    assert vv._required_keys(P("engagements/DSO2/context.md")) == set()
    assert vv._required_keys(P("engagements/DSO2/glossary/MVR.md")) == {"full"}
    assert vv._required_keys(P("misc/x.md")) == set()
    assert vv._required_keys(P("daily/2026-01-01.md")) == set()
    assert vv._required_keys(P("daily/detail/2026-01-01-x.md")) == set()


def test_enum_fields_constant():
    assert vv.ENUM_FIELDS["status"] == {"active", "complete"}
    assert vv.ENUM_FIELDS["relationship"] == {"employer", "client", "partner", "vendor", "organisation"}


def test_find_missing_required_keys_flags_people_missing_role(tmp_path):
    (tmp_path / "people").mkdir()
    (tmp_path / "people" / "NoRole.md").write_text('---\norganisation: "[[X]]"\ndescription: d\n---\n')
    found = dict(vv.find_missing_required_keys(tmp_path))
    assert found[tmp_path / "people" / "NoRole.md"] == ["role"]


def test_find_missing_required_keys_passes_complete_people(tmp_path):
    (tmp_path / "people").mkdir()
    (tmp_path / "people" / "Ok.md").write_text('---\norganisation: "[[X]]"\nrole: Lead\ndescription: d\n---\n')
    assert vv.find_missing_required_keys(tmp_path) == []


def test_find_missing_required_keys_engagement_overview(tmp_path):
    (tmp_path / "engagements" / "DSO2").mkdir(parents=True)
    (tmp_path / "engagements" / "DSO2" / "DSO2.md").write_text("---\ndescription: d\n---\n")
    (tmp_path / "engagements" / "DSO2" / "context.md").write_text("---\ndescription: d\n---\n")
    found = dict(vv.find_missing_required_keys(tmp_path))
    assert found[tmp_path / "engagements" / "DSO2" / "DSO2.md"] == ["client", "status"]
    assert (tmp_path / "engagements" / "DSO2" / "context.md") not in found


def test_find_invalid_enum_values_flags_bad_relationship(tmp_path):
    (tmp_path / "orgs").mkdir()
    (tmp_path / "orgs" / "Bad.md").write_text("---\nrelationship: friend\ndescription: d\n---\n")
    assert (tmp_path / "orgs" / "Bad.md", "relationship", "friend") in vv.find_invalid_enum_values(tmp_path)


def test_find_invalid_enum_values_accepts_valid_quoted_status(tmp_path):
    (tmp_path / "engagements" / "DSO2").mkdir(parents=True)
    (tmp_path / "engagements" / "DSO2" / "DSO2.md").write_text('---\nclient: "[[X]]"\nstatus: "active"\ndescription: d\n---\n')
    assert vv.find_invalid_enum_values(tmp_path) == []


def test_find_invalid_enum_values_flags_bad_status(tmp_path):
    (tmp_path / "engagements" / "DSO2").mkdir(parents=True)
    (tmp_path / "engagements" / "DSO2" / "DSO2.md").write_text('---\nclient: "[[X]]"\nstatus: done\ndescription: d\n---\n')
    assert (tmp_path / "engagements" / "DSO2" / "DSO2.md", "status", "done") in vv.find_invalid_enum_values(tmp_path)


def test_find_invalid_enum_values_ignores_absent_field(tmp_path):
    # relationship absent -> the missing-key check owns that, not the enum check
    (tmp_path / "orgs").mkdir()
    (tmp_path / "orgs" / "NoRel.md").write_text("---\ndescription: d\n---\n")
    assert vv.find_invalid_enum_values(tmp_path) == []


def test_find_invalid_source_flags_wikilink(tmp_path):
    (tmp_path / "orgs").mkdir()
    (tmp_path / "orgs" / "Wikilinked.md").write_text('---\nrelationship: client\ndescription: d\nsource: "[[ClearPoint]]"\n---\n')
    found = dict(vv.find_invalid_source(tmp_path))
    assert (tmp_path / "orgs" / "Wikilinked.md") in found
    assert "wikilink" in found[tmp_path / "orgs" / "Wikilinked.md"]


def test_find_invalid_source_flags_non_url(tmp_path):
    (tmp_path / "people").mkdir()
    (tmp_path / "people" / "BadSource.md").write_text("---\nrole: x\ndescription: d\nsource: clearpoint.digital\n---\n")
    found = dict(vv.find_invalid_source(tmp_path))
    assert (tmp_path / "people" / "BadSource.md") in found
    assert "URL" in found[tmp_path / "people" / "BadSource.md"]


def test_find_invalid_source_accepts_plain_url(tmp_path):
    (tmp_path / "orgs").mkdir()
    (tmp_path / "orgs" / "Ok.md").write_text('---\nrelationship: employer\ndescription: d\nsource: "https://clearpoint.digital"\n---\n')
    assert vv.find_invalid_source(tmp_path) == []


def test_find_invalid_source_ignores_absent_or_empty(tmp_path):
    (tmp_path / "people").mkdir()
    (tmp_path / "people" / "NoSource.md").write_text("---\nrole: x\ndescription: d\n---\n")
    (tmp_path / "people" / "EmptySource.md").write_text('---\nrole: x\ndescription: d\nsource: ""\n---\n')
    assert vv.find_invalid_source(tmp_path) == []


def test_format_report_includes_bad_sources(tmp_path):
    (tmp_path / "orgs").mkdir()
    bad = tmp_path / "orgs" / "Bad.md"
    bad.write_text('---\nrelationship: client\ndescription: d\nsource: "[[X]]"\n---\n')
    report = vv.format_report([], [], tmp_path, bad_sources=[(bad, "contains a wikilink — source must be a plain URL")])
    assert "Invalid source: orgs/Bad.md" in report
    assert "plain URL" in report


def test_hook_reports_invalid_source(tmp_path):
    (tmp_path / "orgs").mkdir()
    (tmp_path / "orgs" / "Bad.md").write_text('---\nrelationship: client\ndescription: d\nsource: "[[X]]"\n---\n')
    r = _run(f'{{"cwd": "{tmp_path}"}}', {"OBSIDIAN_VAULT": str(tmp_path)})
    assert r.returncode == 0
    assert "Invalid source: orgs/Bad.md" in r.stdout


def test_format_report_includes_missing_keys_and_bad_enums(tmp_path):
    (tmp_path / "people").mkdir()
    (tmp_path / "orgs").mkdir()
    nokey = tmp_path / "people" / "NoRole.md"
    nokey.write_text("---\norganisation: x\ndescription: d\n---\n")
    badenum = tmp_path / "orgs" / "Bad.md"
    badenum.write_text("---\nrelationship: friend\ndescription: d\n---\n")
    report = vv.format_report(
        [], [], tmp_path,
        missing_keys=[(nokey, ["role"])],
        bad_enums=[(badenum, "relationship", "friend")],
    )
    assert "Missing required frontmatter: people/NoRole.md (role)" in report
    assert 'Invalid relationship value: orgs/Bad.md ("friend")' in report
    assert "must be one of client, employer, organisation, partner, vendor" in report


def test_format_report_empty_with_inc2b_kwargs_empty(tmp_path):
    assert vv.format_report([], [], tmp_path, missing_keys=[], bad_enums=[]) == ""


def test_hook_reports_missing_required_key(tmp_path):
    (tmp_path / "people").mkdir()
    (tmp_path / "people" / "NoRole.md").write_text("---\norganisation: x\ndescription: d\n---\n")
    r = _run(f'{{"cwd": "{tmp_path}"}}', {"OBSIDIAN_VAULT": str(tmp_path)})
    assert r.returncode == 0
    assert "Missing required frontmatter: people/NoRole.md (role)" in r.stdout


def test_hook_reports_invalid_enum_value(tmp_path):
    (tmp_path / "orgs").mkdir()
    (tmp_path / "orgs" / "Bad.md").write_text("---\nrelationship: friend\ndescription: d\n---\n")
    r = _run(f'{{"cwd": "{tmp_path}"}}', {"OBSIDIAN_VAULT": str(tmp_path)})
    assert r.returncode == 0
    assert 'Invalid relationship value: orgs/Bad.md ("friend")' in r.stdout


def test_read_stdin_returns_empty_on_tty_without_blocking(monkeypatch):
    class FakeTTY:
        def isatty(self):
            return True

        def read(self):  # must never be reached — would block on a real tty
            raise AssertionError("read() must not be called when stdin is a tty")

    monkeypatch.setattr("sys.stdin", FakeTTY())
    assert vv._read_stdin() == ""


def test_read_stdin_reads_when_not_tty(monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO('{"cwd": "/x"}'))  # StringIO.isatty() is False
    assert vv._read_stdin() == '{"cwd": "/x"}'


def test_debug_silent_by_default_on_stderr(tmp_path):
    # No VALIDATE_VAULT_DEBUG -> findings on stdout, stderr stays empty.
    (tmp_path / "people").mkdir()
    (tmp_path / "people" / "Empty.md").write_text("")
    r = _run(f'{{"cwd": "{tmp_path}"}}', {"OBSIDIAN_VAULT": str(tmp_path)})
    assert r.returncode == 0
    assert "people/Empty.md" in r.stdout
    assert r.stderr == ""


def test_debug_writes_to_stderr_when_enabled(tmp_path):
    # VALIDATE_VAULT_DEBUG set -> diagnostics on stderr; stdout still carries findings only.
    (tmp_path / "people").mkdir()
    (tmp_path / "people" / "Empty.md").write_text("")
    r = _run(f'{{"cwd": "{tmp_path}"}}', {"OBSIDIAN_VAULT": str(tmp_path), "VALIDATE_VAULT_DEBUG": "1"})
    assert r.returncode == 0
    assert "people/Empty.md" in r.stdout
    assert "[validate-vault]" not in r.stdout       # debug never leaks onto stdout
    assert f"vault={tmp_path}" in r.stderr
    assert "in_scope=True" in r.stderr
    assert "find_empty_notes" in r.stderr


def test_debug_reports_out_of_scope_reason_on_stderr(tmp_path):
    (tmp_path / "people").mkdir()
    (tmp_path / "people" / "Empty.md").write_text("")
    outside = tmp_path.parent
    r = _run(
        f'{{"cwd": "{outside}"}}',
        {"OBSIDIAN_VAULT": str(tmp_path), "VALIDATE_VAULT_DEBUG": "1"},
    )
    assert r.returncode == 0
    assert r.stdout == ""                # out of scope -> still silent on stdout
    assert "in_scope=False" in r.stderr  # but debug explains why


def test_required_key_matrix_matches_skill_md():
    skill, rows = _skill_md_required_rows()

    def req(key):
        assert key in rows, f"SKILL.md table missing row {key}"
        return rows[key]

    people = req("`people/`")
    assert "organisation:" in people and "role:" in people

    orgs = req("`orgs/`")
    assert "relationship:" in orgs
    for v in vv.ENUM_FIELDS["relationship"]:
        assert v in orgs, f"orgs relationship enum value {v!r} missing from SKILL.md"

    assert "full:" in req("`glossary/`")
    assert "full:" in req("`engagements/<Engagement>/glossary/`")

    overview = req("`engagements/<Engagement>/<Engagement>.md`")
    assert "client:" in overview and "status:" in overview
    for v in vv.ENUM_FIELDS["status"]:
        assert v in overview, f"status enum value {v!r} missing from SKILL.md"


def test_daily_date_parses_filename(tmp_path):
    assert vv._daily_date(tmp_path / "2026-06-08.md") == date(2026, 6, 8)
    assert vv._daily_date(tmp_path / "template.md") is None
    assert vv._daily_date(tmp_path / "2026-13-99.md") is None


def test_recent_daily_files_window(tmp_path):
    (tmp_path / "daily").mkdir()
    for d in ("2026-05-01", "2026-06-05", "2026-06-09"):
        (tmp_path / "daily" / f"{d}.md").write_text("x")
    (tmp_path / "daily" / "template.md").write_text("x")
    got = {p.name for p in vv._recent_daily_files(tmp_path, 14, date(2026, 6, 9))}
    assert got == {"2026-06-05.md", "2026-06-09.md"}


def test_wikilink_targets_handles_alias_and_heading():
    t = "see [[Gagan Dhaliwal|Gagan]] and [[DSO2]] and [[Note#Heading]] and [[2026-06-08]]"
    assert vv._wikilink_targets(t) == {"Gagan Dhaliwal", "DSO2", "Note", "2026-06-08"}


def test_max_date_ref():
    assert vv._max_date_ref("a [[2026-05-29]] b [[2026-06-08-ww-standup]] c") == date(2026, 6, 8)
    assert vv._max_date_ref("no dates here") is None


def test_last_refreshed_parses_marker():
    assert vv._last_refreshed("*Last refreshed: [[2026-06-09]]. Next refresh: next decant.*") == date(2026, 6, 9)
    assert vv._last_refreshed("Last refreshed: 2026-06-05") == date(2026, 6, 5)
    assert vv._last_refreshed("no marker") is None


def _make_person(tmp_path, name, body):
    (tmp_path / "people").mkdir(exist_ok=True)
    (tmp_path / "people" / f"{name}.md").write_text(body)


def _make_daily(tmp_path, d, body):
    (tmp_path / "daily").mkdir(exist_ok=True)
    (tmp_path / "daily" / f"{d}.md").write_text(body)


def test_find_stale_person_notes_flags_lagging_note(tmp_path):
    _make_person(tmp_path, "Gagan Dhaliwal", "# Summary\nseen [[2026-06-04]]\n")
    _make_daily(tmp_path, "2026-06-08", "standup with [[Gagan Dhaliwal|Gagan]]\n")
    assert vv.find_stale_person_notes(tmp_path, date(2026, 6, 9)) == ["Gagan Dhaliwal"]


def test_find_stale_person_notes_fresh_note_not_flagged(tmp_path):
    _make_person(tmp_path, "Gagan Dhaliwal", "# Summary\nupdated [[2026-06-08]]\n")
    _make_daily(tmp_path, "2026-06-08", "standup with [[Gagan Dhaliwal|Gagan]]\n")
    assert vv.find_stale_person_notes(tmp_path, date(2026, 6, 9)) == []


def test_find_stale_person_notes_no_date_ref_skipped(tmp_path):
    _make_person(tmp_path, "Leon", "# Summary\nno dates in this note\n")
    _make_daily(tmp_path, "2026-06-08", "chat with [[Leon]]\n")
    assert vv.find_stale_person_notes(tmp_path, date(2026, 6, 9)) == []


def test_find_stale_person_notes_old_mention_outside_window(tmp_path):
    _make_person(tmp_path, "Gagan Dhaliwal", "# Summary\nseen [[2026-04-01]]\n")
    _make_daily(tmp_path, "2026-05-01", "old standup with [[Gagan Dhaliwal]]\n")
    assert vv.find_stale_person_notes(tmp_path, date(2026, 6, 9)) == []


def test_find_stale_person_notes_takes_latest_mention(tmp_path):
    _make_person(tmp_path, "Gagan Dhaliwal", "# Summary\nseen [[2026-06-06]]\n")
    _make_daily(tmp_path, "2026-06-05", "early [[Gagan Dhaliwal]]\n")
    _make_daily(tmp_path, "2026-06-08", "later [[Gagan Dhaliwal]]\n")
    # note date-ref is 06-06; if MAX mention (06-08) is used -> stale; if MIN (06-05) -> fresh
    assert vv.find_stale_person_notes(tmp_path, date(2026, 6, 9)) == ["Gagan Dhaliwal"]


def _make_context(tmp_path, engagement, refreshed):
    d = tmp_path / "engagements" / engagement
    d.mkdir(parents=True, exist_ok=True)
    (d / "context.md").write_text(f"---\ndescription: ctx\n---\n*Last refreshed: [[{refreshed}]].*\n")


def test_find_stale_context_flags_lagging(tmp_path):
    _make_context(tmp_path, "DSO2", "2026-06-05")
    _make_daily(tmp_path, "2026-06-08", "# Summary\nstandup re [[DSO2]]\n")
    assert vv.find_stale_context(tmp_path, date(2026, 6, 9)) == [("DSO2", "2026-06-05", "2026-06-08")]


def test_find_stale_context_not_flagged_when_daily_not_decanted(tmp_path):
    _make_context(tmp_path, "DSO2", "2026-06-05")
    _make_daily(tmp_path, "2026-06-08", "raw notes re [[DSO2]] (no summary heading)\n")
    assert vv.find_stale_context(tmp_path, date(2026, 6, 9)) == []


def test_find_stale_context_not_flagged_when_engagement_not_mentioned(tmp_path):
    _make_context(tmp_path, "DSO2", "2026-06-05")
    _make_daily(tmp_path, "2026-06-08", "# Summary\nunrelated day, no engagement link\n")
    assert vv.find_stale_context(tmp_path, date(2026, 6, 9)) == []


def test_find_stale_context_not_flagged_when_up_to_date(tmp_path):
    _make_context(tmp_path, "DSO2", "2026-06-09")
    _make_daily(tmp_path, "2026-06-08", "# Summary\nstandup re [[DSO2]]\n")
    assert vv.find_stale_context(tmp_path, date(2026, 6, 9)) == []


def test_find_stale_context_skips_when_no_marker(tmp_path):
    d = tmp_path / "engagements" / "DSO2"
    d.mkdir(parents=True)
    (d / "context.md").write_text("---\ndescription: ctx\n---\nno refresh marker here\n")
    _make_daily(tmp_path, "2026-06-08", "# Summary\nstandup re [[DSO2]]\n")
    assert vv.find_stale_context(tmp_path, date(2026, 6, 9)) == []


def test_format_report_includes_freshness(tmp_path):
    report = vv.format_report(
        [], [], tmp_path,
        stale_people=["Gagan Dhaliwal", "Leon"],
        stale_context=[("DSO2", "2026-06-05", "2026-06-08")],
    )
    assert "consider refresh-person: Gagan Dhaliwal, Leon" in report
    assert "Stale engagement context: DSO2 (last refreshed 2026-06-05; 2026-06-08 decant mentions it)" in report


def test_format_report_freshness_caps_at_15(tmp_path):
    people = [f"P{i:02d}" for i in range(20)]
    report = vv.format_report([], [], tmp_path, stale_people=people)
    assert "+5 more" in report


def test_format_report_empty_with_freshness_empty(tmp_path):
    assert vv.format_report([], [], tmp_path, stale_people=[], stale_context=[]) == ""


def test_hook_reports_stale_person(tmp_path):
    _make_person(tmp_path, "Gagan Dhaliwal", "# Summary\nseen [[2026-04-04]]\n")
    _make_daily(tmp_path, date.today().isoformat(), "standup with [[Gagan Dhaliwal]]\n")
    r = _run(f'{{"cwd": "{tmp_path}"}}', {"OBSIDIAN_VAULT": str(tmp_path)})
    assert r.returncode == 0
    assert "consider refresh-person: Gagan Dhaliwal" in r.stdout


def test_hook_reports_stale_context(tmp_path):
    d = tmp_path / "engagements" / "DSO2"
    d.mkdir(parents=True)
    (d / "context.md").write_text("---\ndescription: ctx\n---\n*Last refreshed: [[2026-01-01]].*\n")
    # a decanted daily dated today (> last refreshed) mentioning the engagement
    _make_daily(tmp_path, date.today().isoformat(), "# Summary\nstandup re [[DSO2]]\n")
    r = _run(f'{{"cwd": "{tmp_path}"}}', {"OBSIDIAN_VAULT": str(tmp_path)})
    assert r.returncode == 0
    assert "Stale engagement context: DSO2" in r.stdout


def test_recent_daily_files_finds_month_nested(tmp_path):
    daily = tmp_path / "daily" / "2026-06"
    daily.mkdir(parents=True)
    nested = daily / "2026-06-10.md"
    nested.write_text("# Notes\n")
    today = date(2026, 6, 12)
    found = vv._recent_daily_files(tmp_path, days=14, today=today)
    assert nested in found


def test_recent_daily_files_still_finds_flat(tmp_path):
    daily = tmp_path / "daily"
    daily.mkdir()
    flat = daily / "2026-06-10.md"
    flat.write_text("# Notes\n")
    found = vv._recent_daily_files(tmp_path, days=14, today=date(2026, 6, 12))
    assert flat in found


def test_daily_note_files_no_daily_dir(tmp_path):
    # vault has no daily/ directory — yields nothing, does not raise
    assert list(vv._daily_note_files(tmp_path)) == []


def test_recent_daily_files_ignores_detail_and_transcripts(tmp_path):
    # month-nested detail/transcripts live under daily/ but must not be treated as daily notes
    (tmp_path / "daily" / "detail" / "2026-06").mkdir(parents=True)
    (tmp_path / "daily" / "detail" / "2026-06" / "2026-06-10-topic.md").write_text("x\n")
    (tmp_path / "daily" / "transcripts" / "2026-06").mkdir(parents=True)
    (tmp_path / "daily" / "transcripts" / "2026-06" / "2026-06-10-x-transcript.md").write_text("x\n")
    found = vv._recent_daily_files(tmp_path, days=14, today=date(2026, 6, 12))
    assert found == []


def test_stale_context_finds_month_nested_trigger(tmp_path):
    ctx = tmp_path / "engagements" / "Acme" / "context.md"
    ctx.parent.mkdir(parents=True)
    ctx.write_text("---\ndescription: x\n---\n*Last refreshed: [[2026-06-01]]*\n")
    nested = tmp_path / "daily" / "2026-06" / "2026-06-09.md"
    nested.parent.mkdir(parents=True)
    nested.write_text("# Summary\n- [[Acme]] talked\n")
    out = vv.find_stale_context(tmp_path, today=date(2026, 6, 12))
    assert ("Acme", "2026-06-01", "2026-06-09") in out


def test_iter_notes_skips_inbox(tmp_path):
    (tmp_path / "inbox").mkdir()
    dropped = tmp_path / "inbox" / "raw-transcript.md"
    dropped.write_text("")  # empty + no description — would normally be flagged
    (tmp_path / "misc").mkdir()
    (tmp_path / "misc" / "Real.md").write_text("content\n")
    names = {p.name for p in vv._iter_notes(tmp_path)}
    assert "raw-transcript.md" not in names
    assert "Real.md" in names


def test_detail_month_nested_still_requires_description(tmp_path):
    rel = Path("daily") / "detail" / "2026-06" / "2026-06-10-topic.md"
    assert vv._requires_description(rel) is True
