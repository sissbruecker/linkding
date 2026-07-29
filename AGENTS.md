# AGENTS.md

## Stack

- **Backend:** Django 6 + DRF, Huey background tasks, SQLite by default (optional Postgres)
- **Frontend:** Lit web components, Hotwired Turbo, Rollup, PostCSS
- **Tooling:** Python 3.13, [uv](https://docs.astral.sh/uv/), Node.js, ruff, pytest, prettier, djlint

## Layout

| Path | Purpose |
|------|---------|
| `bookmarks/` | Main Django app (models, views, API, services, templates, frontend, tests) |
| `bookmarks/api/` | REST API |
| `bookmarks/services/` | Business logic (import/export, favicons, archiving, tags, etc.) |
| `bookmarks/frontend/` | JS components (Lit) |
| `bookmarks/styles/` | CSS themes |
| `bookmarks/tests/`, `bookmarks/tests_e2e/` | Unit/integration and Playwright e2e tests |
| `docs/` | Astro documentation site (separate package) |
| `docker/`, `scripts/` | Packaging and release helpers |
| `Makefile` | Canonical dev commands |

Prefer changing behavior in `bookmarks/services/` and thin views/API layers over stuffing logic into views.

## Setup

Prereqs: Python 3.13, uv, Node.js.

```bash
make init                          # uv sync, data dirs, migrate, npm install
uv run manage.py createsuperuser   # create a login for http://localhost:8000
```

## Day-to-day commands

Run these from the repo root. Always use `make` targets when one exists; use `uv run` only for commands without a Make target (e.g. `manage.py`, scoped pytest). Do not use ad-hoc venvs.

| Task | Command |
|------|---------|
| Django dev server | `make serve` → http://localhost:8000 |
| Frontend watch build | `make frontend` (`npm run dev`) |
| Background tasks (Huey) | `make tasks` |
| Unit/integration tests | `make test` (`pytest -n auto`) |
| Lint (Python) | `make lint` (`ruff check bookmarks`) |
| Format | `make format` (ruff + djlint + prettier) |
| E2E tests | `make e2e` (builds static assets + Playwright Chromium) |
| One-off management | `uv run manage.py <cmd>` |

Production-style frontend build (used by e2e prep): `npm run build`.

## Testing guidance

- Default: `make test`. Scope with pytest paths when iterating, e.g. `uv run pytest bookmarks/tests/test_bookmarks_api.py -q`.
- E2E lives under `bookmarks/tests_e2e/` (`e2e_test_*.py`); needs `make prepare-e2e` / `make e2e`.
- After behavior changes, run the nearest existing tests; add coverage next to similar tests in `bookmarks/tests/`.
- Don’t commit failing lint: `make lint` before finishing.

## Conventions

- Keep changes minimal and aligned with existing Django patterns in `bookmarks/`.
- Python: ruff-enforced style (isort, pyupgrade, bugbear, etc.); line length is not enforced (`E501` ignored).
- Templates: Django templates under `bookmarks/templates/`; format with djlint via `make format`.
- JS/CSS: edit `bookmarks/frontend/` and `bookmarks/styles/`; format with prettier via `make format`.
- User-facing options and Docker env vars are documented via `.env.sample` and `docs/`; update docs when adding options.
- Prefer small, focused PRs. Larger features should be discussed first (see README contributing note).

## Out of scope / caution

- Do not bump dependencies or rewrite Docker/release scripts unless the task requires it.
- `docs/` is a separate Node/Astro project; only touch it for documentation tasks.
- Default DB is SQLite under local `data/`; treat `data/` as local state (not source).
