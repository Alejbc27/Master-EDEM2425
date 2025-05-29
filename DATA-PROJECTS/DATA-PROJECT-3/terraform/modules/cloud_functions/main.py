"""
Robust ETL Cloud Function (Python 3.10)
Postgres + Firestore → BigQuery

Fixes / hardening applied
-------------------------
1. Environment‑variable validation for every required var.
2. Avoid duplicate Cloud Logging handlers on warm starts.
3. Server‑side cursor for large patient tables (streaming batches).
4. Batch Firestore get_all() (≤500 docs) instead of N + 1 calls.
5. Sanitisation of REPEATED fields (None→[]).
6. Safe parsing of legacy JSON strings (evidencia, diagnostico).
7. birth_date coercion (DATE/TIMESTAMP).
8. Chunked upload to BigQuery (default 5000 rows). Handles >100 MB limits.
9. Optional per‑upload retries with exponential back‑off.
10. Configurable chunk size via env var BQ_INSERT_CHUNK.
11. Optional automatic table creation with explicit schema.

Deploy
------
gcloud functions deploy firestore-sql-to-bq-etl \
   --runtime python310 \
   --trigger-http --allow-unauthenticated \
   --entry-point firestore_sql_to_bq

"""

from __future__ import annotations

import json
import logging
import os
import time
from contextlib import contextmanager
from datetime import date, datetime
from typing import Any, Dict, Iterable, List, Sequence

import functions_framework
from flask import Request
from google.cloud import bigquery, firestore, logging as cloud_logging
from google.cloud.logging_v2.handlers import CloudLoggingHandler
from google.api_core import retry, exceptions as g_exceptions

# ---------------------------------------------------------------------------
# Helpers -------------------------------------------------------------------
# ---------------------------------------------------------------------------

@contextmanager
def get_cursor(batch_size: int = 1000):
    """Yield a server‑side cursor against Postgres using settings from utils.get_conn."""
    from utils import get_conn  # local util

    with get_conn() as conn:
        with conn.cursor(name="patient_cursor") as cur:
            cur.itersize = batch_size
            yield cur


def create_logger() -> logging.Logger:
    logger = logging.getLogger("firestore_sql_to_bq")
    logger.setLevel(logging.INFO)

    # Avoid duplicate handlers on warm starts
    if not any(isinstance(h, CloudLoggingHandler) for h in logger.handlers):
        logger.addHandler(CloudLoggingHandler())
    return logger


def require_env(var: str) -> str:
    value = os.getenv(var)
    if not value:
        raise RuntimeError(f"Missing required env var {var}")
    return value


# ---------------------------------------------------------------------------
# Configuration --------------------------------------------------------------
# ---------------------------------------------------------------------------

BQ_PROJECT = require_env("BQ_PROJECT")
BQ_DATASET = require_env("BQ_DATASET")
BQ_TABLE = require_env("BQ_TABLE")
FIRESTORE_COLLECTION = require_env("FIRESTORE_COLLECTION")
CHUNK_SIZE = int(os.getenv("BQ_INSERT_CHUNK", "5000"))

