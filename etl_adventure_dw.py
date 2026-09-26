# etl_adventure_dw.py
import pandas as pd
from sqlalchemy import create_engine, text
import datetime

# === CONFIG ===
SRC_CONN = "postgresql+psycopg2://root:1234@localhost:5432/data"  # ou SQL Server ODBC
DST_CONN = "postgresql+psycopg2://root:1234@localhost:5432/date"

src_engine = create_engine(SRC_CONN)
dst_engine = create_engine(DST_CONN)

def load_dim_date(conn, dates):
    df = pd.DataFrame({'date': pd.to_datetime(dates).dt.date}).drop_duplicates()
    df['date_key'] = df['date'].apply(lambda d: int(d.strftime('%Y%m%d')))
    df['year'] = df['date'].apply(lambda d: d.year)
    df['month'] = df['date'].apply(lambda d: d.month)
    df['day'] = df['date'].apply(lambda d: d.day)
    df['quarter'] = df['date'].apply(lambda d: (d.month-1)//3 + 1)
    df['weekday'] = df['date'].apply(lambda d: d.isoweekday())
    df['month_name'] = df['date'].apply(lambda d: d.strftime('%B'))
    df['is_weekend'] = df['weekday'].isin([6,7])
    # Upsert into dim_date
    with dst_engine.begin() as conn:
        for _, row in df.iterrows():
            conn.execute(text("""
                INSERT INTO dim_date (date_key,date,year,quarter,month,month_name,day,weekday,is_weekend)
                VALUES (:date_key,:date,:year,:quarter,:month,:month_name,:day,:weekday,:is_weekend)
                ON CONFLICT (date_key) DO NOTHING
            """), **row.to_dict())

def upsert_dim(table, unique_key, df):
    # df columns must match table columns (except PK)
    with dst_engine.begin() as conn:
        for _, row in df.iterrows():
            cols = row.index.tolist()
            vals = {c: row[c] for c in cols}
            insert_cols = ','.join(cols)
            insert_vals = ','.join(':'+c for c in cols)
            updates = ','.join(f"{c}=EXCLUDED.{c}" for c in cols if c != unique_key)
            sql = f"""
            INSERT INTO {table} ({insert_cols})
            VALUES ({insert_vals})
            ON CONFLICT ({unique_key}) DO UPDATE SET {updates}
            """
            conn.execute(text(sql), **vals)

def build_and_load_dims():
    # 1) DIM PRODUCT
    q_prod = """
      SELECT p.productid, p.name, p.productnumber, pc.name AS category, p.color, p.size, p.standardcost, p.listprice, p.discontinued
      FROM production_product p
      LEFT JOIN production_productsubcategory ps ON p.productsubcategoryid = ps.productsubcategoryid
      LEFT JOIN production_productcategory pc ON ps.productcategoryid = pc.productcategoryid
    """
    df_prod = pd.read_sql(q_prod, src_engine)
    df_prod = df_prod.rename(columns={
        'productid':'product_id','name':'product_name','productnumber':'product_number',
        'standardcost':'standard_cost','listprice':'list_price','discontinued':'discontinued'
    })
    upsert_dim('dim_product','product_id', df_prod)

    # 2) DIM CUSTOMER (from Sales.Customer + Person.Person)
    q_cust = """
      SELECT c.customerid, p.firstname, p.lastname, p.emailaddress as email
      FROM sales_customer c
      LEFT JOIN person_person p ON c.personid = p.businessentityid
    """
    df_cust = pd.read_sql(q_cust, src_engine)
    df_cust = df_cust.rename(columns={'customerid':'customer_id','firstname':'first_name','lastname':'last_name'})
    upsert_dim('dim_customer','customer_id', df_cust)

    # 3) DIM_TERRITORY
    df_ter = pd.read_sql("SELECT territoryid, name, countryregioncode FROM sales_salesterritory", src_engine)
    df_ter = df_ter.rename(columns={'territoryid':'territory_id','countryregioncode':'country_region_code'})
    upsert_dim('dim_territory','territory_id', df_ter)

    # 4) DIM_SALESPERSON
    df_sp = pd.read_sql("SELECT SalesPersonID as salespersonid, FirstName || ' ' || LastName as name FROM humanresources_employee e LEFT JOIN person_person p ON e.BusinessEntityID=p.BusinessEntityID", src_engine)
    df_sp = df_sp.rename(columns={'salespersonid':'salesperson_id'})
    upsert_dim('dim_salesperson','salesperson_id', df_sp)

def load_fact_sales():
    # read order headers + details
    q = """
        SELECT h.salesorderid, h.orderdate, h.duedate, h.shipdate, h.status,
               d.salesorderdetailid, d.productid, d.orderqty, d.unitprice, d.unitpricediscount,
               p.standardcost, (d.unitprice * d.orderqty * (1 - d.unitpricediscount)) AS line_total,
               h.salespersonid, h.territoryid, h.customerid
        FROM sales_salesorderheader h
        JOIN sales_salesorderdetail d ON h.salesorderid = d.salesorderid
        LEFT JOIN production_product p ON d.productid = p.productid
        WHERE h.orderdate >= '2003-01-01'  -- adaptar conforme necessidade
    """
    df = pd.read_sql(q, src_engine)
    # compute date_key
    df['date_key'] = pd.to_datetime(df['orderdate']).dt.date.apply(lambda d: int(d.strftime('%Y%m%d')))
    # load dim_date
    load_dim_date(df['orderdate'].unique())
    # resolve product_key, customer_key, etc by joining dims in DW
    # we'll map using product_id, customer_id etc.
    # get mapping tables
    prod_map = pd.read_sql("SELECT product_key, product_id FROM dim_product", dst_engine)
    cust_map = pd.read_sql("SELECT customer_key, customer_id FROM dim_customer", dst_engine)
    sp_map = pd.read_sql("SELECT salesperson_key, salesperson_id FROM dim_salesperson", dst_engine)
    ter_map = pd.read_sql("SELECT territory_key, territory_id FROM dim_territory", dst_engine)
    order_map = pd.read_sql("SELECT order_key, order_id FROM dim_order", dst_engine)

    df = df.merge(prod_map, how='left', left_on='productid', right_on='product_id')
    df = df.merge(cust_map, how='left', left_on='customerid', right_on='customer_id')
    df = df.merge(sp_map, how='left', left_on='salespersonid', right_on='salesperson_id')
    df = df.merge(ter_map, how='left', left_on='territoryid', right_on='territory_id')

    # Insert dim_order rows for orders not present
    orders = df[['salesorderid','orderdate','duedate','shipdate','status']].drop_duplicates()
    orders = orders.rename(columns={'salesorderid':'order_id','orderdate':'order_date','duedate':'due_date','shipdate':'ship_date'})
    upsert_dim('dim_order','order_id', orders)

    # refresh order_map (now contains new keys)
    order_map = pd.read_sql("SELECT order_key, order_id FROM dim_order", dst_engine)
    df = df.merge(order_map, how='left', left_on='salesorderid', right_on='order_id')

    # finalize fact columns
    df_fact = df[['date_key','order_key','product_key','customer_key','salesperson_key','territory_key','orderqty','unitprice','unitpricediscount','line_total','standardcost']].copy()
    df_fact = df_fact.rename(columns={
        'orderqty':'order_qty',
        'unitpricediscount':'unit_price_discount',
        'standardcost':'standard_cost'
    })
    df_fact['gross_margin'] = df_fact['line_total'] - (df_fact['standard_cost'] * df_fact['order_qty'])

    # insert facts (simple insert: can avoid duplicates by checking salesorderdetail unique id in production)
    # Here we do a basic insert; production: use a staging with unique key on salesorderdetailid.
    with dst_engine.begin() as conn:
        for _, row in df_fact.iterrows():
            conn.execute(text("""
            INSERT INTO fact_sales (date_key,order_key,product_key,customer_key,salesperson_key,territory_key,order_qty,unit_price,unit_price_discount,line_total,standard_cost,gross_margin)
            VALUES (:date_key,:order_key,:product_key,:customer_key,:salesperson_key,:territory_key,:order_qty,:unit_price,:unit_price_discount,:line_total,:standard_cost,:gross_margin)
            """), **row.to_dict())

def main():
    build_and_load_dims()
    load_fact_sales()
    print("ETL finalizado")

if __name__ == "__main__":
    main()
