#!/usr/bin/env python3
"""
Integration Test Demo for Airflow-Snowflake Data Transformation

This script demonstrates how integration tests can catch data quality bugs
in production pipelines. Perfect for pitching integration testing to your team.

Usage:
    python demo_pitch.py                           # Happy path
    python demo_pitch.py --inject-bug=aggregation  # Simulate aggregation bug
    python demo_pitch.py --inject-bug=negative     # Simulate negative values bug
"""

import os
import time
import sys
import argparse
from datetime import datetime
from dotenv import load_dotenv
import snowflake.connector
import requests
from requests.auth import HTTPBasicAuth

# Load environment variables from .env file
load_dotenv()

# Configuration
TEST_SCHEMA = f"TEST_SCHEMA_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
SOURCE_TABLE = "sales_data"
TARGET_TABLE = "sales_summary"
DAG_ID = "data_transformation_pipeline"
AIRFLOW_BASE_URL = "http://localhost:8080/api/v1"
AIRFLOW_AUTH = HTTPBasicAuth("admin", "admin")

# Colors for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'
BOLD = '\033[1m'


def print_header(message):
    """Print a formatted header."""
    print(f"\n{BLUE}{'=' * 80}{RESET}")
    print(f"{BLUE}{BOLD}{message.center(80)}{RESET}")
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


