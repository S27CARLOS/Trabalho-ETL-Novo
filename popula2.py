import psycopg2
from faker import Faker
import random
from datetime import timedelta

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

# Métodos de envio possíveis
metodos_envio = ["FedEx", "UPS", "DHL", "Correios", "USPS"]

# Populando a tabela dim_order com 200 pedidos
for i in range(1, 201):
    order_id = i
    order_date = fake.date_between(start_date='-2y', end_date='today')
    due_date = order_date + timedelta(days=random.randint(3, 10))
    ship_date = order_date + timedelta(days=random.randint(1, 7))
    status = random.randint(1, 5)  # por exemplo: 1 = pendente, 2 = processando, etc.
    online_order_flag = random.choice([True, False])
    ship_method = random.choice(metodos_envio)

    cursor.execute("""
        INSERT INTO dim_order (
            order_id, order_date, due_date, ship_date, status, online_order_flag, ship_method
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (
        order_id, order_date, due_date, ship_date, status, online_order_flag, ship_method
    ))

# Confirma as alterações
conexao.commit()
print("Tabela dim_order populada com sucesso!")

# Fecha a conexão
cursor.close()
conexao.close()
