# etl_adventureworks_to_dw.py
"""
ETL: AdventureWorks (fonte OLTP) -> DW (PostgreSQL)
Dependências: pandas, sqlalchemy, psycopg2-binary, tqdm
pip install pandas sqlalchemy psycopg2-binary tqdm
"""

import pandas as pd
from sqlalchemy import create_engine, text
from tqdm import tqdm

# -------------- CONFIGURAÇÃO --------------
# Fonte (exemplo: outro Postgres contendo AdventureWorks). Ajuste conforme seu ambiente.
SRC_CONN = "postgresql+psycopg2://postgres:1234@localhost:5432/adventureworks"

# Destino DW
DST_CONN = "postgresql+psycopg2://postgres:1234@localhost:5432/adventure_dw"

# Batch size para inserts
BATCH = 5000

# -------------- FUNÇÕES --------------
def get_source_df(query, src_engine):
    return pd.read_sql(query, src_engine)

def upsert_dim(engine_dst, df, table_name, key_col):
    # Simples estratégia: deletar chaves existentes e inserir (idempotente)
    conn = engine_dst.connect()
    ids = df[key_col].tolist()
    if len(ids) == 0:
        return
    try:
        # Delete existing keys
        conn.execute(text(f"DELETE FROM dw.{table_name} WHERE {key_col} = ANY(:ids)"), {"ids": ids})
        # Insert via pandas to_sql (append)
        df.to_sql(table_name, engine_dst, schema='dw', if_exists='append', index=False, method='multi', chunksize=BATCH)
    finally:
        conn.close()

def load_fact(engine_dst, df, table_name='fact_sales'):
    # append
    df.to_sql(table_name, engine_dst, schema='dw', if_exists='append', index=False, method='multi', chunksize=BATCH)

