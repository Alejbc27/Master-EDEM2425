from __future__ import annotations

"""data_generator.py – *stand-alone* synthetic dataset builder for Clínica API.

Funciones clave
───────────────
1. `ensure_schema()` crea todas las tablas con **`CREATE TABLE IF NOT EXISTS`**
   para que el script funcione en una base virgen (dev/CI). En producción se
   recomienda Alembic, pero esto deja el entorno listo al instante.
2. Todas las inserciones usan el *pool* compartido `utils.get_conn()`.
3. Incluye un stub `InfermedicaMock` que genera síntomas/enfermedades con IDs
   del estilo oficial (`SYM0001`, `DIS0001`). Cuando se disponga de la API real,
   basta con sustituir esta clase por el SDK oficial que ofrezca métodos
   equivalentes.

Uso rápido
──────────
```bash
export DATABASE_URL=postgresql://postgres:admin@localhost:5432/clinica
python data_generator.py --seed 42         # esquema + datos reproducibles
```
Dentro de Docker Compose puedes añadir un servicio `seed` que ejecute simplemente
`python data_generator.py --seed 42` tras esperar a que Postgres esté *healthy*.
"""

from dataclasses import dataclass
from datetime import datetime, time, timedelta
import argparse
import logging
import os
import random
from typing import List, Sequence, Tuple

from dotenv import load_dotenv
from faker import Faker
from psycopg2.extras import execute_values

from utils import get_conn

# ────────────────────────────────────────────────────────────────────────────
# Config & logging
# ────────────────────────────────────────────────────────────────────────────

load_dotenv()
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("data_gen")

faker = Faker("es_ES")

# ────────────────────────────────────────────────────────────────────────────
# Schema bootstrap (dev / CI only)
# ────────────────────────────────────────────────────────────────────────────

def ensure_schema(cur) -> None:
    """Create tables the first time; idempotent thanks to IF NOT EXISTS."""
    cur.execute(
        """
-- Companies/clinics ---------------------------------------------------------
CREATE TABLE IF NOT EXISTS company (
    company_id   SERIAL PRIMARY KEY,
    legal_name   TEXT NOT NULL,
    tax_id       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS location (
    location_id   SERIAL PRIMARY KEY,
    company_id    INTEGER REFERENCES company(company_id) ON DELETE CASCADE,
    name          TEXT NOT NULL,
    address_line1 TEXT,
    address_line2 TEXT,
    city          TEXT,
    province      TEXT,
    postal_code   TEXT,
    phone         TEXT,
    email         TEXT
);

-- Medical domain -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS specialty (
    specialty_id SERIAL PRIMARY KEY,
    name         TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS physician (
    physician_id   SERIAL PRIMARY KEY,
    first_name     TEXT,
    last_name      TEXT,
    license_number TEXT,
    email          TEXT,
    phone          TEXT,
    specialty_id   INTEGER REFERENCES specialty(specialty_id)
);

CREATE TABLE IF NOT EXISTS physician_location (
    physician_id INTEGER REFERENCES physician(physician_id) ON DELETE CASCADE,
    location_id  INTEGER REFERENCES location(location_id)  ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS working_schedule (
    physician_id INTEGER REFERENCES physician(physician_id) ON DELETE CASCADE,
    location_id  INTEGER REFERENCES location(location_id)  ON DELETE CASCADE,
    weekday      SMALLINT,
    start_time   TIME,
    end_time     TIME
);

-- Infermedica data ---------------------------------------------------------
CREATE TABLE IF NOT EXISTS symptom (
    symptom_id   SERIAL PRIMARY KEY,
    infer_id     TEXT UNIQUE,
    name         TEXT,
    common_name  TEXT,
    category     TEXT,
    last_sync_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS disease (
    disease_id   SERIAL PRIMARY KEY,
    infer_id     TEXT UNIQUE,
    name         TEXT,
    common_name  TEXT,
    severity     TEXT,
    last_sync_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS disease_symptom (
    disease_id  INTEGER REFERENCES disease(disease_id)  ON DELETE CASCADE,
    symptom_id  INTEGER REFERENCES symptom(symptom_id) ON DELETE CASCADE
);

-- Patients & appointments ---------------------------------------------------
CREATE TABLE IF NOT EXISTS patient (
    patient_id  SERIAL PRIMARY KEY,
    first_name  TEXT,
    last_name   TEXT,
    birth_date  DATE,
    sex         TEXT,
    email       TEXT,
    phone       TEXT,
    insurance_number TEXT,
    created_at  TIMESTAMP
);

CREATE TABLE IF NOT EXISTS appointment (
    appointment_id  SERIAL PRIMARY KEY,
    patient_id   INTEGER REFERENCES patient(patient_id)   ON DELETE CASCADE,
    physician_id INTEGER REFERENCES physician(physician_id),
    scheduled_at TIMESTAMP,
    duration_mins SMALLINT,
    status        TEXT,
    motive        TEXT
);

CREATE TABLE IF NOT EXISTS appointment_disease (
    appointment_id INTEGER REFERENCES appointment(appointment_id) ON DELETE CASCADE,
    disease_id     INTEGER REFERENCES disease(disease_id)       ON DELETE CASCADE,
    probability    REAL
);
        """
    )

