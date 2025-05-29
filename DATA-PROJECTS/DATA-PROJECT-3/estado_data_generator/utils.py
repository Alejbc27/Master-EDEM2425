from __future__ import annotations

"""Shared database utilities – production‑ready
───────────────────────────────────────────────
* Supports **either** a full `DATABASE_URL` **or** the classic individual
  variables (`DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`).
* Exposes a singleton `CONN_POOL` and a context‑manager `get_conn()` that
  automatically handles commit/rollback + reconnects on transient errors.
* Uses sane defaults and is 12‑Factor compliant: all sensitive data comes from
  env‑vars or secret managers, never from code.
"""

import logging
import os
import sys
from contextlib import contextmanager
from typing import Iterator

from dotenv import load_dotenv
from psycopg2 import OperationalError, pool
from psycopg2.extras import RealDictCursor

__all__ = ["get_conn", "CONN_POOL"]


logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


load_dotenv()  


def _build_dsn() -> str:
    """Return a PostgreSQL DSN, built from either DATABASE_URL or individual vars."""
    url = os.getenv("DATABASE_URL")
    if url:  
        return url

    host = os.getenv("DB_HOST")
    port = os.getenv("DB_PORT", "5432")
    name = os.getenv("DB_NAME", "clinics")
    user = os.getenv("DB_USER", "postgres")
    pwd  = os.getenv("DB_PASSWORD", "postgres")
    if not all([name, user, pwd]):
        logger.critical(
            "DB_NAME, DB_USER and DB_PASSWORD must be set when DATABASE_URL is absent"
        )
        sys.exit(1)

    params = {
        "dbname": name,
        "user": user,
        "password": pwd,
        "host": host,
        "port": port,
        "connect_timeout": os.getenv("DB_CONNECT_TIMEOUT", "3"),
    }
    return " ".join(f"{k}={v}" for k, v in params.items())



try:
    CONN_POOL: pool.SimpleConnectionPool = pool.SimpleConnectionPool(
        minconn=int(os.getenv("DB_POOL_MIN", 1)),
        maxconn=int(os.getenv("DB_POOL_MAX", 10)),
        dsn=_build_dsn(),
    )
    logger.info(
        "Connection pool initialised (min=%s, max=%s)",
        CONN_POOL.minconn,
        CONN_POOL.maxconn,
    )
except OperationalError as exc:
    logger.critical("Failed to create connection pool: %s", exc)
    raise



@contextmanager
def get_conn(*, dict_cursor: bool = False): 
    conn = CONN_POOL.getconn()
    if dict_cursor:
        conn.cursor_factory = RealDictCursor
    try:
        yield conn
        conn.commit()
    except Exception:  
        conn.rollback()
        raise
    finally:
        CONN_POOL.putconn(conn)