# Explicit BigQuery schema (unchanged)
BQ_SCHEMA = [
    bigquery.SchemaField("patient_id", "INT64"),
    bigquery.SchemaField("first_name", "STRING"),
    bigquery.SchemaField("last_name", "STRING"),
    bigquery.SchemaField("birth_date", "DATE"),
    bigquery.SchemaField("sex", "STRING"),
    bigquery.SchemaField(
        "mensajes",
        "RECORD",
        mode="REPEATED",
        fields=[
            bigquery.SchemaField("sender", "STRING"),
            bigquery.SchemaField("message", "STRING"),
        ],
    ),
    bigquery.SchemaField(
        "evidencia",
        "RECORD",
        mode="REPEATED",
        fields=[
            bigquery.SchemaField("id", "STRING"),
            bigquery.SchemaField("name", "STRING"),
            bigquery.SchemaField("choice_id", "STRING"),
            bigquery.SchemaField("probabilidad", "FLOAT64"),
        ],
    ),
    bigquery.SchemaField(
        "condiciones",
        "RECORD",
        mode="REPEATED",
        fields=[
            bigquery.SchemaField("id", "STRING"),
            bigquery.SchemaField("name", "STRING"),
            bigquery.SchemaField("probabilidad", "FLOAT64"),
        ],
    ),
    bigquery.SchemaField("pregunta_actual", "STRING", mode="REPEATED"),
    bigquery.SchemaField("lista_preguntas", "JSON"),
    bigquery.SchemaField(
        "diagnostico",
        "RECORD",
        fields=[
            bigquery.SchemaField("id", "STRING"),
            bigquery.SchemaField("name", "STRING"),
            bigquery.SchemaField("confidence", "FLOAT64"),
            bigquery.SchemaField("recomendacion", "STRING"),
        ],
    ),
    bigquery.SchemaField("should_stop", "BOOL"),
    bigquery.SchemaField("urgencia", "STRING"),
    bigquery.SchemaField("respuesta_usuario", "STRING"),
    bigquery.SchemaField("pasos", "INT64"),
    bigquery.SchemaField("input_valido", "BOOL"),
    bigquery.SchemaField("informe", "STRING"),
]


# ---------------------------------------------------------------------------
# Initial clients (re‑used between cold/warm starts) -------------------------
# ---------------------------------------------------------------------------

LOGGER = create_logger()
FIRESTORE_CLIENT = firestore.Client()
BQ_CLIENT = bigquery.Client()


# ---------------------------------------------------------------------------
# Core logic -----------------------------------------------------------------
# ---------------------------------------------------------------------------

def _coerce_date(value: Any) -> str | None:
    """Convert Python date/datetime/str→ISO YYYY‑MM‑DD or return None."""
    if value is None:
        return None
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, datetime):
        return value.date().isoformat()
    return str(value)


def _parse_legacy_list(raw_list: Any) -> List[Any]:
    """If legacy list of JSON‑strings, parse each element; else return as is."""
    if raw_list and isinstance(raw_list, list) and isinstance(raw_list[0], str):
        try:
            return [json.loads(e) for e in raw_list]
        except json.JSONDecodeError as err:
            LOGGER.error("JSON parse error (list) – keeping raw: %s", err)
            return raw_list
    return raw_list or []


def _parse_legacy_obj(raw_obj: Any) -> Dict[str, Any] | None:
    """If legacy string JSON, parse; else return as is."""
    if raw_obj and isinstance(raw_obj, str):
        try:
            return json.loads(raw_obj)
        except json.JSONDecodeError as err:
            LOGGER.error("JSON parse error (obj) – returning None: %s", err)
            return None
    return raw_obj


def sanitise_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """Guarantee REPEATED fields are lists, handle None values."""
    for fld in ("mensajes", "evidencia", "condiciones", "pregunta_actual"):
        row[fld] = row.get(fld) or []
    return row


def iter_patient_records(batch: int = 1000) -> Iterable[Sequence[Any]]:
    """Yield (patient_id, first_name, ...) batches from Postgres."""
    with get_cursor(batch_size=batch) as cur:
        cur.execute(
            """
            SELECT patient_id, first_name, last_name, birth_date, sex
            FROM patient
            """
        )
        while True:
            recs = cur.fetchmany(batch)
            if not recs:
                break
            for rec in recs:
                yield rec


@retry.Retry(predicate=retry.if_transient_error, deadline=120)
def _load_chunk_to_bq(rows: List[Dict[str, Any]], table_ref: str, job_config: bigquery.LoadJobConfig):
    """Wrapper with automatic retry for transient BigQuery errors."""
    job = BQ_CLIENT.load_table_from_json(rows, table_ref, job_config=job_config)
    job.result()


