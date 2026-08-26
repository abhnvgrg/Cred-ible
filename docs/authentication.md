# Authentication: design decisions and how it works

This document holds the reasoning behind `backend/app/auth.py` and
`backend/app/storage.py`. The code itself is kept free of commentary, so
anything that needs a "why" lives here.

---

## Background

Two authentication systems were built independently on this repo and collided
in a merge:

| | JWT branch | Session branch |
|---|---|---|
| Hashing | scrypt (stdlib) | bcrypt |
| Token | HS256 JWT, stateless | opaque token, row in `sessions` |
| Database file | `backend/data/auth.sqlite3` | `backend/data/auth.sqlite3` |
| Extras | admin gating, 28 tests | organizations, memberships, password reset |

Git auto-merged `main.py` without flagging a conflict and produced a hybrid
that could not work: `/auth/login` issued a JWT while `/auth/me` and
`/auth/logout` looked that same token up as a row in the sessions table. Login
would have succeeded and every authenticated call afterwards returned 401.

The two designs were merged deliberately rather than one being discarded.

---

## Decision 1: server-side sessions, not JWTs

**Chosen:** an opaque 32-byte random token, with the database storing only its
SHA-256 fingerprint.

**Why:** revocation. A JWT is valid until it expires no matter what the server
subsequently decides, which means logout cannot actually log anyone out,
a password reset cannot evict an attacker who already holds a token, and a
demotion from admin to analyst does not apply until the old token ages out.
For a credit product, "sign out did not sign me out" is not an acceptable
property.

The secondary benefit is that there is no signing key. No key means no key
rotation, no key leakage, and no algorithm-confusion attacks — the class of
bug where a token carrying `alg: none` or an attacker-chosen asymmetric
algorithm is accepted as valid.

**Cost:** every authenticated request performs a database read. At this scale
that is a single indexed SQLite lookup on a primary key, which is not a
meaningful cost. If it ever becomes one, the fix is a cache with a short TTL,
not a return to stateless tokens.

## Decision 2: tokens are hashed at rest

The session token is a bearer credential: whoever holds it is the user. Stored
in the clear, the database file becomes a list of live logins — and that file
had already been committed to this repository once.

Session and reset tokens are therefore stored as `sha256(token)`. No salt or
key stretching is used, and none is needed: unlike a password, the token is
already 32 bytes of uniform randomness, so there is nothing to brute-force.

The raw token exists only in the response to the client and in the
`Authorization` header of subsequent requests.

## Decision 3: roles are read per request

The token carries no claims at all. `get_current_user` resolves the session to
a user, then reads that user's membership role from the database on every
request.

This is what makes revocation complete. A role embedded in a token would
outlive the change that revoked it.

An account with no membership resolves to `analyst`, the least-privileged
role, so a missing or malformed organization record can never be read as
elevated access.

## Decision 4: bcrypt with a SHA-256 pre-hash

bcrypt silently truncates its input at 72 bytes. A passphrase longer than that
would be authenticated by its first 72 bytes alone, so two different long
passwords sharing a prefix would both work.

Passwords are therefore pre-hashed to a fixed-width SHA-256 digest and base64
encoded before reaching bcrypt. Base64 also keeps the digest free of the NUL
bytes bcrypt truncates on.

`verify_password` catches `ValueError` and returns `False` rather than
propagating. `bcrypt.checkpw` raises on anything that is not a bcrypt hash,
and the retired JSON store held unsalted SHA-256 digests — without the catch,
those records crash the login endpoint instead of failing it.

---

## What was removed, and why

### The legacy JSON importer

`storage.py` originally imported `backend/data.json` into any empty database.
That file was committed to the repository and contained:

```json
{ "work_email": "a@a.com", "role": "admin",
  "password_hash": "ef797c8118f02dfb649607dd5d3f8c7623048c9c063d532cc95c5ed7a898a64f" }
```

An admin account, with an unsalted SHA-256 password hash, seeded automatically
on every fresh deployment. The importer and the file are both gone, and
`backend/data/` is gitignored.

### The reset token in the HTTP response

`/auth/password-reset/request` returned the reset token to the caller:

```python
return {"message": "Password reset token created", "token": token}
```

Anyone could reset any account by asking for it — the token is the entire
proof of ownership, and handing it to an unauthenticated caller defeats the
flow completely.

The endpoint now returns the same message whether or not the address is
registered, which also stops it being used to enumerate accounts. Outside
production the token is written to the server log so local testing works
without a mail service. In production it is never logged; a real deployment
needs a mail provider wired in here.

### Query parameters on password reset

Both reset endpoints took bare query parameters, meaning the new password
travelled in the URL and was written verbatim into every access log and
browser history entry. Both now take a request body.

### Self-service admin

Registration returned `role="admin"` to every caller, so anyone could mint
themselves an administrator. Registration now always creates an `analyst`, the
role is not read from the request payload, and the `memberships` table carries
a `CHECK` constraint so an unknown role cannot be stored even if the API layer
is wrong.

---

## Login throttling

Hashing makes a single guess expensive; only throttling makes a campaign of
guesses expensive. `/auth/login` allows 8 failures per account in a 5-minute
window, then answers `429` with a `Retry-After` header.

The bucket is keyed by **email, not IP address**, for two reasons: an attacker
distributing guesses across addresses would otherwise bypass it entirely, and
users behind shared NAT would otherwise lock each other out.

While an account is throttled, even the correct password is refused. Allowing
the correct password through would let an attacker step around the limit by
simply guessing right on the next attempt.

This is in-process state. It is correct for a single-instance deployment and
resets on restart; running multiple instances needs it moved to Redis or the
database.

---

## Failure responses are deliberately uniform

`/auth/login` returns one message for "no such account" and "wrong password",
and `authenticate` runs a dummy bcrypt verification against a throwaway hash
when the account does not exist, so both paths take comparable time. Without
both halves, the endpoint reports which email addresses are registered — by
message, or by response time.

The same reasoning applies to `/auth/password-reset/request`.

---

## Structure

`storage.py` is persistence: SQL, schema, and nothing else.
`auth.py` is the security layer: hashing policy, sessions, throttling, and the
FastAPI dependencies.

The split exists so every credential decision is in one file and can be read
end to end during a review. `require_admin` depends on `get_current_user`, so
an endpoint cannot accidentally be given authorisation without authentication.

---

## Schema note

The `sessions` and `password_resets` tables are keyed on `token_hash`, where
earlier versions used `session_token` / `token`. There is no migration: an
existing deployed database must be recreated. Registered users and their
passwords are unaffected — only open sessions and pending reset tokens are
lost.

---

## Known limits

- Throttle state is per-process and resets on restart.
- Reset tokens are logged, not emailed. Wiring a mail provider is the
  remaining work before this flow is usable in production.
- The frontend stores the bearer token in `localStorage`, which is readable by
  any successful XSS. An httpOnly cookie would be stronger; it needs CSRF
  protection to go with it.
- Sessions have a fixed TTL and are not extended on activity.
