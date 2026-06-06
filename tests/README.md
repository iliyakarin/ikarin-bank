# Tests

## Structure

```
tests/
├── unit/          # Fast, isolated unit tests (pytest)
├── integration/   # DB/service integration tests (pytest)
└── e2e/           # End-to-end browser tests (Playwright)
```

Backend also has its own test directory: `backend/tests/`

## Running Tests

```bash
# Backend unit tests
cd backend && pytest tests/ -v

# Integration tests
cd tests/integration && pytest -v

# E2E tests (requires running stack)
cd tests/e2e && npx playwright test

# Frontend Playwright tests
cd frontend && npx playwright test
```

## Key Notes
- E2E tests require the full Docker Compose stack running
- Backend tests use async fixtures via `pytest-asyncio`
- All test data uses artificial/mock values — no real PII
