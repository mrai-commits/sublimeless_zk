#!/usr/bin/env bash
# Runs the whole test suite headless. On Linux this needs xvfb.
cd "$(dirname "$0")"
X=""
command -v xvfb-run >/dev/null && X='xvfb-run -a -s "-screen 0 1400x900x24"'
fail=0
for t in tests/test_bib.py tests/test_export.py; do
    echo "== $t"; python3 -W error::SyntaxWarning "$t" || fail=1
done
for t in tests/smoke.py tests/test_gui_*.py; do
    echo "== $t"; eval $X python3 -W error::SyntaxWarning "$t" || fail=1
done
[ $fail = 0 ] && echo "ALL TESTS PASSED" || echo "SOME TESTS FAILED"
exit $fail
