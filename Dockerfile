FROM apache/airflow:2.8.1-python3.11

# Switch to root to copy file and fix permissions
USER root

# Copy requirements file and fix permissions
COPY requirements.txt /tmp/requirements.txt
RUN chown airflow:root /tmp/requirements.txt

# Switch to airflow user
USER airflow

# Install additional requirements
RUN pip install --no-cache-dir --user -r /tmp/requirements.txt
