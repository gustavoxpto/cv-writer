-- Migration 0002: stable bullet citation ids (spec criterion 18, ADR 0004 decision 1).
--
-- `Bullet` gained a real, human-authored `id` field in profile/models.py (Profile now
-- enforces it's unique across the whole profile). This migration is purely additive —
-- CLAUDE.md's hard rule #1 forbids DROP/TRUNCATE without fresh explicit permission every
-- time, so there is no "recreate the table" step here, even though `bullets` is otherwise a
-- rebuildable projection of data/profile.yaml.
--
-- `bullets.id` (INTEGER PRIMARY KEY AUTOINCREMENT, from 0001_init.sql) is left in place as
-- an internal surrogate key, but it is NOT stable across profile reloads
-- (load_profile_into_db() clears and re-inserts `bullets` wholesale every time) and so was
-- never usable as a citation id. `bullet_id` below is the new, stable, YAML-authored id.
ALTER TABLE bullets ADD COLUMN bullet_id TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS idx_bullets_bullet_id ON bullets(bullet_id);

-- `application_bullet_sources.profile_bullet_id` keeps its declared INTEGER column
-- unchanged rather than being recreated. SQLite's type-affinity rules store a TEXT value
-- that isn't a well-formed integer literal (our bullet ids look like "job-acme-2020-b1") as
-- TEXT regardless of the column's declared affinity, so the existing column already accepts
-- the new string ids without a schema change. This is a deliberate, documented looseness
-- (the declared type no longer matches what's stored) — see ADR 0004 decision 1 — not an
-- oversight; a future migration can recreate this column properly once real track-record
-- data exists and that operation can be explicitly confirmed with a human first.
