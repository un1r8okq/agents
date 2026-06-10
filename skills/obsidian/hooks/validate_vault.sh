#!/usr/bin/env bash
# SessionStart hook wrapper — runs validate_vault.py via python3.
#
# Why this shim exists: Claude Code 2.1.170 silently skips a bare *.py path
# registered as a SessionStart command (it never executes — no hook attachment
# is recorded), but it DOES run a bare *.sh command (the decant hook proves this
# every startup). So the SessionStart hook points here, and this script execs
# the real Python validator.
#
# stdin (the hook payload JSON) is inherited by exec and passes straight through;
# validate_vault.py reads it for `.cwd`. stdout becomes injected session context.
set -u
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
exec python3 "$here/validate_vault.py"
