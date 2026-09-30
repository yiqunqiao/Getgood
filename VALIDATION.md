# Validation status

The demo runs locally on trusted input. Submitted Python runs in a separate, time-limited process with the user's file permissions; this is not sandbox isolation. No real learner study has been conducted or claimed.

## Automated checks

- `.venv/bin/python -m pytest tests -q`: **10 passed** on 2026-09-30. Coverage includes the full three-act progression, Guided success without hints staying at Needs guidance, consequence scoring, comparison runs leaving progress unchanged, risk-location matching, supported boundaries, invalid tests, execution timeout, malformed progress fallback, and API token enforcement.
- `node --check frontend/app.js`: passed.
- Python syntax check: passed.
- GitHub Actions: workflow added to run the integration suite and syntax check; its first remote run must be checked after push.

The local test run emitted one upstream Starlette/httpx TestClient deprecation warning.

## Browser review

Browser checks confirmed that the Guided consequence question stays hidden until a risk is marked, the evidence example fills the question, full comparison leaves progress unchanged, fixed coaching appears after the risk is identified, and the PR preview accepts a senior comment and tag, shows all three steps with local status, and opens the selected exercise. The previous review also confirmed anonymous variant feedback for a missed Guided risk. Full coverage of every visual state and viewport is not claimed.

## Limits

The case variants are hidden in the exercise UI, not inaccessible to a person with repository access. The PR page is a prepared concept case and does not integrate with GitHub. Concurrency is outside validated scope. Growth levels describe observed exercise evidence, not a general certification of engineering competence.
