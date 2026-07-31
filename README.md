# Anonymous Messaging Bot (NGL/Qooh-style)

Production-ready Telegram anonymous messaging SaaS bot built with **Python 3.12**, **aiogram 3**,
**PostgreSQL**, **SQLAlchemy 2.0 (async)**, and **Alembic**, deployed to **Render.com** in
webhook mode.

## Features

- Personal anonymous link (`https://t.me/BOT?start=<token>`), regenerable at any time.
- Text / photo / voice anonymous messages, with threaded replies.
- **Bilingual UI (Uzbek / English)**: language is auto-detected from Telegram's client locale on
  first `/start` and can be changed anytime via *Settings → 🌐 Language*. All bot-facing text
  (menus, buttons, confirmations, errors, admin panel) is translated; admin-authored content
  (broadcast text, plan names) stays in whatever language the admin typed it in.
- **Super admin can appoint/remove admins from inside the bot** — no redeploy or env var change
  needed. Only the super admin (set via `SUPER_ADMIN_IDS`) sees *Admin panel → 👮 Manage admins*,
  where they can add an admin by Telegram ID or tap to remove one. `/addadmin <id>` and
  `/removeadmin <id>` commands work the same way. Appointed admins get full admin-panel access
  (overview, broadcast, reports, pricing) but cannot manage other admins themselves.
- Premium via **Telegram Stars (XTR)**: Daily / Weekly / Yearly plans, admin-editable prices.
- **Critical premium rule**: a message's sender can only ever be revealed if the receiver was
  Premium *at the moment the message arrived* (`can_reveal_sender`, frozen permanently on the
  row). Old anonymous messages stay anonymous forever, even after upgrading.
- Premium analytics: daily / weekly / yearly stats, top senders (revealable only), most active hours.
- Anti-spam: sliding-window rate limit + duplicate-message detection.
- Sender blocking (Premium), reporting, and an admin panel: overview, broadcast (text or
  photo+text), reports review with one-tap ban, ban/unban, price editing.
- Files are **never stored on the server** — only Telegram `file_id`s are persisted.

## Project layout

```
app/
  handlers/       # aiogram routers: start, anonymous_send, reply, premium, payments,
                  #   stats, settings (blocks), reports, admin
  middlewares/     # DB session injection, in-memory throttling
  services/        # business logic (repository/service pattern)
  repositories/    # DB access layer (SQLAlchemy 2.0 async)
  models/          # SQLAlchemy ORM models
  keyboards/       # inline keyboard builders
  utils/           # tokens, logging, text helpers
  config.py        # env-var driven settings
  db.py            # async engine/session factory
  bot.py           # entrypoint: builds Bot/Dispatcher, runs aiohttp webhook server
alembic/           # migrations (async, targets app.models.Base.metadata)
requirements.txt
render.yaml
railway.json
Dockerfile
.env.example
```

## Local setup

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# fill in BOT_TOKEN, BOT_USERNAME, DATABASE_URL, WEBHOOK_BASE_URL (e.g. an ngrok URL),
# WEBHOOK_SECRET, SUPER_ADMIN_IDS

alembic upgrade head
python -m app.bot
```

For local testing without a public HTTPS URL, tunnel with `ngrok http 8080` and set
`WEBHOOK_BASE_URL` to the ngrok URL.

## Deploying to Render.com

1. **Push this project to a GitHub repository.**

2. **Create a Postgres database on Render** (or let `render.yaml` create one for you — see
   step 4). Note its connection string; Render keeps it available across redeploys, so your
   data survives.

3. **Get a bot token** from [@BotFather](https://t.me/BotFather) and note your bot's `@username`.

4. **Deploy via Blueprint**: In the Render dashboard, choose *New → Blueprint*, point it at your
   repo — `render.yaml` at the project root will provision both the web service (Docker) and the
   Postgres database automatically.

   Alternatively, deploy manually:
   - *New → Web Service* → connect the repo → Environment: **Docker**.
   - Attach/create a Postgres instance and copy its **Internal Connection String** into
     `DATABASE_URL`.

5. **Set environment variables** on the web service (Render dashboard → Environment):
   - `BOT_TOKEN`
   - `BOT_USERNAME`
   - `DATABASE_URL` (from the attached Postgres instance)
   - `WEBHOOK_BASE_URL` = your Render service URL, e.g. `https://ngl-bot.onrender.com`
   - `WEBHOOK_SECRET` = any random string (Render can auto-generate this, see `render.yaml`)
   - `SUPER_ADMIN_IDS` = comma-separated Telegram user IDs of the bot owner(s)
   - Optional tuning: `MAX_MSG_PER_WINDOW`, `ANTISPAM_WINDOW_SECONDS`, `MAX_VOICE_SECONDS`,
     `MAX_VOICE_BYTES`, `MAX_PHOTO_BYTES`, `LOG_LEVEL`

