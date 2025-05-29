import os
import sys
from google.cloud import storage

def upload_to_gcs(bucket_name, source_folder):
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)

    for filename in os.listdir(source_folder):
        local_path = os.path.join(source_folder, filename)

        if os.path.isfile(local_path):
            blob_name = f"articles/{filename}"
            blob = bucket.blob(blob_name)

            try:
                blob.upload_from_filename(local_path)
                print(f"Archivo {filename} subido a {bucket_name}/{blob_name}.")
            except Exception as e:
                print(f"Error al subir {filename}: {e}")
        else:
            print(f"Omitiendo {filename} ya que no es un archivo.")

if __name__ == "__main__":
    BUCKET_NAME = os.getenv("BUCKET_NAME")
    SOURCE_FOLDER_PATH = os.getenv("SOURCE_FOLDER_PATH")

    if not BUCKET_NAME or not SOURCE_FOLDER_PATH:
        print("Error: Las variables de entorno BUCKET_NAME y SOURCE_FOLDER_PATH deben estar definidas.")
        sys.exit(1)

    if not os.path.isdir(SOURCE_FOLDER_PATH):
        print(f"Error: La carpeta de origen '{SOURCE_FOLDER_PATH}' no existe.")
        sys.exit(1)

    upload_to_gcs(BUCKET_NAME, SOURCE_FOLDER_PATH)
