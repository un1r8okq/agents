#!/usr/bin/env bash
# SessionStart hook — nudge about undecanted past daily notes.
#
# Scans $OBSIDIAN_VAULT/daily for YYYY-MM-DD.md notes from the last 14 days that
# lack a "# Summary" heading and prints a nudge to stdout (SessionStart stdout is
# injected as session context). Offers; never auto-runs /decant. Always exits 0.

set -u
export LC_ALL=C

# --- Read the hook's stdin JSON; extract cwd (fallback: $PWD) ---
stdin_json="$(cat 2>/dev/null || true)"
cwd=""
if [ -n "$stdin_json" ] && command -v jq >/dev/null 2>&1; then
  cwd="$(printf '%s' "$stdin_json" | jq -r '.cwd // empty' 2>/dev/null || true)"
fi
if [ -z "$cwd" ] && [ -n "$stdin_json" ]; then
  cwd="$(printf '%s' "$stdin_json" \
    | sed -n 's/.*"cwd"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -n1)"
fi
[ -z "$cwd" ] && cwd="$PWD"

# --- Resolve the vault (portable, with CLAUDE_ENV_FILE fallback) ---
if [ -z "${OBSIDIAN_VAULT:-}" ] && [ -n "${CLAUDE_ENV_FILE:-}" ] && [ -f "${CLAUDE_ENV_FILE}" ]; then
  # shellcheck disable=SC1090
  . "$CLAUDE_ENV_FILE" 2>/dev/null || true
fi
vault="${OBSIDIAN_VAULT:-}"
[ -n "$vault" ] || exit 0
[ -d "$vault" ] || exit 0

# --- Self-locate the skills-repo root (no hardcoded paths) ---
hooks_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"   # .../skills/decant/hooks
skills_repo="$(cd "$hooks_dir/../../.." && pwd -P)"            # 3 levels up from hooks/ -> repo root
[ -n "$skills_repo" ] || exit 0

# --- Normalise cwd and vault for prefix matching ---
norm() { (cd "$1" 2>/dev/null && pwd -P) || printf '%s' "$1"; }
cwd="$(norm "$cwd")"
vault="$(norm "$vault")"

# --- cwd guard: act only inside the vault or the skills repo ---
case "$cwd" in
  "$vault"|"$vault"/*|"$skills_repo"|"$skills_repo"/*) : ;;
  *) exit 0 ;;
esac

# --- Window bounds: lower (14 days ago) <= d < today ---
today="$(date +%F)"
if ! lower="$(date -d '14 days ago' +%F 2>/dev/null)"; then
  lower="$(date -v-14d +%F 2>/dev/null)"   # BSD/macOS date fallback
fi
[ -n "$lower" ] || exit 0

# --- Scan for in-window undecanted notes (glob excludes template.md by shape) ---
found=()
shopt -s nullglob
for f in "$vault"/daily/[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9].md \
         "$vault"/daily/[0-9][0-9][0-9][0-9]-[0-9][0-9]/[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9].md; do
  d="$(basename "$f" .md)"
  [[ "$d" < "$lower" ]] && continue   # older than the window
  [[ "$d" < "$today" ]] || continue   # today or future -> exclude
  grep -q '^# Summary' "$f" || found+=("$d")
done
shopt -u nullglob

[ "${#found[@]}" -eq 0 ] && exit 0

# --- Build a "a, b, c" list (glob already yields chronological order) and emit ---
list="$(printf '%s, ' "${found[@]}")"; list="${list%, }"

cat <<EOF
Undecanted daily notes (no \`# Summary\`) from the last 14 days: ${list}.
These past daily notes haven't been decanted. Briefly mention them to the user and offer to run the
/decant skill on them. Do NOT start decanting unless the user agrees — it is a heavy, interactive
process. Offer; don't auto-run.
EOF
exit 0
