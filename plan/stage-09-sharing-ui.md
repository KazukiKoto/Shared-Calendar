# Stage 09 — Laravel: Sharing & Notifications UI

## Goal

Build the calendar sharing flow (share modal accessible from the sidebar) and the invitations inbox where users see and respond to pending calendar invitations. A notification badge on the navbar bell icon indicates pending invitations. All sharing and invitation actions proxy through Laravel controllers to the FastAPI collaboration API built in Stages 04 and 05.

---

## User Stories

1. As a calendar owner, I want to open a share modal from my calendar in the sidebar and invite a user by email with a chosen role, so that I can collaborate with others.
2. As a calendar owner, I want to see a list of current members with their roles and remove or change them from the share modal, so that I can manage access.
3. As an invited user, I want to see a notification badge on the navbar when I have pending invitations, so that I know to check them.
4. As an invited user, I want to visit an invitations page and accept or decline each pending invitation, so that I control which shared calendars appear in my account.
5. As a calendar owner, I want confirmation that an invitation was sent, so that I know the invite was delivered.
6. As any calendar member, I want to leave a shared calendar I no longer want, so that it stops appearing in my calendar list.

---

## Acceptance Criteria

1. Each calendar in the sidebar has a share icon button; clicking it opens a share modal for that calendar.
2. The share modal contains:
   - An email input field + role selector (`Editor` / `Viewer`) + `Send Invite` button.
   - A member list showing current members with name, email, current role (editable dropdown), and a `Remove` button.
3. Submitting the invite form calls `POST /shares/calendars/{id}/invite` (Laravel) → FastAPI `POST /api/v1/calendars/{id}/invitations`; on success, flashes `"Invitation sent to {email}"` inside the modal.
4. Inviting an email that does not have an account returns a `404` from FastAPI; the modal shows an inline error `"No account found for this email address"`.
5. The member list in the modal is loaded via `GET /shares/calendars/{id}/members` → FastAPI `GET /api/v1/calendars/{id}/members` on modal open.
6. Changing a member's role dropdown calls `PATCH /shares/calendars/{id}/members/{user_id}` → FastAPI `PATCH` endpoint; updates the UI on success.
7. Clicking `Remove` on a member calls `DELETE /shares/calendars/{id}/members/{user_id}` → FastAPI `DELETE` endpoint; removes the row from the list.
8. The navbar contains a bell icon; on every page load a JS call to `GET /notifications/count` (Laravel route) is made; if `pending_invitations > 0`, a numeric badge is shown on the bell.
9. `GET /invitations` (Laravel route) renders `invitations/index.blade.php` listing all pending invitations with: calendar name, inviter name, role, sent date, and `Accept` / `Decline` buttons.
10. `POST /invitations/{id}/accept` (Laravel) calls FastAPI `POST /api/v1/invitations/{id}/accept`; redirects back with flash `"You have joined {calendar name}"`.
11. `POST /invitations/{id}/decline` (Laravel) calls FastAPI `POST /api/v1/invitations/{id}/decline`; redirects back with flash `"Invitation declined"`.
12. After accepting an invitation, the shared calendar immediately appears in the sidebar on the next page load (the sidebar calendar list is fetched fresh on every load).
13. A user viewing the share modal on a calendar they are a member of (not owner) sees the member list but no invite form and no role/remove controls.
14. PHPUnit `SharingControllerTest` and `InvitationControllerTest` cover all happy paths plus the 404-no-account and 409-already-member error cases using `Http::fake()`.

---

## Laravel Routes

```php
// routes/web.php — all protected by 'auth' middleware
Route::middleware('auth')->group(function () {
    // Invitations inbox
    Route::get ('/invitations',              [InvitationController::class, 'index'])->name('invitations');
    Route::post('/invitations/{id}/accept',  [InvitationController::class, 'accept'])->name('invitations.accept');
    Route::post('/invitations/{id}/decline', [InvitationController::class, 'decline'])->name('invitations.decline');

    // Notification badge count (called by JS on every page)
    Route::get('/notifications/count',       [NotificationController::class, 'count'])->name('notifications.count');

    // Calendar sharing modal actions
    Route::post  ('/shares/calendars/{id}/invite',          [SharingController::class, 'invite']);
    Route::get   ('/shares/calendars/{id}/members',         [SharingController::class, 'members']);
    Route::patch ('/shares/calendars/{id}/members/{uid}',   [SharingController::class, 'updateRole']);
    Route::delete('/shares/calendars/{id}/members/{uid}',   [SharingController::class, 'removeMember']);
});
```

---

## Key Files / Directories to Create

```
frontend/
├── app/Http/Controllers/
│   ├── InvitationController.php      # index, accept, decline
│   ├── NotificationController.php    # count (returns JSON {pending_invitations: N})
│   └── SharingController.php         # invite, members, updateRole, removeMember
├── resources/
│   ├── js/
│   │   └── share-modal.js            # Alpine.js component: modal open/close, AJAX member list
│   └── views/
│       ├── invitations/
│       │   └── index.blade.php
│       └── partials/
│           └── share-modal.blade.php  # included in calendar/index.blade.php
├── routes/
│   └── web.php
└── tests/Feature/
    ├── SharingControllerTest.php
    └── InvitationControllerTest.php
```

---

## Dependencies

- Stage 06 (`ApiClient`, `auth` middleware, base layout with navbar).
- Stage 07 (sidebar structure in `calendar/index.blade.php` where share button is placed).
- Stage 04 (FastAPI sharing endpoints: invitations, members).
- Stage 05 (invitation email sent by FastAPI when `POST /api/v1/calendars/{id}/invitations` is called).
