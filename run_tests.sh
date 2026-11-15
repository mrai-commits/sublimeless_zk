#!/usr/bin/env bash
# Runs the headless test suite. Needs xvfb on Linux.
set -e
cd "$(dirname "$0")"
python3 -W error::SyntaxWarning tests/test_bib.py
python3 -W error::SyntaxWarning tests/test_export.py
if command -v xvfb-run >/dev/null; then
    xvfb-run -a -s "-screen 0 1400x900x24" python3 -W error::SyntaxWarning tests/smoke.py
else
    python3 -W error::SyntaxWarning tests/smoke.py
fi
