# Stage 08 — Laravel: Event Management UI

## Goal

Implement create, edit, and delete event flows in the Laravel frontend. A modal dialog (Alpine.js + Tailwind) opens when the user clicks an empty calendar slot or an existing event, avoiding full page navigation from the calendar view. Form submissions POST to Laravel controllers which forward to the FastAPI API. The create/edit form includes a recurrence rule builder (UI-driven, no raw RRULE syntax for users) and an IANA timezone picker. Editing a recurring event prompts the user to choose the edit scope (this occurrence / this and future / all).

---

## User Stories

1. As an authenticated user, I want to click an empty calendar slot and see a create-event modal pre-filled with the clicked date and time, so that I can add events without extra navigation.
2. As an authenticated user, I want to click an existing event and see an edit modal with its current details pre-filled, so that I can update events quickly.
3. As an authenticated user, I want to build a recurrence rule via a friendly UI (frequency, days of week, end condition) without typing raw RRULE syntax, so that recurring events are easy to configure.
4. As an authenticated user, I want to pick a display timezone for each event from a searchable dropdown, so that events in other timezones show correct local times.
5. As an authenticated user, I want to delete an event with a confirmation prompt, so that I do not accidentally lose data.
6. As an authenticated user editing a recurring event, I want to choose whether to edit this occurrence only, this and future occurrences, or all occurrences, so that I have fine-grained control over recurrence exceptions.

---

## Acceptance Criteria

1. Clicking an empty time slot on FullCalendar fires `dateClick`; the create-event modal opens with `start` and `end` pre-populated from the clicked slot.
2. The create/edit modal form contains these fields: title (required), description, calendar selector (dropdown of user's calendars), start datetime, end datetime, timezone picker (searchable `<select>` with IANA names), all-day toggle, recurrence section.
3. The recurrence section contains:
   - Frequency: None / Daily / Weekly / Monthly / Yearly.
   - Day-of-week checkboxes (visible when Weekly is selected).
   - End condition: Never / After N occurrences / On date (with appropriate input per choice).
4. The recurrence builder generates a valid RFC 5545 RRULE string client-side before form submission; the string is placed in a hidden `<input name="rrule">`.
5. `POST /events` (Laravel route, authenticated):
   - Accepts form data: `calendar_id`, `title`, `description`, `start`, `end`, `timezone`, `is_all_day`, `rrule`.
   - Calls FastAPI `POST /api/v1/calendars/{calendar_id}/events`.
   - Returns `200 {"success": true, "event": {...}}` so the modal can close and FullCalendar can re-fetch events.
6. `PUT /events/{event_id}` (Laravel route) updates a non-recurring event; calls FastAPI `PATCH /api/v1/events/{event_id}`; returns `200 {"success": true}`.
7. `DELETE /events/{event_id}` (Laravel route) deletes the event; calls FastAPI `DELETE /api/v1/events/{event_id}`; returns `200 {"success": true}`.
8. `PUT /events/{event_id}/occurrences/{date}` handles single-occurrence edits; calls FastAPI `PATCH /api/v1/events/{event_id}/occurrences/{date}`.
9. `DELETE /events/{event_id}/occurrences/{date}` cancels a single occurrence; calls FastAPI `DELETE /api/v1/events/{event_id}/occurrences/{date}`.
10. When the user clicks an existing recurring event and submits an edit, a radio dialog "Edit scope" is shown before the modal closes: "This occurrence", "This and future", "All occurrences"; the correct Laravel/FastAPI endpoint is called based on the selection.
11. Validation errors from FastAPI `422` responses are deserialized and displayed beside the relevant modal form fields.
12. The delete button in the edit modal opens a browser `confirm()` dialog before submitting.
13. After a successful create, edit, or delete, `calendar.refetchEvents()` is called so FullCalendar updates without a page reload.
14. PHPUnit `EventControllerTest` covers store, update, destroy, updateOccurrence, destroyOccurrence happy paths using `Http::fake()`, asserting the correct FastAPI endpoint was called with the correct payload.

---

## Laravel Routes

```php
// routes/web.php — all protected by 'auth' middleware
Route::middleware('auth')->group(function () {
    Route::post  ('/events',                              [EventController::class, 'store']);
    Route::get   ('/events/{id}/edit',                   [EventController::class, 'edit']);
    Route::put   ('/events/{id}',                        [EventController::class, 'update']);
    Route::delete('/events/{id}',                        [EventController::class, 'destroy']);
    Route::put   ('/events/{id}/occurrences/{date}',     [EventController::class, 'updateOccurrence']);
    Route::delete('/events/{id}/occurrences/{date}',     [EventController::class, 'destroyOccurrence']);
});
```

---

## Key Files / Directories to Create

```
frontend/
├── app/Http/Controllers/
│   └── EventController.php           # store, edit, update, destroy, updateOccurrence, destroyOccurrence
├── resources/
│   ├── js/
│   │   ├── event-modal.js            # modal open/close, form serialisation, AJAX submit, refetch
│   │   └── rrule-builder.js          # pure JS: UI state → RRULE string
│   └── views/
│       └── partials/
│           ├── event-modal.blade.php  # create/edit modal HTML (included in calendar/index.blade.php)
│           └── timezone-picker.blade.php  # reusable timezone <select> partial
├── routes/
│   └── web.php                       # add event routes
└── tests/Feature/
    └── EventControllerTest.php
```

---

## RRULE Builder Logic Sketch

```js
// rrule-builder.js — pure function, no DOM dependencies
export function buildRrule({ freq, days, endType, count, until }) {
    if (!freq || freq === 'NONE') return '';
    let rrule = `FREQ=${freq}`;
    if (freq === 'WEEKLY' && days.length) {
        rrule += `;BYDAY=${days.join(',')}`;
    }
    if (endType === 'COUNT')  rrule += `;COUNT=${count}`;
    if (endType === 'UNTIL')  rrule += `;UNTIL=${until.replace(/-/g, '')}T000000Z`;
    return rrule;
}
```

---

## Dependencies

- Stage 06 (`ApiClient`, `auth` middleware, base layout).
- Stage 07 (FullCalendar initialised with `dateClick` and `eventClick` hooks; `calendar.refetchEvents()` available).
- Stage 03 (FastAPI event CRUD endpoints).
- Stage 04 (FastAPI permissions enforce editor/owner for mutation).
