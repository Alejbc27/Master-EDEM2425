from __future__ import annotations

"""email_service – producción
──────────────────────────────
Envío de correos de confirmación y recordatorio mediante **Gmail API** o
**backend alternativo** de consola para desarrollo/CI.

Ventajas respecto a la versión anterior
--------------------------------------
* Carga perezosa y *thread‑safe* del servicio Gmail (singleton).
* Backend configurable vía `EMAIL_BACKEND` → `gmail` | `console`.
* Manejo explícito de *retries* y errores de red (exponential back‑off).
* Planificador APScheduler iniciado solo si se solicita `schedule_reminder`.
* Plantillas internacionales centralizadas y preparados para HTML.
"""


import base64
import datetime as dt
import logging
import os
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Final, Literal

from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.exceptions import RefreshError
from google_auth_oauthlib.flow import InstalledAppFlow


load_dotenv()
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

SCOPES: Final[list[str]] = ["https://www.googleapis.com/auth/gmail.send"]
BACKOFF_INITIAL = 2  # seconds
BACKOFF_MAX = 60     # seconds

TOKEN_FILE = Path(os.getenv("GOOGLE_TOKEN_FILE", "token.json"))
CLIENT_FILE = Path(os.getenv("GOOGLE_CLIENT_SECRET", "client_secret.json"))
EMAIL_FROM = os.getenv("EMAIL_FROM", "Clinica DataProject3 <noreply@example.com>")
EMAIL_BACKEND: Literal["gmail", "console"] = os.getenv("EMAIL_BACKEND", "gmail").lower()  # type: ignore

_service = None  # Gmail service singleton
_scheduler: BackgroundScheduler | None = None


def _build_gmail_service():
    """Create a Gmail API service, refreshing / generating token if required."""
    creds: Credentials | None = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        try:
            if creds and creds.expired and creds.refresh_token:
                logger.info("Refreshing Gmail token…")
                creds.refresh(Request())
            else:
                if not CLIENT_FILE.exists():
                    raise FileNotFoundError(
                        "Falta GOOGLE_CLIENT_SECRET / client_secret.json – ejecute `python email_service.py --setup` primero",
                    )
                flow = InstalledAppFlow.from_client_secrets_file(
                    CLIENT_FILE,
                    SCOPES,
                    redirect_uri="urn:ietf:wg:oauth:2.0:oob",
                )
                auth_url, _ = flow.authorization_url(
                    access_type="offline",
                    include_granted_scopes="true",
                    prompt="select_account consent",
                )
                print("\nAbra la siguiente URL en su navegador y autorice la cuenta de Gmail:\n")
                print(auth_url, "\n")
                code = input("Pega aquí el código de verificación y pulsa Enter: ")
                flow.fetch_token(code=code)
                creds = flow.credentials
        except RefreshError as exc:
            logger.error("No se pudo refrescar el token de Gmail: %s", exc)
            TOKEN_FILE.unlink(missing_ok=True)
            sys.exit(1)

        # Guardar/actualizar token
        TOKEN_FILE.write_text(creds.to_json())

    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def _get_service():
    """Thread‑safe singleton getter for Gmail service."""
    global _service
    if EMAIL_BACKEND == "console":
        return None  # consola no necesita servicio
    if _service is None:
        _service = _build_gmail_service()
    return _service



def _create_message(to: str, subject: str, body: str) -> dict:
    """Return a Gmail API message object (Base64 URL‑safe)."""
    msg = MIMEMultipart("alternative")
    msg["To"] = to
    msg["From"] = EMAIL_FROM
    msg["Subject"] = subject
    # Texto plano
    msg.attach(MIMEText(body, "plain", "utf-8"))
    # (Opcional) HTML – de momento replicamos el texto
    msg.attach(MIMEText(body.replace("\n", "<br>"), "html", "utf-8"))
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    return {"raw": raw}


