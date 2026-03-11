# Make Tech PM Tech

A standalone AOSA study app for technical PMs.

This version is static and deployment-friendly:
- no backend server
- no app-side auth database
- no user table/admin APIs
- progress saved per browser via localStorage

## What it includes

- 89 study sessions across all four AOSA collections
- In-app chapter reading from local bundled content
- Localized chapter figures/assets
- PM-focused prompts, activities, and quiz checks
- Progress, XP, streaks, bookmarks, notes (browser-local)

## Run locally

```bash
python3 -m http.server 4173
```

Open `http://127.0.0.1:4173`.

## Deploy on Cloudflare Pages

1. Push this repo to GitHub.
2. Create a new Cloudflare Pages project from the repo.
3. Build settings:
- Framework preset: `None`
- Build command: (leave empty)
- Build output directory: `/` (root)
4. Deploy.

Because this is a static app, no runtime env vars are required.

## Add login gate with Cloudflare Access

Use Zero Trust Access in front of your Pages custom domain.

1. Attach a custom domain to the Pages project.
2. In Cloudflare Zero Trust, create an Access application (`Self-hosted`) for that hostname.
3. Add allow policies for the identities you want (for example, your email domain or specific users).
4. Optionally block/redirect direct `*.pages.dev` access and force custom-domain access only.

This gives cloud login protection without app backend auth.

## Sharing model

- You can host your own instance behind Access.
- Anyone else can clone/fork and deploy their own copy.
- Each deployment keeps user progress in each user's browser storage.

## Content layout

- `content/chapters/<session-id>/page.html`: raw downloaded chapter page
- `content/chapters/<session-id>/content.html`: transformed chapter body used by the app
- `content/chapters/<session-id>/meta.json`: per-session manifest
- `content/assets/...`: localized figures/assets

## Files

- `index.html`: app shell and layout
- `styles.css`: visual system and responsive styling
- `app.js`: static runtime (dataset load, rendering, progress persistence)
- `scripts/fetch_aosa.py`: corpus refresh script
- `data/aosa_dataset.json`: dataset used by the app
- `content/`: bundled chapter corpus and assets

## Optional legacy backend

`scripts/app_server.py` is retained only as an optional legacy path. It is not required for this static deployment setup.
