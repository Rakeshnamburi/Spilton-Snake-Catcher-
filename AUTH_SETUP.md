# SPILTON — Authentication Setup & Fix Guide

This guide covers (1) why login/signup showed **"Failed to fetch"**, (2) how to
run the project locally, and (3) how to turn on **Email OTP**, **Google**, and
**Microsoft** sign-in on both the website and the mobile app.

---

## 1. Why you were seeing "Failed to fetch"

"Failed to fetch" is a **browser-level** error. It means the browser never got a
response from the API at all — it is *not* a wrong-password error. There were
two things going on:

### 1a. The API was crashing on startup (root cause — now fixed)

The README says to copy `.env.example` to `services/api/.env`. That file sets:

```
DEMO_MODE=true
AUTHORIZED_OPERATION_ENABLED=false
PRICING_AUTHORIZED=false
PAYMENTS_ENABLED=false
```

The settings model declares these as `Literal[True]` / `Literal[False]`. Pydantic
does **not** coerce the strings `"true"` / `"false"` into those literal types, so
the API raised a `ValidationError` and **never started**. The website loaded fine
(it is static), but every API call — including login — died with "Failed to
fetch".

**Fixed** in `services/api/app/core/config.py` with a `coerce_literal_bool`
validator. The API now boots with the documented env file, and the safety
constraints (demo mode on, payments off) are unchanged.

### 1b. Checklist if you still see "Failed to fetch"

The web client now shows a clearer message naming the API URL. Work through:

1. **Is the API actually running?** Open <http://localhost:8000/health> — it
   should return `{"status":"ok"}`. If not, start it (section 2).
2. **Did the API crash at boot?** Read the uvicorn terminal — a traceback there
   is the real cause.
3. **Database reachable?** If you use PostgreSQL, `docker compose up -d postgres
   redis` must be running and `alembic upgrade head` must have succeeded.
4. **Correct API URL?** The web app calls `NEXT_PUBLIC_API_URL` (default
   `http://localhost:8000`). If your API runs elsewhere, create
   `apps/web/.env.local` with `NEXT_PUBLIC_API_URL=http://your-host:port`.
5. **CORS?** `WEB_ORIGINS` in the API env must include the site origin
   (default `http://localhost:3000,http://localhost:8081`).

---

## 2. Running locally

### Option A — Fast start, no Docker (SQLite)

Use this to get running in a couple of minutes. It needs no PostgreSQL.

```bash
# from the repository root
python -m venv .venv
# Windows: .\.venv\Scripts\Activate.ps1      macOS/Linux: source .venv/bin/activate
python -m pip install -r services/api/requirements.txt

cd services/api
cp ../../.env.example .env
```

Now edit `services/api/.env` and set these three lines (SQLite instead of Postgres):

```
DATABASE_URL=sqlite:///./spilton.db
JWT_SECRET=change-me-to-a-random-string-of-at-least-32-chars
ENVIRONMENT=development
```

Then create the schema, seed demo data, and start the API:

```bash
alembic upgrade head
python -m app.db.seed          # optional fictional demo accounts
uvicorn app.main:app --reload --port 8000
```

In a second terminal, start the website:

```bash
npm install
npm run dev:web                # http://localhost:3000
```

The seeded demo logins (fictional, local-only) are:

- Admin — `admin.demo@spilton-demo.example` / `ChangeThisDemo123!`
- Citizen — `citizen.demo@spilton-demo.example` / `ChangeThisDemo123!`

### Option B — Docker stack (PostgreSQL/PostGIS + Redis)

```bash
cp .env.example .env           # root file, used by docker compose
cp .env.example services/api/.env
docker compose up -d postgres redis
cd services/api && alembic upgrade head && python -m app.db.seed && cd ../..
npm install
npm run dev:web
```

> **Note:** `npm ci` fails on this repo because `package-lock.json` is out of
> sync (`react-native-worklets` is missing from it). Use `npm install`.

---

## 3. Sign-in methods

The website and mobile app now offer four ways to sign in:

| Method | Where | Needs configuration? |
| --- | --- | --- |
| Email + password | Web + Mobile | No |
| Email one-time code (OTP) | Web + Mobile | SMTP for real email (else printed to the API console) |
| Google | Web + Mobile | Google Cloud OAuth client |
| Microsoft | Web + Mobile | Azure app registration |

`GET /api/v1/auth/providers` tells the UI which methods are enabled; unconfigured
social buttons simply do not appear.

---

## 4. Configure Email OTP (Gmail SMTP)

The OTP is a 6-digit code, hashed at rest, valid for 10 minutes, single-use,
with a resend cooldown and attempt limit.

### Using a Gmail App Password

1. Turn on **2-Step Verification** for your Google account.
2. Go to <https://myaccount.google.com/apppasswords> and create an **App
   password** (16 characters, shown as four groups).
3. In `services/api/.env` set:

```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your.address@gmail.com
SMTP_PASSWORD=the16charapppassword
SMTP_FROM_ADDRESS=your.address@gmail.com
```

Restart the API. Codes will now be emailed.

### Without SMTP

Leave `SMTP_*` blank. In `ENVIRONMENT=development` the code is written to the API
log **and** returned in the response as `dev_code`, so you can test the flow
instantly. It is never returned outside development.

