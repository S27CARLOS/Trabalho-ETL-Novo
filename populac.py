import psycopg2
from faker import Faker
import random
from datetime import datetime

# Conexão com o banco de dados
conexao = psycopg2.connect(
    database="date",
    host="localhost",
    user="postgres",
    password="1234",
    port="5432"
)

fake = Faker()
cursor = conexao.cursor()

# Possíveis territórios
territorios = [
    "North", "South", "East", "West",
    "Central", "Northeast", "Southeast", "Midwest"
]

# Populando a tabela dim_salesperson com 100 registros
for i in range(1, 101):
    salesperson_key = i
    salesperson_id = i  # ou pode gerar com random.randint(1000, 9999)
    name = fake.name()
    territory = random.choice(territorios)
    hire_date = fake.date_between(start_date='-10y', end_date='today')

    cursor.execute("""
        INSERT INTO dim_salesperson (
            salesperson_key, salesperson_id, name, territory, hire_date
        ) VALUES (%s, %s, %s, %s, %s)
    """, (
        salesperson_key, salesperson_id, name, territory, hire_date
    ))

# Confirma as alterações
conexao.commit()
print("Tabela dim_salesperson populada com sucesso!")

# Fecha a conexão
cursor.close()
conexao.close()
