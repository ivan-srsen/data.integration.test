#!/bin/bash

# Integration Test Runner
# This script runs the integration test using the running Airflow container

set -e

echo "======================================"
echo "Airflow-Snowflake Integration Test"
echo "======================================"
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo "Error: .env file not found!"
    echo "Please copy .env.example to .env and fill in your Snowflake credentials."
    exit 1
fi

echo "Checking for running Airflow containers..."

# Check if Airflow containers are running
AIRFLOW_CONTAINER=$(docker ps --filter "name=airflow-webserver" --format "{{.Names}}" | head -1)

if [ -z "$AIRFLOW_CONTAINER" ]; then
    echo ""
    echo "No running Airflow container found!"
    echo ""
    echo "You have two options:"
    echo ""
    echo "1. Use the existing Airflow containers from parent directory:"
    echo "   cd .."
    echo "   docker-compose -f data.integration.test/docker-compose.yml up -d"
    echo ""
    echo "2. Or if containers are already running in parent, use them:"
    echo "   This script will automatically detect and use them."
    echo ""
    exit 1
fi

echo "✓ Found Airflow container: $AIRFLOW_CONTAINER"
echo ""

# Copy the integration test to the dags directory (which is mounted)
echo "Copying integration test to dags directory..."
cp integration_test_simple.py dags/_integration_test.py

# Run the integration test inside the container
echo ""
echo "Starting integration test..."
echo "======================================"
echo ""

docker exec $AIRFLOW_CONTAINER python /opt/airflow/dags/_integration_test.py

exit_code=$?

# Cleanup
rm -f dags/_integration_test.py 2>/dev/null || true

echo ""
echo "======================================"
if [ $exit_code -eq 0 ]; then
    echo "✓ Integration test completed successfully!"
else
    echo "✗ Integration test failed with exit code $exit_code"
    echo ""
    echo "Note: If the DAG execution timed out, check that:"
    echo "  1. The DAG 'data_transformation_pipeline' exists"
    echo "  2. Airflow scheduler is running"
    echo "  3. Check logs: docker logs super-airflow-scheduler-1"
fi
echo "======================================"

exit $exit_code
