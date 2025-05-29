import json
import psycopg2

db_config = {
    "dbname": "dataproject",
    "user": "postgres",
    "password": "Welcome01",
    "host": "postgres",
    "port": 5432
}

def extraer_top3_poligonos_sql(nombres_distritos):
    connection = psycopg2.connect(**db_config)
    
    try:
        with connection.cursor() as cursor:
            # Crear una consulta dinámica para filtrar por nombres de distritos
            query = """
            SELECT geo_shape 
            FROM distritos 
            WHERE nombre_corregido = ANY(%s)
            """
            cursor.execute(query, (nombres_distritos,))
                
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