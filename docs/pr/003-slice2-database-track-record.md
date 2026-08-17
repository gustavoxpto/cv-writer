# PR body — CV Writer slice 2: database + track record (001, criteria 6, 29-31)

Branch: `feat/001-slice2-database-track-record` → `main`.
Title: `feat(001): slice 2 — database + track record (criteria 6, 29-31)`.

---

## What & why

Implements slice 2 of [`specs/features/001-cv-writer.md`](../../specs/features/001-cv-writer.md): loading the validated profile into the embedded SQLite database as a derived, rebuildable, queryable store (criterion 6), and the track-record schema plus its persistence/query API (criteria 29-31). Still headless — no UI, no LLM; those are slices 4-5.

## What's in it

- **`src/cv_writer/db/connection.py`** — `connect()`/`migrate()`. DB path resolves explicit override → `CV_WRITER_DB_PATH` env var → `data/cv_writer.sqlite3` default (criterion 31). A missing DB file is created and migrated automatically; migrations are ordered `.sql` scripts under `migrations/`, tracked in a `schema_migrations` table so re-running is a no-op.
- **`src/cv_writer/db/migrations/0001_init.sql`** — profile-derived tables (`identity`, `languages`, `education`, `job_histories`, `bullets`, `skills`, `skill_evidence`) and track-record tables (`applications`, `application_skills`, `application_bullet_sources`).
- **`src/cv_writer/db/profile_store.py`** — `load_profile_into_db(profile, conn)`: clears and reinserts every profile-derived table inside one transaction on each call. Idempotent by construction (no per-row upsert-key scheme needed) — the DB is a disposable projection of `data/profile.yaml`, which stays the only write path.
- **`src/cv_writer/db/queries.py`** — `bullets_evidencing_skill()` and `histories_in_country()`, the two cross-reference examples criterion 6 names explicitly.
- **`src/cv_writer/db/track_record.py`** — `Application` (Pydantic model matching criterion 29's field list) plus `insert_application()` / `list_applications()`. Filters (`company`/`country`/`area`/`skill`) combine with AND; `sort_by` is validated against a whitelist so it can never reach raw SQL.
- **15 new integration tests** in `tests/integration/db/`, real SQLite in `tmp_path` per the spec's own criterion→test-placement table.
- **`pyproject.toml`** — `package-data` for the migration SQL files, so a non-editable build ships them too.

## Acceptance criteria covered

Criterion 6 (spec section A): profile loads into SQLite, queryable/cross-referenceable, idempotent re-load. Criteria 29-31 (spec section F): application persistence with the full field list, list/sort/filter by date/company/country/area/skill including combined filters, configurable DB location with auto-create-and-migrate on a missing file.

Note: criterion 29 is exercised against directly-constructed `Application` records, not a real generation pipeline — that pipeline doesn't exist until slice 4, matching the spec's own slice ordering ("Database + track record ... still headless").

## Learning notes

- **"Derived and rebuildable" is a design constraint, not just a comment.** Framing the profile DB copy as disposable (source of truth stays the YAML file) turns idempotency into "clear and reinsert atomically" instead of an upsert-key design problem.
- **Join tables over JSON columns for `skills_featured`/`profile_bullet_ids`.** Criterion 30 asks for filtering by skill, including combined filters — that needs to be real SQL, not an application-side scan over deserialized JSON.

## Checklist

- [x] Spec in `specs/features/` signed off before implementation — `001-cv-writer.md`, criteria 6 and 29-31 targeted
- [x] Tests written before implementation (TDD, confirmed red before green) — 15 tests, each citing its criterion
- [x] CI passing — `ruff check` clean, `pytest tests/unit tests/integration` green locally (38 passed)
- [x] No secrets committed — DB files are gitignored (`*.sqlite3`); no credentials touched
- [x] Pairing notes added — `pairing/sessions/2026-08-17-slice2-database-track-record.md`

### Reviewer: worth a look

1. **Full-replace vs. upsert for profile reload** — confirm the "derived, disposable" framing for the profile-derived tables is the right call, vs. wanting update-in-place semantics later (e.g. to preserve DB-side row ids across reloads).
2. **`profile_bullet_id` has no stable source yet** — `Bullet` (in `profile/models.py`) has no `id` field, unlike `JobHistory`. For now `application_bullet_sources.profile_bullet_id` is just an int (in practice the DB's own autoincrement `bullets.id`). Slice 4 (criteria 18-19, "every generated bullet carries the id of the profile bullet ... it was derived from") will need to either lean on that DB id as canonical or add an explicit id to `Bullet` — flagged in the pairing note, not resolved here.
3. **`sort_by` whitelist only covers date/company/country/area** — matches criterion 30's list; extend if a reviewer wants skill-based sorting too (skill is filter-only right now, which matches the spec's wording).
