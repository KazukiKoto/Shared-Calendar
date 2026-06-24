# Stage 04 — FastAPI: Sharing & Collaboration

## Goal

Allow users to share calendars with other registered users, assigning one of three permission levels: `owner`, `editor`, or `viewer`. Sharing is invitation-based — the calendar owner sends an invitation by email address and the invitee accepts or declines. The permissions model is enforced as FastAPI dependencies that gate all calendar and event mutation endpoints introduced in Stage 03. Members and ownership are tracked in a `calendar_memberships` join table; pending invitations live in a separate `invitations` table.

---

## User Stories

1. As a calendar owner, I want to invite another registered user by email with a role of `editor` or `viewer`, so that we can collaborate on events.
2. As an invited user, I want to see my pending invitations and accept or decline them individually, so that I control which shared calendars appear in my account.
3. As a calendar owner, I want to change a collaborator's permission level, so that I can promote or demote access over time.
4. As a calendar owner, I want to remove a collaborator, so that I can revoke access when needed.
5. As a viewer, I want to read events on a shared calendar, so that I can stay informed without being able to change anything.
6. As an editor, I want to create and modify events on a shared calendar, so that I can contribute to the shared schedule.
7. As any member, I want to remove myself from a shared calendar I no longer need, so that it does not clutter my calendar list.

---

## Acceptance Criteria

1. `POST /api/v1/calendars/{calendar_id}/invitations` (owner only) creates an invitation; returns `201` with the invitation object.
2. Inviting an email address that has no account returns `404 {"detail": "User not found"}`.
3. Inviting a user who is already a member of the calendar returns `409 Conflict`.
4. `GET /api/v1/invitations` returns all `pending` invitations addressed to the authenticated user.
5. `POST /api/v1/invitations/{invitation_id}/accept` adds a `calendar_membership` row for the invitee at the specified role; the calendar now appears in `GET /api/v1/calendars`; returns `204`.
6. `POST /api/v1/invitations/{invitation_id}/decline` marks the invitation as `declined`; no membership is created; returns `204`.
7. An invitation that has expired (> 7 days old) cannot be accepted; attempting to do so returns `410 Gone`.
8. `GET /api/v1/calendars/{calendar_id}/members` returns all members with their roles; accessible by any current member; returns `list[MemberResponse]`.
9. `PATCH /api/v1/calendars/{calendar_id}/members/{user_id}` changes a member's role; only the owner may do this; returns `200 MemberResponse`. Attempting to change the owner's own role returns `400`.
10. `DELETE /api/v1/calendars/{calendar_id}/members/{user_id}` removes the member; the owner can remove any member; a member may remove themselves; returns `204`.
11. A `viewer` calling `POST /api/v1/calendars/{calendar_id}/events` receives `403 Forbidden`.
12. An `editor` calling `POST /api/v1/calendars/{calendar_id}/events` succeeds with `201`.
13. Only the `owner` may call `DELETE /api/v1/calendars/{calendar_id}` or `PATCH /api/v1/calendars/{calendar_id}/members/{user_id}`.
14. A non-member calling any endpoint on a calendar they do not belong to receives `404` (not `403`) to avoid leaking calendar existence.
15. Alembic migrations `004_create_calendar_memberships_table.py` and `005_create_invitations_table.py` run cleanly on a clean database and are independently reversible.
16. pytest coverage for sharing endpoints and `app/core/permissions.py` is ≥ 85%.

---

## API Endpoint Signatures

```
POST   /api/v1/calendars/{calendar_id}/invitations
       Body:  CreateInvitationRequest(email: EmailStr, role: Literal["editor", "viewer"])
       201:   InvitationResponse(id, calendar_id, calendar_name, inviter_id, invitee_id, role, status, created_at, expires_at)

GET    /api/v1/invitations
       200:   list[InvitationResponse]

POST   /api/v1/invitations/{invitation_id}/accept
       204

POST   /api/v1/invitations/{invitation_id}/decline
       204

GET    /api/v1/calendars/{calendar_id}/members
       200:   list[MemberResponse(user_id, name, email, role, joined_at)]

PATCH  /api/v1/calendars/{calendar_id}/members/{user_id}
       Body:  UpdateMemberRequest(role: Literal["editor", "viewer"])
       200:   MemberResponse

DELETE /api/v1/calendars/{calendar_id}/members/{user_id}
       204
```

---

## Key Files / Directories to Create

```
backend/
├── alembic/versions/
│   ├── 004_create_calendar_memberships_table.py
│   └── 005_create_invitations_table.py
└── app/
    ├── api/v1/
    │   ├── invitations.py
    │   └── members.py
    ├── core/
    │   └── permissions.py            # require_role() FastAPI dependency factory
    ├── models/
    │   ├── calendar_membership.py
    │   └── invitation.py
    ├── schemas/
    │   ├── invitation.py
    │   └── member.py
    └── services/
        └── sharing_service.py
```

```
backend/tests/
├── test_invitations.py
└── test_permissions.py
```

---

## Database Schema

```sql
-- schema: calendar_app
CREATE TABLE calendar_memberships (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    calendar_id UUID NOT NULL REFERENCES calendars(id) ON DELETE CASCADE,
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role        VARCHAR(20) NOT NULL CHECK (role IN ('owner', 'editor', 'viewer')),
    joined_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (calendar_id, user_id)
);

CREATE TABLE invitations (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    calendar_id UUID NOT NULL REFERENCES calendars(id) ON DELETE CASCADE,
    inviter_id  UUID NOT NULL REFERENCES users(id),
    invitee_id  UUID NOT NULL REFERENCES users(id),
    role        VARCHAR(20) NOT NULL CHECK (role IN ('editor', 'viewer')),
    status      VARCHAR(20) NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending', 'accepted', 'declined')),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at  TIMESTAMPTZ NOT NULL DEFAULT (now() + INTERVAL '7 days'),
    UNIQUE (calendar_id, invitee_id)  -- one active invite per person per calendar
);
```

---

## Permissions Model

`app/core/permissions.py` exposes a `require_role(*allowed_roles)` dependency factory:

```python
def require_role(*roles: str) -> Callable:
    async def dependency(
        calendar_id: UUID,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> CalendarMembership:
        membership = await get_membership(db, calendar_id, current_user.id)
        if membership is None:
            raise HTTPException(404)          # do not reveal calendar existence
        if membership.role not in roles:
            raise HTTPException(403)
        return membership
    return dependency
```

Usage in route handlers:
- `Depends(require_role("owner", "editor", "viewer"))` — any member may read
- `Depends(require_role("owner", "editor"))` — editor or owner may write
- `Depends(require_role("owner"))` — only owner may manage

---

## Dependencies

- Stage 01 (infrastructure).
- Stage 02 (`User` model, `get_current_user` dependency).
- Stage 03 (`Calendar` model, existing CRUD endpoints to be re-gated with permission checks).
