#!/bin/bash
set -e

# Check if we should run against local server
LOCAL_MODE=${LOCAL_MODE:-false}
SERVER_PID=""

# Function to cleanup on exit
cleanup() {
    if [ ! -z "$SERVER_PID" ]; then
        echo "🛑 Stopping local server (PID: $SERVER_PID)..."
        kill $SERVER_PID 2>/dev/null || true
        wait $SERVER_PID 2>/dev/null || true
    fi
}

trap cleanup EXIT

echo "🔐 Generating Firebase test token..."
export FIREBASE_TEST_TOKEN=$(uv run python scripts/get_test_token.py)

if [ "$LOCAL_MODE" = "true" ]; then
    echo "✅ Token generated"
    echo "🚀 Starting local server..."
    
    # Start local server in background
    uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 > /tmp/veo-server.log 2>&1 &
    SERVER_PID=$!
    
    export API_URL="http://localhost:8000"
    
    # Wait for server to be ready
    echo "⏳ Waiting for server to start..."
    for i in {1..30}; do
        if curl -s http://localhost:8000/ > /dev/null 2>&1; then
            echo "✅ Server is ready!"
            break
        fi
        if [ $i -eq 30 ]; then
            echo "❌ Server failed to start. Check /tmp/veo-server.log"
            exit 1
        fi
        sleep 1
    done
    
    echo "🧪 Running E2E tests against LOCAL server (http://localhost:8000)..."
else
    echo "✅ Token generated"
    export API_URL=${API_URL:-"https://veo-api-otfo2ctxma-uc.a.run.app"}
    echo "🧪 Running E2E tests against PRODUCTION ($API_URL)..."
fi

echo ""

# If specific tests provided, use them; otherwise run all e2e tests
if [ $# -gt 0 ]; then
    uv run pytest --run-e2e -v "$@"
else
    uv run pytest tests/e2e/ --run-e2e -v
fi
