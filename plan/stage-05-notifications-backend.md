# Stage 05 — FastAPI: Notifications

## Goal

Implement email notifications for two triggers: (1) calendar invitation delivery and (2) configurable event reminders. Invitation emails are sent via FastAPI `BackgroundTasks` for immediate delivery. Event reminder emails are sent via Celery + Redis so they can be scheduled at a precise time before the event starts. A `Mailpit` container is added to Docker Compose to catch all outgoing SMTP in development. Email bodies are rendered with Jinja2 HTML + plain-text multipart templates. This stage completes the `email_service.py` stub from Stage 02.

---

## User Stories

1. As an invited user, I want to receive an email when someone invites me to their calendar, so that I know to check my invitations.
2. As an event attendee, I want to receive a configurable email reminder before an event starts (default 15 minutes), so that I am not late.
3. As a developer, I want all emails caught by Mailpit in development, so that no real emails are sent during testing or local dev.
4. As a system operator, I want the notification worker to retry on temporary SMTP failures with exponential back-off, so that transient outages do not drop notifications.
5. As a developer, I want to run tests without any real SMTP connection, so that the test suite is fast and self-contained.

---

## Acceptance Criteria

1. When `POST /api/v1/calendars/{calendar_id}/invitations` is called, the invitee receives an email within 5 seconds in development (visible in Mailpit at `http://localhost:8025`).
2. The invitation email contains: inviter's name, calendar name, assigned role, and a direct link to the Laravel frontend's `/invitations` page.
3. A `worker` container is defined in `docker-compose.yml`, using the same image as `backend`, running `celery -A app.worker.celery_app worker -Q notifications -c 2 --loglevel=info`.
4. A `scheduler` container is defined, using the same image, running `celery -A app.worker.celery_app beat --scheduler redbeat.RedBeatScheduler --loglevel=info`.
5. `mailpit` container (`axllent/mailpit:latest`) is added to `docker-compose.yml`, exposing SMTP on port `1025` and web UI on port `8025`.
6. `POST /api/v1/events/{event_id}/reminders` creates a reminder record and schedules a Celery task at `event.start_at - reminder_minutes`; returns `201 ReminderResponse`.
7. `GET /api/v1/events/{event_id}/reminders` returns all reminders configured for the event by the authenticated user; returns `200 list[ReminderResponse]`.
8. `DELETE /api/v1/events/{event_id}/reminders/{reminder_id}` revokes the scheduled Celery task (via `task_id` stored on the reminder) and deletes the reminder row; returns `204`.
9. Reminder emails include: event title, start time in the recipient's profile timezone, calendar name, and a link to the Laravel frontend calendar view.
10. All email templates are HTML + plain-text multipart; HTML rendered via Jinja2; stored in `app/templates/email/`.
11. `MAIL_MAILER=console` env var causes email bodies to be logged to stdout instead of sent via SMTP (useful in CI).
12. Alembic migration `006_create_reminders_table.py` runs on a clean database and is reversible.
13. pytest tests mock `BackgroundTasks.add_task` and Celery `.apply_async`; no real SMTP connection or Redis scheduling occurs during tests.
14. Celery task retries use exponential back-off: `max_retries=3`, `countdown=60 * 2**retry_count`.

---

## API Endpoint Signatures

```
POST   /api/v1/events/{event_id}/reminders
       Header: Authorization: Bearer <token>
       Body:   CreateReminderRequest(minutes_before: int = 15)
       201:    ReminderResponse(id, event_id, user_id, minutes_before, scheduled_at, task_id)

GET    /api/v1/events/{event_id}/reminders
       Header: Authorization: Bearer <token>
       200:    list[ReminderResponse]

DELETE /api/v1/events/{event_id}/reminders/{reminder_id}
       Header: Authorization: Bearer <token>
       204
```

---

## Key Files / Directories to Create

```
backend/
├── alembic/versions/
│   └── 006_create_reminders_table.py
└── app/
    ├── api/v1/
    │   └── reminders.py
    ├── models/
    │   └── reminder.py
    ├── schemas/
    │   └── reminder.py
    ├── services/
    │   ├── email_service.py          # completes the Stage 02 stub; aiosmtplib + Jinja2
    │   └── notification_service.py   # orchestrates invitation email + reminder scheduling
    ├── templates/
    │   └── email/
    │       ├── base.html
    │       ├── invitation.html
    │       ├── invitation.txt
    │       ├── reminder.html
    │       └── reminder.txt
    └── worker/
        ├── __init__.py
        ├── celery_app.py             # Celery app + RedBeat config
        └── tasks/
            ├── __init__.py
            └── notification_tasks.py # send_reminder_email Celery task
```

Docker Compose additions to `docker-compose.yml`:
```yaml
  mailpit:
    image: axllent/mailpit:latest
    ports:
      - "8025:8025"   # web UI
      - "1025:1025"   # SMTP

  worker:
    build: ./backend
    command: celery -A app.worker.celery_app worker -Q notifications -c 2 --loglevel=info
    depends_on: [redis, postgres]
    env_file: .env

  scheduler:
    build: ./backend
    command: celery -A app.worker.celery_app beat --scheduler redbeat.RedBeatScheduler --loglevel=info
    depends_on: [redis]
    env_file: .env
```

---

## Database Schema

```sql
-- schema: calendar_app
CREATE TABLE reminders (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id       UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    user_id        UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    minutes_before INT  NOT NULL DEFAULT 15,
    scheduled_at   TIMESTAMPTZ NOT NULL,       -- event.start_at - minutes_before
    task_id        VARCHAR(255),               -- Celery task ID for revocation
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (event_id, user_id, minutes_before)
);
```

---

## Dependencies

- Stage 01 (Docker Compose, Redis, infrastructure).
- Stage 02 (`User` model, `email_service.py` stub).
- Stage 03 (`Event` model, `start_at` field used for scheduling).
- Stage 04 (`Invitation` model, invitation creation hook).
