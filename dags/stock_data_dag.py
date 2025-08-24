#!/usr/bin/env python3
"""
Stock Data Pipeline DAG
Airflow DAG for fetching and storing stock market data
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from airflow.operators.empty import EmptyOperator
import logging

logger = logging.getLogger(__name__)

default_args = {
    'owner': 'stock-data-team',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'catchup': False,
}

dag = DAG(
    'stock_data_pipeline',
    default_args=default_args,
    description='Fetch and store stock market data daily',
    schedule_interval=timedelta(hours=6),
    max_active_runs=1,
    tags=['stocks', 'finance', 'etl'],
)

def check_api_connection():
    """
    Check if we can connect to the Alpha Vantage API
    """
    import os
    import requests
    
    api_key = os.getenv('ALPHA_VANTAGE_API_KEY')
    if not api_key:
        raise ValueError("API key not found in environment variables!")
    
    test_url = f"https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol=AAPL&interval=1min&apikey={api_key}"
    
    try:
        response = requests.get(test_url, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        if 'Error Message' in data:
            raise Exception(f"API Error: {data['Error Message']}")
        
        logger.info("API connection test successful!")
        return True
        
    except Exception as e:
        logger.error(f"API connection test failed: {e}")
        raise

def check_database_connection():
    """
    Check if we can connect to PostgreSQL database
    """
    import os
    import psycopg2
    
    db_config = {
        'host': os.getenv('POSTGRES_HOST', 'postgres'),
        'database': os.getenv('POSTGRES_DB', 'stock_data'),
        'user': os.getenv('POSTGRES_USER', 'stockuser'),
        'password': os.getenv('POSTGRES_PASSWORD', 'stockpass123'),
        'port': os.getenv('POSTGRES_PORT', '5432')
    }
    
    try:
        connection = psycopg2.connect(**db_config)
        cursor = connection.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM stock_prices;")
        count = cursor.fetchone()[0]
        
        cursor.close()
        connection.close()
        
        logger.info(f"Database connection test successful! Found {count} records in stock_prices table.")
        return True
        
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        raise

start_task = EmptyOperator(
    task_id='start_pipeline',
    dag=dag,
)

check_api_task = PythonOperator(
    task_id='check_api_connection',
    python_callable=check_api_connection,
    dag=dag,
)

check_db_task = PythonOperator(
    task_id='check_database_connection',
    python_callable=check_database_connection,
    dag=dag,
)

fetch_aapl_task = BashOperator(
    task_id='fetch_aapl_data',
    bash_command='cd /opt/airflow/scripts && python fetch_stock_data.py AAPL',
    dag=dag,
)

fetch_googl_task = BashOperator(
    task_id='fetch_googl_data',
    bash_command='cd /opt/airflow/scripts && python fetch_stock_data.py GOOGL',
    dag=dag,
)

fetch_msft_task = BashOperator(
    task_id='fetch_msft_data',
    bash_command='cd /opt/airflow/scripts && python fetch_stock_data.py MSFT',
    dag=dag,
)

verify_data_task = BashOperator(
    task_id='verify_data_saved',
    bash_command='''
    cd /opt/airflow/scripts && python -c "
import psycopg2
import os

db_config = {
    'host': os.getenv('POSTGRES_HOST', 'postgres'),
    'database': os.getenv('POSTGRES_DB', 'stock_data'),
    'user': os.getenv('POSTGRES_USER', 'stockuser'),
    'password': os.getenv('POSTGRES_PASSWORD', 'stockpass123'),
    'port': os.getenv('POSTGRES_PORT', '5432')
}

connection = psycopg2.connect(**db_config)
cursor = connection.cursor()

cursor.execute('SELECT symbol, COUNT(*) as record_count, MAX(date) as latest_date FROM stock_prices WHERE date >= CURRENT_DATE - INTERVAL \\'7 days\\' GROUP BY symbol ORDER BY symbol;')

results = cursor.fetchall()
print('Recent stock data summary:')
for symbol, count, latest_date in results:
    print(f'  {symbol}: {count} records, latest: {latest_date}')

cursor.close()
connection.close()
print('Data verification complete!')
"
    ''',
    dag=dag,
)

end_task = EmptyOperator(
    task_id='pipeline_complete',
    dag=dag,
)

# Define task dependencies
start_task >> check_api_task
start_task >> check_db_task

check_api_task >> fetch_aapl_task
check_api_task >> fetch_googl_task
check_api_task >> fetch_msft_task

check_db_task >> fetch_aapl_task
check_db_task >> fetch_googl_task
check_db_task >> fetch_msft_task

fetch_aapl_task >> verify_data_task
fetch_googl_task >> verify_data_task
fetch_msft_task >> verify_data_task

verify_data_task >> end_task