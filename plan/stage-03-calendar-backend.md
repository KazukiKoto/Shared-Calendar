# Stage 03 — FastAPI: Calendar & Event Core

## Goal

Implement the calendar and event data models, full CRUD API endpoints, iCalendar-compatible recurrence rules (RFC 5545 RRULE via `python-dateutil`), and comprehensive timezone support. All datetimes are stored as UTC in PostgreSQL; the optional `Accept-Timezone` request header controls the timezone used in responses. Events belong to exactly one calendar. Recurring event exceptions (single-occurrence overrides or cancellations) are stored in a separate `event_exceptions` table. A default "Personal" calendar is automatically created for every new user at registration.

---

## User Stories

1. As an authenticated user, I want to create a named calendar with a colour and timezone, so that I can organise different areas of my life.
2. As an authenticated user, I want to list, rename, and delete my calendars, so that I can keep my calendar list current.
3. As an authenticated user, I want to create a one-time event with a title, description, start time, end time, and timezone, so that I can record appointments.
4. As an authenticated user, I want to create a recurring event using RRULE syntax (daily, weekly, monthly, yearly with UNTIL or COUNT), so that I can represent repeating schedules.
5. As an authenticated user, I want to edit a single occurrence of a recurring event without affecting other occurrences, so that I can handle exceptions.
6. As an authenticated user, I want to list all events (including recurring occurrences) within a date range, so that I can build calendar views.
7. As an authenticated user, I want all times stored as UTC and returned in my profile timezone, so that I see correct local times regardless of server location.

---

## Acceptance Criteria

1. `POST /api/v1/calendars` with valid `{name, color, timezone}` returns `201` with the calendar object including a UUID `id`.
2. A default calendar named "Personal" with colour `#3B82F6` is automatically created for a user immediately upon registration (triggered from `auth_service.py`).
3. `GET /api/v1/calendars` returns all calendars for which the authenticated user is owner or member.
4. `GET /api/v1/calendars/{calendar_id}` returns `404` if the calendar does not belong to or is not shared with the requester.
5. `PATCH /api/v1/calendars/{calendar_id}` updates `name`, `color`, or `timezone` and returns the updated calendar.
6. `DELETE /api/v1/calendars/{calendar_id}` deletes the calendar and all its events; returns `204`. Only the owner may delete a calendar.
7. `POST /api/v1/calendars/{calendar_id}/events` with `{title, start, end}` creates a one-time event and returns `201`.
8. Events with an `rrule` field are validated to be RFC 5545-compliant RRULE strings; invalid strings return `422` with a descriptive error.
9. `GET /api/v1/calendars/{calendar_id}/events?start=<ISO8601>&end=<ISO8601>` returns all event occurrences (including expanded recurrence instances) that overlap the requested window. `start` and `end` are required.
10. Each occurrence in the list response includes: `id`, `calendar_id`, `title`, `description`, `start`, `end`, `is_all_day`, `rrule`, `occurrence_date` (for recurring), `is_exception`.
11. `GET /api/v1/events/{event_id}` returns the master event object (not expanded occurrences).
12. `PATCH /api/v1/events/{event_id}` updates a non-recurring event, or modifies the master recurring event (affects all future occurrences).
13. `PATCH /api/v1/events/{event_id}/occurrences/{occurrence_date}` creates or updates an exception record in `event_exceptions`; the date is an ISO 8601 date string (`YYYY-MM-DD`).
14. `DELETE /api/v1/events/{event_id}` deletes the master event and all exceptions; returns `204`.
15. `DELETE /api/v1/events/{event_id}/occurrences/{occurrence_date}` inserts a cancellation exception; the occurrence no longer appears in range queries.
16. All datetime fields in responses are ISO 8601 strings with UTC offset. When `Accept-Timezone: <tz>` header is present, times are converted to that timezone in the response.
17. Alembic migrations `002_create_calendars_table.py` and `003_create_events_and_exceptions_tables.py` run cleanly on a fresh database and are independently reversible.
18. pytest coverage for `app/api/v1/calendars.py`, `app/api/v1/events.py`, and `app/services/calendar_service.py` is ≥ 85%.

