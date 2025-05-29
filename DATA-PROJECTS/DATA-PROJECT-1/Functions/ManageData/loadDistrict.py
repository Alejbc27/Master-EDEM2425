import pandas as pd
import requests
from io import StringIO
import psycopg2
from psycopg2 import sql
import time

time.sleep(20)

# URL del archivo CSV
url = "https://valencia.opendatasoft.com/api/explore/v2.1/catalog/datasets/districtes-distritos/exports/csv?lang=es&timezone=Europe%2FBerlin&use_labels=true&delimiter=%3B"

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

def descargar_csv_a_df(url):
    try:
        # Descargar y cargar CSV en un DataFrame
        response = requests.get(url)
        response.raise_for_status()
        csv_data = StringIO(response.text)
        df = pd.read_csv(csv_data, sep=';')
        valores_a_excluir = ["POBLATS DEL NORD", "POBLATS DEL SUD", "POBLATS DE L'OEST"]
        df = df[~df['Nombre'].isin(valores_a_excluir)]
        nombre_mapping = {
            "EL PLA DEL REAL": "el Pla del Real",
            "EXTRAMURS": "Extramurs",
            "L'EIXAMPLE": "l'Eixample",
            "ALGIROS": "Algirós",
            "RASCANYA": "Rascanya",
            "L'OLIVERETA": "l'Olivereta",
            "BENICALAP": "Benicalap",
            "LA SAIDIA": "la Saïdia",
            "CAMINS AL GRAU": "Camins al Grau",
            "BENIMACLET": "Benimaclet",
            "CAMPANAR": "Campanar",
            "POBLATS MARITIMS": "Poblats Marítims",
            "CIUTAT VELLA": "Ciutat Vella",
            "JESUS": "Jesús",
            "QUATRE CARRERES": "Quatre Carreres",
            "PATRAIX": "Patraix",
        }

        df['Nombre Corregido'] = df['Nombre'].map(nombre_mapping)

        print(f"CSV cargado con {len(df)} registros después de filtrar.")
        return df
    except Exception as e:
        print(f"Error al descargar o procesar el CSV: {e}")
        return None


def crear_tabla_y_insertar_datos(df, db_config):
    # Conexión a la base de datos
    connection = psycopg2.connect(**db_config)
    cursor = connection.cursor()

    # Crear la tabla
    create_table_query = """
    CREATE TABLE IF NOT EXISTS distritos (
        objectid INT PRIMARY KEY,
        nombre VARCHAR(255),
        nombre_corregido VARCHAR(255),
        codigo_distrito INT,
        area FLOAT,
        geo_shape TEXT,
        geo_point_2d VARCHAR(255),
        latitud FLOAT,
        longitud FLOAT
    );
    """
    cursor.execute(create_table_query)
    print("Tabla 'distritos' creada o verificada correctamente.")
     
    # Insertar los datos
    insert_query = """
    INSERT INTO distritos (objectid, nombre,nombre_corregido, codigo_distrito, area, geo_shape, geo_point_2d, latitud, longitud)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
    """
    for _, row in df.iterrows():
        geo_point_split = str(row['geo_point_2d']).split(',')
        latitud = float(geo_point_split[0]) if len(geo_point_split) > 1 else None
        longitud = float(geo_point_split[1]) if len(geo_point_split) > 1 else None

        # Ejecutar la inserción
        cursor.execute(insert_query, (
            int(row['objectid']),
            row['Nombre'],
            row['Nombre Corregido'],
            int(row['Código distrito']),
            float(row['gis.gis.DISTRITOS.area']),
            row['geo_shape'],
            row['geo_point_2d'],
            latitud,
            longitud
        ))

    # Confirmar los cambios
    connection.commit()
    print("Datos insertados correctamente.")

    # Cerrar la conexión
    cursor.close()
    connection.close()
# Verificar o crear la base de datos
verificar_o_crear_base_datos(SERVER_CONFIG, DB_NAME)

# Descargar el CSV y procesar los datos
df = descargar_csv_a_df(url)

if df is not None:
    # Crear tabla y cargar datos en la base de datos
    crear_tabla_y_insertar_datos(df, DB_CONFIG)