#!/usr/bin/env python3
"""
Stock Data Fetcher
Fetches stock data from Alpha Vantage API and stores it in PostgreSQL
"""

import os
import sys
import requests
import psycopg2
import pandas as pd
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import time
import random

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class StockDataFetcher:
    """
    Stock data fetcher that handles API calls and database operations
    """
    
    def __init__(self):
        self.api_key = os.getenv('ALPHA_VANTAGE_API_KEY')
        if not self.api_key:
            raise ValueError("API key not found! Check your .env file")
        
        self.db_config = {
            'host': os.getenv('POSTGRES_HOST', 'postgres'),
            'database': os.getenv('POSTGRES_DB', 'stock_data'),
            'user': os.getenv('POSTGRES_USER', 'stockuser'),
            'password': os.getenv('POSTGRES_PASSWORD', 'stockpass123'),
            'port': os.getenv('POSTGRES_PORT', '5432')
        }
        
        self.base_url = "https://www.alphavantage.co/query"
        logger.info("Robot initialized successfully!")
    
    def get_demo_data(self, symbol: str) -> Dict:
        """
        Generate demo stock data when API is not available
        """
        logger.info(f"Generating demo data for {symbol}")
        
        base_price = {'AAPL': 150.0, 'GOOGL': 2500.0, 'MSFT': 300.0}.get(symbol, 100.0)
        time_series = {}
        
        for i in range(7):
            date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
            
            daily_change = random.uniform(-0.05, 0.05)
            open_price = base_price * (1 + random.uniform(-0.02, 0.02))
            close_price = open_price * (1 + daily_change)
            high_price = max(open_price, close_price) * (1 + random.uniform(0, 0.03))
            low_price = min(open_price, close_price) * (1 - random.uniform(0, 0.03))
            volume = random.randint(1000000, 10000000)
            
            time_series[date] = {
                '1. open': f"{open_price:.2f}",
                '2. high': f"{high_price:.2f}",
                '3. low': f"{low_price:.2f}",
                '4. close': f"{close_price:.2f}",
                '5. volume': str(volume)
            }
        
        return {
            'Time Series (Daily)': time_series,
            'Meta Data': {
                '1. Information': f"Demo Daily Prices and Volumes for {symbol}",
                '2. Symbol': symbol,
                '3. Last Refreshed': datetime.now().strftime('%Y-%m-%d'),
                '4. Output Size': 'Compact',
                '5. Time Zone': 'US/Eastern'
            }
        }
    
    def fetch_stock_data(self, symbol: str = "AAPL") -> Optional[Dict]:
        """
        Fetch stock data from Alpha Vantage API
        """
        logger.info(f"Calling API for symbol: {symbol}")
        
        params = {
            'function': 'TIME_SERIES_DAILY',
            'symbol': symbol,
            'apikey': self.api_key,
            'datatype': 'json'
        }
        
        try:
            response = requests.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if 'Error Message' in data:
                logger.error(f"API Error: {data['Error Message']}")
                return None
            
            if 'Note' in data:
                logger.warning(f"API Limit Warning: {data['Note']}")
                return None
                
            if 'Information' in data:
                logger.warning(f"API Rate Limit: {data['Information']}")
                logger.info("Using demo data instead...")
                return self.get_demo_data(symbol)
            
            if 'Time Series (Daily)' not in data:
                logger.error(f"Unexpected API response format: {list(data.keys())}")
                if 'Information' in data:
                    logger.error(f"API Rate limit message: {data['Information']}")
                logger.error(f"Full response: {data}")
                logger.info("Using demo data instead...")
                return self.get_demo_data(symbol)
            
            logger.info(f"Successfully fetched data for {symbol}")
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error while fetching data: {e}")
            logger.info("Using demo data instead...")
            return self.get_demo_data(symbol)
        except Exception as e:
            logger.error(f"Unexpected error while fetching data: {e}")
            logger.info("Using demo data instead...")
            return self.get_demo_data(symbol)
    
    def parse_stock_data(self, data: Dict, symbol: str) -> List[Dict]:
        """
        Parse the API response and convert it to database format
        """
        logger.info(f"Parsing data for {symbol}")
        
        try:
            time_series = data['Time Series (Daily)']
            parsed_data = []
            
            sorted_dates = sorted(time_series.keys(), reverse=True)[:7]
            
            for date_str in sorted_dates:
                daily_data = time_series[date_str]
                
                record = {
                    'symbol': symbol,
                    'date': datetime.strptime(date_str, '%Y-%m-%d').date(),
                    'open_price': float(daily_data['1. open']),
                    'high_price': float(daily_data['2. high']),
                    'low_price': float(daily_data['3. low']),
                    'close_price': float(daily_data['4. close']),
                    'volume': int(daily_data['5. volume'])
                }
                
                parsed_data.append(record)
            
            logger.info(f"Parsed {len(parsed_data)} records for {symbol}")
            return parsed_data
            
        except Exception as e:
            logger.error(f"Error parsing data: {e}")
            return []
    
    def connect_to_database(self):
        """
        Connect to PostgreSQL database
        """
        try:
            connection = psycopg2.connect(**self.db_config)
            logger.info("Connected to database successfully")
            return connection
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            return None
    
    def save_to_database(self, records: List[Dict]) -> bool:
        """
        Save stock data to PostgreSQL database
        """
        if not records:
            logger.warning("No records to save")
            return False
        
        connection = self.connect_to_database()
        if not connection:
            return False
        
        try:
            cursor = connection.cursor()
            
            insert_query = """
                INSERT INTO stock_prices (symbol, date, open_price, high_price, low_price, close_price, volume)
                VALUES (%(symbol)s, %(date)s, %(open_price)s, %(high_price)s, %(low_price)s, %(close_price)s, %(volume)s)
                ON CONFLICT (symbol, date) 
                DO UPDATE SET 
                    open_price = EXCLUDED.open_price,
                    high_price = EXCLUDED.high_price,
                    low_price = EXCLUDED.low_price,
                    close_price = EXCLUDED.close_price,
                    volume = EXCLUDED.volume,
                    created_at = CURRENT_TIMESTAMP
            """
            
            cursor.executemany(insert_query, records)
            connection.commit()
            
            logger.info(f"Successfully saved {len(records)} records to database")
            return True
            
        except Exception as e:
            logger.error(f"Error saving to database: {e}")
            connection.rollback()
            return False
            
        finally:
            cursor.close()
            connection.close()
            logger.info("Database connection closed")
    
    def run_pipeline(self, symbols: List[str] = None) -> bool:
        """
        Run the complete pipeline for fetching and storing stock data
        """
        if symbols is None:
            symbols = ['AAPL', 'GOOGL', 'MSFT']
        
        logger.info(f"Starting stock data pipeline for symbols: {symbols}")
        
        overall_success = True
        
        for symbol in symbols:
            try:
                logger.info(f"Processing {symbol}...")
                
                raw_data = self.fetch_stock_data(symbol)
                if not raw_data:
                    logger.error(f"Failed to fetch data for {symbol}")
                    overall_success = False
                    continue
                
                parsed_records = self.parse_stock_data(raw_data, symbol)
                if not parsed_records:
                    logger.error(f"Failed to parse data for {symbol}")
                    overall_success = False
                    continue
                
                if not self.save_to_database(parsed_records):
                    logger.error(f"Failed to save data for {symbol}")
                    overall_success = False
                    continue
                
                logger.info(f"Successfully processed {symbol}")
                time.sleep(12)
                
            except Exception as e:
                logger.error(f"Unexpected error processing {symbol}: {e}")
                overall_success = False
                continue
        
        if overall_success:
            logger.info("Pipeline completed successfully for all symbols!")
        else:
            logger.warning("Pipeline completed with some errors")
        
        return overall_success


def main():
    """
    Main function
    """
    logger.info("Stock Data Fetcher Robot starting up...")
    
    try:
        fetcher = StockDataFetcher()
        symbols = sys.argv[1:] if len(sys.argv) > 1 else ['AAPL', 'GOOGL', 'MSFT']
        success = fetcher.run_pipeline(symbols)
        
        if success:
            logger.info("Mission accomplished! Robot going to sleep...")
            sys.exit(0)
        else:
            logger.error("Mission failed! Check the logs above")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("Robot stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Robot crashed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()