import os
import json
from google.cloud import firestore, bigquery
from google.api_core.exceptions import NotFound
from flask import Request

# Configuración por variables de entorno
COLLECTION = os.environ.get("FIRESTORE_COLLECTION")
BQ_PROJECT = os.environ.get("BQ_PROJECT")
BQ_DATASET = os.environ.get("BQ_DATASET")
BQ_TABLE   = os.environ.get("BQ_TABLE")

def fetch_from_firestore():
    fs = firestore.Client()
    col = fs.collection(COLLECTION)
    for doc in col.stream():
        data = doc.to_dict()
        data["_doc_id"] = doc.id
        yield data

def ensure_bq_table(bq: bigquery.Client, dataset_id: str, table_id: str):
    ds_ref = bq.dataset(dataset_id)
    try:
        bq.get_dataset(ds_ref)
    except NotFound:
        bq.create_dataset(ds_ref)
    tbl_ref = ds_ref.table(table_id)
    try:
        bq.get_table(tbl_ref)
    except NotFound:
        job = bq.load_table_from_json(
            [{}],
            tbl_ref,
            job_config=bigquery.LoadJobConfig(autodetect=True)
        )
        job.result()
    return tbl_ref

def load_to_bigquery(
    bq: bigquery.Client,
    rows: list,
    table_ref: bigquery.TableReference
):
    job = bq.load_table_from_json(
        rows,
        table_ref,
        job_config=bigquery.LoadJobConfig(
            autodetect=True,
            write_disposition="WRITE_APPEND"
        )
    )
    job.result()

def firestore_to_bq(request: Request):
    """HTTP Cloud Function entrypoint."""
    bq = bigquery.Client(project=BQ_PROJECT)
    table_ref = ensure_bq_table(bq, BQ_DATASET, BQ_TABLE)
    batch = []
    for doc in fetch_from_firestore():
        batch.append(doc)
        if len(batch) >= 500:
            load_to_bigquery(bq, batch, table_ref)
            batch.clear()
    if batch:
        load_to_bigquery(bq, batch, table_ref)
    return ("ETL completada", 200)


def main():
    """
    Ejecución local para pruebas.
    Simula una llamada HTTP sin parámetros.
    """
    class DummyRequest:
        pass  
    response, status = firestore_to_bq(DummyRequest())
    print(f"{status}: {response}")

if __name__ == "__main__":
    main()
