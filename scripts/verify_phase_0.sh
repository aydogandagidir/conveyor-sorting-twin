#!/usr/bin/env bash
# Phase 0 verification entrypoint (proves Engineering Gate 1).
# Delegates to the cross-platform Python verifier.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec python "${HERE}/tests/verify_phase0.py"
