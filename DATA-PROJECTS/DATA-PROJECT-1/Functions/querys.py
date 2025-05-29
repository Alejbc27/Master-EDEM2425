import psycopg2
import pandas as pd

#Query para Compra
def obtener_coste_compra():
    db_config = {
    "dbname": "dataproject",
    "user": "postgres",
    "password": "Welcome01",
    "host": "postgres",
    "port": 5432
    }
    query = """
    SELECT coddistrit AS codigo_distrito, distrito AS nombre_distrito, ROUND(CAST(AVG(precio_2022_euros_m2) AS NUMERIC), 2) AS precio_medio_2022_m2
    FROM precios_compra
    GROUP BY coddistrit, distrito
    ORDER BY distrito;
    """
    try:
        connection = psycopg2.connect(**db_config)
        cursor = connection.cursor()
        cursor.execute(query)
        resultados = cursor.fetchall()
        # Convertir los resultados a un DataFrame de pandas
        df = pd.DataFrame(resultados, columns=["codigo_distrito", "nombre_distrito", "precio_medio_2022_m2"])
        return df
    except Exception as e:
        print(f"Error al ejecutar la consulta: {e}")
        return None
    finally:
        if connection:
            cursor.close()
            connection.close()
#Query para Alquiler
def obtener_coste_alquiler():
    db_config = {
    "dbname": "dataproject",
    "user": "postgres",
    "password": "Welcome01",
    "host": "postgres",
    "port": 5432
    }
    query = """
    SELECT coddistrit AS codigo_distrito, distrito AS nombre_distrito, ROUND(CAST(AVG(precio_2022_euros_m2) AS NUMERIC), 2) AS precio_medio_2022_m2
    FROM precios_alquiler
    GROUP BY coddistrit, distrito
    ORDER BY distrito;
    """
    try:
        connection = psycopg2.connect(**db_config)
        cursor = connection.cursor()
        cursor.execute(query)
        resultados = cursor.fetchall()
        # Convertir los resultados a un DataFrame de pandas
        df = pd.DataFrame(resultados, columns=["codigo_distrito", "nombre_distrito", "precio_medio_2022_m2"])
        return df
    except Exception as e:
        print(f"Error al ejecutar la consulta: {e}")
        return None
    finally:
        if connection:
            cursor.close()
            connection.close()
#Query para Transporte
def obtener_transporte():
    db_config = {
    "dbname": "dataproject",
    "user": "postgres",
    "password": "Welcome01",
    "host": "postgres",
    "port": 5432
    }
    query = """
    SELECT d.codigo_distrito AS codigo_distrito, d.nombre_corregido AS distrito, COUNT(tp.id) AS total_transporte
    FROM distritos d
    LEFT JOIN transporte_publico tp
    ON d.codigo_distrito = tp.coddistrit
    GROUP BY d.nombre_corregido,d.codigo_distrito
    ORDER BY d.nombre_corregido;
    """
    try:
        connection = psycopg2.connect(**db_config)
        cursor = connection.cursor()
        cursor.execute(query)
        resultados = cursor.fetchall()
        # Convertir los resultados a un DataFrame de pandas
        df = pd.DataFrame(resultados, columns=["codigo_distrito", "distrito", "total_transporte"])
        return df
    except Exception as e:
        print(f"Error al ejecutar la consulta: {e}")
        return None
    finally:
        if connection:
            cursor.close()
            connection.close()
#Query para Escuelas          
def obtener_escuelas():
    db_config = {
    "dbname": "dataproject",
    "user": "postgres",
    "password": "Welcome01",
    "host": "postgres",
    "port": 5432
    }
    query = """
    SELECT d.cod_dist AS codigo_distrito, d.nombre AS nombre_distrito, COUNT(c.id) AS total_centros_educativos
    FROM distritos_cp d
    LEFT JOIN centros_educativos c
    ON d.codigo_postal = c.codpos
    GROUP BY d.cod_dist, d.nombre
    ORDER BY d.nombre;
    """
    try:
        connection = psycopg2.connect(**db_config)
        cursor = connection.cursor()
        cursor.execute(query)
        resultados = cursor.fetchall()
        # Convertir los resultados a un DataFrame de pandas
        df = pd.DataFrame(resultados, columns=["codigo_distrito", "distrito", "total_centros_educativos"])
        return df
    except Exception as e:
        print(f"Error al ejecutar la consulta: {e}")
        return None
    finally:
        if connection:
            cursor.close()
            connection.close()
#Query para Hospitales
def obtener_hospitales():
    db_config = {
    "dbname": "dataproject",
    "user": "postgres",
    "password": "Welcome01",
    "host": "postgres",
    "port": 5432
    }
    query = """
    SELECT d.codigo_distrito AS codigo_distrito, d.nombre_corregido AS distrito, COUNT(cs.id) AS total_hospitales
    FROM distritos d
    LEFT JOIN centros_sanitarios cs
    ON d.codigo_distrito = cs.coddistrit
    GROUP BY d.nombre_corregido,d.codigo_distrito
    ORDER BY d.nombre_corregido;
    """
    try:
        connection = psycopg2.connect(**db_config)
        cursor = connection.cursor()
        cursor.execute(query)
        resultados = cursor.fetchall()
        # Convertir los resultados a un DataFrame de pandas
        df = pd.DataFrame(resultados, columns=["codigo_distrito", "distrito", "total_hospitales"])
        return df
    except Exception as e:
        print(f"Error al ejecutar la consulta: {e}")
        return None
    finally:
        if connection:
            cursor.close()
            connection.close()
#Query para Ocio
def obtener_ocio():
    db_config = {
    "dbname": "dataproject",
    "user": "postgres",
    "password": "Welcome01",
    "host": "postgres",
    "port": 5432
    }
    query = """
    SELECT barrio AS distrito, numero_ocio
    FROM zonas_de_ocio
    ORDER BY distrito;
    """
    try:
        connection = psycopg2.connect(**db_config)
        cursor = connection.cursor()
        cursor.execute(query)
        resultados = cursor.fetchall()
        # Convertir los resultados a un DataFrame de pandas
        df = pd.DataFrame(resultados, columns=["distrito", "total_ocio"])
        return df
    except Exception as e:
        print(f"Error al ejecutar la consulta: {e}")
        return None
    finally:
        if connection:
            cursor.close()
            connection.close()
#Query para Zonas Verdes       
def obtener_zonas_verdes():
    db_config = {
    "dbname": "dataproject",
    "user": "postgres",
    "password": "Welcome01",
    "host": "postgres",
    "port": 5432
    }
    query = """
    SELECT barrio AS distrito, numero_parques AS zonas_verdes
    FROM zonas_verdes
    ORDER BY distrito;
    """
    try:
        connection = psycopg2.connect(**db_config)
        cursor = connection.cursor()
        cursor.execute(query)
        resultados = cursor.fetchall()
        # Convertir los resultados a un DataFrame de pandas
        df = pd.DataFrame(resultados, columns=["distrito", "zonas_verdes"])
        return df
    except Exception as e:
        print(f"Error al ejecutar la consulta: {e}")
        return None
    finally:
        if connection:
            cursor.close()
            connection.close()