#!/usr/bin/env python3
"""
Simplified Integration Test for Airflow-Snowflake Data Transformation

This version uses Airflow CLI to check DAG status instead of direct database queries.
"""

import os
import time
import sys
import subprocess
from datetime import datetime
import snowflake.connector
from airflow.models import Variable
from airflow.api.client.local_client import Client

# Configuration
TEST_SCHEMA = f"TEST_SCHEMA_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
SOURCE_TABLE = "sales_data"
TARGET_TABLE = "sales_summary"
DAG_ID = "data_transformation_pipeline"

# Colors for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'


def print_header(message):
    """Print a formatted header."""
    print(f"\n{BLUE}{'=' * 80}{RESET}")
    print(f"{BLUE}{message.center(80)}{RESET}")
    print(f"{BLUE}{'=' * 80}{RESET}\n")


def print_success(message):
    """Print success message."""
    print(f"{GREEN}✓ {message}{RESET}")


def print_error(message):
    """Print error message."""
    print(f"{RED}✗ {message}{RESET}")


def print_info(message):
    """Print info message."""
    print(f"{YELLOW}ℹ {message}{RESET}")


def get_snowflake_connection(schema=None):
    """Create Snowflake connection."""
    conn_params = {
        'account': os.getenv('SNOWFLAKE_ACCOUNT'),
        'user': os.getenv('SNOWFLAKE_USER'),
        'password': os.getenv('SNOWFLAKE_PASSWORD'),
        'role': os.getenv('SNOWFLAKE_ROLE', 'ACCOUNTADMIN'),
        'warehouse': os.getenv('SNOWFLAKE_WAREHOUSE'),
        'database': os.getenv('SNOWFLAKE_DATABASE'),
    }

    if schema:
        conn_params['schema'] = schema

    return snowflake.connector.connect(**conn_params)


def setup_test_environment():
    """Create test schema and source table with sample data."""
    print_header("STEP 1: Setting Up Test Environment")

    conn = get_snowflake_connection()
    cursor = conn.cursor()

    try:
        # Create test schema
        print_info(f"Creating test schema: {TEST_SCHEMA}")
        cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {TEST_SCHEMA}")
        print_success(f"Schema {TEST_SCHEMA} created")

        # Use the test schema
        cursor.execute(f"USE SCHEMA {TEST_SCHEMA}")

        # Create source table
        print_info(f"Creating source table: {SOURCE_TABLE}")
        create_table_sql = f"""
        CREATE TABLE {SOURCE_TABLE} (
            product_id INTEGER,
            product_name VARCHAR(100),
            category VARCHAR(50),
            sale_date DATE,
            quantity INTEGER,
            unit_price FLOAT
        )
        """
        cursor.execute(create_table_sql)
        print_success(f"Table {SOURCE_TABLE} created")

        # Insert sample data
        print_info("Inserting sample sales data...")
        insert_sql = f"""
        INSERT INTO {SOURCE_TABLE}
            (product_id, product_name, category, sale_date, quantity, unit_price)
        VALUES
            (1, 'Laptop Pro', 'Electronics', CURRENT_DATE() - 5, 10, 1200.00),
            (1, 'Laptop Pro', 'Electronics', CURRENT_DATE() - 10, 5, 1200.00),
            (1, 'Laptop Pro', 'Electronics', CURRENT_DATE() - 15, 8, 1150.00),
            (2, 'Wireless Mouse', 'Electronics', CURRENT_DATE() - 3, 50, 25.99),
            (2, 'Wireless Mouse', 'Electronics', CURRENT_DATE() - 7, 30, 25.99),
            (2, 'Wireless Mouse', 'Electronics', CURRENT_DATE() - 12, 45, 24.99),
            (3, 'USB-C Cable', 'Accessories', CURRENT_DATE() - 2, 100, 9.99),
            (3, 'USB-C Cable', 'Accessories', CURRENT_DATE() - 8, 75, 9.99),
            (3, 'USB-C Cable', 'Accessories', CURRENT_DATE() - 14, 80, 8.99),
            (4, 'Ergonomic Keyboard', 'Electronics', CURRENT_DATE() - 4, 15, 89.99),
            (4, 'Ergonomic Keyboard', 'Electronics', CURRENT_DATE() - 11, 12, 89.99),
            (5, 'Monitor Stand', 'Accessories', CURRENT_DATE() - 6, 20, 45.50),
            (5, 'Monitor Stand', 'Accessories', CURRENT_DATE() - 13, 18, 45.50),
            (6, 'Webcam HD', 'Electronics', CURRENT_DATE() - 1, 25, 79.99),
            (6, 'Webcam HD', 'Electronics', CURRENT_DATE() - 9, 22, 79.99)
        """
        cursor.execute(insert_sql)
        row_count = cursor.rowcount
        print_success(f"Inserted {row_count} rows of sample data")

        # Verify inserted data
        cursor.execute(f"SELECT COUNT(*) FROM {SOURCE_TABLE}")
        count = cursor.fetchone()[0]
        print_success(f"Verified: Source table contains {count} rows")

        return True

    except Exception as e:
        print_error(f"Failed to setup test environment: {e}")
        return False

    finally:
        cursor.close()
        conn.close()


