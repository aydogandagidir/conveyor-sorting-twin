# Phase 0 verification entrypoint (proves Engineering Gate 1).
# Delegates to the cross-platform Python verifier.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
python "$root/tests/verify_phase0.py"
exit $LASTEXITCODE
