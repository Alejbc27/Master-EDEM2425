from __future__ import annotations

"""Flask API – Clínica (JSON-first, fixed filters)

Endpoints:
• POST /availability – devuelve huecos libres vía JSON
• POST /appointments – confirma cita (same JSON schema)

"""

import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Tuple

import psycopg2.extensions
from dateutil.parser import isoparse
from flask import Flask, jsonify, request
from zoneinfo import ZoneInfo


from email_service import schedule_reminder, send_confirmation
from queries import FIND_SLOTS_SQL, AVAIL_APPOINTMENT_SQL
from utils import get_conn

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


def _build_filters(ctx: Dict[str, Any]) -> Dict[str, str]:
    """Devuelve mapeo para `format(**)` en la SQL de filtros opcionales."""
    return {
        "city":   "AND loc.city = %(city)s"                if ctx.get("city")        else "",
        "loc":    "AND ws.location_id = %(location_id)s"   if ctx.get("location_id") else "",
        "spec":   "AND sp.specialty_id = %(specialty_id)s" if ctx.get("specialty_id") else "",
        "phy":    "AND p.physician_id = %(physician_id)s"  if ctx.get("physician_id") else "",
        "clinic": "AND loc.name ILIKE %(clinic_name)s"     if ctx.get("clinic_name") else "",
    }


def _find_free_slots(*, date_from: datetime, date_to: datetime, **ctx) -> List[Dict[str, Any]]:
    """Consulta huecos libres entre dos fechas, con filtros en ctx."""
    params: Dict[str, Any] = {"dfrom": date_from, "dto": date_to, **ctx}
    sql = FIND_SLOTS_SQL.format(**_build_filters(ctx))

    with get_conn(dict_cursor=True) as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()

    slots: List[Dict[str, Any]] = []
    for r in rows:
        start = r.get("slot_at") if isinstance(r, dict) else r[2]

        # ————————————— Convertir UTC → Europe/Madrid —————————————
        if isinstance(start, datetime):
            # si viene naive lo tratamos como UTC
            if start.tzinfo is None:
                start = start.replace(tzinfo=ZoneInfo("UTC"))
            # lo pasamos a hora local de Madrid
            start = start.astimezone(ZoneInfo("Europe/Madrid"))
            ts = start.isoformat()
        else:
            ts = start
        # ——————————————————————————————————————————————————————————

        phy = r.get("physician_id") if isinstance(r, dict) else r[0]
        loc = r.get("location_id")    if isinstance(r, dict) else r[1]

        slots.append({
            "slot_id":      f"{phy}|{ts}",
            "starts_at":    ts,
            "physician_id": phy,
            "location_id":  loc,
        })
    return slots

app = Flask(__name__)

@app.post("/availability/")
def api_availability():
    payload = request.get_json(force=True, silent=True) or {}
    ctx = payload.get("context", {})
    slot = payload.get("slot", {})

    try:
        date_from = isoparse(slot["from"])
        date_to   = isoparse(slot["to"])
    except (KeyError, ValueError):
        return {"error": "slot.from y slot.to ISO-8601 requeridos"}, 400

    availability = _find_free_slots(date_from=date_from, date_to=date_to, **ctx)
    return jsonify({"availability": availability})

@app.post("/appointments/")
def api_create_appointment():
    data = request.get_json(force=True, silent=True) or {}

    # Retro-compatibilidad
    if "patient_id" in data:
        data = {"patient": {"id": data.pop("patient_id")},
                "slot": {"physician_id": data.pop("physician_id"),
                         "starts_at":    data.pop("scheduled_at")}}

    patient = data.get("patient", {})
    slot    = data.get("slot", {})
    if not patient.get("id"):
        return {"error": "patient.id requerido"}, 400

    if "slot_id" in slot:
        try:
            phy, ts = slot["slot_id"].split("|", 1)
            slot["physician_id"] = int(phy)
            slot["starts_at"]    = ts
        except ValueError:
            return {"error": "slot_id no válido"}, 400

    try:
        physician_id = int(slot["physician_id"])
        starts_at    = isoparse(slot["starts_at"])
    except (KeyError, ValueError):
        return {"error": "slot.physician_id y slot.starts_at requeridos"}, 400

    # 1) Chequeo de disponibilidad → usa cursor clásico (no dict)
    with get_conn() as conn, \
         conn.cursor(cursor_factory=psycopg2.extensions.cursor) as cur:
        cur.execute(AVAIL_APPOINTMENT_SQL, {"phy": physician_id, "dt": starts_at})
        row = cur.fetchone()
        available = row[0] if isinstance(row, tuple) else list(row.values())[0]

    if not available:
        return {"error": "Ese hueco ya no está disponible"}, 409

    # 2) Insertar cita + recuperar ID
    with get_conn() as conn, \
     conn.cursor(cursor_factory=psycopg2.extensions.cursor) as cur:
        cur.execute(
        """
        INSERT INTO appointment (
            patient_id,
            physician_id,
            scheduled_at,
            status
        )
        VALUES (%s, %s, %s, 'confirmed')
        RETURNING appointment_id
        """,
        (patient["id"], physician_id, starts_at),
    )
        appt_id = cur.fetchone()[0]

    # 3) Emails y recordatorio
    with get_conn(dict_cursor=True) as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT p.email AS patient_email,
                   p.first_name || ' ' || p.last_name AS patient_name,
                   dr.first_name  || ' ' || dr.last_name AS doctor_name,
                   loc.name AS clinic_name
              FROM patient p
              JOIN physician dr            ON dr.physician_id = %s
              JOIN physician_location pl   ON pl.physician_id = dr.physician_id
              JOIN location loc            ON loc.location_id = pl.location_id
             WHERE p.patient_id = %s
             LIMIT 1
            """,
            (physician_id, patient["id"]),
        )
        info = cur.fetchone()

    if info and info.get("patient_email"):
        send_confirmation(
            patient_email=info["patient_email"],
            patient_name= info["patient_name"],
            doctor=       info["doctor_name"],
            clinic=       info["clinic_name"],
            when=         starts_at,
        )
        schedule_reminder(
            patient_email=info["patient_email"],
            patient_name= info["patient_name"],
            doctor=       info["doctor_name"],
            clinic=       info["clinic_name"],
            when=         starts_at,
        )

    return ({"appointment_id": appt_id,
             "slot": {"starts_at": starts_at.isoformat(), "physician_id": physician_id},
             "status": "confirmed"},
            201)


def _env_bool(key: str, default: str = "false") -> bool:
    return os.getenv(key, default).lower() in {"true", "1", "yes"}

if __name__ == "__main__":
    debug = _env_bool("FLASK_DEBUG")
    port = int(os.getenv("PORT", 5000))
    app.run(debug=debug, host="0.0.0.0", port=port)
