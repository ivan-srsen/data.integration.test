# Integration Testing Guide

This guide will help you understand and write integration tests for our Airflow + Snowflake data pipelines.

## Why Integration Tests Matter for Data Pipelines

Data pipelines are particularly vulnerable to silent failures:
- **Aggregation bugs** can cause incorrect business metrics
- **Schema changes** might break transformations without immediate errors
- **Data quality issues** often pass unit tests but fail in production
- **Pipeline orchestration** problems only appear when steps run together

Integration tests catch these issues by validating the entire data flow from source to target.

## Quick Start

### Prerequisites
- Airflow running locally via Docker: `docker-compose up -d`
- Snowflake credentials in `.env` file
- Python 3.11+ with required packages

### Running the Demo Test

```bash
# Happy path - everything should pass
python demo_pitch.py

# With bug injection - test should catch the problem
python demo_pitch.py --inject-bug=aggregation
```

### Expected Output

```
================================================================================
          AIRFLOW + SNOWFLAKE INTEGRATION TEST DEMO
================================================================================

Test Schema: TEST_SCHEMA_20250214_143022
Estimated time: 60 seconds (vs 30 minutes manual)

[... test runs through 6 steps ...]

✓ Result: PASSED
⏱ Total time: 62 seconds
💰 Time saved: 28 minutes (vs manual testing)
```

## How the Test Works

### The 6-Step Pattern

All integration tests follow this structure:

#### 1. **Setup Test Environment**
- Create isolated test schema with timestamp
- Create source tables
- Insert known test data
- Why: Ensures tests don't interfere with production or each other

#### 2. **Configure Airflow**
- Set Airflow Variables that DAGs will read
- Tell the DAG where to find test data
- Why: Makes DAGs testable by accepting configuration

#### 3. **Trigger the Pipeline**
- Use Airflow REST API to trigger DAG
- Capture run ID for monitoring
- Why: Simulates production execution path

#### 4. **Monitor Execution**
- Poll DAG status via REST API
- Wait for SUCCESS or FAILED state
- Timeout after 5 minutes
- Why: Ensures DAG completes before validation

#### 5. **Validate Results**
- Check target tables exist
- Verify row counts match expectations
- Validate aggregations (SUM, AVG, COUNT)
- Check for data quality issues (nulls, negatives)
- Why: Catches bugs in transformation logic

#### 6. **Cleanup**
- Drop test schema (cascades to all tables)
- Remove Airflow variables
- Always runs, even if test fails
- Why: Keeps test environment clean for next run

## Writing Your First Test

### 1. Identify the Critical Flow

Start with your most important data pipeline:
- Highest business impact
- Changes frequently
- Complex transformation logic
- Known to have bugs in the past

### 2. Copy the Template

```python
#!/usr/bin/env python3
"""Integration test for [YOUR PIPELINE]"""

import os
import time
from datetime import datetime
import snowflake.connector
from airflow.models import Variable
import requests
from requests.auth import HTTPBasicAuth

TEST_SCHEMA = f"TEST_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
DAG_ID = "your_pipeline_dag"
AIRFLOW_URL = "http://localhost:8080/api/v1"
AUTH = HTTPBasicAuth("admin", "admin")

def setup_test_data():
    """Create test schema and insert known data"""
    # TODO: Your setup code here
    pass

def trigger_and_wait():
    """Trigger DAG via REST API and wait for completion"""
    # Trigger
    response = requests.post(
        f"{AIRFLOW_URL}/dags/{DAG_ID}/dagRuns",
        json={},
        auth=AUTH
    )
    run_id = response.json()['dag_run_id']

    # Wait
    while True:
        response = requests.get(
            f"{AIRFLOW_URL}/dags/{DAG_ID}/dagRuns/{run_id}",
            auth=AUTH
        )
        state = response.json()['state']
        if state in ['success', 'failed']:
            return state == 'success'
        time.sleep(5)

def validate_results():
    """Check that output matches expectations"""
    # TODO: Your validation code here
    pass

def cleanup():
    """Always cleanup test resources"""
    # TODO: Your cleanup code here
    pass

if __name__ == "__main__":
    try:
        setup_test_data()
        if trigger_and_wait():
            assert validate_results()
            print("✓ Test PASSED")
    finally:
        cleanup()
```

### 3. Add Known Test Data

Use predictable values that make validation easy:

```python
# Good: Known totals
INSERT INTO sales VALUES
    (1, 'Product A', 100, 10.00),  -- $1,000
    (2, 'Product B', 50, 20.00);    -- $1,000
-- Total: $2,000 (easy to verify)

# Bad: Random data
INSERT INTO sales VALUES
    (1, 'Product A', 73, 12.47),   -- $910.31
    (2, 'Product B', 29, 18.93);    -- $548.97
-- Total: $1,459.28 (hard to verify)
```

### 4. Write Specific Validations

```python
def validate_results():
    cursor.execute("SELECT SUM(total_sales) FROM target_table")
    actual = cursor.fetchone()[0]

    expected = 2000.00  # We know this from test data

    if abs(actual - expected) < 0.01:
        print(f"✓ Sales total matches: ${actual}")
        return True
    else:
        print(f"✗ Sales mismatch: expected ${expected}, got ${actual}")
        return False
```

