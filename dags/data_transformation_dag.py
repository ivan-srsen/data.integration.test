"""
Data Transformation DAG

This DAG demonstrates a data transformation pipeline:
1. Reads data from a source table
2. Transforms the data (aggregation, filtering, calculations)
3. Writes the transformed data to a target table
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.models import Variable
import os
import logging

logger = logging.getLogger(__name__)

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=2),
}

dag = DAG(
    'data_transformation_pipeline',
    default_args=default_args,
    description='Transform data from source to target table',
    schedule_interval=None,
    catchup=False,
    tags=['snowflake', 'transformation', 'etl'],
)


def get_snowflake_connection(schema=None):
    """
    Create and return a Snowflake connection.
    """
    import snowflake.connector

    conn_params = {
        'account': os.getenv('SNOWFLAKE_ACCOUNT'),
        'user': os.getenv('SNOWFLAKE_USER'),
        'password': os.getenv('SNOWFLAKE_PASSWORD'),
        'role': os.getenv('SNOWFLAKE_ROLE', 'ACCOUNTADMIN'),
        'warehouse': os.getenv('SNOWFLAKE_WAREHOUSE'),
        'database': os.getenv('SNOWFLAKE_DATABASE'),
    }

    # Use custom schema if provided, otherwise use default
    if schema:
        conn_params['schema'] = schema
    else:
        conn_params['schema'] = os.getenv('SNOWFLAKE_SCHEMA', 'PUBLIC')

    return snowflake.connector.connect(**conn_params)


def extract_source_data(**context):
    """
    Extract data from the source table.
    """
    # Get schema from Airflow variable or use PUBLIC
    schema = Variable.get('test_schema', default_var='PUBLIC')
    source_table = Variable.get('source_table', default_var='sales_data')

    logger.info(f"Extracting data from {schema}.{source_table}...")

    conn = get_snowflake_connection(schema=schema)
    cursor = conn.cursor()

    try:
        query = f"""
        SELECT
            product_id,
            product_name,
            category,
            sale_date,
            quantity,
            unit_price,
            quantity * unit_price as total_amount
        FROM {source_table}
        WHERE sale_date >= DATEADD(day, -30, CURRENT_DATE())
        ORDER BY sale_date DESC
        """

        cursor.execute(query)
        results = cursor.fetchall()

        logger.info(f"Extracted {len(results)} rows from source table")

        # Push data to XCom for next task
        context['ti'].xcom_push(key='source_data_count', value=len(results))

        return len(results)

    finally:
        cursor.close()
        conn.close()


def transform_and_load(**context):
    """
    Transform data and load into target table.
    Aggregates sales by product and category.
    """
    schema = Variable.get('test_schema', default_var='PUBLIC')
    source_table = Variable.get('source_table', default_var='sales_data')
    target_table = Variable.get('target_table', default_var='sales_summary')

    logger.info(f"Transforming data from {schema}.{source_table} to {schema}.{target_table}...")

    conn = get_snowflake_connection(schema=schema)
    cursor = conn.cursor()

    try:
        # Create target table if it doesn't exist
        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {target_table} (
            product_id INTEGER,
            product_name VARCHAR(100),
            category VARCHAR(50),
            total_quantity INTEGER,
            total_sales FLOAT,
            avg_unit_price FLOAT,
            transaction_count INTEGER,
            created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
        )
        """
        cursor.execute(create_table_sql)
        logger.info(f"Target table {target_table} ready")

        # Clear existing data in target table
        cursor.execute(f"TRUNCATE TABLE {target_table}")
        logger.info("Cleared existing data from target table")

        # Perform transformation and insert
        transform_sql = f"""
        INSERT INTO {target_table}
            (product_id, product_name, category, total_quantity,
             total_sales, avg_unit_price, transaction_count)
        SELECT
            product_id,
            product_name,
            category,
            SUM(quantity) as total_quantity,
            SUM(quantity * unit_price) as total_sales,
            AVG(unit_price) as avg_unit_price,
            COUNT(*) as transaction_count
        FROM {source_table}
        WHERE sale_date >= DATEADD(day, -30, CURRENT_DATE())
        GROUP BY product_id, product_name, category
        ORDER BY total_sales DESC
        """

        cursor.execute(transform_sql)
        rows_inserted = cursor.rowcount

        logger.info(f"Transformed and loaded {rows_inserted} rows into target table")

        # Push result to XCom
        context['ti'].xcom_push(key='rows_transformed', value=rows_inserted)

        return rows_inserted

    finally:
        cursor.close()
        conn.close()


def validate_results(**context):
    """
    Validate the transformation results.
    """
    schema = Variable.get('test_schema', default_var='PUBLIC')
    target_table = Variable.get('target_table', default_var='sales_summary')

    logger.info(f"Validating results in {schema}.{target_table}...")

    conn = get_snowflake_connection(schema=schema)
    cursor = conn.cursor()

    try:
        # Check row count
        cursor.execute(f"SELECT COUNT(*) FROM {target_table}")
        row_count = cursor.fetchone()[0]
        logger.info(f"Target table contains {row_count} rows")

        # Validate data quality
        validation_sql = f"""
        SELECT
            COUNT(*) as total_rows,
            SUM(total_quantity) as total_qty,
            SUM(total_sales) as total_sales_amount,
            MIN(total_sales) as min_sales,
            MAX(total_sales) as max_sales
        FROM {target_table}
        """

        cursor.execute(validation_sql)
        result = cursor.fetchone()

        validation_results = {
            'total_rows': result[0],
            'total_quantity': int(result[1]),
            'total_sales_amount': float(result[2]),
            'min_sales': float(result[3]),
            'max_sales': float(result[4])
        }

        logger.info(f"Validation results: {validation_results}")

        # Check for data quality issues
        cursor.execute(f"""
            SELECT COUNT(*) FROM {target_table}
            WHERE total_quantity <= 0 OR total_sales <= 0
        """)
        invalid_rows = cursor.fetchone()[0]

        if invalid_rows > 0:
            logger.warning(f"Found {invalid_rows} rows with invalid data")
            raise ValueError(f"Data quality check failed: {invalid_rows} invalid rows")

        logger.info("All validation checks passed!")

        # Push validation results to XCom
        context['ti'].xcom_push(key='validation_results', value=validation_results)

        return validation_results

    finally:
        cursor.close()
        conn.close()


# Define tasks
task_extract = PythonOperator(
    task_id='extract_source_data',
    python_callable=extract_source_data,
    dag=dag,
)

task_transform_load = PythonOperator(
    task_id='transform_and_load',
    python_callable=transform_and_load,
    dag=dag,
)

task_validate = PythonOperator(
    task_id='validate_results',
    python_callable=validate_results,
    dag=dag,
)

# Define task dependencies
task_extract >> task_transform_load >> task_validate
