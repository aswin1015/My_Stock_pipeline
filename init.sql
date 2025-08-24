-- Create the stock_prices table if it doesn't exist
-- This is like creating a special drawer in our filing cabinet for stock information


CREATE TABLE IF NOT EXISTS stock_prices (
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

CREATE INDEX IF NOT EXISTS idx_stock_symbol_date ON stock_prices(symbol, date);

INSERT INTO stock_prices (symbol, date, open_price, high_price, low_price, close_price, volume) 
VALUES ('AAPL', '2024-01-01', 100.00, 105.00, 99.00, 104.00, 1000000)
ON CONFLICT (symbol, date) DO NOTHING;