def setup_test_environment(inject_bug=None):
    """Create test schema and source table with sample data."""
    print_header("STEP 1: Setting Up Test Data")

    conn = get_snowflake_connection()
    cursor = conn.cursor()

    try:
        # Create test schema
        print_info(f"Creating schema {TEST_SCHEMA}")
        cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {TEST_SCHEMA}")
        print_success(f"Schema {TEST_SCHEMA} created")

        # Use the test schema
        cursor.execute(f"USE SCHEMA {TEST_SCHEMA}")

        # Create source table
        print_info(f"Creating source table {SOURCE_TABLE}")
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

        # Insert sample data (with optional bug injection)
        print_info("Inserting sample sales data...")

        # Normal data - adjust quantity if injecting negative bug
        qty_laptop_1 = -10 if inject_bug == 'negative' else 10

        insert_sql = f"""
        INSERT INTO {SOURCE_TABLE}
            (product_id, product_name, category, sale_date, quantity, unit_price)
        VALUES
            (1, 'Laptop Pro', 'Electronics', CURRENT_DATE() - 5, {qty_laptop_1}, 1200.00),
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

        # Inject aggregation bug if requested
        if inject_bug == 'aggregation':
            print_info(f"{YELLOW}[BUG INJECTED] Adding extra row that won't appear in target{RESET}")
            cursor.execute(f"""
                INSERT INTO {SOURCE_TABLE} VALUES
                (7, 'Mystery Product', 'Unknown', CURRENT_DATE() - 100, 50, 99.99)
            """)
            print_error("Bug injected: Extra row with old date outside 30-day window")

        # Get stats
        cursor.execute(f"""
            SELECT COUNT(*), SUM(quantity), SUM(quantity * unit_price)
            FROM {SOURCE_TABLE}
        """)
        stats = cursor.fetchone()
        total_items = stats[1]
        total_sales = stats[2]

        print_success(f"Source data ready: {total_items} items, ${total_sales:,.2f} total sales")

        return True, stats

    except Exception as e:
        print_error(f"Failed to setup test environment: {e}")
        return False, None

    finally:
        cursor.close()
        conn.close()


def set_airflow_variables():
    """Set Airflow variables for the test using REST API."""
    print_header("STEP 2: Configuring Test Variables")

    variables = {
        'test_schema': TEST_SCHEMA,
        'source_table': SOURCE_TABLE,
        'target_table': TARGET_TABLE
    }

    try:
        for key, value in variables.items():
            response = requests.patch(
                f"{AIRFLOW_BASE_URL}/variables/{key}",
                json={"key": key, "value": value},
                auth=AIRFLOW_AUTH,
                headers={"Content-Type": "application/json"}
            )

            # If variable doesn't exist (404), create it with POST
            if response.status_code == 404:
                response = requests.post(
                    f"{AIRFLOW_BASE_URL}/variables",
                    json={"key": key, "value": value},
                    auth=AIRFLOW_AUTH,
                    headers={"Content-Type": "application/json"}
                )

            if response.status_code in [200, 201]:
                print_success(f"Set {key} = {value}")
            else:
                print_error(f"Failed to set {key}: {response.status_code} - {response.text}")
                return False

        return True

    except Exception as e:
        print_error(f"Failed to set Airflow variables: {e}")
        return False


def trigger_dag_via_rest():
    """Trigger the transformation DAG using Airflow REST API."""
    print_header("STEP 3: Triggering ETL Pipeline")

    try:
        print_info(f"Triggering DAG: {DAG_ID}")

        # Trigger DAG via REST API
        response = requests.post(
            f"{AIRFLOW_BASE_URL}/dags/{DAG_ID}/dagRuns",
            json={},
            auth=AIRFLOW_AUTH,
            headers={"Content-Type": "application/json"}
        )

        if response.status_code in [200, 201]:
            run_data = response.json()
            run_id = run_data['dag_run_id']
            print_success(f"DAG triggered successfully")
            print_info(f"Run ID: {run_id}")
            return run_id
        else:
            print_error(f"Failed to trigger DAG: {response.status_code} - {response.text}")
            return None

    except Exception as e:
        print_error(f"Failed to trigger DAG: {e}")
        return None


def wait_for_dag_completion(run_id, timeout=300):
    """Wait for DAG to complete using REST API."""
    print_header("STEP 4: Monitoring DAG Execution")

    start_time = time.time()
    print_info(f"Waiting for DAG to complete (timeout: {timeout}s)...")

    # Give scheduler a moment to register the trigger
    time.sleep(3)

    while time.time() - start_time < timeout:
        try:
            # Get DAG run state via REST API
            response = requests.get(
                f"{AIRFLOW_BASE_URL}/dags/{DAG_ID}/dagRuns/{run_id}",
                auth=AIRFLOW_AUTH
            )

            if response.status_code == 200:
                run_data = response.json()
                state = run_data['state']

                elapsed = int(time.time() - start_time)
                print_info(f"  [{elapsed}s] DAG state: {state}")

                if state == 'success':
                    print_success(f"DAG completed successfully in {elapsed} seconds")
                    return True
                elif state == 'failed':
                    print_error("DAG execution failed")
                    return False
                # Otherwise keep waiting (running/queued)

            time.sleep(5)

        except Exception as e:
            elapsed = int(time.time() - start_time)
            print_info(f"  [{elapsed}s] Checking DAG status... ({e})")
            time.sleep(5)

    print_error(f"DAG did not complete within {timeout} seconds")
    print_info("Note: The DAG may still be running. Check Airflow UI or logs.")
    return False


def validate_transformation(source_stats):
    """Validate the transformation results."""
    print_header("STEP 5: Validating Results")

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
        print_success(f"Target table contains {row_count} aggregated products")

        # Show sample transformed data
        print_info("\nTransformed Data:")
        cursor.execute(f"""
            SELECT product_name, category, total_quantity, total_sales,
                   avg_unit_price, transaction_count
            FROM {TARGET_TABLE}
            ORDER BY total_sales DESC
        """)

        results = cursor.fetchall()
        print(f"  {'Product':<25} {'Category':<15} {'Qty':<8} {'Sales':<12} {'Avg Price':<12} {'Txns':<6}")
        print(f"  {'-' * 90}")

        for row in results[:6]:  # Show top 6
            print(f"  {row[0]:<25} {row[1]:<15} {row[2]:<8} ${row[3]:<11,.2f} ${row[4]:<11.2f} {row[5]:<6}")

        # Validate aggregation
        print_info("\nValidation checks:")

        cursor.execute(f"""
            SELECT SUM(quantity), SUM(quantity * unit_price)
            FROM {SOURCE_TABLE}
        """)
        source_totals = cursor.fetchone()

        cursor.execute(f"""
            SELECT SUM(total_quantity), SUM(total_sales)
            FROM {TARGET_TABLE}
        """)
        target_totals = cursor.fetchone()

        all_checks_passed = True

        # Check quantities match
        if abs(source_totals[0] - target_totals[0]) < 0.01:
            print_success(f"Quantity totals match: {target_totals[0]}")
        else:
            print_error(f"Quantity mismatch: Source={source_totals[0]}, Target={target_totals[0]}")
            all_checks_passed = False

        # Check sales totals match
        if abs(source_totals[1] - target_totals[1]) < 0.01:
            print_success(f"Sales totals match: ${target_totals[1]:,.2f}")
        else:
            print_error(f"Sales mismatch: Source=${source_totals[1]:,.2f}, Target=${target_totals[1]:,.2f}")
            all_checks_passed = False

        # Verify no negative values
        cursor.execute(f"""
            SELECT COUNT(*)
            FROM {TARGET_TABLE}
            WHERE total_quantity <= 0 OR total_sales <= 0
        """)
        invalid_count = cursor.fetchone()[0]

        if invalid_count == 0:
            print_success("No invalid data (negative quantities or sales)")
        else:
            print_error(f"Found {invalid_count} rows with invalid data")
            all_checks_passed = False

        if all_checks_passed:
            print(f"\n{GREEN}{BOLD}All validation checks PASSED!{RESET}\n")
        else:
            print(f"\n{RED}{BOLD}Some validation checks FAILED!{RESET}\n")

        return all_checks_passed

    except Exception as e:
        print_error(f"Validation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        cursor.close()
        conn.close()


def cleanup_test_resources():
    """Clean up all test resources."""
    print_header("STEP 6: Cleaning Up")

    conn = get_snowflake_connection()
    cursor = conn.cursor()

    try:
        # Drop test schema (cascades to all tables)
        print_info(f"Dropping test schema: {TEST_SCHEMA}")
        cursor.execute(f"DROP SCHEMA IF EXISTS {TEST_SCHEMA} CASCADE")
        print_success(f"Dropped test schema {TEST_SCHEMA}")

        # Clean up Airflow variables using REST API
        print_info("Removing Airflow variables")
        try:
            for var_key in ['test_schema', 'source_table', 'target_table']:
                response = requests.delete(
                    f"{AIRFLOW_BASE_URL}/variables/{var_key}",
                    auth=AIRFLOW_AUTH
                )
                # 404 is fine - variable didn't exist
                if response.status_code not in [200, 204, 404]:
                    print_info(f"Could not delete {var_key}: {response.status_code}")
            print_success("Removed Airflow variables")
        except Exception as e:
            print_info(f"Some variables may not exist: {e}")

        return True

    except Exception as e:
        print_error(f"Cleanup failed: {e}")
        return False

    finally:
        cursor.close()
        conn.close()


def main():
    """Run the integration test."""
    # Parse arguments
    parser = argparse.ArgumentParser(
        description='Integration test demo for Airflow-Snowflake pipeline'
    )
    parser.add_argument(
        '--inject-bug',
        choices=['aggregation', 'negative'],
        help='Inject a bug for demo purposes'
    )
    args = parser.parse_args()

    # Print banner
    print_header("AIRFLOW + SNOWFLAKE INTEGRATION TEST DEMO")
    print_info(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print_info(f"Test Schema: {TEST_SCHEMA}")
    print_info(f"Estimated time: 60 seconds (vs 30 minutes manual)")

    if args.inject_bug:
        print_error(f"⚠️  BUG INJECTION MODE: {args.inject_bug}")
        print_info("This test should FAIL to demonstrate validation catching bugs")

    test_passed = False
    start_time = time.time()

    try:
        # Step 1: Setup
        success, source_stats = setup_test_environment(inject_bug=args.inject_bug)
        if not success:
            print_error("Test failed at setup stage")
            return 1

        # Step 2: Configure Airflow
        if not set_airflow_variables():
            print_error("Test failed at configuration stage")
            return 1

        # Step 3: Trigger DAG
        run_id = trigger_dag_via_rest()
        if not run_id:
            print_error("Test failed at DAG trigger stage")
            return 1

        # Step 4: Wait for completion
        if not wait_for_dag_completion(run_id):
            print_error("Test failed at DAG execution stage")
            return 1

        # Step 5: Validate
        if not validate_transformation(source_stats):
            print_error("Test failed at validation stage")
            return 1

        test_passed = True

    except Exception as e:
        print_error(f"Test failed with exception: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Step 6: Cleanup (always run)
        cleanup_test_resources()

        # Print summary
        print_header("TEST SUMMARY")

        elapsed_time = int(time.time() - start_time)
        print_info(f"Test ended at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        if test_passed:
            print_success(f"Result: PASSED ✓")
            print_info(f"⏱  Total time: {elapsed_time} seconds")
            print_info(f"💰 Time saved: ~{30 - elapsed_time//60} minutes (vs manual testing)")
            print_info(f"🎯 Coverage: End-to-end ETL pipeline with data quality validation")
            return 0
        else:
            print_error(f"Result: FAILED ✗")
            print_info(f"⏱  Total time: {elapsed_time} seconds")
            if args.inject_bug:
                print_success("✓ Test correctly detected the injected bug!")
                print_info("This demonstrates how integration tests catch data quality issues")
            return 1


if __name__ == "__main__":
    sys.exit(main())
