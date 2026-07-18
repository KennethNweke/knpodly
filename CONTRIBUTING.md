# Contributing to Knpodly

Thanks for your interest in improving Knpodly, a self-hosted educational Linux
lab platform.

## Development setup

1. Fork and clone the repo.
2. Copy `.env.example` to `.env` and fill in values.
3. Backend: `cd backend && python -m venv .venv && source .venv/bin/activate && pip install -r requirements-dev.txt`
4. Frontend: `cd frontend && npm install`
5. Bring up dependencies only (Postgres/Redis) with `docker compose -f docker-compose.dev.yml up -d db redis`
6. Run backend: `uvicorn app.main:app --reload`
7. Run frontend: `npm run dev`

## Branching

- `main` is always deployable.
- Feature branches: `feature/<short-description>`
- Bugfix branches: `fix/<short-description>`

## Commit style

Use [Conventional Commits](https://www.conventionalcommits.org/), e.g.
`feat(api): add VM extension endpoint`, `fix(worker): correct overlay cleanup race`.

## Code quality

- Backend: `black`, `ruff`, `mypy` must pass. Run `make lint` in `backend/`.
- Frontend: `eslint` + `prettier` must pass. Run `npm run lint` in `frontend/`.
- New backend logic requires unit tests (`pytest`) and, where it touches VM
  lifecycle, an integration test using the fake libvirt driver
  (`app/services/libvirt_client.py` supports a `LIBVIRT_DRIVER=fake` mode).

## Pull requests

- Fill in the PR template.
- Link the issue it closes.
- Keep PRs focused; large architectural changes should start as a discussion/issue first.

## Reporting security issues

Do not open a public issue for security vulnerabilities. Email the
maintainers (see `SECURITY.md`) instead.
