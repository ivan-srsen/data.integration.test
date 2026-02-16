"""
Snowflake Integration PoC DAG

This DAG demonstrates a simple integration between Apache Airflow and Snowflake.
It performs the following operations:
1. Creates a sample table in Snowflake
2. Inserts sample data
3. Queries and displays the data
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
import os
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Default arguments for the DAG
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# DAG definition
dag = DAG(
    'snowflake_integration_poc',
    default_args=default_args,
    description='A simple PoC DAG for Airflow-Snowflake integration',
    schedule_interval=None,  # Manual trigger only
    catchup=False,
    tags=['snowflake', 'poc'],
)


def get_snowflake_connection():
    """
    Create and return a Snowflake connection using environment variables.
    """
    try:
        import snowflake.connector
    except ImportError:
        logger.error("snowflake-connector-python is not installed. Please add it to requirements.txt")
        raise

    conn = snowflake.connector.connect(
        account=os.getenv('SNOWFLAKE_ACCOUNT'),
        user=os.getenv('SNOWFLAKE_USER'),
        password=os.getenv('SNOWFLAKE_PASSWORD'),
        role=os.getenv('SNOWFLAKE_ROLE', 'ACCOUNTADMIN'),
        warehouse=os.getenv('SNOWFLAKE_WAREHOUSE'),
        database=os.getenv('SNOWFLAKE_DATABASE'),
        schema=os.getenv('SNOWFLAKE_SCHEMA', 'PUBLIC'),
    )
    return conn


def setup_database(**context):
    """
    Create database and schema if they don't exist.
    """
    logger.info("Setting up Snowflake database and schema...")

    # Connect without specifying database
    import snowflake.connector
    conn = snowflake.connector.connect(
        account=os.getenv('SNOWFLAKE_ACCOUNT'),
        user=os.getenv('SNOWFLAKE_USER'),
        password=os.getenv('SNOWFLAKE_PASSWORD'),
        role=os.getenv('SNOWFLAKE_ROLE', 'ACCOUNTADMIN'),
        warehouse=os.getenv('SNOWFLAKE_WAREHOUSE'),
    )
    cursor = conn.cursor()

    try:
        database_name = os.getenv('SNOWFLAKE_DATABASE')
        schema_name = os.getenv('SNOWFLAKE_SCHEMA', 'PUBLIC')

        # Create database if not exists
        logger.info(f"Creating database {database_name}...")
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {database_name}")

        # Use database
        cursor.execute(f"USE DATABASE {database_name}")

        # Create schema if not exists
        logger.info(f"Creating schema {schema_name}...")
        cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {schema_name}")

        logger.info(f"Database {database_name} and schema {schema_name} are ready")

    finally:
        cursor.close()
        conn.close()


def create_table(**context):
    """
    Create a sample table in Snowflake.
    """
    logger.info("Creating sample table in Snowflake...")

    conn = get_snowflake_connection()
    cursor = conn.cursor()

    try:
        # Drop table if exists
        cursor.execute("DROP TABLE IF EXISTS airflow_poc_table")
        logger.info("Dropped existing table if any")

        # Create new table
        create_table_sql = """
        CREATE TABLE airflow_poc_table (
            id INTEGER,
            name VARCHAR(100),
            created_at TIMESTAMP_NTZ,
            value FLOAT
        )
        """
        cursor.execute(create_table_sql)
        logger.info("Table 'airflow_poc_table' created successfully")

    finally:
        cursor.close()
        conn.close()


def insert_data(**context):
    """
    Insert sample data into the Snowflake table.
    """
    logger.info("Inserting sample data into Snowflake...")

    conn = get_snowflake_connection()
    cursor = conn.cursor()

    try:
        insert_sql = """
        INSERT INTO airflow_poc_table (id, name, created_at, value)
        VALUES
            (1, 'Record One', CURRENT_TIMESTAMP(), 100.5),
            (2, 'Record Two', CURRENT_TIMESTAMP(), 200.75),
            (3, 'Record Three', CURRENT_TIMESTAMP(), 300.25),
            (4, 'Record Four', CURRENT_TIMESTAMP(), 400.00),
            (5, 'Record Five', CURRENT_TIMESTAMP(), 500.50)
        """
        cursor.execute(insert_sql)
        logger.info(f"Inserted {cursor.rowcount} rows successfully")

    finally:
        cursor.close()
        conn.close()


def query_data(**context):
    """
    Query data from the Snowflake table and push to XCom.
    """
    logger.info("Querying data from Snowflake...")

    conn = get_snowflake_connection()
    cursor = conn.cursor()

    try:
        query_sql = """
        SELECT id, name, created_at, value
        FROM airflow_poc_table
        ORDER BY id
        """
        cursor.execute(query_sql)

        results = cursor.fetchall()
        logger.info(f"Retrieved {len(results)} rows")

        # Log the results
        for row in results:
            logger.info(f"Row: {row}")

        # Push results to XCom for downstream tasks
        context['ti'].xcom_push(key='query_results', value=len(results))

        return f"Successfully queried {len(results)} rows"

    finally:
        cursor.close()
        conn.close()


def calculate_statistics(**context):
    """
    Calculate statistics from the Snowflake table.
    """
    logger.info("Calculating statistics from Snowflake...")

    conn = get_snowflake_connection()
    cursor = conn.cursor()

    try:
        stats_sql = """
        SELECT
            COUNT(*) as total_records,
            AVG(value) as avg_value,
            MIN(value) as min_value,
            MAX(value) as max_value,
            SUM(value) as sum_value
        FROM airflow_poc_table
        """
        cursor.execute(stats_sql)

        result = cursor.fetchone()
        stats = {
            'total_records': result[0],
            'avg_value': float(result[1]),
            'min_value': float(result[2]),
            'max_value': float(result[3]),
            'sum_value': float(result[4])
        }

        logger.info(f"Statistics: {stats}")

        return stats

    finally:
        cursor.close()
        conn.close()


# Define tasks
task_setup_database = PythonOperator(
    task_id='setup_database',
    python_callable=setup_database,
    dag=dag,
)

task_create_table = PythonOperator(
    task_id='create_snowflake_table',
    python_callable=create_table,
    dag=dag,
)

task_insert_data = PythonOperator(
    task_id='insert_sample_data',
    python_callable=insert_data,
    dag=dag,
)

task_query_data = PythonOperator(
    task_id='query_data',
    python_callable=query_data,
    dag=dag,
)

task_calculate_stats = PythonOperator(
    task_id='calculate_statistics',
    python_callable=calculate_statistics,
    dag=dag,
)

# Define task dependencies
task_setup_database >> task_create_table >> task_insert_data >> [task_query_data, task_calculate_stats]