6. **Deploy.** The Dockerfile runs `alembic upgrade head` before starting the bot, so the schema
   is created/updated automatically on every deploy — no manual migration step needed. (If you're
   upgrading an existing deployment onto this version, migration `0002` adds the `admin` role
   value and the `language` column automatically.)

7. **Verify the webhook**: on startup the bot calls `setWebhook` itself. Check
   `https://api.telegram.org/bot<TOKEN>/getWebhookInfo` to confirm `url` matches your service and
   `pending_update_count` is draining.

8. **Bootstrap admin access**: message the bot from a Telegram account whose ID is listed in
   `SUPER_ADMIN_IDS`, then send `/admin` to open the admin panel. Default plan prices
   (Daily/Weekly/Yearly) are seeded automatically on first startup — edit them anytime via
   *Admin panel → Manage prices*.

## Deploying to Railway

1. **Push this project to a GitHub repository** (same as above).

2. In [Railway](https://railway.app), click **New Project → Deploy from GitHub repo** and select
   your repo. Railway detects the `Dockerfile` automatically (the included `railway.json` pins the
   builder to Docker and points the health check at `/health`).

3. **Add a Postgres database**: in the same project, click **+ New → Database → Add PostgreSQL**.
   Railway creates it and exposes a `DATABASE_URL` variable automatically.

4. **Link the database to the bot service**: open the bot service → *Variables* → click
   **+ New Variable → Add Reference** → pick the Postgres service's `DATABASE_URL`. This keeps the
   connection string in sync automatically (survives redeploys and credential rotation).

5. **Generate a public domain** for the bot service: *Settings → Networking → Generate Domain*.
   Copy the resulting URL, e.g. `https://ngl-bot-production.up.railway.app`.

6. **Set the remaining environment variables** on the bot service (*Variables* tab):
   - `BOT_TOKEN`
   - `BOT_USERNAME`
   - `WEBHOOK_BASE_URL` = the domain from step 5 (no trailing slash)
   - `WEBHOOK_PATH` = `/webhook`
   - `WEBHOOK_SECRET` = any random string
   - `SUPER_ADMIN_IDS` = your Telegram user ID (comma-separated if more than one)
   - Optional tuning: `MAX_MSG_PER_WINDOW`, `ANTISPAM_WINDOW_SECONDS`, `MAX_VOICE_SECONDS`,
     `MAX_VOICE_BYTES`, `MAX_PHOTO_BYTES`, `LOG_LEVEL`

   Railway injects `PORT` itself — don't set it manually; `app/config.py` already reads it.

7. **Deploy.** Railway builds the Docker image and runs
   `alembic upgrade head && python -m app.bot` automatically (from `railway.json`/`Dockerfile`),
   so the schema is created on first boot and kept up to date on every redeploy.

8. **Verify the webhook**: check
   `https://api.telegram.org/bot<TOKEN>/getWebhookInfo` — `url` should match your Railway domain
   and `pending_update_count` should drain to 0.

9. Message the bot from the Telegram account listed in `SUPER_ADMIN_IDS`, then send `/admin` to
   confirm the admin panel opens.

**On redeploys**: Railway's Postgres is a separate, persistent service — pushing new code and
redeploying the bot service never touches or wipes the database, exactly like on Render.



- Prices are in **XTR** (Telegram Stars) integer amounts — no real-money currency codes needed.
- The bot implements `send_invoice`, `pre_checkout_query` (auto-approved unless the invoice is
  stale), and `successful_payment`, which atomically marks the payment paid, extends
  `premium_until` (stacking on top of any remaining time), and records a `PremiumEvent` for audit.

## Extending

- Swap `ThrottlingMiddleware`'s in-memory store for Redis if you scale to multiple instances
  (Render's `web` service type can run multiple replicas, and in-memory rate limiting is
  per-instance).
- The optional captcha mentioned in anti-spam requirements is stubbed via the `settings` table
  (`Setting` model) — wire a captcha challenge into `anonymous_send.py` keyed off a
  `captcha_enabled` setting if needed.
