# RUN ME FIRST — SPILTON local quick start

This folder is the **fixed** project. It already includes a ready `.env`, so
there is **no database or Docker setup needed** (it uses SQLite).

---

## 1. Start the API  (terminal 1)

```bash
cd services/api

python -m venv .venv
# Windows:      .\.venv\Scripts\Activate.ps1
# macOS/Linux:  source .venv/bin/activate

python -m pip install -r requirements.txt

alembic upgrade head
python -m app.db.load_lgd    # real State / District / Mandal / Village data (~1 min)
python -m app.db.seed        # demo rescuers + demo accounts
uvicorn app.main:app --reload --port 8000
```

Leave this terminal running.

## 2. Start the website  (terminal 2, from this project root)

```bash
npm install
npm run dev:web
```

Then open <http://localhost:3000>

> Use `npm install` (NOT `npm ci` — the lock file in this repo is out of sync).

---

## 3. Check that it works

| What | Where | Expected |
| --- | --- | --- |
| API alive | <http://localhost:8000/health> | `{"status":"ok"}` |
| Website | <http://localhost:3000/login> | Login page loads |
| Sign in | create an account on `/register` | Redirects, no "Failed to fetch" |
| Backend suite | `cd services/api && python -m pytest tests -q` | `57 passed` |

Demo logins created by the seed (local-only, fictional, password `ChangeThisDemo123!`):

| Role | Email |
| --- | --- |
| Admin | `admin.demo@spilton-demo.example` |
| Citizen | `citizen.demo@spilton-demo.example` |
| Rescuer (snake catcher) | `rescuer.ravi.demo@spilton-demo.example` |
| Rescuer (snake catcher) | `rescuer.anitha.demo@spilton-demo.example` |

`load_lgd` loads a bundled, openly-licensed extract of the India Local
Government Directory (**36 states, 763 districts, 6,921 mandals, 95,457
villages** across the five southern states) so the State → District → Mandal →
Village selectors and the location search work immediately.

The seed then adds two **verified, available demo rescuers**, so the booking
flow below works out of the box. All of it is clearly marked as demo data.

---

## Try the "book a nearby snake catcher" flow

This works like ordering from a nearby store.

1. Open <http://localhost:3000> → **Book a snake catcher** (or the top nav → *Demo rescuers*).
2. Share your location (or pick Telangana → Hyderabad). Two demo rescuers appear, sorted by distance.
3. Open one → **Request** → describe the situation, confirm the demo/safety box, submit.
4. Now act as the rescuer: open a **private/incognito window**, sign in as
   `rescuer.ravi.demo@spilton-demo.example`, go to **Rescuer desk** and **Accept** the request.
5. Back in the first window, **Bookings** shows the accepted status and **live tracking**
   (distance / journey state). A notification appears for the "rescuer accepted" event.
6. Open the booking and use **Message in the app** to chat with the rescuer
   (phone numbers stay hidden). Both sides see the same thread.
   A **Masked calling line** card also appears — a platform proxy number, like a
   delivery app. The rescuer's line only activates once they mark arrival, so
   neither side ever sees the other's real phone number.
7. The rescuer can share location, mark arrival, and a **demo payment** (cash or online)
   is recorded under **Payments**.

Rescuers who tick extra mandals in **Join as catcher** show a
**"Serves your mandal"** badge to customers searching that mandal.

> Everything here is a **simulation** — no real rescuer is dispatched and no real
> money moves. That is by design.

---

## 4. Optional extras (only if you want them)

**Email OTP (Gmail)** — open `services/api/.env` and fill the `SMTP_*` lines
with your Gmail App Password. Without it, the OTP code is printed in the API
console so you can still test the flow.

**Google / Microsoft login** — put your OAuth client ID + secret in
`services/api/.env` (`GOOGLE_*`, `MICROSOFT_*`). Step-by-step instructions
(Google Cloud, Azure, Gmail App Password) are in **AUTH_SETUP.md**.

---

## 5. Mobile app (optional)

```bash
npm run dev:mobile
```

Scan the QR with Expo Go, or press `a` / `i` for an Android / iOS emulator.

---

## Troubleshooting

- **"Failed to fetch"** on login → the API is not running. Check terminal 1,
  and that <http://localhost:8000/health> returns ok.
- **`alembic: command not found`** → activate the virtualenv first (step 1).
- **API crashes on start** → make sure you are running from inside
  `services/api` (so it finds `.env`).
- Full background and provider setup: see **AUTH_SETUP.md**.
