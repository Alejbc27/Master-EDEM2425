import json
import psycopg2


db_config = {
    "dbname": "dataproject",
    "user": "postgres",
    "password": "Welcome01",
    "host": "postgres",
    "port": 5432
}

def extraer_barrios_sql():
    connection = psycopg2.connect(**db_config)
    
    try:
        with connection.cursor() as cursor:
            query = "SELECT nombre_corregido, geo_shape FROM distritos"
            cursor.execute(query)
                
            barrios_lista = []
            for row in cursor.fetchall():
                nombre, geo_shape = row
                # Parsear el campo geo_shape desde JSON
                geo_shape_dict = json.loads(geo_shape)
                coordenadas = geo_shape_dict["coordinates"]
                barrios_lista.append({"nombre": nombre, "coordenadas": coordenadas})
                    
            return barrios_lista
    finally:
        connection.close()
