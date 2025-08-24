#  Stock Data Pipeline - Dockerized Airflow ETL

A fully automated, Dockerized data pipeline that fetches real-time stock market data using Apache Airflow orchestration and stores it in PostgreSQL.

##  Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Usage](#usage)
- [Monitoring](#monitoring)
- [Project Structure](#project-structure)
- [API Reference](#api-reference)

##  Overview

This pipeline automatically fetches stock market data from Alpha Vantage API and stores it in PostgreSQL database. The entire system runs in Docker containers orchestrated by Apache Airflow, providing:

- **Automated Data Fetching**: Retrieves stock data every 6 hours
- **Error Handling**: Robust retry logic and error management
- **Scalability**: Easy to add more stocks or modify schedule
- **Monitoring**: Web-based Airflow interface for pipeline monitoring
- **Data Persistence**: PostgreSQL database with proper indexing

###  Default Stock Symbols
- **AAPL** (Apple Inc.)
- **GOOGL** (Alphabet Inc.)
- **MSFT** (Microsoft Corporation)

##  Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Alpha Vantage │    │     Airflow     │    │   PostgreSQL    │
│      API        │◄───┤   Orchestrator  ├───►│    Database     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
        │                        │                        │
        │                        │                        │
        ▼                        ▼                        ▼
   Stock Market              Task Scheduling          Data Storage
      Data                   & Management             & Persistence
```

###  Docker Services

1. **PostgreSQL Database** (`stock_database`)
   - Stores stock price data
   - Automatic table creation and indexing
   
2. **Airflow Database** (`airflow-db`)
   - Manages Airflow metadata
   
3. **Airflow Webserver** (`airflow-webserver`)
   - Web interface for monitoring (Port 8080)
   
4. **Airflow Scheduler** (`airflow-scheduler`)
   - Task scheduling and execution

##  Prerequisites

- **Docker** (v20.0 or higher)
- **Docker Compose** (v2.0 or higher)
- **Alpha Vantage API Key** (free at [alphavantage.co](https://www.alphavantage.co/support/#api-key))

###  Get Your API Key

1. Visit: https://www.alphavantage.co/support/#api-key
2. Click "Get your free API key today"
3. Fill in your email and name
4. Copy the provided API key (looks like: `ABCD1234EFGH5678`)

##  Quick Start

### 1. Clone and Setup

```bash
# Clone or create project directory
mkdir my-stock-pipeline
cd my-stock-pipeline

# Create required directories
mkdir -p dags scripts logs
```

### 2. Environment Configuration

Create a `.env` file with your API key:

```bash
# .env file
ALPHA_VANTAGE_API_KEY=your_actual_api_key_here
POSTGRES_DB=stock_data
POSTGRES_USER=stockuser
POSTGRES_PASSWORD=stockpass123
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
```

### 3. Build and Run

```bash
# Build and start all services
docker-compose up --build

# Or run in background
docker-compose up --build -d
```

### 4. Access Airflow Web Interface

1. Wait 2-3 minutes for services to start
2. Open browser: http://localhost:8080
3. Login with:
   - **Username:** `admin`
   - **Password:** `admin`

### 5. Activate the Pipeline

1. Find `stock_data_pipeline` DAG in the list
2. Toggle the switch to **ON** (turns blue/green)
3. Click "Trigger DAG" to run immediately

##  Configuration

###  Schedule Configuration

Modify the schedule in `dags/stock_data_dag.py`:

```python
# Run every 6 hours (default)
schedule_interval=timedelta(hours=6)

# Run daily at 9 AM
schedule_interval='0 9 * * *'

# Run every weekday at market close
schedule_interval='0 16 * * 1-5'
```

###  Stock Symbols Configuration

Add or modify symbols in `dags/stock_data_dag.py`:

```python
# Default symbols
symbols = ['AAPL', 'GOOGL', 'MSFT']

# Add more stocks
symbols = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN', 'META']
```

Or run specific stocks:

```bash
# Fetch only Tesla data
docker exec -it airflow_webserver bash
cd /opt/airflow/scripts
python fetch_stock_data.py TSLA
```

##  Usage

### View Stored Data

```bash
# Connect to database
docker exec -it stock_database psql -U stockuser -d stock_data

# View recent data
SELECT symbol, date, close_price, volume 
FROM stock_prices 
ORDER BY date DESC, symbol 
LIMIT 20;

# Get summary by symbol
SELECT 
    symbol, 
    COUNT(*) as records, 
    MIN(date) as first_date, 
    MAX(date) as latest_date,
    AVG(close_price) as avg_price
FROM stock_prices 
GROUP BY symbol;
```

### Manual Pipeline Execution

```bash
# Run pipeline for default stocks
docker exec -it airflow_webserver python /opt/airflow/scripts/fetch_stock_data.py

# Run for specific stocks
docker exec -it airflow_webserver python /opt/airflow/scripts/fetch_stock_data.py AAPL TSLA NVDA
```


##  Monitoring

### Airflow Web Interface

Access: http://localhost:8080

**Key Features:**
- **DAG Overview**: See all pipelines and their status
- **Task Status**: Monitor individual task progress
- **Logs**: View detailed execution logs
- **Retry History**: Track failed tasks and retries
- **Scheduler Status**: Monitor system health

### Task Status Colors

-  **Green**: Task completed successfully
-  **Yellow**: Task is currently running
-  **Red**: Task failed
-  **Gray**: Task hasn't started yet
-  **Orange**: Task is queued

### Log Monitoring

```bash
# View all logs
docker-compose logs

# View specific service logs
docker-compose logs airflow-webserver
docker-compose logs stock_database

# Follow real-time logs
docker-compose logs -f airflow-scheduler
```



### Restart Services

```bash
# Restart all services
docker-compose down
docker-compose up --build

# Restart specific service
docker-compose restart airflow-webserver
```



##  Project Structure

```
my-stock-pipeline/
├── .env                          # Environment variables
├── docker-compose.yml            # Docker services configuration
├── Dockerfile.airflow           # Custom Airflow image
├── init.sql                     # Database initialization
├── README.md                    # This file
├── dags/
│   └── stock_data_dag.py       # Main pipeline DAG
├── scripts/
│   └── fetch_stock_data.py     # Data fetching script
└── logs/                       # Airflow logs (auto-generated)
```

### File Descriptions

- **`.env`**: Contains API keys and database credentials
- **`docker-compose.yml`**: Defines all Docker services and their configuration
- **`Dockerfile.airflow`**: Custom Airflow image with required Python packages
- **`init.sql`**: Creates database tables and indexes on startup
- **`stock_data_dag.py`**: Airflow DAG defining the pipeline workflow
- **`fetch_stock_data.py`**: Python script that fetches and stores stock data

##  API Reference

### Database Schema

```sql
CREATE TABLE stock_prices (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    date DATE NOT NULL,
    open_price DECIMAL(10,2),
    high_price DECIMAL(10,2),
    low_price DECIMAL(10,2),
    close_price DECIMAL(10,2),
    volume BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, date)
);
```

### Alpha Vantage API

**Endpoint:** `https://www.alphavantage.co/query`

**Parameters:**
- `function`: TIME_SERIES_DAILY
- `symbol`: Stock symbol (e.g., AAPL)
- `apikey`: Your API key
- `datatype`: json


### Enhancements You Can Add

1. **More Data Sources**: Yahoo Finance, IEX Cloud, Quandl
2. **Data Analysis**: Add pandas-based analysis tasks
3. **Alerting**: Email/Slack notifications for failures
4. **Data Visualization**: Grafana dashboard
5. **Data Quality**: Add validation checks
6. **Backup**: Automated database backups
7. **Scaling**: Multiple worker nodes
8. **Real-time**: WebSocket connections for live data



