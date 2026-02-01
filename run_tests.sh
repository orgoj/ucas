#!/usr/bin/env bash
# UCAS Test Runner

set -e

# Ensure we are in project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Setup PYTHONPATH to include current directory
export PYTHONPATH=$PYTHONPATH:.

echo "🚀 Running UCAS Test Suite..."
echo "---------------------------"

# Run all files starting with test_ in the tests/ directory
python3 -m unittest discover -v -s tests -p 'test_*.py'

echo "---------------------------"
echo "✅ All tests passed!"
