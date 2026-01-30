# Digi1 Timetable to iCal exporter

Automatically fetches timetable data from the Digi1 API and publishes it as an ICS calendar that Google Calendar can subscribe to.

**Security note:** This project stores your Digi1 credentials as GitHub secrets and publishes your timetable via GitHub Pages. While the calendar URL is obscured with a secret path, anyone with the link can access it. Only use this if you're comfortable with these trade-offs.

## Setup

### 1. Fork/clone this repo

### 2. Add your login credentials as secrets

Go to your repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

- `DIGI1_USER_EMAIL`: Your login email
- `DIGI1_USER_PASSWORD`: Your login password
- `PATH_SECRET`: A random string to obscure your calendar URL (e.g., `Xk9m2Pq_a8Fy3NvB`)

### 3. Enable GitHub Pages

Go to your repo → **Settings** → **Pages**

- Source: **Deploy from a branch**
- Branch: **master**
- Folder: **/docs**

Click **Save**.

### 4. Subscribe in Google Calendar

Once GitHub Pages is enabled, your calendar will be available at:

``` plaintext
https://<YOUR-USERNAME>.github.io/<REPO-NAME>/<PATH_SECRET>/calendar.ics
```

In Google Calendar:

1. Click the **+** next to "Other calendars"
2. Select **From URL**
3. Paste your calendar URL
4. Click **Add calendar**

Google will periodically refresh the calendar (usually every 12-24 hours).

## Schedule

The calendar updates automatically every day at 6:00 AM UTC. You can:

- Change the schedule in `.github/workflows/update-calendar.yml`
- Manually trigger an update from the **Actions** tab