def set_airflow_variables():
    """Set Airflow variables for the test."""
    print_header("STEP 2: Configuring Airflow Variables")

    try:
        Variable.set('test_schema', TEST_SCHEMA)
        Variable.set('source_table', SOURCE_TABLE)
        Variable.set('target_table', TARGET_TABLE)

        print_success(f"Set test_schema = {TEST_SCHEMA}")
        print_success(f"Set source_table = {SOURCE_TABLE}")
        print_success(f"Set target_table = {TARGET_TABLE}")

        return True

    except Exception as e:
        print_error(f"Failed to set Airflow variables: {e}")
        return False


def trigger_dag():
    """Trigger the transformation DAG."""
    print_header("STEP 3: Triggering Data Transformation DAG")

    try:
        client = Client(None, None)

        print_info(f"Triggering DAG: {DAG_ID}")
        run_id = client.trigger_dag(dag_id=DAG_ID)

        print_success(f"DAG triggered successfully")
        print_info(f"Run ID: {run_id}")

        return run_id

    except Exception as e:
        print_error(f"Failed to trigger DAG: {e}")
        return None


def wait_for_dag_completion_cli(run_id, timeout=300):
    """Wait for DAG to complete using CLI."""
    print_header("STEP 4: Waiting for DAG Completion")

    print_info(f"Waiting for DAG to complete (timeout: {timeout}s)...")
    start_time = time.time()

    # Give scheduler a moment to register the trigger
    time.sleep(3)

    while time.time() - start_time < timeout:
        try:
            # Use airflow CLI to check DAG state
            result = subprocess.run(
                ['airflow', 'dags', 'list-runs', '--dag-id', DAG_ID, '--no-backfill', '--output', 'json'],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0 and result.stdout.strip():
                import json
                try:
                    runs = json.loads(result.stdout)

                    if runs:
                        # Get the most recent run
                        latest_run = runs[0] if isinstance(runs, list) else runs
                        state = latest_run.get('state', 'unknown')

                        elapsed = int(time.time() - start_time)
                        print_info(f"  [{elapsed}s] DAG state: {state}")

                        if state == 'success':
                            print_success(f"DAG completed successfully in {elapsed} seconds")
                            return True
                        elif state == 'failed':
                            print_error("DAG execution failed")
                            return False
                        # Otherwise keep waiting (running/queued)
                    else:
                        print_info(f"  Waiting for DAG run to start...")
                except json.JSONDecodeError as e:
                    print_info(f"  Could not parse DAG status: {e}")

            # Wait before checking again
            time.sleep(5)

        except Exception as e:
            elapsed = int(time.time() - start_time)
            print_info(f"  [{elapsed}s] Checking DAG status... ({e})")
            time.sleep(5)

    print_error(f"DAG did not complete within {timeout} seconds")
    print_info("Note: The DAG may still be running. Check Airflow UI or logs.")
    return False


def validate_transformation():
    """Validate the transformation results."""
    print_header("STEP 5: Validating Transformation Results")

    conn = get_snowflake_connection(schema=TEST_SCHEMA)
    cursor = conn.cursor()

    try:
        # Check if target table exists
        cursor.execute(f"""
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_schema = '{TEST_SCHEMA}'
            AND table_name = '{TARGET_TABLE.upper()}'
        """)

        if cursor.fetchone()[0] == 0:
            print_error(f"Target table {TARGET_TABLE} does not exist")
            return False

        print_success(f"Target table {TARGET_TABLE} exists")

        # Get row count
        cursor.execute(f"SELECT COUNT(*) FROM {TARGET_TABLE}")
        row_count = cursor.fetchone()[0]
        print_success(f"Target table contains {row_count} rows")

        # Validate aggregation
        cursor.execute(f"""
            SELECT
                SUM(quantity) as source_qty,
                SUM(quantity * unit_price) as source_sales
            FROM {SOURCE_TABLE}
        """)
        source_totals = cursor.fetchone()

        cursor.execute(f"""
            SELECT
                SUM(total_quantity) as target_qty,
                SUM(total_sales) as target_sales
            FROM {TARGET_TABLE}
        """)
        target_totals = cursor.fetchone()

        print_info("\nValidation checks:")

        # Check quantities match
        if abs(source_totals[0] - target_totals[0]) < 0.01:
            print_success(f"Quantity totals match: {target_totals[0]}")
        else:
            print_error(f"Quantity mismatch: Source={source_totals[0]}, Target={target_totals[0]}")
            return False

        # Check sales totals match
        if abs(source_totals[1] - target_totals[1]) < 0.01:
            print_success(f"Sales totals match: ${target_totals[1]:,.2f}")
        else:
            print_error(f"Sales mismatch: Source=${source_totals[1]}, Target=${target_totals[1]}")
            return False

        print_success("\nAll validation checks passed!")
        return True

    except Exception as e:
        print_error(f"Validation failed: {e}")
        return False

    finally:
        cursor.close()
        conn.close()


def cleanup_test_resources():
    """Clean up all test resources."""
    print_header("STEP 6: Cleaning Up Test Resources")

    conn = get_snowflake_connection()
    cursor = conn.cursor()

    try:
        # Drop test schema (cascades to all tables)
        print_info(f"Dropping test schema: {TEST_SCHEMA}")
        cursor.execute(f"DROP SCHEMA IF EXISTS {TEST_SCHEMA} CASCADE")
        print_success(f"Schema {TEST_SCHEMA} and all tables deleted")

        # Clean up Airflow variables
        print_info("Removing Airflow variables")
        try:
            Variable.delete('test_schema')
            Variable.delete('source_table')
            Variable.delete('target_table')
            print_success("Airflow variables cleaned up")
        except Exception as e:
            print_info(f"Some variables may not exist: {e}")

        print_success("\nCleanup completed successfully!")
        return True

    except Exception as e:
        print_error(f"Cleanup failed: {e}")
        return False

    finally:
        cursor.close()
        conn.close()


def main():
    """Run the integration test."""
    print_header("AIRFLOW-SNOWFLAKE INTEGRATION TEST (Simplified)")
    print_info(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    test_passed = False

    try:
        # Step 1: Setup
        if not setup_test_environment():
            print_error("Test failed at setup stage")
            return 1

        # Step 2: Configure Airflow
        if not set_airflow_variables():
            print_error("Test failed at configuration stage")
            return 1

        # Step 3: Trigger DAG
        run_id = trigger_dag()
        if not run_id:
            print_error("Test failed at DAG trigger stage")
            return 1

        # Step 4: Wait for completion
        if not wait_for_dag_completion_cli(run_id):
            print_info("DAG monitoring timed out, but checking results anyway...")

        # Step 5: Validate (even if monitoring failed)
        if not validate_transformation():
            print_error("Test failed at validation stage")
            return 1

        test_passed = True
        print_header("TEST PASSED")
        print_success("All stages completed successfully!")

    except Exception as e:
        print_error(f"Test failed with exception: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Step 6: Cleanup (always run)
        cleanup_test_resources()

        print_header("TEST SUMMARY")
        print_info(f"Test ended at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        if test_passed:
            print_success("Result: PASSED ✓")
            return 0
        else:
            print_error("Result: FAILED ✗")
            return 1


if __name__ == "__main__":
    sys.exit(main())
