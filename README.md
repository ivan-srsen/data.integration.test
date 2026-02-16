# Airflow-Snowflake Integration Test

This integration test validates the complete end-to-end workflow of the Airflow-Snowflake data transformation pipeline.

## What Does This Test Do?

The test performs a full integration test of your Airflow DAG that transforms data in Snowflake:

1. **Creates a test environment** - Sets up a temporary Snowflake schema with sample sales data
2. **Configures Airflow** - Sets variables for the test schema and table names
3. **Triggers the DAG** - Executes the `data_transformation_pipeline` DAG
4. **Validates results** - Verifies that:
   - The target table was created
   - Data was correctly aggregated
   - Totals match between source and target
5. **Cleans up** - Removes all test data and variables

## Prerequisites

### Required Software
- **Docker & Docker Compose** - For running Airflow containers
- **Bash shell** - The test script is a bash script

### Required Configuration
You must have valid Snowflake credentials configured in the `.env` file.

## Setup Instructions

### 1. Configure Snowflake Credentials

Copy the example environment file and fill in your Snowflake credentials:

```bash
cp .env.example .env
```

Edit `.env` and provide your Snowflake connection details:

```bash
# Snowflake Connection
SNOWFLAKE_ACCOUNT=your-account.snowflakecomputing.com
SNOWFLAKE_USER=your-username
SNOWFLAKE_PASSWORD=your-password
SNOWFLAKE_ROLE=ACCOUNTADMIN
SNOWFLAKE_WAREHOUSE=your-warehouse
SNOWFLAKE_DATABASE=your-database
SNOWFLAKE_SCHEMA=PUBLIC
```

**Important:** Make sure your Snowflake user has permissions to:
- Create and drop schemas
- Create and drop tables
- Insert and query data

### 2. Verify DAG Files

Ensure the following DAG files exist in the `dags/` directory:
- `data_transformation_dag.py` - The main transformation DAG
- `setup_snowflake.py` - Snowflake setup utilities
- `snowflake_integration_dag.py` - Integration DAG

## Running the Test

### Quick Start

Simply run the test script:

```bash
./run_integration_test.sh
```

That's it! The script will automatically:
- Start Docker containers if they're not running
- Wait for Airflow to be healthy
- Unpause the DAG
- Run the complete integration test
- Report results

### What to Expect

The test takes approximately **30-45 seconds** to complete:

```
======================================
Airflow-Snowflake Integration Test
======================================

Checking for running Airflow containers...
✓ Found Airflow container: dataintegrationtest-airflow-webserver-1

Ensuring DAG is unpaused...
✓ DAG unpaused

Starting integration test...
======================================

STEP 1: Setting Up Test Environment
✓ Schema TEST_SCHEMA_20260216_101058 created
✓ Table sales_data created
✓ Inserted 15 rows of sample data

STEP 2: Configuring Airflow Variables
✓ Set test_schema = TEST_SCHEMA_20260216_101058
✓ Set source_table = sales_data
✓ Set target_table = sales_summary

STEP 3: Triggering Data Transformation DAG
✓ DAG triggered successfully

STEP 4: Waiting for DAG Completion
✓ DAG completed successfully in 10 seconds

STEP 5: Validating Transformation Results
✓ Target table sales_summary exists
✓ Target table contains 6 rows
✓ Quantity totals match: 515
✓ Sales totals match: $40,789.46
✓ All validation checks passed!

STEP 6: Cleaning Up Test Resources
✓ Schema and tables deleted
✓ Airflow variables cleaned up

======================================
✓ Integration test completed successfully!
======================================
```

## Understanding the Test

### Test Data

The test creates sample sales data with:
- **6 unique products** (Laptop Pro, Wireless Mouse, USB-C Cable, etc.)
- **15 sales transactions** across different dates
- **Total quantity:** 515 units
- **Total sales:** $40,789.46

### DAG Execution

The test triggers the `data_transformation_pipeline` DAG which:
1. Reads from the source `sales_data` table
2. Aggregates sales by product
3. Writes results to the `sales_summary` table

### Validation Checks

The test validates:
- ✓ Target table exists
- ✓ Correct number of rows (6 products from 15 transactions)
- ✓ Quantity totals match between source and target
- ✓ Sales amount totals match between source and target

## Container Management

### Automatic Container Startup

If containers aren't running, the script automatically:
1. Stops any conflicting containers from other projects
2. Starts `docker-compose up -d`
3. Waits for services to be healthy (up to 2 minutes)
4. Unpauses the DAG

### Manual Container Management

If you prefer to manage containers manually:

**Start containers:**
```bash
docker-compose up -d
```

**Check container status:**
```bash
docker ps --filter "name=dataintegrationtest"
```

**View logs:**
```bash
docker logs dataintegrationtest-airflow-webserver-1
docker logs dataintegrationtest-airflow-scheduler-1
```

**Stop containers:**
```bash
docker-compose down
```

## Troubleshooting

### Test Fails at Configuration Stage

**Error:** `Failed to set Airflow variables: could not translate host name "postgres"`

**Solution:** Postgres container isn't running. The script should handle this automatically, but if it doesn't:
```bash
docker-compose down
docker-compose up -d
```

### DAG Stays Queued and Times Out

**Error:** `DAG did not complete within 300 seconds`

**Possible causes:**
1. DAG is paused - The script should unpause it automatically
2. Scheduler isn't running - Check scheduler logs:
   ```bash
   docker logs dataintegrationtest-airflow-scheduler-1
   ```