# ────────────────────────────────────────────────────────────────────────────
# Helpers – realistic IDs & mock Infermedica
# ────────────────────────────────────────────────────────────────────────────

_PROVINCE_CODES = {
    "Madrid": "28",
    "Barcelona": "08",
    "Valencia": "46",
    "Sevilla": "41",
    "Bilbao": "48",
    "Málaga": "29",
    "Alicante": "03",
    "Zaragoza": "50",
    "Murcia": "30",
}

def generate_license(city: str) -> str:
    prov = _PROVINCE_CODES.get(city, "99")
    return f"{prov}/{random.randint(100_0000, 999_9999):07d}"

def generate_nif() -> str:
    num = random.randint(10_000_000, 99_999_999)
    return f"{num}{'TRWAGMYFPDXBNJZSQVHLCKE'[num % 23]}"

@dataclass
class Symptom:
    infer_id: str
    name: str
    common_name: str
    category: str
@dataclass
class Disease:
    infer_id: str
    name: str
    common_name: str
    severity: str

class InfermedicaMock:
    """Tiny in-memory stand-in for Infermedica public API."""
    def __init__(self, *, seed: int | None = None):
        self.fake = Faker("es_ES")
        if seed is not None:
            random.seed(seed)
            self.fake.seed_instance(seed)
    def list_symptoms(self, n: int = 100) -> List[Symptom]:
        cats = ["general", "respiratorio", "digestivo", "neurológico"]
        return [Symptom(f"SYM{i:04d}", self.fake.word().capitalize(), self.fake.word(), random.choice(cats)) for i in range(1, n + 1)]
    def list_diseases(self, n: int = 150) -> List[Disease]:
        sev = ["mild", "moderate", "severe"]
        return [Disease(f"DIS{i:04d}", f"{self.fake.word().capitalize()}itis", self.fake.word(), random.choice(sev)) for i in range(1, n + 1)]

# ────────────────────────────────────────────────────────────────────────────
# DB-insert helpers (bulk friendly)
# ────────────────────────────────────────────────────────────────────────────

def gen_company(cur) -> int:
    cur.execute("INSERT INTO company (legal_name, tax_id) VALUES (%s,%s) RETURNING company_id", (faker.company(), generate_nif()))
    return cur.fetchone()[0]

def gen_locations(cur, company_id: int, n: int = 3) -> List[int]:
    ids: List[int] = []
    for _ in range(n):
        city = faker.city()
        cur.execute(
            """INSERT INTO location (company_id,name,address_line1,address_line2,city,province,postal_code,phone,email)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING location_id""",
            (
                company_id,
                f"{city} Clínica",
                faker.street_address(),
                faker.secondary_address(),
                city,
                faker.state(),
                faker.postcode(),
                faker.phone_number(),
                faker.company_email(),
            ),
        )
        ids.append(cur.fetchone()[0])
    return ids

def gen_specialties(cur) -> List[int]:
    names = ["Cardiología", "Dermatología", "Pediatría", "Neurología", "Psiquiatría", "Oncología", "Ginecología", "Traumatología", "Endocrinología", "Neumología"]
    ids: List[int] = []
    for name in names:
        cur.execute("INSERT INTO specialty (name) VALUES (%s) RETURNING specialty_id", (name,))
        ids.append(cur.fetchone()[0])
    return ids

def gen_physicians(cur, spec_ids: Sequence[int], loc_ids: Sequence[int], n: int = 25) -> List[int]:
    phy_ids: List[int] = []
    links: List[Tuple[int, int]] = []
    for _ in range(n):
        city_for_license = faker.city()
        cur.execute(
            """INSERT INTO physician (first_name,last_name,license_number,email,phone,specialty_id)
                   VALUES (%s,%s,%s,%s,%s,%s) RETURNING physician_id""",
            (
                faker.first_name(),
                faker.last_name(),
                generate_license(city_for_license),
                faker.email(),
                faker.phone_number(),
                random.choice(spec_ids),
            ),
        )
        pid = cur.fetchone()[0]
        phy_ids.append(pid)
        for lid in random.sample(list(loc_ids), random.randint(1, 3)):
            links.append((pid, lid))
    execute_values(cur, "INSERT INTO physician_location (physician_id,location_id) VALUES %s", links)
    return phy_ids

