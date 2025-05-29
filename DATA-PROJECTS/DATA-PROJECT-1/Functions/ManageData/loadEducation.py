import time
import pandas as pd
import requests
from io import StringIO
import psycopg2
from psycopg2 import sql

# URL del archivo CSV
url_centros_educativos = "https://valencia.opendatasoft.com/api/explore/v2.1/catalog/datasets/centros-educativos-en-valencia/exports/csv?lang=es&timezone=Europe%2FBerlin&use_labels=true&delimiter=%3B"
time.sleep(2)

# Configuración de la conexión inicial para el servidor
SERVER_CONFIG = {
    "dbname": "postgres",
    "user": "postgres",
    "password": "Welcome01",
    "host": "postgres",
    "port": 5432
}

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
        connection = psycopg2.connect(**server_config)
        connection.autocommit = True
        cursor = connection.cursor()

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
    finally:
        if connection:
            cursor.close()
            connection.close()

def descargar_csv_a_df(url):
    try:
        response = requests.get(url)
        response.raise_for_status()

        csv_data = StringIO(response.text)
        df = pd.read_csv(csv_data, sep=';')
        print(f"CSV cargado con {len(df)} registros.")
        return df
    except Exception as e:
        print(f"Error al descargar o procesar el CSV: {e}")
        return None

def crear_tabla_centros_y_insertar_datos(df, db_config):
    connection = psycopg2.connect(**db_config)
    cursor = connection.cursor()

    # Crear la tabla
    create_table_query = """
    CREATE TABLE IF NOT EXISTS centros_educativos (
        id SERIAL PRIMARY KEY,
        Geo_Point VARCHAR(255),
        Geo_Shape TEXT,
        codcen INT,
        dlibre VARCHAR(255),
        dgenerica VARCHAR(255),
        despecific VARCHAR(255),
        regimen VARCHAR(50),
        direccion VARCHAR(255),
        codpos INT,
        municipio VARCHAR(100),
        provincia VARCHAR(100),
        telef VARCHAR(50),
        fax VARCHAR(50),
        mail VARCHAR(255),
        latitud FLOAT,
        longitud FLOAT
    );
    """
    cursor.execute(create_table_query)
    print("Tabla 'centros_educativos' creada o verificada correctamente.")

    # Insertar los datos
    insert_query = """
    INSERT INTO centros_educativos (
        Geo_Point, Geo_Shape, codcen, dlibre, dgenerica, despecific, regimen,
        direccion, codpos, municipio, provincia, telef, fax, mail, latitud, longitud
    ) VALUES (
        %s,%s,
        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
    );
    """
    for _, row in df.iterrows():
        geo_point_split = str(row['Geo Point']).split(',')
        latitud = float(geo_point_split[0]) if len(geo_point_split) > 1 else None
        longitud = float(geo_point_split[1]) if len(geo_point_split) > 1 else None
        cursor.execute(insert_query, (
            row['Geo Point'],
            row['Geo Shape'],
            int(row['codcen']),
            row['dlibre'],
            row['dgenerica_'],
            row['despecific'],
            row['regimen'],
            row['direccion'],
            int(row['codpos']),
            row['municipio_'],
            row['provincia_'],
            row['telef'],
            row['fax'],
            row['mail'],
            latitud,
            longitud
        ))

    connection.commit()
    print("Datos insertados correctamente.")

    cursor.close()
    connection.close()

# Verificar o crear la base de datos
verificar_o_crear_base_datos(SERVER_CONFIG, DB_NAME)

# Descargar el CSV y procesar los datos
df_centros = descargar_csv_a_df(url_centros_educativos)

if df_centros is not None:
    # Crear tabla y cargar datos en la base de datos
    crear_tabla_centros_y_insertar_datos(df_centros, DB_CONFIG)