import re
import json
import os
import requests
from html import unescape
from icalendar import Calendar, Event
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from urllib.parse import unquote

USER_EMAIL = os.environ.get("DIGI1_USER_EMAIL")
USER_PASSWORD = os.environ.get("DIGI1_USER_PASSWORD")
PATH_SECRET = os.environ.get("PATH_SECRET")


def fetch_timetable() -> list:
    """Fetch timetable JSON for this and next week."""
    session = requests.Session()

    # Get session details
    response = session.get("https://app.digi1.lt/")
    response.raise_for_status()

    match = re.search(r'data-page="([^"]+)"', response.text)
    if not match:
        raise ValueError("Could not find data-page attribute")

    data_page = json.loads(unescape(match.group(1)))
    inertia_version = data_page.get("version")
    if not inertia_version:
        raise ValueError("Could not find inertia version")

    xsrf_token = session.cookies.get("XSRF-TOKEN")
    if not xsrf_token:
        raise ValueError("Could not find XSRF token")
    xsrf_token = unquote(xsrf_token)

    # Authenticate session
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

    # Calculate week start dates (Monday 23:00 UTC = Tuesday 00:00 Lithuanian time)
    today = datetime.now(timezone.utc)
    days_since_monday = today.weekday()
    this_monday = today - timedelta(days=days_since_monday)
    this_week_start = this_monday.replace(hour=23, minute=0, second=0, microsecond=0) - timedelta(days=1)
    next_week_start = this_week_start + timedelta(days=7)

    this_week = request_timetable(session, xsrf_token, inertia_version, week_start=this_week_start)
    next_week = request_timetable(session, xsrf_token, inertia_version, week_start=next_week_start)

    return this_week + next_week  # type: ignore


def request_timetable(
    session: requests.Session,
    xsrf_token: str,
    inertia_version: str,
    week_start: datetime | None = None,
) -> list:
    """Request timetable from API."""
    params = {}
    if week_start:
        params["weekStart"] = week_start.strftime("%Y-%m-%dT%H:%M:%S.000Z")

    response = session.get(
        "https://app.digi1.lt/teacher/dashboard",
        params=params,
        headers={
            "Accept": "text/html, application/xhtml+xml",
            "Content-Type": "application/json",
            "X-Inertia": "true",
            "X-Inertia-Version": inertia_version,
            "X-Requested-With": "XMLHttpRequest",
            "X-XSRF-TOKEN": xsrf_token,
        },
    )
    response.raise_for_status()

    response_json = response.json()
    props = response_json.get("props")
    if not props:
        raise ValueError("Response missing 'props'")

    timetable = props.get("timetable")
    if not timetable:
        raise ValueError("Response missing 'timetable'")

    table = timetable.get("table")
    if table is None:
        raise ValueError("Response missing 'table'")

    return table


def convert_to_ics(timetable_data: list) -> Calendar:
    """Convert timetable JSON to an iCalendar object."""
    cal = Calendar()
    cal.add("prodid", "-//Digi1 Lessons//EN")
    cal.add("version", "2.0")
    cal.add("calscale", "GREGORIAN")
    cal.add("method", "PUBLISH")
    cal.add("x-wr-calname", "Digi1 Lessons")

    for day in timetable_data:
        for item in day:
            user_info = item.get("user") or {}
            subject_info = item.get("subject") or {}
            grade_info = item.get("grade") or {}

            subject = subject_info.get("name", "<unknown>")
            student_grade = grade_info.get("name", "? kl.")
            first_name = user_info.get("first_name", "")
            last_name = user_info.get("last_name", "")

            last_initial = f"{last_name[0]}." if last_name else ""
            title = f"{subject} {student_grade} - {first_name} {last_initial}"

            published_at = item.get("published_at")
            if not published_at:
                continue

            start_time = datetime.strptime(published_at, "%Y-%m-%d %H:%M:%S")
            start_time_local = start_time.replace(tzinfo=ZoneInfo("Europe/Vilnius"))
            start_time_utc = start_time_local.astimezone(timezone.utc)
            end_time_utc = start_time_utc + timedelta(hours=1)

            uuid = item.get("uuid")
            if not uuid:
                continue

            event = Event()
            event.add("uid", uuid)
            event.add("summary", title)
            event.add("dtstart", start_time_utc)
            event.add("dtend", end_time_utc)
            cal.add_component(event)

    return cal


def save_calendar(cal: Calendar) -> None:
    """Save the calendar to a file."""
    if not PATH_SECRET:
        raise ValueError("PATH_SECRET environment variable not set")

    output_path = f"docs/{PATH_SECRET}/calendar.ics"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(cal.to_ical())
    print(f"Calendar saved to {output_path}")


def main():
    if not USER_EMAIL or not USER_PASSWORD:
        print("DIGI1_USER_EMAIL and DIGI1_USER_PASSWORD must be set")
        return 1

    if not PATH_SECRET:
        print("PATH_SECRET must be set")
        return 1

    try:
        print("Fetching timetable...")
        timetable_data = fetch_timetable()

        print("Converting to ICS format...")
        calendar = convert_to_ics(timetable_data)

        print("Saving calendar...")
        save_calendar(calendar)

        print("Done!")
        return 0
    except Exception as e:
        print(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
