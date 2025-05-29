import time
import pandas as pd
import requests
from io import StringIO
import psycopg2
from psycopg2 import sql

url_precios = "https://valencia.opendatasoft.com/api/explore/v2.1/catalog/datasets/precio-de-compra-en-idealista/exports/csv?lang=es&timezone=Europe%2FBerlin&use_labels=true&delimiter=%3B"

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
        columnas_a_limpiar = [
            'Precio_2022 (Euros/m2)', 'Precio_2010 (Euros/m2)', 
            'Max_historico (Euros/m2)', 'Año_Max_Hist'
        ]
        
        df = df.dropna(subset=columnas_a_limpiar)

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
    CREATE TABLE IF NOT EXISTS precios_compra (
        id SERIAL PRIMARY KEY,
        Geo_Point VARCHAR(255),
        Geo_Shape TEXT,
        coddistbar INT,
        barrio VARCHAR(255),
        codbarrio INT,
        coddistrit INT,
        distrito VARCHAR(255),
        precio_2022_Euros_m2 INT,
        precio_2010_Euros_m2 INT,
        max_historico_Euros_m2 INT,
        año_max_hist INT,
        fecha_creacion DATE

    );
    """
    cursor.execute(create_table_query)
    print("Tabla 'precios_compra' creada o verificada correctamente.")

    # Insertar los datos
    insert_query = """
    INSERT INTO precios_compra (Geo_Point, Geo_Shape, coddistbar, barrio, codbarrio, coddistrit, distrito, precio_2022_Euros_m2, precio_2010_Euros_m2, max_historico_Euros_m2, año_max_hist, fecha_creacion )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
    """
    for _, row in df.iterrows():
        geo_point_split = str(row['Geo Point']).split(',')
        latitud = float(geo_point_split[0]) if len(geo_point_split) > 1 else None
        longitud = float(geo_point_split[1]) if len(geo_point_split) > 1 else None

        # Ejecutar la inserción
        cursor.execute(insert_query, (
            row['Geo Point'],               
            row['Geo Shape'],               
            int(row['coddistbar']),         
            row['BARRIO'],                  
            int(row['codbarrio']),  
            int(row['coddistrit']),        
            row['DISTRITO'],               
            int(row['Precio_2022 (Euros/m2)']),  
            int(row['Precio_2010 (Euros/m2)']),  
            int(row['Max_historico (Euros/m2)']),  
            int(row['Año_Max_Hist']),          
            row['Fecha_creacion']           
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
df = descargar_csv_a_df(url_precios)

if df is not None:
    # Crear tabla y cargar datos en la base de datos
    crear_tabla_y_insertar_datos(df, DB_CONFIG)
