# Airflow + Snowflake Integration PoC

A proof-of-concept project demonstrating the integration between Apache Airflow and Snowflake using Docker containers.

## Project Structure

```
.
├── dags/                           # Airflow DAGs directory
│   └── snowflake_integration_dag.py
├── logs/                           # Airflow logs
├── plugins/                        # Airflow plugins
├── config/                         # Airflow configuration
├── docker-compose.yml              # Docker Compose configuration
├── Dockerfile                      # Custom Airflow image with Snowflake connector
├── requirements.txt                # Python dependencies
├── .env.example                    # Environment variables template
└── README.md                       # This file
```

## Prerequisites

- Docker and Docker Compose installed on your machine
- A Snowflake trial account (sign up at https://signup.snowflake.com/)

## Getting Started

### 1. Set Up Snowflake Trial Account

1. Sign up for a free Snowflake trial at https://signup.snowflake.com/
2. After signing up, note down the following details:
   - Account identifier (from the URL: `https://<account>.snowflakecomputing.com`)
   - Username
   - Password
   - Warehouse name (default: `COMPUTE_WH`)
   - Database name (you may need to create one in Snowflake UI)

### 2. Configure Environment Variables

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit the `.env` file and fill in your Snowflake credentials:
   ```bash
   SNOWFLAKE_ACCOUNT=your-account-identifier
   SNOWFLAKE_USER=your-username
   SNOWFLAKE_PASSWORD=your-password
   SNOWFLAKE_ROLE=ACCOUNTADMIN
   SNOWFLAKE_WAREHOUSE=COMPUTE_WH
   SNOWFLAKE_DATABASE=your-database
   SNOWFLAKE_SCHEMA=PUBLIC
   ```

### 3. Build and Start Airflow

1. Build the custom Airflow image with Snowflake connector:
   ```bash
   docker-compose build
   ```

2. Initialize Airflow and start all services:
   ```bash
   docker-compose up
   ```

   This will:
   - Start PostgreSQL database for Airflow metadata
   - Initialize Airflow database
   - Create an admin user (username: `admin`, password: `admin`)
   - Start Airflow webserver and scheduler

3. Wait for all services to be healthy. You should see logs indicating the webserver is running.

### 4. Access Airflow UI

1. Open your browser and navigate to: http://localhost:8080
2. Login with:
   - Username: `admin`
   - Password: `admin`

### 5. Run the PoC DAG

1. In the Airflow UI, you should see a DAG named `snowflake_integration_poc`
2. Toggle the DAG to "On" (if it's paused)
3. Click the "Play" button to trigger the DAG manually
4. Monitor the execution in the UI

## What Does the PoC DAG Do?

The `snowflake_integration_poc` DAG demonstrates a complete workflow:

1. **Create Table**: Creates a sample table called `airflow_poc_table` in Snowflake
2. **Insert Data**: Inserts 5 sample records into the table
3. **Query Data**: Retrieves and logs all records from the table
4. **Calculate Statistics**: Computes aggregate statistics (count, avg, min, max, sum) on the data

The DAG runs on manual trigger (not scheduled) and includes proper error handling and logging.

## Troubleshooting

### Permission Issues

If you encounter permission errors with the logs or dags directories:

```bash
# On Linux/Mac
export AIRFLOW_UID=$(id -u)
docker-compose down
docker-compose up
```

### Snowflake Connection Issues

1. Verify your Snowflake credentials in the `.env` file
2. Ensure your Snowflake account is active (trial accounts are active for 30 days)
3. Check that the database and warehouse exist in Snowflake
4. Review the task logs in Airflow UI for detailed error messages

### DAG Not Appearing

1. Check the scheduler logs: `docker-compose logs airflow-scheduler`
2. Verify the DAG file syntax: The scheduler will skip DAGs with syntax errors
3. Refresh the Airflow UI

## Viewing Logs

To view logs for specific services:

```bash
# Airflow webserver logs
docker-compose logs -f airflow-webserver

# Airflow scheduler logs
docker-compose logs -f airflow-scheduler

# All logs
docker-compose logs -f
```

## Stopping the Environment

To stop all services:

```bash
docker-compose down
```

To stop and remove all volumes (including database data):

```bash
docker-compose down -v
```

## Customizing the DAG

The sample DAG is located at `dags/snowflake_integration_dag.py`. You can:

- Modify the table structure
- Change the sample data
- Add more tasks
- Implement your own business logic

Any changes to the DAG file will be automatically picked up by Airflow (may take up to 30 seconds).

## Next Steps

- Explore more complex Snowflake operations (JOINs, CTEs, window functions)
- Implement error handling and retry logic
- Add data quality checks
- Integrate with other data sources
- Set up scheduled DAG runs
- Implement alerting and monitoring

## Resources

- [Apache Airflow Documentation](https://airflow.apache.org/docs/)
- [Snowflake Documentation](https://docs.snowflake.com/)
- [Snowflake Connector for Python](https://docs.snowflake.com/en/user-guide/python-connector.html)
- [Airflow Snowflake Provider](https://airflow.apache.org/docs/apache-airflow-providers-snowflake/)

## License

This is a proof-of-concept project for demonstration purposes.
