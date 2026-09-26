import psycopg2
from datetime import date, timedelta

# Conexão com o banco de dados PostgreSQL
conexao = psycopg2.connect(
    database="date",
    host="localhost",
    user="postgres",
    password="1234",
    port="5432"
)
cursor = conexao.cursor()

# Define o período que deseja popular (ex: de 2000-01-01 a 2030-12-31)
data_inicio = date(2000, 1, 1)
data_fim = date(2030, 12, 31)
delta = data_fim - data_inicio

for i in range(delta.days + 1):
    full_date = data_inicio + timedelta(days=i)
    year = full_date.year
    quarter = (full_date.month - 1) // 3 + 1
    month = full_date.month
    month_name = full_date.strftime('%B')
    day = full_date.day
    weekday = full_date.weekday()  # 0 = segunda-feira, 6 = domingo
    is_weekend = weekday >= 5  # sábado=5, domingo=6

    cursor.execute("""
        INSERT INTO date_key (full_date, year, quarter, month, month_name, day, weekday, is_weekend)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, (full_date, year, quarter, month, month_name, day, weekday, is_weekend))

# Confirma as alterações
conexao.commit()
print("Tabela date_key populada com sucesso!")

# Fecha a conexão
cursor.close()
conexao.close()
