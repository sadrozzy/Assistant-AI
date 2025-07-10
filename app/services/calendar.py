from typing import Optional, List
from datetime import datetime
from app.utils.logger import logger
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials


class GoogleCalendarService:
    def __init__(self, credentials):
        self.credentials = credentials
        self.service = build("calendar", "v3", credentials=self.credentials)
        self.logger = logger("calendar-service")

    async def create_event(
        self,
        user_id: int,
        description: str,
        start: datetime,
        end: Optional[datetime] = None,
        reminder_minutes: Optional[int] = None,
    ) -> str:
        """
        Создаёт событие в Google Calendar.
        start — начало события (datetime, UTC)
        end — конец события (datetime, UTC), если не задан — событие считается мгновенным или однодневным
        reminder_minutes — за сколько минут напомнить (None — не указывать, будет дефолт Google)
        """
        self.logger.info(
            f"Creating event for user {user_id}: {description} {start} - {end}, reminder: {reminder_minutes}"
        )
        event = {
            "summary": description,
            "start": {
                "dateTime": start.isoformat(),
                "timeZone": "UTC",
            },
            "end": {
                "dateTime": (end or start).isoformat(),
                "timeZone": "UTC",
            },
        }
        if reminder_minutes is not None:
            event["reminders"] = {
                "useDefault": False,
                "overrides": [
                    {"method": "popup", "minutes": reminder_minutes}
                ]
            }
        created_event = self.service.events().insert(
            calendarId="primary", body=event
        ).execute()
        return created_event["id"]

    async def update_event(
        self,
        google_event_id: str,
        description: Optional[str] = None,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> None:
        self.logger.info(
            f"Updating event {google_event_id}: {description} {start} - {end}"
        )
        event = self.service.events().get(
            calendarId="primary", eventId=google_event_id
        ).execute()
        if description is not None:
            event["summary"] = description
        if start is not None:
            event["start"] = {
                "dateTime": start.isoformat(),
                "timeZone": "UTC",
            }
        if end is not None:
            event["end"] = {
                "dateTime": end.isoformat(),
                "timeZone": "UTC",
            }
        self.service.events().update(
            calendarId="primary", eventId=google_event_id, body=event
        ).execute()

    async def delete_event(self, google_event_id: str) -> None:
        self.logger.info(f"Deleting event {google_event_id}")
        self.service.events().delete(
            calendarId="primary", eventId=google_event_id
        ).execute()

    async def get_events(
        self,
        user_id: int,
        time_min: Optional[datetime] = None,
        time_max: Optional[datetime] = None,
    ) -> List[dict]:
        self.logger.info(
            f"Getting events for user {user_id} from {time_min} to {time_max}"
        )
        params = {
            "calendarId": "primary",
            "singleEvents": True,
            "orderBy": "startTime",
        }
        if time_min:
            params["timeMin"] = time_min.isoformat()
        if time_max:
            params["timeMax"] = time_max.isoformat()
        events_result = self.service.events().list(**params).execute()
        return events_result.get("items", [])
