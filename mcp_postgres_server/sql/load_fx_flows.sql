-- Active: 1755605048204@@127.0.0.1@5438
-- Load fx_flows from a CSV exported from Sample_data.xlsx
--
-- Prerequisites:
-- 1) Export the Excel file to CSV (UTF-8) and keep the header row.
-- 2) Edit the column list in the CREATE TABLE and \copy statements below to match the CSV header.
-- 3) Update the CSV file path to your local path.
--
-- Notes:
-- - Using all TEXT columns keeps loading simple; you can ALTER TABLE later to proper types.
-- - \copy is a psql meta-command (client-side). Run this file with psql: psql "<dsn>" -f load_fx_flows.sql
-- - On Windows, forward slashes in paths work: C:/Users/...

BEGIN;

DROP TABLE IF EXISTS fx_flows;

CREATE TABLE fx_flows (
    year INT,
    quarter INT,
    month INT,
    cash_group_code VARCHAR(50),
    bank_code VARCHAR(50),
    expand_platform VARCHAR(50),
    expand_platform_type VARCHAR(50),
    expand_flow_type VARCHAR(50),
    expand_client_type VARCHAR(100),
    expand_product_type1 VARCHAR(100),
    expand_product_type2 VARCHAR(100),
    g10em VARCHAR(20),
    expand_currency1_region FLOAT,
    expand_currency2_region FLOAT,
    expand_currency1 VARCHAR(10),
    expand_currency2 VARCHAR(10),
    expand_client_region VARCHAR(100),
    expand_hour_region FLOAT,
    expand_client_country FLOAT,
    expand_value_date FLOAT,
    disclosed_non_disclosed FLOAT,
    expand_client_sub_type FLOAT,
    sales_credit INT,
    client_count FLOAT,
    volume_bucket FLOAT,
    expand_client_country_region FLOAT,
    expand_order_type FLOAT,
    expand_platform_vendor_name FLOAT,
    expand_tenor_bucket VARCHAR(50),
    expand_trade_type FLOAT,
    trade_count INT,
    block_trade FLOAT,
    expand_trader_location FLOAT,
    expand_booking_type FLOAT,
    expand_sales_location FLOAT,
    sales_credit_methodology FLOAT,
    onshore_offshore FLOAT,
    volume FLOAT
);

-- ✅ One-line \copy command (no line breaks inside parentheses)
\copy fx_flows (year, quarter, month, cash_group_code, bank_code, expand_platform, expand_platform_type, expand_flow_type, expand_client_type, expand_product_type1, expand_product_type2, g10em, expand_currency1_region, expand_currency2_region, expand_currency1, expand_currency2, expand_client_region, expand_hour_region, expand_client_country, expand_value_date, disclosed_non_disclosed, expand_client_sub_type, sales_credit, client_count, volume_bucket, expand_client_country_region, expand_order_type, expand_platform_vendor_name, expand_tenor_bucket, expand_trade_type, trade_count, block_trade, expand_trader_location, expand_booking_type, expand_sales_location, sales_credit_methodology, onshore_offshore, volume) FROM '/tmp/fx_flows.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');

COMMIT;
