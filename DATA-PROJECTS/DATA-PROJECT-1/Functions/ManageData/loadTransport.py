
import time
import pandas as pd
import psycopg2
from psycopg2 import sql
import ssl
import urllib.request


# Ruta del archivo CSV
file_path = 'https://valencia.opendatasoft.com/api/explore/v2.1/catalog/datasets/transporte-barrios/exports/csv?lang=es&timezone=Europe%2FMadrid&use_labels=true&delimiter=%3B'

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
                CREATE TABLE IF NOT EXISTS transporte_publico (
                    id SERIAL PRIMARY KEY,
                    geo_point VARCHAR(255),
                    geo_shape TEXT,
                    codbarrio INT,
                    nombre VARCHAR(255),
                    coddistbar INT,
                    coddistrit INT,
                    codbar INT,
                    transporte VARCHAR(50),
                    stop_id FLOAT,
                    stop_name VARCHAR(255),
                    stop_desc TEXT,
                    x FLOAT,
                    y FLOAT,
                    zone_id VARCHAR(50),
                    latitud FLOAT,
                    longitud FLOAT
                );
                """
                cursor.execute(create_table_query)
                print("Tabla 'transporte_publico' creada o verificada correctamente.")

                # Insertar los datos
                insert_query = """
                INSERT INTO transporte_publico (
                    geo_point, geo_shape, codbarrio, nombre, coddistbar, coddistrit, codbar, transporte,
                    stop_id, stop_name, stop_desc, x, y, zone_id, latitud, longitud
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ;
                """
                for _, row in df.iterrows():
                    geo_point_split = str(row['Geo Point']).split(',')
                    latitud = float(geo_point_split[0]) if len(geo_point_split) > 1 else None
                    longitud = float(geo_point_split[1]) if len(geo_point_split) > 1 else None
                    cursor.execute(insert_query, (
                        row['Geo Point'],
                        row['Geo Shape'],
                        row['codbarrio'],
                        row['nombre'],
                        row['coddistbar'],
                        row['coddistrit'],
                        row['codbar'],
                        row['transporte'],
                        row['stop_id'],
                        row['stop_name'],
                        row['stop_desc'],
                        row['X'],
                        row['Y'],
                        row['zone_id'],
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
