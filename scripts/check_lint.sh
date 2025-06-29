#!/bin/bash
# Enhanced lint check script with strict mode support

STRICT_MODE=false
if [[ "$1" == "--strict" ]]; then
    STRICT_MODE=true
fi

echo "Running flake8 linting check..."
if python3 -m flake8 dazzlesum.py tests/ --exclude=tests/test_runs/; then
    echo "✅ Flake8 check passed!"
else
    if [[ "$STRICT_MODE" == "true" ]]; then
        echo "❌ Flake8 check failed (strict mode)!"
        exit 1
    else
        echo "⚠️ Flake8 issues found (non-strict mode)"
    fi
fi

echo "Running Python syntax check..."
if python3 -m py_compile dazzlesum.py; then
    echo "✅ Python syntax check passed!"
else
    echo "❌ Python syntax check failed!"
    exit 1
fi

if [[ "$STRICT_MODE" == "false" ]]; then
    echo "All checks completed (warnings allowed)"
else
    echo "All checks passed - ready to push!"
fi