def gen_working_schedule(cur, phy_ids: Sequence[int], loc_ids: Sequence[int]) -> None:
    rows = [
        (pid, lid, weekday, time(9, 0), time(17, 0))
        for pid in phy_ids
        for lid in loc_ids
        for weekday in range(1, 6)  # ISO dow 1-5 → lunes-viernes
    ]
    execute_values(cur, "INSERT INTO working_schedule (physician_id,location_id,weekday,start_time,end_time) VALUES %s", rows)

def gen_symptoms(cur, api: InfermedicaMock) -> List[int]:
    rows = [(s.infer_id, s.name, s.common_name, s.category, datetime.now()) for s in api.list_symptoms()]
    execute_values(cur, "INSERT INTO symptom (infer_id,name,common_name,category,last_sync_at) VALUES %s RETURNING symptom_id", rows)
    return [r[0] for r in cur.fetchall()]

def gen_diseases(cur, api: InfermedicaMock) -> List[int]:
    rows = [(d.infer_id, d.name, d.common_name, d.severity, datetime.now()) for d in api.list_diseases()]
    execute_values(cur, "INSERT INTO disease (infer_id,name,common_name,severity,last_sync_at) VALUES %s RETURNING disease_id", rows)
    return [r[0] for r in cur.fetchall()]

def gen_disease_symptoms(cur, dis_ids: Sequence[int], sym_ids: Sequence[int]) -> None:
    links: List[Tuple[int, int]] = []
    for did in dis_ids:
        for sid in random.sample(list(sym_ids), random.randint(1, 5)):
            links.append((did, sid))
    execute_values(cur, "INSERT INTO disease_symptom (disease_id,symptom_id) VALUES %s", links)

def gen_patients(cur, n: int = 200) -> List[int]:
    rows = [
        (
            faker.first_name(),
            faker.last_name(),
            faker.date_between(start_date="-80y", end_date="-1y"),
            random.choice(["male", "female", "other"]),
            faker.email(),
            faker.phone_number(),
            faker.bothify(text="INS-######"),
            datetime.now(),
        )
        for _ in range(n)
    ]
    execute_values(cur, "INSERT INTO patient (first_name,last_name,birth_date,sex,email,phone,insurance_number,created_at) VALUES %s RETURNING patient_id", rows)
    return [r[0] for r in cur.fetchall()]

def gen_appointments(cur, pat_ids: Sequence[int], phy_ids: Sequence[int], dis_ids: Sequence[int]) -> None:
    apps: List[Tuple[int, int, datetime, int, str, str | None]] = []
    used: set[Tuple[int, datetime]] = set()
    now = datetime.now()
    end = now + timedelta(days=30)
    for pid in pat_ids:
        phy = random.choice(list(phy_ids))
        while True:
            dt = faker.date_time_between_dates(datetime_start=now, datetime_end=end)
            dt = dt.replace(minute=(dt.minute // 30) * 30, second=0, microsecond=0)
            if (phy, dt) not in used:
                used.add((phy, dt))
                break
        apps.append((pid, phy, dt, 30, "confirmed", None))
    execute_values(cur, "INSERT INTO appointment (patient_id,physician_id,scheduled_at,duration_mins,status,motive) VALUES %s RETURNING appointment_id", apps)
    app_ids = [r[0] for r in cur.fetchall()]
    links: List[Tuple[int, int, float]] = []
    for aid in app_ids:
        for did in random.sample(list(dis_ids), random.randint(0, 3)):
            links.append((aid, did, round(random.random(), 3)))
    if links:
        execute_values(cur, "INSERT INTO appointment_disease (appointment_id,disease_id,probability) VALUES %s", links)

# ────────────────────────────────────────────────────────────────────────────
# Main entrypoint
# ────────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic clinic data (schema + seed)")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility")
    parser.add_argument("--infermedica", choices=["mock", "none"], default="mock", help="Data source for symptoms/diseases (default: mock)")
    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)
        faker.seed_instance(args.seed)

    api = InfermedicaMock(seed=args.seed) if args.infermedica == "mock" else None

    logger.info("▶️  Generating data (%s mode)…", args.infermedica)

    with get_conn() as conn, conn.cursor() as cur:
        ensure_schema(cur)
        comp_id = gen_company(cur)
        loc_ids = gen_locations(cur, comp_id)
        spec_ids = gen_specialties(cur)
        phy_ids = gen_physicians(cur, spec_ids, loc_ids)
        gen_working_schedule(cur, phy_ids, loc_ids)
        if api is None:
            logger.warning("--infermedica none → fallback to internal mock")
            api = InfermedicaMock(seed=args.seed)
        sym_ids = gen_symptoms(cur, api)
        dis_ids = gen_diseases(cur, api)
        gen_disease_symptoms(cur, dis_ids, sym_ids)
        pat_ids = gen_patients(cur)
        gen_appointments(cur, pat_ids, phy_ids, dis_ids)

    logger.info("✅ Database ready: schema created & %s records inserted", len(pat_ids))

if __name__ == "__main__":
    main()