---

## API Endpoint Signatures

```
# Calendars
POST   /api/v1/calendars
       Body:  CreateCalendarRequest(name: str, color: str = "#3B82F6", timezone: str = "UTC")
       201:   CalendarResponse(id, name, color, timezone, owner_id, created_at)

GET    /api/v1/calendars
       200:   list[CalendarResponse]

GET    /api/v1/calendars/{calendar_id}
       200:   CalendarResponse  |  404

PATCH  /api/v1/calendars/{calendar_id}
       Body:  UpdateCalendarRequest(name?: str, color?: str, timezone?: str)
       200:   CalendarResponse

DELETE /api/v1/calendars/{calendar_id}
       204

# Events
POST   /api/v1/calendars/{calendar_id}/events
       Body:  CreateEventRequest(
                title: str,
                description: str | None = None,
                start: datetime,           # timezone-aware ISO 8601
                end: datetime,
                is_all_day: bool = False,
                rrule: str | None = None,  # RFC 5545 e.g. "FREQ=WEEKLY;BYDAY=MO,WE"
                timezone: str = "UTC"
              )
       201:   EventResponse

GET    /api/v1/calendars/{calendar_id}/events
       Query: start: datetime (required), end: datetime (required)
       200:   list[EventOccurrenceResponse]

GET    /api/v1/events/{event_id}
       200:   EventResponse  |  404

PATCH  /api/v1/events/{event_id}
       Body:  UpdateEventRequest(title?, description?, start?, end?, rrule?, timezone?)
       200:   EventResponse

PATCH  /api/v1/events/{event_id}/occurrences/{occurrence_date}
       Body:  UpdateOccurrenceRequest(title?, description?, start?, end?)
       200:   EventOccurrenceResponse

DELETE /api/v1/events/{event_id}
       204

DELETE /api/v1/events/{event_id}/occurrences/{occurrence_date}
       204
```

---

## Key Files / Directories to Create

```
backend/
├── alembic/versions/
│   ├── 002_create_calendars_table.py
│   └── 003_create_events_and_exceptions_tables.py
└── app/
    ├── api/v1/
    │   ├── calendars.py
    │   └── events.py
    ├── models/
    │   ├── calendar.py
    │   ├── event.py
    │   └── event_exception.py
    ├── schemas/
    │   ├── calendar.py
    │   └── event.py
    └── services/
        ├── calendar_service.py
        └── recurrence_service.py    # expands RRULE into occurrences within a time window
```

```
backend/tests/
├── test_calendars.py
└── test_events.py
```

---

## Database Schema

```sql
-- schema: calendar_app
CREATE TABLE calendars (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name        VARCHAR(255) NOT NULL,
    color       VARCHAR(20)  NOT NULL DEFAULT '#3B82F6',
    timezone    VARCHAR(50)  NOT NULL DEFAULT 'UTC',
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE TABLE events (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    calendar_id  UUID NOT NULL REFERENCES calendars(id) ON DELETE CASCADE,
    title        VARCHAR(500) NOT NULL,
    description  TEXT,
    start_at     TIMESTAMPTZ  NOT NULL,
    end_at       TIMESTAMPTZ  NOT NULL,
    is_all_day   BOOLEAN      NOT NULL DEFAULT FALSE,
    rrule        VARCHAR(1024),                    -- NULL = one-time event
    timezone     VARCHAR(50)  NOT NULL DEFAULT 'UTC',
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE TABLE event_exceptions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id        UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    occurrence_date DATE NOT NULL,                -- original occurrence date being overridden
    is_cancelled    BOOLEAN NOT NULL DEFAULT FALSE,
    title           VARCHAR(500),
    description     TEXT,
    start_at        TIMESTAMPTZ,
    end_at          TIMESTAMPTZ,
    UNIQUE (event_id, occurrence_date)
);
```

---

## Dependencies

- Stage 01 (infrastructure, Docker, PostgreSQL with `calendar_app` schema).
- Stage 02 (`User` model, `get_current_user` FastAPI dependency, `auth_service` for creating the default Personal calendar on registration).
