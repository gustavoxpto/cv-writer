"""Shared fixtures for the e2e tests (criteria 32, 33, 37) — the only tests in this repo that
drive the full web UI. Everything runs through FastAPI's TestClient, which exercises the ASGI
app in-process without binding a real socket, and FakeRephraser + a stub/failing `ingest_url`
keep every test offline (no API key, no network), matching criterion 22's posture extended to
the UI layer.

`profile_path` writes a real profile YAML into `tmp_path` and returns its path, so
create_app()'s default collaborator (`load_profile()`) is exercised for real rather than
stubbed — the same posture the plan calls for ("the real load_profile() path is exercised").
"""

from __future__ import annotations

from pathlib import Path

import pytest

_PROFILE_YAML = """
identity:
  name: Ana Example
  email: ana@example.com
  location: Lisbon, Portugal

languages:
  - name: English
    proficiency: professional
  - name: Portuguese
    proficiency: native

job_histories:
  - id: job-acme-2020
    company: Acme Corp
    role_title: Backend Engineer
    country: Portugal
    area: Engineering
    start_date: 2020-01-15
    end_date: present
    bullets:
      - id: job-acme-2020-b1
        situation: Checkout API had frequent timeouts under peak load.
        task: Bring p99 latency under the 500ms SLA.
        action: Profiled the request path and added a read-through cache for product lookups.
        result: Cut checkout p99 latency from 1.4s to 320ms.
        metric:
          value: "-77%"
          unit: p99 latency
          baseline: "from 1.4s to 320ms"
      - id: job-acme-2020-b2
        situation: Deploys required a manual 45-minute runbook.
        task: Make deploys safe enough to run without a human babysitting them.
        action: Wrote a CI pipeline with automated smoke tests and one-click rollback.
        result: Deploys became a single click, run several times a day.
        metric:
          value: "45min -> ~2min"
          unit: deploy time
      - id: job-acme-2020-b3
        situation: New hires took weeks to make their first production change.
        task: Shorten onboarding time for backend engineers.
        action: Wrote an onboarding guide and pairing checklist for the backend team.
        result: New hires shipped a first change noticeably faster.

skills:
  - name: Python
    category: language
    level: senior
    years: 6
    evidence: [job-acme-2020]
  - name: SQL
    category: database
    evidence: [job-acme-2020]
"""


@pytest.fixture
def profile_path(tmp_path: Path) -> Path:
    path = tmp_path / "profile.yaml"
    path.write_text(_PROFILE_YAML, encoding="utf-8")
    return path