def _send_via_gmail(to: str, subject: str, body: str) -> None:
    service = _get_service()
    if service is None:
        logger.warning("EMAIL_BACKEND=console → no se envía realmente el correo")
        logger.info("[Console email] to=%s | subject=%s\n%s", to, subject, body)
        return

    message = _create_message(to, subject, body)
    backoff = BACKOFF_INITIAL
    while True:
        try:
            service.users().messages().send(userId="me", body=message).execute()
            logger.info("Email enviado a %s", to)
            return
        except HttpError as exc:
            status = exc.resp.status if exc.resp else None
            # Reintentar en errores 429/5xx
            if status in {429, 500, 502, 503, 504} and backoff <= BACKOFF_MAX:
                logger.warning("Error %s al enviar correo; retry en %s s", status, backoff)
                dt.time.sleep(backoff)
                backoff *= 2
                continue
            logger.error("Fallo permanente enviando correo a %s: %s", to, exc)
            raise



send_email = _send_via_gmail  # alias exportado



CONF_TMPL = (
    "Buenas {name},\n\n"
    "Ha reservado cita para el día {date} a las {time} con el doctor/a {doctor} "
    "en la clínica {clinic}.\n\n"
    "Gracias por confiar en nosotros."
)

REM_TMPL = (
    "Le recordamos, {salute} {name}, que mañana ({date}) tiene cita a las {time} "
    "con el doctor/a {doctor} en la clínica {clinic}.\n\n"
    "Por favor, llegue con 10 minutos de antelación."
)


def send_confirmation(*, patient_email: str, patient_name: str, doctor: str, clinic: str, when: dt.datetime) -> None:
    body = CONF_TMPL.format(
        name=patient_name,
        date=when.strftime("%d-%m-%Y"),
        time=when.strftime("%H:%M"),
        doctor=doctor,
        clinic=clinic,
    )
    send_email(patient_email, "Confirmación de cita", body)


def schedule_reminder(*, patient_email: str, patient_name: str, doctor: str, clinic: str, when: dt.datetime) -> None:
    """Programa un recordatorio 24 h antes de la cita."""
    global _scheduler
    if EMAIL_BACKEND == "console":
        logger.info("EMAIL_BACKEND=console → no se programa reminder real")
        return

    if _scheduler is None:
        _scheduler = BackgroundScheduler(timezone="UTC")
        _scheduler.start()

    run_at = when - dt.timedelta(hours=24)

    def _task():
        body = REM_TMPL.format(
            salute="Sr." if patient_name.split()[0][-1] != "a" else "Sra.",
            name=patient_name,
            date=when.strftime("%d-%m-%Y"),
            time=when.strftime("%H:%M"),
            doctor=doctor,
            clinic=clinic,
        )
        send_email(patient_email, "Recordatorio de cita", body)

    _scheduler.add_job(
        _task,
        trigger="date",
        run_date=run_at,
        misfire_grace_time=3600,
        id=f"reminder_{patient_email}_{when.isoformat()}",
        replace_existing=True,
    )
    logger.info("Recordatorio programado para %s", run_at.isoformat())


if __name__ == "__main__":
    import argparse, time as _time

    parser = argparse.ArgumentParser(description="Herramienta de email de la clínica")
    parser.add_argument("--setup", action="store_true", help="Inicia flujo OAuth y crea token.json")
    parser.add_argument("--reset", action="store_true", help="Borra token.json para autorizar otra cuenta")
    parser.add_argument("--to", help="Envía un email de prueba a esta dirección")
    args = parser.parse_args()

    if args.reset and TOKEN_FILE.exists():
        TOKEN_FILE.unlink()
        logger.info("token.json eliminado")

    if args.setup:
        _build_gmail_service()
        logger.info("token.json generado y guardado en %s", TOKEN_FILE)
        sys.exit(0)

    if args.to:
        send_email(args.to, "Prueba API Clínica", "Esto es un test de la API de la clínica.")
        # El servicio Gmail se crea on‑demand; espera un segundo para que termine el hilo de envío
        _time.sleep(1.0)
