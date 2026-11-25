# Diapers Product Test 2026 — progress dashboard

Local page that reads the three Kobo forms and matches them on respondent ID.

1. Recruitment
2. Product test 1
3. Product test 2

A respondent has passed recruitment when every screen is cleared, including income bands 2–7. Product tests count only after that same ID is submitted on the product link.

## Start

From this folder:

```bash
python local_server.py
```

Open http://127.0.0.1:8766

The page loads on open and refreshes every minute. Use **Refresh from Kobo** to pull immediately. **Export CSV** downloads the respondent tracker.

The API token stays in `.env` on this machine. The browser never receives it.

## Deploy on Vercel

Import this repository in Vercel. The framework is already set to Flask.

Add one environment variable in the Vercel project settings:

- `KOBO_TOKEN` — the Kobo API token

The three form IDs are already set for recruitment, product test 1, and product test 2. Do not put the token in the repository. After the variable is saved, redeploy.
