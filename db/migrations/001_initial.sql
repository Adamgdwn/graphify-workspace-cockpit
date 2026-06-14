-- Graphify Workspace Cockpit — Supabase schema (migration 001)
-- Apply with: supabase db push  OR  psql $DATABASE_URL < 001_initial.sql
-- Safe to re-run (idempotent via IF NOT EXISTS).

-- ── decisions ─────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS decisions (
  id              UUID        PRIMARY KEY,
  target_type     TEXT        NOT NULL DEFAULT 'project',
  target_id       TEXT        NOT NULL,
  label           TEXT        NOT NULL,
  classification  TEXT        NOT NULL,
  rationale       TEXT        NOT NULL DEFAULT '',
  status          TEXT        NOT NULL DEFAULT 'active',
  created_by      TEXT        NOT NULL DEFAULT 'adam',
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── recommendations ───────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS recommendations (
  id              UUID        PRIMARY KEY,
  mode            TEXT        NOT NULL,
  title           TEXT        NOT NULL,
  summary         TEXT        NOT NULL DEFAULT '',
  evidence        JSONB       NOT NULL DEFAULT '[]',
  confidence      FLOAT       NOT NULL DEFAULT 0,
  risk            TEXT        NOT NULL DEFAULT 'unknown',
  effort          TEXT        NOT NULL DEFAULT 'unknown',
  proposed_action TEXT        NOT NULL DEFAULT '',
  status          TEXT        NOT NULL DEFAULT 'pending',
  model           TEXT        NOT NULL DEFAULT '',
  created_by      TEXT        NOT NULL DEFAULT 'adam',
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── actions ───────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS actions (
  id                       UUID        PRIMARY KEY,
  source_recommendation_id UUID        REFERENCES recommendations(id),
  action_type              TEXT        NOT NULL,
  description              TEXT        NOT NULL DEFAULT '',
  target_path              TEXT        NOT NULL DEFAULT '',
  dry_run_command          TEXT        NOT NULL DEFAULT '',
  proposed_action_text     TEXT        NOT NULL DEFAULT '',
  evidence                 JSONB       NOT NULL DEFAULT '[]',
  rec_title                TEXT        NOT NULL DEFAULT '',
  rec_summary              TEXT        NOT NULL DEFAULT '',
  confidence               FLOAT       NOT NULL DEFAULT 0,
  risk                     TEXT        NOT NULL DEFAULT 'unknown',
  dry_run_preview          JSONB,
  dry_run_at               TIMESTAMPTZ,
  approval_required        BOOLEAN     NOT NULL DEFAULT TRUE,
  approved_at              TIMESTAMPTZ,
  executed_at              TIMESTAMPTZ,
  result                   JSONB,
  rollback_note            TEXT        NOT NULL DEFAULT '',
  status                   TEXT        NOT NULL DEFAULT 'pending',
  created_by               TEXT        NOT NULL DEFAULT 'adam',
  created_at               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at               TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── sessions ──────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS sessions (
  id          UUID        PRIMARY KEY,
  question    TEXT        NOT NULL DEFAULT '',
  mode_used   TEXT        NOT NULL DEFAULT 'query',
  answer      TEXT        NOT NULL DEFAULT '',
  evidence    JSONB       NOT NULL DEFAULT '[]',
  suggestions JSONB       NOT NULL DEFAULT '[]',
  created_by  TEXT        NOT NULL DEFAULT 'adam',
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── Row-level security (enable before opening to the internet) ─────────────
-- Disabled by default — the API key middleware on the cockpit backend is the
-- auth boundary for now.  Enable RLS and add policies before any multi-tenant
-- or public deployment.

-- ALTER TABLE decisions ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE recommendations ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE actions ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;
