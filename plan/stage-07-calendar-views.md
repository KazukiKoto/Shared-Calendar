# Stage 07 — Laravel: Calendar Views

## Goal

Build the primary calendar UI using FullCalendar.js v6 (bundled via Vite, not CDN). Laravel controllers fetch event data from the FastAPI backend via `ApiClient` and serve it through a dedicated internal JSON endpoint in the FullCalendar event feed format. Blade templates render the calendar shell (toolbar, sidebar, view container); FullCalendar populates events asynchronously via a JavaScript fetch to the Laravel event-feed route. A sidebar lists all calendars with colour swatches and client-side show/hide toggles.

---

## User Stories

1. As an authenticated user, I want to see a monthly calendar view of all my events on load, so that I get an overview of my schedule.
2. As an authenticated user, I want to switch between monthly, weekly, and daily views using toolbar buttons, so that I can focus on the level of detail I need.
3. As an authenticated user, I want the calendar to automatically load events for the visible date range without manual refresh, so that navigation is seamless.
4. As an authenticated user, I want events to be colour-coded by calendar, so that I can visually distinguish between different calendars.
5. As an authenticated user, I want to click an event to see a popover with its title, time, calendar name, and description, so that I can read event details without leaving the calendar.
6. As an authenticated user, I want to toggle calendar visibility in the sidebar, so that I can reduce visual clutter.
7. As an authenticated user, I want recurring event occurrences to appear on each correct date, so that I see my full schedule.

---

## Acceptance Criteria

1. `GET /calendar` renders a Blade page containing the FullCalendar mount point; default view is `dayGridMonth`.
2. FullCalendar is configured with `events: '/api/calendar/events'` using its `start` and `end` query parameters.
3. `GET /api/calendar/events?start=<ISO>&end=<ISO>` (internal Laravel route, authenticated):
   - Calls FastAPI `GET /api/v1/calendars` to get all user calendars.
   - For each calendar, calls FastAPI `GET /api/v1/calendars/{id}/events?start=&end=`.
   - Merges results into a JSON array in FullCalendar event format:
     `[{id, title, start, end, allDay, color, extendedProps: {calendar_id, calendar_name, description}}]`
   - Returns `200` with `Content-Type: application/json`.
4. Events from each calendar use that calendar's `color` field as the FullCalendar `color` property.
5. All-day events appear in the all-day row of weekly/daily views.
6. Clicking an event opens a Bootstrap/Alpine.js popover showing: title, formatted start/end, calendar name, description.
7. The weekly view (`timeGridWeek`) is selectable via a FullCalendar toolbar button.
8. The daily view (`timeGridDay`) is selectable via a toolbar button and is also reachable by clicking a day number in month view.
9. The sidebar lists all calendars with: a colour swatch, the calendar name, and a checkbox/toggle.
10. Unchecking a calendar in the sidebar hides its events from FullCalendar client-side (no re-fetch); re-checking restores them.
11. FullCalendar packages (`@fullcalendar/core`, `@fullcalendar/daygrid`, `@fullcalendar/timegrid`, `@fullcalendar/interaction`) are installed via npm and bundled by Vite; no external CDN scripts.
12. Tailwind CSS is used for all layout and utility styling; no inline styles.
13. PHPUnit `CalendarControllerTest`: mocks `ApiClient`, asserts `GET /calendar` returns `200`, asserts `GET /api/calendar/events` returns a valid JSON array with correct FullCalendar fields.
14. The page is responsive: on viewport widths below 768px the sidebar collapses to a drawer toggled by a hamburger button.

---

## Laravel Routes

```php
// routes/web.php  (all protected by 'auth' middleware)
Route::middleware('auth')->group(function () {
    Route::get('/calendar',              [CalendarController::class, 'index'])->name('calendar');
    Route::get('/calendars/{id}',        [CalendarController::class, 'show'])->name('calendar.show');
    Route::get('/api/calendar/events',   [CalendarController::class, 'eventFeed'])->name('calendar.events');
});
```

---

## Key Files / Directories to Create

```
frontend/
├── app/Http/Controllers/
│   └── CalendarController.php        # index(), show(), eventFeed()
├── resources/
│   ├── js/
│   │   ├── app.js                    # Vite entry point; imports Alpine.js
│   │   └── calendar.js               # FullCalendar initialisation + event feed URL + popover
│   ├── css/
│   │   └── app.css                   # Tailwind CSS directives
│   └── views/
│       └── calendar/
│           └── index.blade.php       # calendar shell + sidebar
├── routes/
│   └── web.php                       # add calendar routes
├── package.json                      # add @fullcalendar/* + tailwindcss + alpinejs
├── vite.config.js
└── tests/Feature/
    └── CalendarControllerTest.php
```

---

## FullCalendar Initialisation Sketch (`calendar.js`)

```js
import { Calendar } from '@fullcalendar/core';
import dayGridPlugin  from '@fullcalendar/daygrid';
import timeGridPlugin from '@fullcalendar/timegrid';
import interactionPlugin from '@fullcalendar/interaction';

document.addEventListener('DOMContentLoaded', () => {
    const el = document.getElementById('calendar');
    const calendar = new Calendar(el, {
        plugins: [dayGridPlugin, timeGridPlugin, interactionPlugin],
        initialView: 'dayGridMonth',
        headerToolbar: {
            left:   'prev,next today',
            center: 'title',
            right:  'dayGridMonth,timeGridWeek,timeGridDay',
        },
        events: '/api/calendar/events',
        eventClick(info) { showPopover(info.event); },
        dateClick(info)  { openCreateModal(info.dateStr); },
    });
    calendar.render();
});
```

---

## Dependencies

- Stage 01 (Vite/npm setup in the frontend Docker image).
- Stage 06 (`ApiClient`, `auth` middleware, `layouts/app.blade.php`).
- Stage 03 (FastAPI event list endpoint `/api/v1/calendars/{id}/events`).
- Stage 02 (FastAPI JWT stored in session for `ApiClient`).
