#!/usr/bin/env bash
# Install the repo's git hooks by symlinking them into .git/hooks so the
# tracked versions under scripts/git-hooks stay the source of truth.
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
hooks_src="$repo_root/scripts/git-hooks"
hooks_dst="$repo_root/.git/hooks"

for hook in "$hooks_src"/*; do
    name="$(basename "$hook")"
    chmod +x "$hook"
    ln -sf "../../scripts/git-hooks/$name" "$hooks_dst/$name"
    echo "installed hook: $name"
done
