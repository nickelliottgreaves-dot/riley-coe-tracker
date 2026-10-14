# Riley & Coe Tracker

This repository contains an automated pipeline (GitHub Actions) to:

- Scrape BBC 6 Music "Riley & Coe" tracklistings and build/maintain an artists pool (artists.json).
- Check Newcastle venues for gigs by artists in the pool.
- Each run commits a structured JSON report (matches/YYYY-MM-DD.json) and a human-readable Markdown report (reports/YYYY-MM-DD.md).
- Creates a GitHub Issue weekly summarising matches (so you can receive GitHub email notifications by watching the repo).

No external secrets are required for the default flow (GitHub Issues + commit reports). Optional API keys (Bandsintown, Songkick, Ticketmaster) can be added later as repository secrets to improve event coverage.

Usage
1. Watch this repository on GitHub (select "All Activity") to receive weekly email notifications when I create the report issue.
2. The workflow runs weekly (Monday 09:00 GMT) and also runs on push or when manually triggered.
3. Check the matches/ and reports/ directories for persisted output.

If you later want direct email delivery, add SMTP or SendGrid credentials as repository secrets and switch the workflow.

Files of interest
- artists.json — seeded baseline artist list (deduped where possible).
- scripts/ingest_tracks.py — fetches Riley & Coe tracklists and updates the artist pool.
- scripts/fetch_events.py — looks up events for artists at the specified Newcastle venues.
- .github/workflows/weekly.yml — scheduled Action that runs the pipeline and creates a weekly GitHub Issue.

Contact
If anything needs to be changed (venues, schedule, notification method), open an issue in this repository.
