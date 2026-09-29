# GetGood — The judgement lab

A local hackathon demo for practising evidence-backed review of AI-generated code.

## Start on macOS

Requires Python 3.10 or newer. Open this folder in VS Code, then open **Terminal → New Terminal**:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python run.py
```

Open **http://127.0.0.1:8000** in your browser. Keep the terminal running. Stop with **Control+C**.

Next time, run only:

```bash
source .venv/bin/activate
python run.py
```

Windows PowerShell: use `py -m venv .venv` and `.venv\Scripts\Activate.ps1`, then the same install/run commands. If port 8000 is occupied, stop the old process or run `python -m uvicorn backend.app:app --host 127.0.0.1 --port 8001` and open port 8001.

## Architecture

- `frontend/`: English HTML/CSS/JavaScript UI, served by FastAPI. No Node build step, CDN or external fonts.
- `backend/app.py`: API, server-recorded hint usage, local JSON progress.
- `backend/grader.py`: fresh temporary directory per target, pytest JUnit XML, 5-second timeout.
- `tasks/`: three exercises with shown code, reference code and three faulty variants each.
- `harness/conftest.py`: fresh fake database, gateway and wallet per test.
- `tests/`: integration checks for the three-act journey, invalid code, boundaries and timeout.

The initial frontend deliberately uses plain JavaScript instead of the document's proposed Next.js to make the first version easy to run. The API can support a replacement frontend later.

## Grading rules

- `Run on reference` checks the reference implementation only and does not update progress.
- `Submit` first checks the reference. If it passes, the suite runs against V1, V2 and V3.
- Only assertion failures count as caught variants. Syntax/collection errors, exceptions, skipped tests and timeouts do not count as evidence.
- A failed assertion on the reference means the test rejects correct behavior; this may be overblocking or a bad test expectation, not automatically an accurately diagnosed learner misconception.
- Judgement matching uses risk type and the exact external-effect line. The current UI supports one judgement per exercise because these exercises each have at most one known risk. Third exercise expects no risk found within the stated scope.
- Verified boundaries need the corresponding variants to be caught. Concurrent execution has no validator and cannot be marked verified.
- Guided success stays at Needs guidance. Independent success in a new exercise can reach Independent. Independent success in both coupon and refund-exception tasks reaches Verified across scenarios. These are two distinct business contexts; a later failed submission lowers the level by one.
- An honest unverified boundary does not erase evidence already established for sequential operations. Concurrency is shown separately as unverified.
- Levels are demo evidence labels, not a validated measurement of general engineering competence.

## Scope and limitations

This is a **single-learner local demo for trusted test input**, not a public code execution service. Submitted Python has the permissions of the Python process. Temporary directories, timeouts and a local session token do **not** provide sandbox isolation. Keep the server on `127.0.0.1`; do not expose it publicly or run untrusted submissions. Public deployment requires a genuinely isolated execution service, resource limits and authentication.

A source-code repository necessarily contains the reference implementations and demo examples; "hidden" means hidden from the normal task UI, not inaccessible to someone who owns the source. Presentation shortcuts intentionally reveal prepared answers. No LLM API, user accounts, real GitHub integration, production payment gateway, concurrency verification, or empirical learning study is included. Records persist in `data/progress.json`, which is excluded from Git. PR preview is static concept content.

Compared with the larger product document, this first version omits free-text consequence explanations and explicit per-judgement test-name associations. It records evidence for the whole submission. Test targets execute sequentially (at most four 5-second executions), rather than in parallel, to keep local resource usage simple.

## Verify

```bash
python -m pytest tests -q
```

## Put this project in your empty GitHub repository

Run these commands **inside this extracted folder**, after checking that no credentials or personal files have been added:

```bash
git init
git add .
git commit -m "Add working GetGood local demo"
git branch -M main
git remote add origin https://github.com/yiqunqiao/Getgood.git
git push -u origin main
```

If Git asks for your identity, configure your own name and GitHub email. GitHub authentication may open your browser; never paste a token into source files. If `origin already exists` or `push rejected` appears, stop and check the existing remote/history instead of force-pushing. These commands assume your remote repository is still empty.

Once uploaded, teammates clone this repository, follow the same setup instructions, and make changes on feature branches. The Python virtual environment and learner records must not be committed.

## API

`GET /api/tasks`, `GET /api/progress`, `POST /api/run`, `POST /api/submit`, `POST /api/hint/{task_id}`, `POST /api/reset`. POST requests require the session token from `GET /api/session` in `X-GetGood-Token`. The browser adds it automatically.

References: [FastAPI request bodies](https://fastapi.tiangolo.com/tutorial/body/), [pytest output and JUnit XML](https://docs.pytest.org/en/stable/how-to/output.html).