**Manual fix:**
```bash
docker exec dataintegrationtest-airflow-webserver-1 airflow dags unpause data_transformation_pipeline
```

### Snowflake Connection Errors

**Error:** `Failed to setup test environment: 250001 (08001): Failed to connect to DB`

**Solution:** Check your `.env` file credentials:
- Verify account URL is correct
- Confirm username and password
- Ensure warehouse and database exist
- Check user has required permissions

### Target Table Doesn't Exist

**Error:** `Target table sales_summary does not exist`

**Possible causes:**
1. DAG failed during execution - Check DAG logs in Airflow UI
2. Transformation logic error - Review DAG code

**Debug:**
1. Access Airflow UI: http://localhost:8080 (admin/admin)
2. Find the DAG run
3. Check task logs for errors

### Validation Failures

**Error:** `Quantity mismatch` or `Sales mismatch`

This indicates a bug in the transformation logic. The aggregation isn't correctly summing the values.

**Debug:**
1. Check the DAG's SQL transformation query
2. Verify the aggregation logic in `data_transformation_dag.py`
3. Manually query both tables in Snowflake to compare

## Architecture

### Components

```
┌─────────────────────────────────────────────────────────────┐
│                    run_integration_test.sh                   │
│  • Starts containers if needed                               │
│  • Unpauses DAG                                              │
│  • Runs integration_test_simple.py                           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              integration_test_simple.py                      │
│                                                               │
│  1. Setup:    Create test schema + sample data               │
│  2. Configure: Set Airflow variables                         │
│  3. Trigger:   Run data_transformation_pipeline DAG          │
│  4. Wait:      Monitor DAG execution (5 min timeout)         │
│  5. Validate:  Check results in Snowflake                    │
│  6. Cleanup:   Remove test schema and variables              │
└─────────────────────────────────────────────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
        ┌──────────────────┐  ┌──────────────────┐
        │  Airflow (Docker) │  │   Snowflake      │
        │  • Webserver      │  │   • Test Schema  │
        │  • Scheduler      │  │   • Source Table │
        │  • Postgres       │  │   • Target Table │
        └──────────────────┘  └──────────────────┘
```

### Files

- **`run_integration_test.sh`** - Main test runner script
- **`integration_test_simple.py`** - Python test implementation
- **`docker-compose.yml`** - Airflow container configuration
- **`.env`** - Snowflake credentials (not in git)
- **`dags/data_transformation_dag.py`** - The DAG being tested

## Advanced Usage

### Running Tests in CI/CD

The script is designed to work in CI/CD environments:

```bash
# In your CI pipeline
export SNOWFLAKE_ACCOUNT="your-account"
export SNOWFLAKE_USER="ci-user"
export SNOWFLAKE_PASSWORD="${SNOWFLAKE_CI_PASSWORD}"
export SNOWFLAKE_WAREHOUSE="CI_WAREHOUSE"
export SNOWFLAKE_DATABASE="CI_DB"

./run_integration_test.sh
```

### Adjusting Timeout

The default DAG execution timeout is 300 seconds (5 minutes). To change it, edit `integration_test_simple.py`:

```python
def wait_for_dag_completion_cli(run_id, timeout=300):  # Change this value
```

### Testing Different DAGs

To test a different DAG, edit the `DAG_ID` in `integration_test_simple.py`:

```python
DAG_ID = "your_dag_name_here"
```

## Getting Help

### Useful Commands

**Check if containers are running:**
```bash
docker ps --filter "name=dataintegrationtest"
```

**Access Airflow UI:**
```
http://localhost:8080
Username: admin
Password: admin
```

**View Airflow logs:**
```bash
docker logs -f dataintegrationtest-airflow-scheduler-1
docker logs -f dataintegrationtest-airflow-webserver-1
```

**Access Airflow container shell:**
```bash
docker exec -it dataintegrationtest-airflow-webserver-1 bash
```

**List Airflow DAGs:**
```bash
docker exec dataintegrationtest-airflow-webserver-1 airflow dags list
```

**Check DAG status:**
```bash
docker exec dataintegrationtest-airflow-webserver-1 airflow dags list-runs --dag-id data_transformation_pipeline
```

### Common Issues Summary

| Issue | Solution |
|-------|----------|
| Containers won't start | `docker-compose down && docker-compose up -d` |
| Port 8080 already in use | Stop conflicting services or change port in docker-compose.yml |
| DAG not found | Check DAG files are in `dags/` directory |
| Snowflake permission denied | Verify user has CREATE/DROP schema permissions |
| Test hangs during execution | Check scheduler logs for errors |

## What Success Looks Like

A successful test run should:
- ✓ Complete in under 1 minute (typically 30-45 seconds)
- ✓ Show green checkmarks (✓) for all 6 steps
- ✓ Display "TEST PASSED" header
- ✓ End with "Integration test completed successfully!"
- ✓ Return exit code 0

## Next Steps

After the integration test passes:
1. Review the DAG logs in Airflow UI to understand execution flow
2. Examine the transformation SQL in `data_transformation_dag.py`
3. Modify the DAG for your specific use case
4. Run the integration test again to validate changes

---

**Questions or Issues?**
- Check troubleshooting section above
- Review Airflow logs: `docker logs dataintegrationtest-airflow-scheduler-1`
- Access Airflow UI: http://localhost:8080
