CREATE TABLE date_key (
    date_key_id SERIAL PRIMARY KEY,   -- chave primária da tabela
    full_date DATE NOT NULL,          -- data completa
    year INTEGER NOT NULL,
    quarter INTEGER NOT NULL,
    month INTEGER NOT NULL,
    month_name TEXT NOT NULL,
    day INTEGER NOT NULL,
    weekday INTEGER NOT NULL,
    is_weekend BOOLEAN NOT NULL
);
