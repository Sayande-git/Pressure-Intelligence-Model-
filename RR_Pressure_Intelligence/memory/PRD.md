# PRD — RR SupeRR Selector S2 · Pressure Intelligence Platform

## Original problem
Rajasthan Royals SupeRR Selector Season 2, Round 1: identify the most reliable players under pressure. Two separate Top-10 lists (batters, bowlers), with a reproducible methodology report and an IPL franchise-level analytics dashboard built from the supplied data pack (IPL + T20I + Emerging, 2022-26). Full master prompt covers data audit, eligibility, pressure engine, batting and bowling models, venue intelligence, validation, evidence, versioning, requirement tracker and PDF report.

## User choices
- Eligibility: mark players capped when the data proves it (a T20I appearance means Ineligible in the "Uncapped lens"); everyone else is Unverified. The official PDF scope treats all players as eligible.
- Top-10 lists show all qualifying players, each with a status flag.
- Outputs: PDF methodology report and an interactive dashboard.

## Architecture
- `backend/analytics/engine.py`: ingest, audit, pre-ball state reconstruction, logistic win-probability models (setting and chasing), Leverage Index, pressure tiers set within each innings (P50/P80), venue factor (Kruskal-Wallis test), context expectations, wicket run value from run expectancy.
- `backend/analytics/ratings.py`: player universe and eligibility flags, runs value (RV) per ball, empirical-Bayes Q/D/C rating, bootstrap of ranks, weight/threshold/sample sensitivity, temporal stability, outlier influence, match evidence.
- `backend/analytics/run.py`: runs the whole pipeline. Writes JSON, CSV and the PDF to `outputs/<version>/`, keeps `registry.json` and a schema change log.
- `backend/analytics/report.py`: 25-section reportlab PDF with matplotlib charts.
- `server.py`: `/api/data/{name}`, `/api/export/{file}`, `/api/versions`, dataset zip upload (re-runs the pipeline in the background), version activation, eligibility overrides (MongoDB).
- Frontend: React app with 12 pages (Overview, Data, Eligibility, Pressure, Batting, Bowling, Venues, Rankings, Evidence, Validation, Methodology, Reports).

## Implemented (2026-11-10)
- Full pipeline on the original dataset (version 6ffc18bfb9): 138 qualified batters and 58 qualified bowlers.
- PDF report, CSV exports and engineered deliveries export.
- Dashboard with all pages working.
- Testing: backend 100%. Frontend fixes applied for shared route state, pagination reset, mobile overflow and sort.

## Known limitations
- No venue names, pitch, weather or boundary data in the pack.
- Bye, leg-bye and wide run values are not stored, so team totals are approximate.
- Uncapped status cannot be proven from the data alone. Only 4 bowlers qualify under the uncapped lens.

## Backlog
- P1: external, per-player verification of uncapped status.
- P1: opposition-strength adjustment.
- P2: shortlist comparison view.
- P2: PPT export.
