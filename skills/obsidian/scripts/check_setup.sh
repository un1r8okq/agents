#!/bin/bash

# check_setup.sh
# Verifies that the cross-CLI Obsidian Vault environment is configured correctly.

echo "Checking Obsidian Vault setup..."

VAULT_VAR="OBSIDIAN_VAULT"
MISSING_CONFIG=0

# 1. Check if the environment variable is currently exported in the active shell
if [ -z "${!VAULT_VAR}" ]; then
  echo "❌ $VAULT_VAR environment variable is not currently set in the active shell."
  MISSING_CONFIG=1
else
  echo "✅ $VAULT_VAR is set to: ${!VAULT_VAR}"
  if [ ! -d "${!VAULT_VAR}" ]; then
     echo "   ⚠️ Warning: The directory ${!VAULT_VAR} does not exist."
  fi
fi

# 2. Check Shell Profiles (for persistence)
PROFILE_FOUND=0
for profile in ~/.bashrc ~/.zshrc ~/.bash_profile; do
  if [ -f "$profile" ]; then
    if grep -q "$VAULT_VAR" "$profile"; then
      echo "✅ $VAULT_VAR found in $profile"
      PROFILE_FOUND=1
    fi
  fi
done

if [ $PROFILE_FOUND -eq 0 ]; then
  echo "❌ $VAULT_VAR not found in common shell profiles (~/.bashrc, ~/.zshrc)."
  MISSING_CONFIG=1
fi

# 3. Gemini CLI Verification
echo ""
echo "Gemini CLI:"
GEMINI_SETTINGS=~/.gemini/settings.json
if [ -f "$GEMINI_SETTINGS" ]; then
  if grep -q "$VAULT_VAR" "$GEMINI_SETTINGS"; then
    echo "✅ $VAULT_VAR found in context.includeDirectories."
  else
    echo "❌ $VAULT_VAR not found in $GEMINI_SETTINGS."
    MISSING_CONFIG=1
  fi
else
  echo "⚠️ $GEMINI_SETTINGS not found."
fi

# 4. Claude Code Verification
echo ""
echo "Claude Code:"
CLAUDE_LINK=~/.claude/CLAUDE.md
AGENTS_FILE=~/.agents/AGENTS.md
if [ -L "$CLAUDE_LINK" ]; then
  TARGET=$(readlink -f "$CLAUDE_LINK")
  if [ "$TARGET" == "$AGENTS_FILE" ]; then
    echo "✅ $CLAUDE_LINK is correctly symlinked to $AGENTS_FILE"
  else
    echo "⚠️ $CLAUDE_LINK points to $TARGET instead of $AGENTS_FILE"
  fi
else
  echo "❌ $CLAUDE_LINK is not a symlink (or doesn't exist)."
  MISSING_CONFIG=1
fi

if [ -f "$AGENTS_FILE" ]; then
  if grep -q "\$VAULT_VAR" "$AGENTS_FILE" || grep -q "\$OBSIDIAN_VAULT" "$AGENTS_FILE"; then
    echo "✅ $AGENTS_FILE references \$OBSIDIAN_VAULT"
  else
    echo "❌ $AGENTS_FILE does not reference the vault variable."
    MISSING_CONFIG=1
  fi
else
  echo "❌ $AGENTS_FILE not found."
  MISSING_CONFIG=1
fi

# 5. GitHub Copilot CLI Verification
echo ""
echo "GitHub Copilot CLI:"
COPILOT_CONFIG=~/.copilot/config.json
if [ -f "$COPILOT_CONFIG" ]; then
  # Note: Copilot uses absolute paths in trusted_folders
  RESOLVED_PATH="${!VAULT_VAR}"
  if [ -n "$RESOLVED_PATH" ] && grep -q "$RESOLVED_PATH" "$COPILOT_CONFIG"; then
    echo "✅ Vault path found in trusted_folders."
  else
    echo "❌ Vault path not found in trusted_folders in $COPILOT_CONFIG."
    echo "   (Consider adding \"$RESOLVED_PATH\" to the trusted_folders array in $COPILOT_CONFIG)"
    # We don't mark MISSING_CONFIG=1 here as this is often project-specific and non-blocking
  fi
else
  echo "⚠️ $COPILOT_CONFIG not found."
fi

# Summary
echo ""
if [ $MISSING_CONFIG -eq 1 ]; then
  echo "Action Required: The environment is not fully configured."
  exit 1
else
  echo "Setup looks good!"
  exit 0
fi