## Common Patterns

### Using Timestamp Schemas
```python
TEST_SCHEMA = f"TEST_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
```
- Prevents test conflicts
- Makes cleanup easier
- Allows parallel test runs

### REST API Trigger + Wait
```python
# Trigger
response = requests.post(f"{AIRFLOW_URL}/dags/{dag_id}/dagRuns",
                        json={}, auth=AUTH)
run_id = response.json()['dag_run_id']

# Wait for completion
while time.time() - start < timeout:
    response = requests.get(
        f"{AIRFLOW_URL}/dags/{dag_id}/dagRuns/{run_id}",
        auth=AUTH
    )
    if response.json()['state'] in ['success', 'failed']:
        break
    time.sleep(5)
```

### Always Cleanup
```python
try:
    # Run test
    pass
finally:
    # Always cleanup, even on failure
    cursor.execute(f"DROP SCHEMA IF EXISTS {TEST_SCHEMA} CASCADE")
    Variable.delete('test_var')
```

### Validation Assertions
```python
# Check existence
assert table_exists(TARGET_TABLE), "Target table should exist"

# Check counts
assert row_count > 0, "Target should have data"

# Check aggregations
source_total = get_source_total()
target_total = get_target_total()
assert abs(source_total - target_total) < 0.01, \
    f"Totals should match: {source_total} vs {target_total}"

# Check data quality
invalid_rows = count_invalid_rows()
assert invalid_rows == 0, f"Found {invalid_rows} invalid rows"
```

## Troubleshooting

### Test Times Out Waiting for DAG

**Symptom**: Test hangs at "Monitoring DAG Execution"

**Solutions**:
1. Check Airflow scheduler is running: `docker ps | grep scheduler`
2. Verify DAG exists: Open http://localhost:8080
3. Check DAG isn't paused
4. Increase timeout: `wait_for_dag_completion(run_id, timeout=600)`

### Snowflake Connection Fails

**Symptom**: "Failed to connect to Snowflake"

**Solutions**:
1. Verify `.env` file has correct credentials
2. Check warehouse is running in Snowflake UI
3. Verify role has necessary permissions
4. Test connection manually: `python -c "import snowflake.connector; ..."`

### Test Cleanup Fails

**Symptom**: Test fails but leaves behind test schemas

**Solutions**:
1. Ensure cleanup is in `finally` block
2. Add error handling to cleanup:
   ```python
   try:
       cursor.execute(f"DROP SCHEMA {TEST_SCHEMA} CASCADE")
   except Exception as e:
       print(f"Cleanup warning: {e}")
   ```

### DAG State is "failed"

**Symptom**: DAG execution fails

**Solutions**:
1. Check Airflow logs: `docker logs super-airflow-scheduler-1`
2. Open Airflow UI and click on failed task
3. Verify test schema and tables exist
4. Check Snowflake permissions

## Best Practices

### DO
- ✓ Use timestamp-based test schemas
- ✓ Insert known, predictable test data
- ✓ Validate aggregations against source
- ✓ Always cleanup in `finally` block
- ✓ Add clear print statements showing progress
- ✓ Set reasonable timeouts (5-10 minutes)
- ✓ Test critical paths first

### DON'T
- ✗ Test against production schemas
- ✗ Use random/unpredictable test data
- ✗ Skip validation - test everything that matters
- ✗ Leave test resources behind
- ✗ Make tests depend on each other
- ✗ Test every edge case immediately

## CI/CD Integration

### Running in CI/CD

```yaml
# .github/workflows/integration-tests.yml
name: Integration Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Start Airflow
        run: docker-compose up -d

      - name: Wait for Airflow
        run: sleep 30

      - name: Run Integration Tests
        env:
          SNOWFLAKE_ACCOUNT: ${{ secrets.SNOWFLAKE_ACCOUNT }}
          SNOWFLAKE_USER: ${{ secrets.SNOWFLAKE_USER }}
          SNOWFLAKE_PASSWORD: ${{ secrets.SNOWFLAKE_PASSWORD }}
        run: python demo_pitch.py
```

## Next Steps

1. **Run the demo**: `python demo_pitch.py`
2. **Study the code**: Open `demo_pitch.py` and read through it
3. **Identify your critical flow**: Pick one pipeline to test
4. **Copy and adapt**: Use `demo_pitch.py` as a template
5. **Add to CI/CD**: Automate tests in your deployment pipeline

## Getting Help

- **Check the demo**: `python demo_pitch.py` has examples of all patterns
- **Review DAG logs**: Airflow UI → DAG → Task → Logs
- **Snowflake queries**: Run test queries manually in Snowflake UI
- **Team chat**: Ask in #engineering for help

## Metrics to Track

- **Coverage**: % of critical pipelines with tests
- **Bugs caught**: Issues found before production
- **Time saved**: Manual testing time eliminated
- **Confidence**: Developer survey on refactoring confidence
