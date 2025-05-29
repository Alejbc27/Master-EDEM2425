
import time
import pandas as pd
import psycopg2
from psycopg2 import sql
import ssl
import urllib.request


# Ruta del archivo CSV
file_path = 'https://valencia.opendatasoft.com/api/explore/v2.1/catalog/datasets/hospitales/exports/csv?lang=es&timezone=Europe%2FMadrid&use_labels=true&delimiter=%3B'

# Configuración de conexión inicial para el servidor
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
        with psycopg2.connect(**server_config) as connection:
            connection.autocommit = True
            with connection.cursor() as cursor:
                cursor.execute(
                    sql.SQL("SELECT 1 FROM pg_database WHERE datname = %s"),
                    [db_name]
                )
                if cursor.fetchone() is None:
                    cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(db_name)))
                    print(f"Base de datos '{db_name}' creada.")
                else:
                    print(f"La base de datos '{db_name}' ya existe.")
    except Exception as e:
        print(f"Error al verificar o crear la base de datos: {e}")

def cargar_csv_a_df(file_path):
    try:
        ssl_context = ssl._create_unverified_context()
        response = urllib.request.urlopen(file_path, context=ssl_context)
        df = pd.read_csv(response, sep=';')
        print(f"CSV cargado con {len(df)} registros.")
        return df
    except Exception as e:
        print(f"Error al cargar el archivo CSV: {e}")
        return None

def crear_tabla_transporte_y_insertar_datos(df, db_config):
    try:
        with psycopg2.connect(**db_config) as connection:
            with connection.cursor() as cursor:
                # Crear la tabla
                create_table_query = """
                CREATE TABLE IF NOT EXISTS centros_sanitarios (
                    id SERIAL PRIMARY KEY,
                    geo_point VARCHAR(255),
                    geo_shape TEXT,
                    nombre VARCHAR(255),
                    tipo VARCHAR(255),
                    financiaci VARCHAR(255),
                    camas INT,
                    direccion VARCHAR(255),
                    fecha DATE,
                    barrio VARCHAR(255),
                    codbarrio INT,
                    coddistbar INT,
                    coddistrit INT,
                    x FLOAT,
                    y FLOAT,
                    latitud FLOAT,
                    longitud FLOAT
                );
                """
                cursor.execute(create_table_query)
                print("Tabla 'centros_sanitarios' creada o verificada correctamente.")

                # Insertar los datos
                insert_query = """
                INSERT INTO centros_sanitarios (
                    geo_point, geo_shape, nombre, tipo, financiaci, camas, direccion, 
                    fecha, barrio, codbarrio, coddistbar, coddistrit, x, y, latitud, longitud
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ;
                """
                for _, row in df.iterrows():
                    geo_point_split = str(row['geo_point_2d']).split(',')
                    latitud = float(geo_point_split[0]) if len(geo_point_split) > 1 else None
                    longitud = float(geo_point_split[1]) if len(geo_point_split) > 1 else None
                    cursor.execute(insert_query, (
                        row['geo_point_2d'],
                        row['Geo Shape'],
                        row['Nombre'],
                        row['Tipo'],
                        row['Financiaci'],
                        row['Camas'],
                        row['Direccion'],
                        row['Fecha'],
                        row['Barrio'],
                        row['codbarrio'],
                        row['coddistbar'],
                        row['coddistrit'],
                        row['X'],
                        row['Y'],
                        latitud,
                        longitud
                    ))
            connection.commit()
            print("Datos insertados correctamente.")
    except Exception as e:
        print(f"Error al crear la tabla o insertar los datos: {e}")

# Verificar o crear la base de datos
verificar_o_crear_base_datos(SERVER_CONFIG, DB_NAME)

# Cargar el CSV y procesar los datos
df_transporte = cargar_csv_a_df(file_path)

if df_transporte is not None:
    # Crear tabla y cargar datos en la base de datos
    crear_tabla_transporte_y_insertar_datos(df_transporte, DB_CONFIG)
