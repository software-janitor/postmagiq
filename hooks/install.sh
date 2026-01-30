#!/bin/bash
# Install git hooks for this repository

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GIT_DIR="$(git rev-parse --git-dir 2>/dev/null)"

if [ -z "$GIT_DIR" ]; then
    echo "Error: Not in a git repository"
    exit 1
fi

HOOKS_DIR="$GIT_DIR/hooks"

# Make hooks executable
chmod +x "$SCRIPT_DIR/pre-commit" 2>/dev/null
chmod +x "$SCRIPT_DIR/commit-msg" 2>/dev/null

# Install pre-commit hook
if [ -f "$SCRIPT_DIR/pre-commit" ]; then
    ln -sf "$SCRIPT_DIR/pre-commit" "$HOOKS_DIR/pre-commit"
    echo "Installed pre-commit hook"
fi

# Install commit-msg hook
if [ -f "$SCRIPT_DIR/commit-msg" ]; then
    ln -sf "$SCRIPT_DIR/commit-msg" "$HOOKS_DIR/commit-msg"
    echo "Installed commit-msg hook"
fi

echo "Git hooks installed successfully"
