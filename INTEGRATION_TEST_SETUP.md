# Integration Test Setup

This directory now contains all the necessary files to run the integration test standalone.

## Files Copied from Parent Directory

1. **`.env`** - Snowflake credentials and configuration
   - Contains: SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, SNOWFLAKE_PASSWORD, etc.
   - Location: Copied from `../.env`

2. **`.env.example`** - Template for environment variables
   - Use this as a reference for required variables
   - Location: Copied from `../.env.example`

## Directory Structure

```
data.integration.test/
├── .env                           # Snowflake credentials (copied)
├── .env.example                   # Environment template (copied)
├── run_integration_test.sh        # NEW: Easy test runner script
├── integration_test.py            # Main integration test script
├── docker-compose.yml             # Docker Compose configuration
├── Dockerfile                     # Custom Airflow image
├── requirements.txt               # Python dependencies
├── dags/                          # Airflow DAGs
│   ├── data_transformation_dag.py # The DAG tested by integration test
│   ├── snowflake_integration_dag.py
│   └── setup_snowflake.py
├── logs/                          # Airflow logs
├── config/                        # Airflow config
└── README.md                      # Project documentation
```

## Running the Integration Test

### Option 1: Using the Wrapper Script (Recommended)

```bash
./run_integration_test.sh
```

This script will:
- Check for `.env` file
- Load environment variables
- Install Python dependencies if needed
- Run the integration test
- Display results

### Option 2: Direct Python Execution

```bash
# Load environment variables
set -a
source .env
set +a

# Run the test
python integration_test.py
```

### Option 3: Using Docker Compose

If you need to run the full Airflow environment:

```bash
# Start Airflow services
docker-compose up -d

# Wait for services to be healthy
docker-compose ps

# Run the test inside the Airflow container
docker exec -it <container_name> python /opt/airflow/dags/integration_test.py
```

## What the Integration Test Does

The integration test performs a complete end-to-end validation:

1. **Setup** (Step 1)
   - Creates a test schema in Snowflake
   - Creates a `sales_data` source table
   - Inserts 15 rows of sample sales data

2. **Configuration** (Step 2)
   - Sets Airflow variables (test_schema, source_table, target_table)

3. **Execution** (Step 3)
   - Triggers the `data_transformation_pipeline` DAG

4. **Monitoring** (Step 4)
   - Waits for the DAG to complete (300s timeout)
   - Monitors task execution

5. **Validation** (Step 5)
   - Verifies target table exists
   - Validates row counts
   - Checks data quality
   - Compares totals between source and target

6. **Cleanup** (Step 6)
   - Drops test schema and all test tables
   - Removes Airflow variables

## Required Environment Variables

The following variables must be set in `.env`:

```bash
# Snowflake Connection
SNOWFLAKE_ACCOUNT=your-account.region.cloud
SNOWFLAKE_USER=your-username
SNOWFLAKE_PASSWORD=your-password
SNOWFLAKE_ROLE=ACCOUNTADMIN
SNOWFLAKE_WAREHOUSE=COMPUTE_WH
SNOWFLAKE_DATABASE=your-database
SNOWFLAKE_SCHEMA=PUBLIC

# Airflow (for Docker Compose)
AIRFLOW_UID=50000
```

## Dependencies

Python packages (from `requirements.txt`):
- `snowflake-connector-python==3.6.0`
- `apache-airflow-providers-snowflake==5.1.2`

These are automatically installed by the wrapper script.

## Troubleshooting

### "User is empty" Error
- Check that `.env` file exists and contains valid credentials
- Ensure environment variables are loaded: `source .env`

### DAG Not Found
- Ensure Airflow is running: `docker-compose ps`
- Check DAG is not paused: `docker exec <container> airflow dags list`
- Verify DAG file exists in `dags/` directory

### Connection Timeout
- Check Snowflake credentials are correct
- Verify network connectivity to Snowflake
- Ensure warehouse is running in Snowflake

### DAG Execution Timeout
- The test waits 300 seconds (5 minutes) for DAG completion
- If DAG is slow, increase timeout in `integration_test.py`
- Check scheduler logs: `docker-compose logs airflow-scheduler`

## Success Criteria

A successful test run will show:
- ✓ Schema and table created
- ✓ Sample data inserted
- ✓ Airflow variables configured
- ✓ DAG triggered and completed
- ✓ Transformation validated
- ✓ All resources cleaned up

## Notes

- The test creates temporary resources with timestamps (e.g., `TEST_SCHEMA_20260214_125258`)
- All test resources are automatically cleaned up, even if the test fails
- The test is safe to run multiple times
- No permanent changes are made to your Snowflake database
