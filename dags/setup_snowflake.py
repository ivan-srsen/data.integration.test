"""
Setup script to create the Snowflake database for the PoC
This DAG should be run once before the main integration DAG
"""

from datetime import datetime
from airflow import DAG
from airflow.operators.python import PythonOperator
import os
import logging

logger = logging.getLogger(__name__)

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 0,
}

dag = DAG(
    'setup_snowflake_database',
    default_args=default_args,
    description='Create Snowflake database for the PoC',
    schedule_interval=None,
    catchup=False,
    tags=['snowflake', 'setup'],
)


def setup_database(**context):
    """
    Create the database and schema if they don't exist
    """
    try:
        import snowflake.connector
    except ImportError:
        logger.error("snowflake-connector-python is not installed")
        raise

    logger.info("Connecting to Snowflake to set up database...")

    # Connect without specifying database first
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

        # Create database if it doesn't exist
        logger.info(f"Creating database {database_name} if it doesn't exist...")
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {database_name}")
        logger.info(f"Database {database_name} is ready")

        # Use the database
        cursor.execute(f"USE DATABASE {database_name}")

        # Create schema if it doesn't exist
        logger.info(f"Creating schema {schema_name} if it doesn't exist...")
        cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {schema_name}")
        logger.info(f"Schema {schema_name} is ready")

        logger.info("Snowflake setup completed successfully!")

        return {
            'database': database_name,
            'schema': schema_name,
            'status': 'success'
        }

    finally:
        cursor.close()
        conn.close()


task_setup = PythonOperator(
    task_id='setup_database',
    python_callable=setup_database,
    dag=dag,
)
