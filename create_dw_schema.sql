-- dim_product
CREATE TABLE dim_product (
  product_key SERIAL PRIMARY KEY,
  product_id INTEGER UNIQUE,
  product_name TEXT,
  product_number TEXT,
  category TEXT,
  subcategory TEXT,
  color TEXT,
  size TEXT,
  standard_cost NUMERIC,
  list_price NUMERIC,
  discontinued BOOLEAN
);

-- dim_customer
CREATE TABLE dim_customer (
  customer_key SERIAL PRIMARY KEY,
  customer_id INTEGER UNIQUE,
  first_name TEXT,
  last_name TEXT,
  email TEXT,
  phone TEXT,
  address TEXT,
  city TEXT,
  state TEXT,
  country TEXT,
  postal_code TEXT,
  customer_type TEXT
);

-- dim_salesperson
CREATE TABLE dim_salesperson (
  salesperson_key SERIAL PRIMARY KEY,
  salesperson_id INTEGER UNIQUE,
  name TEXT,
  territory TEXT,
  hire_date DATE
);

-- dim_territory
CREATE TABLE dim_territory (
  territory_key SERIAL PRIMARY KEY,
  territory_id INTEGER UNIQUE,
  name TEXT,
  country_region_code TEXT
);

-- dim_order
CREATE TABLE dim_order (
  order_key SERIAL PRIMARY KEY,
  order_id INTEGER UNIQUE,
  order_date DATE,
  due_date DATE,
  ship_date DATE,
  status INTEGER,
  online_order_flag BOOLEAN,
  ship_method TEXT
);

-- dim_date
CREATE TABLE dim_date (
    date_key INTEGER PRIMARY KEY,      -- ex: 20251010
    full_date DATE NOT NULL,
    year INTEGER NOT NULL,
    quarter INTEGER NOT NULL,
    month INTEGER NOT NULL,
    month_name TEXT NOT NULL,
    day INTEGER NOT NULL,
    weekday INTEGER NOT NULL,
    is_weekend BOOLEAN NOT NULL
);


-- fact_sales
CREATE TABLE fact_sales (
  fact_sales_id BIGSERIAL PRIMARY KEY,
  date_key INTEGER REFERENCES dim_date(date_key),
  order_key INTEGER REFERENCES dim_order(order_key),
  product_key INTEGER REFERENCES dim_product(product_key),
  customer_key INTEGER REFERENCES dim_customer(customer_key),
  salesperson_key INTEGER REFERENCES dim_salesperson(salesperson_key),
  territory_key INTEGER REFERENCES dim_territory(territory_key),
  order_qty INTEGER,
  unit_price NUMERIC,
  unit_price_discount NUMERIC,
  line_total NUMERIC,
  standard_cost NUMERIC,
  gross_margin NUMERIC
);
