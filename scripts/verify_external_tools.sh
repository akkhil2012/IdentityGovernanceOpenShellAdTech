#!/usr/bin/env bash
set -euo pipefail
: "${OPEN_SHELL_VERSION:?Set the exact version approved from official NVIDIA OpenShell release documentation}"
: "${OPEN_SHELL_VALIDATE_COMMAND:?Set the documented policy validation command for that exact release}"
command -v openshell >/dev/null || { echo 'OpenShell unavailable: real isolation tests NOT RUN' >&2; exit 2; }
actual="$(openshell --version 2>&1)"
printf 'Expected OpenShell: %s\nInstalled: %s\n' "$OPEN_SHELL_VERSION" "$actual"
[[ "$actual" == *"$OPEN_SHELL_VERSION"* ]] || { echo 'Pinned version mismatch' >&2; exit 3; }
# Operator-provided because policy CLI syntax must come from official docs, never guesswork.
bash -lc "$OPEN_SHELL_VALIDATE_COMMAND"
python - <<'PY'
import google.adk
print("Google ADK import: OK", getattr(google.adk, "__version__", "version metadata unavailable"))
PY
