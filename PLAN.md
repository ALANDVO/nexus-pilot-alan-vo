# Product development plan

Each round completes one feature or repair. Future items are planned, not implemented claims.

## Current round

core-skeleton

## Roadmap

### core-skeleton — FastAPI/React skeleton with OIDC auth and CAD geometry service

Status: in_progress

Acceptance:
- FastAPI app starts and serves health endpoint
- React frontend builds and loads
- OIDC Keycloak authentication flow works (login/callback/logout)
- SQLite persistence with models for CAD parts and unfold operations
- Docker compose with backend, frontend, Keycloak, and volumes
- Backend and frontend tests pass

Implementation: `backend/app/main.py`, `backend/app/api/routes.py`, `backend/app/models/__init__.py`, `backend/app/services/cad_service.py`, `backend/app/core/config.py`, `backend/app/core/auth.py`, `frontend/src/main.tsx`, `frontend/src/App.tsx`, `frontend/src/api/client.ts`, `frontend/src/components/Login.tsx`, `frontend/src/components/Dashboard.tsx`

Tests: `backend/tests/test_auth.py`, `backend/tests/test_cad_service.py`, `backend/tests/test_routes.py`, `frontend/src/__tests__/App.test.tsx`, `frontend/src/__tests__/client.test.ts`

### sheet-metal-unfold — Sheet-metal unfolding engine (cadgen.unfold)

Status: planned

Acceptance:
- Thickness detection from parallel planar face pairs
- Bend detection from coaxial cylindrical faces
- Flange tree construction and layout into XY plane
- Bend allowance calculation (K-factor and bend table)
- Unfolded output with profile, bend lines, and bend records
- Refusal for hems, curls, conical bends, variable thickness, collisions

Implementation: `backend/app/services/unfold.py`, `backend/app/models/unfold.py`

Tests: `backend/tests/test_unfold.py`

### viewport-selection — Viewport region selection for agent context

Status: planned

Acceptance:
- Selection box overlay on 3D viewport
- Face/edge picking capability
- Selected geometry exported as agent context
- Token usage reduction measurable

Implementation: `frontend/src/components/ViewportSelector.tsx`, `frontend/src/hooks/useViewportSelection.ts`

Tests: `frontend/src/__tests__/ViewportSelector.test.tsx`

### large-model-handling — Large STEP model loading with streaming/memory management

Status: planned

Acceptance:
- Progressive loading for large STEP files
- Memory envelope enforcement with graceful degradation
- Component-level loading control

Implementation: `backend/app/services/step_loader.py`, `frontend/src/components/ModelLoader.tsx`

Tests: `backend/tests/test_step_loader.py`

