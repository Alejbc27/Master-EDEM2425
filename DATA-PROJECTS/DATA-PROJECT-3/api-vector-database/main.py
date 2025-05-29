from flask import Flask, request, jsonify
import os
import logging
import json
from dotenv import load_dotenv
from langchain_postgres.vectorstores import PGVector
from langchain_core.documents import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from google.cloud import storage

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)


def create_vector_store(collection_name):

    embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")

    vector_store = PGVector(
        connection=os.getenv("PG_CONNECTION_STRING"),
        collection_name=collection_name,
        embeddings=embeddings,
    )
    return vector_store


@app.route("/search", methods=["POST"])
def search_with_filter():
    logger.info("POST /search")
    logger.info(f"body: {request.json}")

    try:
        data = request.json
        collection_name = data.get("collection_name")
        query_text = data.get("query")
        limit = data.get("limit", 5)

        if not collection_name or not query_text:
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": "Los parámetros collection_name y query son obligatorios",
                    }
                ),
                400,
            )

        vector_store = create_vector_store(collection_name)

        docs = vector_store.similarity_search_with_relevance_scores(
            query=query_text,
            k=limit,
        )

        results = []
        for doc, score in docs:
            result = {
                "relevance_score": score,
                "metadata": doc.metadata,
                "content": doc.page_content,
            }
            results.append(result)

        return jsonify({"status": "success", "query": query_text, "results": results})

    except Exception as error:
        logger.error(f"Error durante la búsqueda: {error}")
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "Ocurrió un error durante la búsqueda.",
                    "details": str(error),
                }
            ),
            500,
        )


@app.route("/create-collection", methods=["POST"])
def create_collection():
    logger.info("POST /create-table")
    logger.info(f"body: {request.json}")

    try:
        data = request.get_json()
        collection_name = data.get("collection_name")

        if not collection_name:
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": "El parámetro collection_name es obligatorio",
                    }
                ),
                400,
            )

        vector_store = create_vector_store(collection_name)

        vector_store.create_collection()

        logger.info(f"Colección {collection_name} creada exitosamente")

        return jsonify(
            {
                "status": "success",
                "message": f"Colección {collection_name} creada exitosamente",
            }
        )

    except Exception as error:
        logger.error(f"Error al crear la colección: {error}")
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "Ocurrió un error al crear la colección.",
                    "details": str(error),
                }
            ),
            500,
        )


@app.route("/upload-data", methods=["POST"])
def upload_data():
    logger.info("POST /upload-data")
    logger.info(f"body: {request.json}")

    try:
        data = request.json
        collection_name = data.get("collection_name")
        gcs_bucket_name = os.getenv("GCS_BUCKET_NAME", "medical_articles")
        gcs_prefix = os.getenv("GCS_PREFIX", "articles/")

        if not collection_name:
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": "El parámetro collection_name es obligatorio",
                    }
                ),
                400,
            )

        vector_store = create_vector_store(collection_name)
        storage_client = storage.Client()
        bucket = storage_client.bucket(gcs_bucket_name)

        blobs = list(bucket.list_blobs(prefix=gcs_prefix))
        json_files_blobs = [
            blob
            for blob in blobs
            if blob.name.endswith(".json") and blob.name != gcs_prefix
        ]

        logger.info(f"Encontrados {len(json_files_blobs)} archivos JSON en GCS")

        batch_size = 100
        total_processed = 0

        for i in range(0, len(json_files_blobs), batch_size):
            batch_blobs = json_files_blobs[i : i + batch_size]
            documents = []

            for blob in batch_blobs:
                try:
                    json_content_string = blob.download_as_text(encoding="utf-8")
                    article_data = json.loads(json_content_string)

                    file_name_with_prefix = blob.name
                    relative_file_name = (
                        file_name_with_prefix[len(gcs_prefix) :]
                        if file_name_with_prefix.startswith(gcs_prefix)
                        else file_name_with_prefix
                    )
                    title = os.path.splitext(relative_file_name)[0]

                    if isinstance(article_data, dict):
                        content = json.dumps(article_data, ensure_ascii=False)
                        metadata = {
                            "title": title,
                            "file_name": relative_file_name,
                            "gcs_path": f"gs://{gcs_bucket_name}/{blob.name}",
                        }

                        if "category" in article_data:
                            metadata["category"] = article_data["category"]
                    else:
                        content = str(article_data)
                        metadata = {
                            "title": title,
                            "file_name": relative_file_name,
                            "gcs_path": f"gs://{gcs_bucket_name}/{blob.name}",
                        }

                    document = Document(page_content=content, metadata=metadata)
                    documents.append(document)

                    logger.info(f"Procesado: {relative_file_name}")

                except Exception as e:
                    logger.error(f"Error procesando {blob.name}: {e}")

            if documents:
                vector_store.add_documents(documents)
                total_processed += len(documents)
                logger.info(f"Lote de {len(documents)} documentos procesado")

        return jsonify(
            {
                "status": "success",
                "message": f"Datos cargados exitosamente.{total_processed} documentos procesados.",
            }
        )

    except Exception as error:
        logger.error(f"Error al cargar datos: {error}")
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "Ocurrió un error al cargar los datos.",
                    "details": str(error),
                }
            ),
            500,
        )


@app.route("/delete-collection", methods=["POST"])
def delete_collection():
    logger.info("POST /delete-table")
    logger.info(f"body: {request.json}")

    try:
        data = request.get_json()
        collection_name = data.get("collection_name")

        if not collection_name:
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": "El parámetro collection_name es obligatorio",
                    }
                ),
                400,
            )

        vector_store = create_vector_store(collection_name)

        vector_store.delete_collection()

        logger.info(f"Colección {collection_name} borrada exitosamente")

        return jsonify(
            {
                "status": "success",
                "message": f"Colección {collection_name} borrada exitosamente",
            }
        )

    except Exception as error:
        logger.error(f"Error al crear la colección: {error}")
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "Ocurrió un error al crear la colección.",
                    "details": str(error),
                }
            ),
            500,
        )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
