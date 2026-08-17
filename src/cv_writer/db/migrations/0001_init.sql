-- Migration 0001: initial schema.
--
-- Two families of tables, kept deliberately separate (see profile_store.py / track_record.py):
--   - profile-derived tables (identity, languages, education, job_histories, bullets, skills,
--     skill_evidence) are a *rebuildable projection* of data/profile.yaml (spec criterion 6).
--     load_profile_into_db() clears and repopulates them wholesale on every call — that's what
--     keeps re-running idempotent without needing per-row upsert logic.
--   - track-record tables (applications, application_skills, application_bullet_sources) hold
--     real generated-application history (spec criteria 29-31) and are never touched by a
--     profile reload.

CREATE TABLE IF NOT EXISTS identity (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    phone TEXT,
    location TEXT,
    links_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS languages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    proficiency TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS education (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    institution TEXT NOT NULL,
    degree TEXT NOT NULL,
    field TEXT,
    start_date TEXT,
    end_date TEXT
);

CREATE TABLE IF NOT EXISTS job_histories (
    id TEXT PRIMARY KEY,
    company TEXT NOT NULL,
    role_title TEXT NOT NULL,
    country TEXT NOT NULL,
    area TEXT NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS bullets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_history_id TEXT NOT NULL REFERENCES job_histories(id),
    position INTEGER NOT NULL,
    situation TEXT NOT NULL,
    task TEXT NOT NULL,
    action TEXT NOT NULL,
    result TEXT NOT NULL,
    metric_value TEXT,
    metric_unit TEXT,
    metric_baseline TEXT
);

CREATE INDEX IF NOT EXISTS idx_bullets_job_history_id ON bullets(job_history_id);

CREATE TABLE IF NOT EXISTS skills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    level TEXT,
    years REAL
);

CREATE TABLE IF NOT EXISTS skill_evidence (
    skill_id INTEGER NOT NULL REFERENCES skills(id),
    job_history_id TEXT NOT NULL REFERENCES job_histories(id),
    PRIMARY KEY (skill_id, job_history_id)
);

CREATE TABLE IF NOT EXISTS applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    application_date TEXT NOT NULL,
    company TEXT NOT NULL,
    country TEXT NOT NULL,
    area TEXT NOT NULL,
    role_title TEXT NOT NULL,
    source TEXT NOT NULL,
    ingestion_tier INTEGER,
    match_score REAL,
    output_language TEXT NOT NULL,
    page_count INTEGER NOT NULL,
    markdown_path TEXT,
    pdf_path TEXT,
    text_path TEXT
);

CREATE INDEX IF NOT EXISTS idx_applications_date ON applications(application_date);
CREATE INDEX IF NOT EXISTS idx_applications_company ON applications(company);
CREATE INDEX IF NOT EXISTS idx_applications_country ON applications(country);
CREATE INDEX IF NOT EXISTS idx_applications_area ON applications(area);

CREATE TABLE IF NOT EXISTS application_skills (
    application_id INTEGER NOT NULL REFERENCES applications(id),
    skill_name TEXT NOT NULL,
    PRIMARY KEY (application_id, skill_name)
);

CREATE TABLE IF NOT EXISTS application_bullet_sources (
    application_id INTEGER NOT NULL REFERENCES applications(id),
    profile_bullet_id INTEGER NOT NULL,
    PRIMARY KEY (application_id, profile_bullet_id)
);
