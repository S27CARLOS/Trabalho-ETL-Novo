import psycopg2
from faker import Faker
import random

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

# Listas para gerar dados aleatórios
cores = ["Red", "Blue", "Green", "Black", "White", "Yellow", "Gray"]
tamanhos = ["XS", "S", "M", "L", "XL", "XXL"]
categorias = [
    ("Clothing", "Shirts"),
    ("Clothing", "Pants"),
    ("Clothing", "Shoes"),
    ("Electronics", "Smartphones"),
    ("Electronics", "Laptops"),
    ("Accessories", "Watches"),
    ("Accessories", "Bags")
]

# Populando a tabela dim_customer com 100 registros simulados
for i in range(1, 101):
    customer_key = i
    customer_id = f"CUST-{i:05d}"
    first_name = fake.first_name()
    last_name = fake.last_name()
    email = fake.email()
    phone = fake.phone_number()
    address = fake.street_address()
    city = fake.city()
    state = fake.state()
    country = fake.country()
    postal_code = fake.postcode()
    customer_type = random.choice(["Regular", "VIP", "Premium"])

    cursor.execute("""
        INSERT INTO dim_customer (
            customer_key, customer_id, fitst_name,
            last_name, email, phone, address,
            city, state, country, postal_code, customer_type
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        customer_key, customer_id, first_name,
        last_name, email, phone, address,
        city, state, country, postal_code, customer_type
    ))

# Confirmar as alterações
conexao.commit()
print("Tabela dim_customer populada com sucesso!")

# Fechar conexão
cursor.close()
conexao.close()
