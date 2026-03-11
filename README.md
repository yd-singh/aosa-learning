# Architecture Arcade

A standalone, offline-first study app for learning from [The Architecture of Open Source Applications]() as a technical PM.

## What it includes

- 89 study sessions across all four AOSA collections
- Real chapter URLs from the AOSA site
- Downloaded local chapter content for in-app reading
- Localized chapter figures and other AOSA-hosted assets
- PM-focused study prompts, activities, and boss-battle questions
- Local progress tracking, XP, streaks, bookmarks, and notes
- Reader routes like `?session=v1-02&view=reader`

Notes:
- The repo does not store the admin password.
- On first bootstrap, `ADMIN_PASSWORD` is required so the server can create the admin password hash.
- After the first successful startup, remove `ADMIN_PASSWORD` from your run command. The stored hash in `data/app.db` is then used for future logins.
- After that, only `join.ydsingh@gmail.com` can be admin.
- Learners created in the UI are always `learner` role users.
- Learner accounts must use usernames, not email addresses.

## Refresh the offline corpus

The bundler crawls the current AOSA site, downloads chapter pages, localizes images/assets, and regenerates the dataset bundle used by the app server.

```bash
python3 scripts/fetch_aosa.py
```

## Content layout

- `content/chapters/<session-id>/page.html`: raw downloaded chapter page
- `content/chapters/<session-id>/content.html`: transformed chapter body used by the app
- `content/chapters/<session-id>/meta.json`: per-session offline manifest
- `content/assets/...`: localized AOSA-hosted figures and assets

## Files

- `index.html`: app shell and reader layout
- `styles.css`: visual design, responsive layout, and reader prose styling
- `app.js`: rendering, routing, auth flow, admin UX, and server-backed progress
- `scripts/app_server.py`: multi-user app server with SQLite auth and progress storage
- `scripts/fetch_aosa.py`: offline bundler for the AOSA site
- `data/aosa_dataset.json`: raw structured dataset used by the server
- `content/`: downloaded chapter corpus and assets
