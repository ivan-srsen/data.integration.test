#!/bin/bash

# Integration Test Runner
# This script automatically starts docker-compose if needed and runs the integration test

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

# Get the project name from directory (used for container naming)
PROJECT_NAME=$(basename "$(pwd)" | tr '[:upper:]' '[:lower:]' | tr -d '.')

echo "Checking for running Airflow containers..."

# Check if Airflow containers are running with our project name
AIRFLOW_CONTAINER=$(docker ps --filter "name=${PROJECT_NAME}-airflow-webserver" --format "{{.Names}}" | head -1)

if [ -z "$AIRFLOW_CONTAINER" ]; then
    echo ""
    echo "No running Airflow containers found. Starting docker-compose..."
    echo ""

    # Stop any existing containers from other directories to avoid conflicts
    echo "Stopping any conflicting containers..."
    docker stop $(docker ps -q --filter "name=airflow") 2>/dev/null || true
    docker stop $(docker ps -q --filter "name=postgres") 2>/dev/null || true

    # Start docker-compose services
    echo "Starting Airflow and Postgres services..."
    docker-compose up -d

    # Wait for services to be healthy
    echo ""
    echo "Waiting for Airflow webserver to be healthy..."
    AIRFLOW_CONTAINER="${PROJECT_NAME}-airflow-webserver-1"

    for i in {1..60}; do
        STATUS=$(docker inspect $AIRFLOW_CONTAINER --format='{{.State.Health.Status}}' 2>/dev/null || echo "unknown")
        if [ "$STATUS" = "healthy" ]; then
            echo "✓ Airflow is healthy!"
            break
        fi

        if [ $i -eq 60 ]; then
            echo "✗ Timeout waiting for Airflow to become healthy"
            echo "Check logs with: docker logs $AIRFLOW_CONTAINER"
            exit 1
        fi

        echo "  [$i/60] Health status: $STATUS (waiting...)"
        sleep 2
    done
else
    echo "✓ Found Airflow container: $AIRFLOW_CONTAINER"
fi

echo ""

# Unpause the DAG if it's paused
echo "Ensuring DAG is unpaused..."
docker exec $AIRFLOW_CONTAINER airflow dags unpause data_transformation_pipeline 2>/dev/null || echo "  (DAG may already be unpaused or not yet loaded)"
echo ""

# Copy the integration test to the dags directory (which is mounted)
echo "Copying integration test to dags directory..."
cp integration_test_simple.py dags/_integration_test.py

# Give the scheduler a moment to detect the file
sleep 2

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
    echo "Troubleshooting:"
    echo "  1. Check scheduler logs: docker logs ${PROJECT_NAME}-airflow-scheduler-1"
    echo "  2. Check webserver logs: docker logs ${PROJECT_NAME}-airflow-webserver-1"
    echo "  3. Access Airflow UI: http://localhost:8080 (admin/admin)"
fi
echo "======================================"

exit $exit_code
