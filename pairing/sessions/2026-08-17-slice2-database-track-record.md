# 2026-08-17 — CV Writer slice 2: database + track record

## Goal

Deliver slice 2 of `specs/features/001-cv-writer.md`: criteria 6, 29-31 — load the validated
profile into SQLite as a derived, rebuildable, queryable store, and build the track-record
schema and its list/sort/filter API. Still no UI, still no LLM (per the spec's slice ordering).

## Tried

- **Upsert-per-row vs. full-replace for idempotency (criterion 6).** Considered diffing the
  incoming `Profile` against existing DB rows and upserting. Rejected: bullets have no stable
  natural id in the Pydantic model (only `JobHistory.id` is stable), so an upsert key would have
  to be invented (e.g. `history_id + position`), which is exactly the kind of ad-hoc scheme the
  slice-1 pairing note already steered away from for metrics. Went with **full replace inside
  one transaction** instead: every `load_profile_into_db()` call deletes all profile-derived
  rows, child-tables-first, then reinserts from the in-memory `Profile`. This is what "the
  database copy is derived and rebuildable" (the spec's own words) is asking for — YAML stays
  the only real write path (open question 3), the DB is disposable. Simpler code, and the
  transaction (`with conn:`) means a failure mid-rebuild rolls back rather than leaving a
  half-populated snapshot.
- **One SQL migration file vs. one per table/feature.** Went with a single
  `migrations/0001_init.sql` covering both the profile-derived tables and the track-record
  tables, since they're introduced together in this slice and splitting them wouldn't buy
  anything yet. `schema_migrations` tracks applied filenames so future slices just add
  `0002_*.sql` and `migrate()` picks it up — no migration-runner dependency needed for this
  scale.
- **Skills-featured / bullet-sources as join tables, not JSON columns on `applications`.**
  A JSON blob would've been less code, but criterion 30 explicitly asks for filtering by skill,
  and combined filters (skill AND country) need to be real SQL, not an application-side scan
  over deserialized JSON. `application_skills` and `application_bullet_sources` are junction
  tables for that reason.

## Decided

- `src/cv_writer/db/{connection,profile_store,queries,track_record}.py` +
  `migrations/0001_init.sql`.
  - `connection.py`: `get_db_path()` resolves explicit path > `CV_WRITER_DB_PATH` env var >
    `data/cv_writer.sqlite3` default (criterion 31). `connect()` creates parent dirs and runs
    `migrate()` unconditionally — a fresh run against a missing file just works.
  - `profile_store.py`: `load_profile_into_db(profile, conn)` — full replace, one transaction,
    described above.
  - `queries.py`: `bullets_evidencing_skill()` and `histories_in_country()` as the two example
    cross-references criterion 6 names explicitly.
  - `track_record.py`: `Application` (Pydantic model, mirrors criterion 29's field list exactly)
    plus `insert_application()` / `list_applications()`. `list_applications()` takes
    `company`/`country`/`area`/`skill` filters (AND-combined) and a whitelisted `sort_by` (never
    interpolates a caller-provided column name into SQL).
- 15 new integration tests in `tests/integration/db/` (real SQLite in `tmp_path`, per the
  criterion→test-placement table) — profile load/idempotency/cross-ref queries, DB
  auto-create+migrate, env-var-configurable path, insert/list/filter/sort. Full suite: 38 passed,
  `ruff check` clean.
- `pyproject.toml` gained `[tool.setuptools.package-data]` for `db/migrations/*.sql` — the
  editable install used in dev/CI reads `src/` directly regardless, but a real (non-editable)
  build would silently drop the migration without this.

## Learned

- **"Derived and rebuildable" is a design constraint, not just a comment.** Once the profile DB
  copy is framed as disposable (source of truth stays `data/profile.yaml`), idempotency stops
  being a hard problem — no upsert-key design needed, just "clear and reinsert, atomically."
  Worth remembering for the track-record tables too: those are *not* derived (they're the only
  copy of "what was actually sent"), which is why `load_profile_into_db()` never touches them.
- **Open point for slice 4, logged rather than solved here:** criteria 18-19 talk about "the
  `id` of the profile bullet" a generated CV bullet was derived from, but `Bullet` (in
  `profile/models.py`) has no `id` field — only `JobHistory` does. For slice 2,
  `application_bullet_sources.profile_bullet_id` is just an int (in practice, the DB's own
  autoincrement `bullets.id`). Slice 4 will need to decide whether that DB rowid *is* the
  canonical "profile bullet id" the spec means, or whether `Bullet` needs an explicit stable id
  of its own (more consistent with how `JobHistory.id` already works, but a schema change to
  `profile.yaml` and every fixture). Flagging now so it isn't rediscovered from scratch later.

## Next

Slice 3 (criteria 7-16): posting ingestion (tier 1 HTTP fetch + tier 3 paste fallback first,
tier 2 headless-browser render last since it brings in the Chromium dependency) and the
deterministic match report. Still no LLM.