**Flow:** `POST /api/v1/auth/otp/request {email}` → `POST
/api/v1/auth/otp/verify {email, code}`. Verifying creates the account on first
use, then returns a session exactly like password login.

---

## 5. Configure Google sign-in

1. Open <https://console.cloud.google.com/> and create (or pick) a project.
2. **APIs & Services → OAuth consent screen** — choose *External*, fill in the app
   name and support email, and add your own Google account under **Test users**
   while the app is in testing.
3. **APIs & Services → Credentials → Create credentials → OAuth client ID**.
   - Application type: **Web application**
   - **Authorised redirect URI** (exact):
     `http://localhost:8000/api/v1/auth/oauth/google/callback`
4. Copy the **Client ID** and **Client secret** into `services/api/.env`:

```
GOOGLE_CLIENT_ID=xxxxxxxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=xxxxxxxx
API_PUBLIC_URL=http://localhost:8000
```

5. Restart the API. A **Continue with Google** button now appears on
   `/login` and `/register` (web) and on the mobile sign-in/registration screens.

> For production, add your real HTTPS domain to the authorised redirect URIs and
> set `API_PUBLIC_URL` to that public API URL.

---

## 6. Configure Microsoft sign-in

1. Open <https://portal.azure.com/> → **Microsoft Entra ID → App registrations →
   New registration**.
2. Supported account types: *Accounts in any organizational directory and personal
   Microsoft accounts* (to allow Outlook/Hotmail/Live users).
3. **Redirect URI**: platform **Web**, value
   `http://localhost:8000/api/v1/auth/oauth/microsoft/callback`
4. **Certificates & secrets → New client secret** — copy the *value*.
5. Under **API permissions**, ensure `openid`, `email`, `profile`, `User.Read`
   (Microsoft Graph) are present (grant admin consent if your tenant requires it).
6. Add to `services/api/.env`:

```
MICROSOFT_CLIENT_ID=your-application-client-id
MICROSOFT_CLIENT_SECRET=your-client-secret-value
MICROSOFT_TENANT=common
```

7. Restart the API. A **Continue with Microsoft** button appears.

---

## 7. How each flow works (technical)

- **OTP** — code hashed with an HMAC keyed by `JWT_SECRET`, stored in
  `auth_otp_codes`, expires per `OTP_TTL_MINUTES`.
- **OAuth (web)** — the button opens
  `/api/v1/auth/oauth/{provider}/start?mode=web`; the provider redirects to the
  API callback, which exchanges the code, finds/creates the user, links the
  identity in `oauth_identities`, sets the session cookie, and redirects to
  `/auth/callback` on the site.
- **OAuth (mobile)** — `mode=mobile` makes the API redirect to the deep link
  `spilton://auth-callback?code=...`; the app exchanges that one-time code at
  `POST /api/v1/auth/oauth/exchange` for a bearer token stored in SecureStore.
- **Logout** — `POST /api/v1/auth/logout` bumps the user's token version, which
  invalidates every previously issued JWT, and clears the cookies.

Accounts created via OTP or a social provider have `phone = NULL` and
`password_hash = NULL` (both columns are now nullable). An existing account is
reused when the email matches, so password, OTP, Google, and Microsoft all land
on the same user.

---

## 8. Quick test

```bash
# API health
curl http://localhost:8000/health

# Which methods are enabled
curl http://localhost:8000/api/v1/auth/providers

# Request an OTP (dev mode returns dev_code in the response)
curl -X POST http://localhost:8000/api/v1/auth/otp/request \
  -H 'Content-Type: application/json' -d '{"email":"you@example.com"}'
```

Automated tests for the new flows:

```bash
cd services/api && python -m pytest tests/test_auth_social.py -q
```

---

## 9. Files changed / added

**API**
- `app/core/config.py` — fixed the startup crash; added OTP + OAuth settings.
- `app/models/entities.py` — `users.phone` / `users.password_hash` nullable;
  new `OAuthIdentity` and `AuthOtp` models.
- `app/schemas/api.py` — new request/response schemas.
- `app/services/auth_email.py` — OTP email sender (SMTP, console fallback).
- `app/api/auth_social.py` — OTP + OAuth endpoints.
- `app/main.py` — registers the new router and CSRF exemptions.
- `alembic/versions/0007_auth_otp_oauth.py` — migration.
- `tests/test_auth_social.py` — tests.

**Web**
- `features/auth/auth-form.tsx` — Google / Microsoft / OTP UI.
- `app/auth/callback/page.tsx` — OAuth landing page.
- `lib/api.ts` — actionable network-error message.

**Mobile**
- `services/auth.ts`, `app/auth-callback.tsx`, `app/login.tsx`,
  `app/register.tsx`.

**Config**
- `.env.example` — new OAuth/OTP variables documented.

---

## 10. Security notes

- Never commit `.env` — it holds your OAuth secrets and Gmail App Password.
- OTP codes are hashed, single-use, rate-limited, and never returned outside
  development.
- OAuth `state` is a signed, short-lived JWT (CSRF/replay protection).
- Rotating the token version on logout invalidates old tokens everywhere.
- The demo-mode safety gates (no live dispatch, no real payments) are unchanged.
