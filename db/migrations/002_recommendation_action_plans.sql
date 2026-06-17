-- Graphify Workspace Cockpit - Supabase schema (migration 002)
-- Apply after 001_initial.sql.
-- Safe to re-run (idempotent via IF NOT EXISTS).

-- Current recommendation records can include structured overlap review data and
-- action plans. Keep these optional so older records remain valid.

ALTER TABLE recommendations
  ADD COLUMN IF NOT EXISTS action_plan JSONB,
  ADD COLUMN IF NOT EXISTS overlap JSONB,
  ADD COLUMN IF NOT EXISTS overlap_dossier JSONB;

ALTER TABLE actions
  ADD COLUMN IF NOT EXISTS action_plan JSONB;

COMMENT ON COLUMN recommendations.action_plan IS
  'Optional structured plan generated for the recommendation card.';
COMMENT ON COLUMN recommendations.overlap IS
  'Optional semantic overlap metadata used by duplicate/review recommendations.';
COMMENT ON COLUMN recommendations.overlap_dossier IS
  'Optional triage dossier captured from overlap analysis.';
COMMENT ON COLUMN actions.action_plan IS
  'Optional structured plan copied from the accepted recommendation.';
