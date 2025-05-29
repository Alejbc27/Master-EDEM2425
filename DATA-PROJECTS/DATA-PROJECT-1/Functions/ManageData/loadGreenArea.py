import time
import psycopg2
from psycopg2 import sql
from extractParkFromOPMS import contar_parques_en_barrios
# Configuración de la conexión inicial para el servidor
SERVER_CONFIG = {
    "dbname": "postgres",
    "user": "postgres",
    "password": "Welcome01",
    "host": "postgres",
    "port": 5432
}
time.sleep(2)

# Configuración para la nueva base de datos
DB_NAME = "dataproject"
DB_CONFIG = {
    "dbname": DB_NAME,
    "user": "postgres",
    "password": "Welcome01",
    "host": "postgres",
    "port": 5432
}

def verificar_o_crear_base_datos(server_config, db_name):
    try:
        # Conexión inicial al servidor PostgreSQL
        connection = psycopg2.connect(**server_config)
        connection.autocommit = True
        cursor = connection.cursor()

        # Verificar si la base de datos existe
        cursor.execute(
            sql.SQL("SELECT 1 FROM pg_database WHERE datname = %s"),
            [db_name]
        )
        if cursor.fetchone() is None:
            # Crear la base de datos si no existe
            cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(db_name)))
            print(f"Base de datos '{db_name}' creada.")
        else:
            print(f"La base de datos '{db_name}' ya existe.")
    except Exception as e:
        print(f"Error al verificar o crear la base de datos: {e}")
    finally:
        if connection:
            cursor.close()
            connection.close()

def crear_tabla_y_insertar_datos(df, db_config):
    try:
        # Conexión a la base de datos
        connection = psycopg2.connect(**db_config)
        cursor = connection.cursor()

        # Crear la tabla
        create_table_query = """
        CREATE TABLE IF NOT EXISTS zonas_verdes (
            id SERIAL PRIMARY KEY,
            barrio VARCHAR(255) NOT NULL,
            numero_parques INT NOT NULL
        );
        """
        cursor.execute(create_table_query)
        print("Tabla 'zonas_verdes' creada o verificada correctamente.")

        # Insertar los datos
        insert_query = """
        INSERT INTO zonas_verdes (barrio, numero_parques)
        VALUES (%s, %s);
        """
        for _, row in df.iterrows():
            cursor.execute(insert_query, (row['Barrio'], row['NumeroParques']))

        # Confirmar los cambios
        connection.commit()
        print("Datos insertados correctamente.")
    except Exception as e:
        print(f"Error al crear la tabla o insertar los datos: {e}")
    finally:
        if connection:
            cursor.close()
            connection.close()

verificar_o_crear_base_datos(SERVER_CONFIG, DB_NAME)

df = contar_parques_en_barrios()
crear_tabla_y_insertar_datos(df, DB_CONFIG)
