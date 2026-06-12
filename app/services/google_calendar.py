import logging
from typing import Optional

from google.oauth2 import service_account
from googleapiclient.discovery import build
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/calendar"]
GCAL_TIME_FORMAT = "%Y-%m-%dT%H:%M:%S%z"

_service = None


def _get_service():
    global _service
    if _service is not None:
        return _service
    if not settings.GOOGLE_SERVICE_ACCOUNT_FILE:
        return None
    try:
        creds = service_account.Credentials.from_service_account_file(
            settings.GOOGLE_SERVICE_ACCOUNT_FILE, scopes=SCOPES
        )
        _service = build("calendar", "v3", credentials=creds)
        return _service
    except Exception as e:
        logger.warning(f"Failed to load service account file '{settings.GOOGLE_SERVICE_ACCOUNT_FILE}': {e}")
        return None


def is_configured() -> bool:
    return bool(settings.GOOGLE_SERVICE_ACCOUNT_FILE)


async def _get_calendar_id(db: AsyncSession, appointment) -> Optional[str]:
    from app.models.master import Master
    master = await db.get(Master, appointment.master_id)
    if master and master.google_calendar_id:
        return master.google_calendar_id
    return None


async def _build_event_body(db: AsyncSession, appointment) -> Optional[dict]:
    from app.models.client import Client
    from app.models.master import Master
    from app.models.pet import Pet
    from app.models.service import Service

    client = await db.get(Client, appointment.client_id)
    master = await db.get(Master, appointment.master_id)
    pet = await db.get(Pet, appointment.pet_id)
    svc = await db.get(Service, appointment.service_id)
    if not all([client, master, pet, svc]):
        return None

    start_str = appointment.start_time.strftime(GCAL_TIME_FORMAT)
    end_str = appointment.end_time.strftime(GCAL_TIME_FORMAT)

    description = (
        f"Клиент: {client.name}\n"
        f"Телефон: {client.phone}\n"
        f"Мастер: {master.name}\n"
        f"Питомец: {pet.name} ({pet.breed or pet.species})\n"
        f"Услуга: {svc.name} — {svc.price}₽\n"
        f"Заметки: {appointment.notes or '—'}"
    )

    return {
        "summary": f"{svc.name} — {pet.name} ({client.name})",
        "description": description,
        "start": {"dateTime": start_str, "timeZone": "Europe/Moscow"},
        "end": {"dateTime": end_str, "timeZone": "Europe/Moscow"},
        "reminders": {
            "useDefault": False,
            "overrides": [
                {"method": "popup", "minutes": 30},
                {"method": "popup", "minutes": 120},
            ],
        },
    }


async def create_event(db: AsyncSession, appointment) -> Optional[str]:
    service = _get_service()
    if not service:
        logger.info("Google Calendar event skipped: service account not configured")
        return None

    calendar_id = await _get_calendar_id(db, appointment)
    if not calendar_id:
        logger.info(f"Google Calendar event skipped: master {appointment.master_id} has no calendar ID")
        return None

    event_body = await _build_event_body(db, appointment)
    if not event_body:
        logger.warning("Cannot create Google Calendar event: missing related data")
        return None

    try:
        event = service.events().insert(
            calendarId=calendar_id,
            body=event_body,
        ).execute()
        logger.info(f"Google Calendar event created: {event.get('id')}")
        return event.get("id")
    except Exception as e:
        logger.error(f"Failed to create Google Calendar event: {e}")
        return None


async def update_event(db: AsyncSession, appointment) -> bool:
    if not appointment.google_event_id:
        return False
    service = _get_service()
    if not service:
        return False
    calendar_id = await _get_calendar_id(db, appointment)
    if not calendar_id:
        return False
    event_body = await _build_event_body(db, appointment)
    if not event_body:
        return False
    try:
        service.events().patch(
            calendarId=calendar_id,
            eventId=appointment.google_event_id,
            body=event_body,
        ).execute()
        return True
    except Exception as e:
        logger.error(f"Failed to update Google Calendar event: {e}")
        return False


async def delete_event(db: AsyncSession, appointment) -> bool:
    if not appointment.google_event_id:
        return False
    service = _get_service()
    if not service:
        return False
    calendar_id = await _get_calendar_id(db, appointment)
    if not calendar_id:
        return False
    try:
        service.events().delete(
            calendarId=calendar_id,
            eventId=appointment.google_event_id,
        ).execute()
        return True
    except Exception as e:
        logger.error(f"Failed to delete Google Calendar event: {e}")
        return False
