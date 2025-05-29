import time
import pandas as pd
import requests
from io import StringIO
import psycopg2
from psycopg2 import sql

url_alquiler = "https://valencia.opendatasoft.com/api/explore/v2.1/catalog/datasets/precio-alquiler-vivienda/exports/csv?lang=es&timezone=Europe%2FBerlin&use_labels=true&delimiter=%3B"

SERVER_CONFIG = {
    "dbname": "postgres",
    "user": "postgres",
    "password": "Welcome01",
    "host": "postgres",
    "port": 5432
}
time.sleep(2)

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
        response = requests.get(url)
        response.raise_for_status()

        df = pd.read_csv(StringIO(response.text), sep=';')
        columnas_a_limpiar = ['Año_Max_Hist']
        
        df = df.dropna(subset=columnas_a_limpiar)

        # Crear la nueva columna 'CodDistrit' según la lógica de 'CodBar-CodDistrit'
        if 'CodBar-CodDistrit' in df.columns:
            df['CodDistrit'] = df['CodBar-CodDistrit'].astype(str).apply(
                lambda x: x[:2] if len(x) == 3 else x[:1]
            )
        
        for col in columnas_a_limpiar:
            if col in df.columns:
                # Convertir la columna a string primero
                df[col] = df[col].astype(str)
                # Reemplazar comas por puntos
                df[col] = df[col].str.replace(',', '.')
                # Convertir a float y luego a entero
                df[col] = pd.to_numeric(df[col], errors='coerce')
                df[col] = df[col].astype(int)
        
        print(f"CSV cargado con {len(df)} registros.")
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
    CREATE TABLE IF NOT EXISTS precios_alquiler (
        id SERIAL PRIMARY KEY,
        distrito VARCHAR(255),
        barrio VARCHAR(255),
        Precio_2022_Euros_m2 FLOAT,
        Precio_2010_Euros_m2 FLOAT,
        Max_historico_Euros_m2 FLOAT,
        Año_Max_Hist INT,
        CodBar_CodDistrit INT,
        CodDistrit INT

    );
    """
    cursor.execute(create_table_query)
    print("Tabla 'precios_alquiler' creada o verificada correctamente.")

    # Insertar los datos
    insert_query = """
    INSERT INTO precios_alquiler (distrito, barrio, Precio_2022_Euros_m2, Precio_2010_Euros_m2, Max_historico_Euros_m2, Año_Max_Hist, CodBar_CodDistrit, CodDistrit)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
    """
    
    for _, row in df.iterrows():
        # Ejecutar la inserción
        cursor.execute(insert_query, (
            row['DISTRITO'],               
            row['BARRIO'],               
            float(row['Precio_2022 (Euros/m2)']),         
            float(row['Precio_2010 (Euros/m2)']),                  
            float(row['Max_historico (Euros/m2)']),  
            int(row['Año_Max_Hist']),        
            int(row['CodBar-CodDistrit']),
            int(row['CodDistrit'])

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
df = descargar_csv_a_df(url_alquiler)

if df is not None:
    # Crear tabla y cargar datos en la base de datos
    crear_tabla_y_insertar_datos(df, DB_CONFIG)