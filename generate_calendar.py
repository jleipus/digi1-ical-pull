import re
import json
import os
import requests
import logging
from html import unescape
from icalendar import Calendar, Event
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from urllib.parse import unquote

USER_EMAIL = os.environ.get("DIGI1_USER_EMAIL")
USER_PASSWORD = os.environ.get("DIGI1_USER_PASSWORD")
PATH_SECRET = os.environ.get("PATH_SECRET")

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def fetch_timetable() -> dict:
    """Fetch timetable JSON from the API."""
    session = requests.Session()
    response = session.get("https://app.digi1.lt/login")

    match = re.search(r'data-page="([^"]+)"', response.text)
    data_page = json.loads(unescape(match.group(1) if match else ""))
    inertia_version = data_page["version"]

    xsrf_token = unquote(session.cookies.get("XSRF-TOKEN"))  # type: ignore

    response = session.post(
        "https://app.digi1.lt/login",
        headers={
            "Accept": "text/html, application/xhtml+xml",
            "Content-Type": "application/json",
            "X-Inertia": "true",
            "X-Inertia-Version": inertia_version,
            "X-Requested-With": "XMLHttpRequest",
            "X-XSRF-TOKEN": xsrf_token,
        },
        json={
            "email": USER_EMAIL,
            "password": USER_PASSWORD,
            "remember": False,
        },
    )

    response.raise_for_status()

    full_response = response.json()
    return full_response["props"]["timetable"]["table"]


def convert_to_ics(timetable_data: dict) -> Calendar:
    """Convert timetable JSON to an iCalendar object."""
    cal = Calendar()
    cal.add("prodid", "-//Digi1 Lessons//EN")
    cal.add("version", "2.0")
    cal.add("calscale", "GREGORIAN")
    cal.add("method", "PUBLISH")
    cal.add("x-wr-calname", "Digi1 Lessons")

    for day in timetable_data:
        for item in day:
            user_info = item.get("user", {})
            subject = item.get("subject", {}).get("name", "<unknown>")
            student_grade = item.get("grade", {}).get("name", "? kl.")

            title = f"{subject} {student_grade} - {user_info.get('first_name')} {user_info.get('last_name')}"

            start_time = datetime.strptime(item.get("published_at", ""), "%Y-%m-%d %H:%M:%S")
            start_time_local = start_time.replace(tzinfo=ZoneInfo("Europe/Vilnius"))
            start_time_utc = start_time_local.astimezone(timezone.utc)

            end_time_utc = start_time_utc + timedelta(hours=1)

            event = Event()
            event.add("uid", item.get("uuid"))
            event.add("summary", title)
            event.add("dtstart", start_time_utc)
            event.add("dtend", end_time_utc)
            cal.add_component(event)

    return cal


def save_calendar(cal: Calendar) -> None:
    """Save the calendar to a file."""
    output_path = f"docs/{PATH_SECRET}/calendar.ics"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(cal.to_ical())
    logger.info(f"Calendar saved to {output_path}")


def main():
    try:
        logger.info(f"Fetching timetable...")
        timetable_data = fetch_timetable()

        logger.info("Converting to ICS format...")
        calendar = convert_to_ics(timetable_data)

        logger.info("Saving calendar...")
        save_calendar(calendar)

        logger.info("Done!")
    except Exception as e:
        logger.error(e)


if __name__ == "__main__":
    main()
