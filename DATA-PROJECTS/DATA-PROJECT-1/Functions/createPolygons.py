import json
import psycopg2


db_config = {
    "dbname": "dataproject",
    "user": "postgres",
    "password": "Welcome01",
    "host": "postgres",
    "port": 5432
}

def extraer_poligonos_sql():
    connection = psycopg2.connect(**db_config)
    
    try:
        with connection.cursor() as cursor:
            query = "SELECT geo_shape FROM distritos"
            cursor.execute(query)
                
            # Crear una lista solo con los polígonos
            polygons = []
            for row in cursor.fetchall():
                geo_shape = row[0]
                # Parsear el campo geo_shape desde JSON
                geo_shape_dict = json.loads(geo_shape)
                # Extraer coordenadas y añadirlas a la lista de polígonos
                coordenadas = geo_shape_dict["coordinates"]
                polygons.extend(coordenadas)  # Agrega directamente cada sublista de coordenadas
            
            return polygons
    finally:
        connection.close()