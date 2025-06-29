#!/bin/bash
# Simple lint check script to run before pushing to GitHub

echo "Running flake8 linting check..."
python3 -m flake8 dazzlesum.py tests/ --exclude=tests/test_runs/ || {
    echo "❌ Flake8 check failed!"
    exit 1
}

echo "✅ Flake8 check passed!"

# Run a basic syntax check
echo "Running Python syntax check..."
python3 -m py_compile dazzlesum.py || {
    echo "❌ Python syntax check failed!"
    exit 1
}

echo "✅ Python syntax check passed!"
echo "All checks passed - ready to push!"