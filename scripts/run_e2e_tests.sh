#!/bin/bash
set -e

echo "🔐 Generating Firebase test token..."
export FIREBASE_TEST_TOKEN=$(uv run python scripts/get_test_token.py)

echo "✅ Token generated"
echo "🧪 Running E2E tests against production..."
echo ""

uv run pytest tests/e2e/ --run-e2e -v "$@"