# -------------- ETL --------------
def etl():
    src_engine = create_engine(SRC_CONN)
    dst_engine = create_engine(DST_CONN)

    # 1) Extrair: Products
    print("Extraindo produtos...")
    q_prod = """
    SELECT p.productid AS product_id, p.name AS product_name, p.productnumber, p.color, p.standardcost, p.listprice,
           pc.name AS category, psc.name AS subcategory
    FROM production_product p
    LEFT JOIN production_productsubcategory psc ON p.productsubcategoryid = psc.productsubcategoryid
    LEFT JOIN production_productcategory pc ON psc.productcategoryid = pc.productcategoryid
    """
    df_prod = get_source_df(q_prod, src_engine).drop_duplicates(subset=['product_id'])
    print(f"Produtos extraídos: {len(df_prod)}")

    # 2) Extrair: Customers + Person/Store join (varia conforme modelo AdventureWorks)
    print("Extraindo clientes...")
    q_cust = """
    SELECT c.customerid AS customer_id,
           COALESCE(p.firstname || ' ' || p.lastname, s.name) AS customer_name,
           c.accountnumber, a.city, a.stateprovince, a.countryregioncode AS country, a.postalcode
    FROM sales_customer c
    LEFT JOIN person_person p ON c.personid = p.businessentityid
    LEFT JOIN sales_store s ON c.storeid = s.businessentityid
    LEFT JOIN person_address pa ON pa.businessentityid = COALESCE(c.personid, c.storeid)
    LEFT JOIN person_stateprovince sp ON sp.stateprovinceid = pa.stateprovinceid
    LEFT JOIN person_countryregion cr ON cr.countryregioncode = sp.countryregioncode
    LEFT JOIN sales_customeraddress ca ON ca.customerid = c.customerid
    LEFT JOIN address a ON a.addressid = ca.addressid
    """
    try:
        df_cust = get_source_df(q_cust, src_engine).drop_duplicates(subset=['customer_id'])
    except Exception as e:
        # Fallback: simpler customers
        df_cust = pd.DataFrame(columns=['customer_id', 'customer_name', 'accountnumber', 'city', 'stateprovince', 'country', 'postalcode'])
        print("Aviso: query de cliente falhou. Criando dataset vazio de clientes:", e)

    # 3) Extrair: Employees (vendedores)
    print("Extraindo employees...")
    q_emp = """
    SELECT e.businessentityid AS employee_id, p.firstname || ' ' || p.lastname AS employee_name, e.jobtitle
    FROM humanresources_employee e
    LEFT JOIN person_person p ON e.businessentityid = p.businessentityid
    """
    df_emp = get_source_df(q_emp, src_engine).drop_duplicates(subset=['employee_id'])

    # 4) Extrair: Territories
    print("Extraindo territory...")
    q_ter = """
    SELECT territoryid AS territory_id, name AS territory_name, countryregioncode AS region
    FROM sales_territory
    """
    df_ter = get_source_df(q_ter, src_engine).drop_duplicates(subset=['territory_id'])

    # 5) Extrair: Sales Orders + Details (LINHA)
    print("Extraindo vendas (detalhes)...")
    q_sales = """
    SELECT soh.salesorderid AS order_id,
           sod.salesorderdetailid AS order_line_id,
           soh.orderdate::date AS order_date,
           sod.productid AS product_id,
           soh.customerid AS customer_id,
           soh.salespersonid AS employee_id,
           soh.territoryid AS territory_id,
           sod.orderqty AS quantity,
           sod.unitprice,
           (sod.orderqty * sod.unitprice) AS line_total
    FROM sales_salesorderheader soh
    JOIN sales_salesorderdetail sod ON soh.salesorderid = sod.salesorderid
    WHERE sod.unitprice IS NOT NULL
    """
    df_sales = get_source_df(q_sales, src_engine)
    print(f"Linhas de venda extraídas: {len(df_sales)}")

    # 6) Transformações:
    #   - Criar dim_date
    print("Transformando dim_date...")
    df_dates = pd.DataFrame({'date': pd.to_datetime(df_sales['order_date'].unique())})
    df_dates['date_id'] = df_dates['date'].dt.strftime('%Y%m%d').astype(int)
    df_dates['year'] = df_dates['date'].dt.year
    df_dates['quarter'] = df_dates['date'].dt.quarter
    df_dates['month'] = df_dates['date'].dt.month
    df_dates['month_name'] = df_dates['date'].dt.strftime('%B')
    df_dates['day'] = df_dates['date'].dt.day
    df_dates['day_of_week'] = df_dates['date'].dt.weekday + 1
    df_dates['day_name'] = df_dates['date'].dt.strftime('%A')
    df_dates['is_weekend'] = df_dates['day_of_week'].isin([6,7])

    dim_date = df_dates[['date_id','date','year','quarter','month','month_name','day','day_of_week','day_name','is_weekend']]

    # 7) Transform dim_product: preencher colunas faltantes com defaults
    dim_product = df_prod.fillna({'brand': 'Unknown', 'color': 'Unknown', 'standardcost': 0.0, 'listprice': 0.0})
    dim_product = dim_product.rename(columns={'product_id':'product_id','name':'product_name'})

    # 8) Transform dim_customer
    if df_cust.empty:
        # Criar customers via vendas (fallback)
        print("Criando dim_customer a partir de vendas (fallback)...")
        unique_cust = df_sales[['customer_id']].drop_duplicates()
        unique_cust['customer_name'] = 'Cliente ' + unique_cust['customer_id'].astype(str)
        unique_cust['accountnumber'] = None
        unique_cust['city']=None; unique_cust['stateprovince']=None; unique_cust['country']=None; unique_cust['postalcode']=None
        dim_customer = unique_cust.rename(columns={'customer_id':'customer_id'})
    else:
        dim_customer = df_cust.rename(columns={
            'customer_id':'customer_id',
            'customer_name':'customer_name',
            'accountnumber':'account_number',
            'city':'city',
            'stateprovince':'state_province',
            'country':'country',
            'postalcode':'postal_code'
        })
        # Normalize cols
        dim_customer = dim_customer[['customer_id','customer_name','account_number','city','state_province','country','postal_code']]

    # 9) Dim Employee e Territory já prontos (df_emp, df_ter)
    dim_employee = df_emp.rename(columns={'employee_id':'employee_id','employee_name':'employee_name','jobtitle':'job_title'})
    dim_territory = df_ter.rename(columns={'territory_id':'territory_id','territory_name':'territory_name','region':'region'})

    # 10) Construir fact_sales unindo dados e criando keys
    print("Montando fato de vendas...")
    # join date_id
    df_sales['order_date'] = pd.to_datetime(df_sales['order_date'])
    df_sales['date_id'] = df_sales['order_date'].dt.strftime('%Y%m%d').astype(int)
    # left join unit_cost via dim_product.standardcost (se disponível)
    prod_cost_map = dim_product.set_index('product_id')['standardcost'].to_dict() if 'standardcost' in dim_product.columns else {}
    df_sales['unit_cost'] = df_sales['product_id'].map(prod_cost_map).fillna(0.0)
    df_sales = df_sales.rename(columns={'unitprice':'unit_price','line_total':'line_total'})

    fact_sales = df_sales[['order_id','order_line_id','date_id','product_id','customer_id','employee_id','territory_id','quantity','unit_price','line_total','unit_cost']].fillna({'employee_id':None,'territory_id':None})

    # 11) Carregar (LOAD) — upsert dims, insert facts
    print("Carregando dimensões no DW...")
    upsert_dim(dst_engine, dim_date, 'dim_date', 'date_id')
    upsert_dim(dst_engine, dim_product[['product_id','product_name','productnumber','brand','color','standardcost','listprice','category','subcategory']], 'dim_product', 'product_id')
    upsert_dim(dst_engine, dim_customer, 'dim_customer', 'customer_id')
    upsert_dim(dst_engine, dim_employee[['employee_id','employee_name','jobtitle']], 'dim_employee', 'employee_id')
    upsert_dim(dst_engine, dim_territory, 'dim_territory', 'territory_id')

    print("Carregando fatos (fact_sales)...")
    load_fact(dst_engine, fact_sales, 'fact_sales')

    print("ETL concluído com sucesso.")

if __name__ == "__main__":
    etl()
