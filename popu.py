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

# Possíveis valores para campos categóricos
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

# Populando a tabela dim_product com 100 produtos
for i in range(1, 101):
    product_id = i
    product_name = fake.word().capitalize() + " " + fake.color_name()
    product_number = f"P-{i:05d}"
    category, subcategory = random.choice(categorias)
    color = random.choice(cores)
    size = random.choice(tamanhos)
    standard_cost = round(random.uniform(20.00, 500.00), 2)
    list_price = round(standard_cost * random.uniform(1.1, 2.0), 2)
    discontinued = random.choice([True, False])

    cursor.execute("""
        INSERT INTO dim_product (
            product_id, product_name, product_number,
            category, subcategory, color, size,
            standard_cost, list_price, discontinued
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        product_id, product_name, product_number,
        category, subcategory, color, size,
        standard_cost, list_price, discontinued
    ))

# Confirma as alterações
conexao.commit()

print("Tabela dim_product populada com sucesso!")

# Fecha a conexão
cursor.close()
conexao.close()
