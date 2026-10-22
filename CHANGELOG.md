# Changelog

## 1.0.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-10-22

### Added
- Initial repository scaffold for nexus-pilot-alan-vo
- FastAPI backend with OIDC Keycloak authentication (PKCE, bearer tokens)
- React + TypeScript + Vite frontend with login, dashboard, viewport selector
- SQLite persistence with SQLAlchemy for parts and unfold operations
- Docker Compose with backend, frontend, Keycloak, and persistent volumes
- Sheet-metal unfold service skeleton (cadgen.unfold integration planned)
- STEP file upload and progressive loading service skeleton
- Backend test suite (≥12 tests): auth, CAD service, routes, models
- Frontend test suite (≥3 tests): app, API client, viewport selector
- CI workflow (GitHub Actions): backend pytest, frontend build/test, Docker builds
- Portfolio metadata (portfolio.json) with workflows and provider support
- Documentation: README with AI/ML evaluation, architecture, API reference, SSO/SAML setup