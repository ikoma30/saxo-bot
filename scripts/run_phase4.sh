#!/usr/bin/env bash

set -euo pipefail

cd "$(dirname "$0")/.."

echo "Starting Phase-4 test sequence..."

echo "Step 1: Checking SIM refresh token validity..."
poetry run python scripts/check_token_validity.py sim
if [ $? -ne 0 ]; then
    echo "❌ SIM refresh token check failed"
    exit 1
fi
echo "✅ SIM refresh token is valid"

echo "Step 2: Deploying simulation environment..."
./scripts/oneclick_start.sh sim
if [ $? -ne 0 ]; then
    echo "❌ Simulation deployment failed"
    exit 1
fi
echo "✅ Simulation environment deployed successfully"

echo "Step 3: Verifying monitoring systems..."
poetry run python scripts/verify_monitoring.py
if [ $? -ne 0 ]; then
    echo "❌ Monitoring verification failed"
    exit 1
fi
echo "✅ Monitoring systems verified successfully"

echo "Step 4: Running 0.01-lot Sim Canary test with 10 trades..."
poetry run python scripts/run_canary_test.py USDJPY 10 0.01
if [ $? -ne 0 ]; then
    echo "❌ Canary test failed to meet KPIs"
    exit 1
fi
echo "✅ Canary test passed successfully"

echo "Phase-4 test sequence completed successfully!"
exit 0