def load_rows_to_bigquery(rows: List[Dict[str, Any]], table_ref: str):
    if not rows:
        return

    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        schema=BQ_SCHEMA,
    )

    for i in range(0, len(rows), CHUNK_SIZE):
        chunk = rows[i : i + CHUNK_SIZE]
        _load_chunk_to_bq(chunk, table_ref, job_config)
        LOGGER.info("Uploaded rows %s–%s (%s) to %s", i, i + len(chunk) - 1, len(chunk), table_ref)


def fetch_firestore_states(pids: List[int]) -> Dict[int, Dict[str, Any]]:
    """Batch‑fetch Firestore docs → dict keyed by patient_id (int)."""
    result: Dict[int, Dict[str, Any]] = {}

    # Firestore batch limit = 500 reads
    for i in range(0, len(pids), 500):
        slice_ids = pids[i : i + 500]
        doc_refs = [FIRESTORE_CLIENT.collection(FIRESTORE_COLLECTION).document(str(pid)) for pid in slice_ids]
        docs = FIRESTORE_CLIENT.get_all(doc_refs)
        for doc in docs:
            if doc.exists:
                result[int(doc.id)] = doc.to_dict()
            else:
                LOGGER.warning("No Firestore doc for patient_id=%s", doc.id)
    return result


# ---------------------------------------------------------------------------
# Cloud Function entry‑point --------------------------------------------------
# ---------------------------------------------------------------------------

@functions_framework.http
def firestore_sql_to_bq(request: Request):
    start_ts = time.time()
    try:
        LOGGER.info("ETL started")

        # 1️⃣  Extract identities from Postgres -----------------------------
        patient_ids: List[int] = []
        for rec in iter_patient_records():
            patient_ids.append(rec[0])
        LOGGER.info("Fetched %s patient_id(s) from Postgres", len(patient_ids))

        # 2️⃣  Batch fetch Firestore docs -----------------------------------
        fs_states = fetch_firestore_states(patient_ids)

        # 3️⃣  Combine Postgres + Firestore → rows --------------------------
        rows: List[Dict[str, Any]] = []
        for pid, first_name, last_name, birth_date, sex in iter_patient_records():
            data = fs_states.get(pid)
            if not data:
                continue  # ya se avisó en fetch_firestore_states

            # Parse legacy fields ------------------
            evidencia = _parse_legacy_list(data.get("evidencia", []))
            diagnostico = _parse_legacy_obj(data.get("diagnostico"))

            row = sanitise_row(
                {
                    "patient_id": pid,
                    "first_name": first_name,
                    "last_name": last_name,
                    "birth_date": _coerce_date(birth_date),
                    "sex": sex,
                    "mensajes": data.get("mensajes"),
                    "evidencia": evidencia,
                    "condiciones": data.get("condiciones"),
                    "pregunta_actual": data.get("pregunta_actual"),
                    "lista_preguntas": data.get("lista_preguntas"),
                    "diagnostico": diagnostico,
                    "should_stop": data.get("should_stop"),
                    "urgencia": data.get("urgencia"),
                    "respuesta_usuario": data.get("respuesta_usuario"),
                    "pasos": data.get("pasos"),
                    "input_valido": data.get("input_valido"),
                    "informe": data.get("informe"),
                }
            )
            rows.append(row)

        LOGGER.info("Prepared %s rows for BigQuery", len(rows))

        # 4️⃣  Load into BigQuery (chunked) ----------------------------------
        table_ref = f"{BQ_PROJECT}.{BQ_DATASET}.{BQ_TABLE}"
        load_rows_to_bigquery(rows, table_ref)

        elapsed = time.time() - start_ts
        LOGGER.info("ETL completed in %.1fs", elapsed)
        return ("ETL completed successfully", 200)

    except g_exceptions.BadRequest as err:
        # BigQuery schema mismatch etc.
        LOGGER.exception("BadRequest from BigQuery: %s", err)
        return (f"ETL failed: {err}", 400)
    except Exception as err:  # pylint: disable=broad-except
        LOGGER.exception("ETL failed: %s", err)
        return (f"ETL failed: {err}", 500)
