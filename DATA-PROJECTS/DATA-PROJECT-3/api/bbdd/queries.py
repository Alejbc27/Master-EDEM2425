# queries.py – SQL statements for Clínica API
# -----------------------------------------------
# Define la duración fija de cada hueco (en minutos)
SLOT_MINUTES: int = 30

# 1) SQL para buscar huecos (generación de series + filtros opcionales)
#    Usa f-string solo para SLOT_MINUTES, escapando llaves para filtros dinámicos
FIND_SLOTS_SQL: str = f"""
WITH base AS (
    SELECT
        ws.physician_id,
        ws.location_id,
        generate_series(
            date_trunc('day', %(dfrom)s) + (ws.weekday-1) * interval '1 day' + ws.start_time,
            date_trunc('day', %(dto)s)   + (ws.weekday-1) * interval '1 day' + ws.end_time - interval '{SLOT_MINUTES} minutes',
            interval '{SLOT_MINUTES} minutes'
        ) AS slot_at
    FROM working_schedule ws
    WHERE
      date_trunc('day', %(dfrom)s) + (ws.weekday-1) * interval '1 day'
        BETWEEN date_trunc('day', %(dfrom)s) AND date_trunc('day', %(dto)s)
),
avail AS (
    SELECT
        base.physician_id,
        base.location_id,
        base.slot_at
    FROM base
    JOIN physician p           ON p.physician_id      = base.physician_id
    JOIN physician_location pl ON pl.physician_id     = p.physician_id
    JOIN location loc          ON loc.location_id     = pl.location_id
    JOIN specialty sp          ON sp.specialty_id     = p.specialty_id
    WHERE base.slot_at BETWEEN %(dfrom)s AND %(dto)s
      {{city}} {{loc}} {{spec}} {{phy}} {{clinic}}
      AND NOT EXISTS (
          SELECT 1 FROM appointment a
           WHERE a.physician_id = base.physician_id
             AND a.scheduled_at = base.slot_at
             AND a.status <> 'cancelled'
      )
)
SELECT *
  FROM avail
ORDER BY physician_id, slot_at;
"""

# 2) SQL para verificar disponibilidad y reservar cita
AVAIL_APPOINTMENT_SQL: str = """
SELECT
  NOT EXISTS (
    SELECT 1 FROM appointment
     WHERE physician_id = %(phy)s
       AND scheduled_at = %(dt)s::timestamp
       AND status <> 'cancelled'
  )
  AND EXISTS (
    SELECT 1 FROM working_schedule ws
     WHERE ws.physician_id = %(phy)s
       AND ws.weekday = EXTRACT(ISODOW FROM %(dt)s::timestamp)::int
       AND (%(dt)s::timestamp)::time
           BETWEEN ws.start_time
               AND ws.end_time - INTERVAL '30 minutes'
  );
"""