-- FitOS Sprint 7: Analytics & Fitness Intelligence Engine Schema
-- Adds: fitness_scores, weekly_reports, monthly_reports, analytics_snapshots, progress_trends
-- DOES NOT modify any Sprint 1-6 tables.

-- 1. Fitness Scores Table — Daily computed overall fitness score (0-100) with sub-scores
CREATE TABLE IF NOT EXISTS fitness_scores (
    score_id                   TEXT PRIMARY KEY,
    user_id                    TEXT NOT NULL,
    log_date                   TEXT NOT NULL,  -- YYYY-MM-DD
    overall_score              REAL NOT NULL CHECK(overall_score >= 0 AND overall_score <= 100),
    nutrition_score            REAL DEFAULT 0.0,
    workout_consistency_score  REAL DEFAULT 0.0,
    progressive_overload_score REAL DEFAULT 0.0,
    recovery_score             REAL DEFAULT 0.0,
    habits_score               REAL DEFAULT 0.0,
    body_progress_score        REAL DEFAULT 0.0,
    ai_adherence_score         REAL DEFAULT 0.0,
    created_at                 TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    UNIQUE(user_id, log_date)
);

CREATE INDEX IF NOT EXISTS idx_fitness_scores_user_date ON fitness_scores(user_id, log_date);

-- 2. Weekly Reports Table — Aggregated weekly performance summaries
CREATE TABLE IF NOT EXISTS weekly_reports (
    report_id        TEXT PRIMARY KEY,
    user_id          TEXT NOT NULL,
    week_start       TEXT NOT NULL,  -- YYYY-MM-DD (Monday)
    week_end         TEXT NOT NULL,  -- YYYY-MM-DD (Sunday)
    total_workouts   INTEGER DEFAULT 0,
    avg_calories     REAL DEFAULT 0.0,
    avg_protein_g    REAL DEFAULT 0.0,
    avg_recovery_score REAL DEFAULT 0.0,
    habit_streaks_best INTEGER DEFAULT 0,
    avg_fitness_score REAL DEFAULT 0.0,
    adherence_rate   REAL DEFAULT 0.0,
    insight_summary  TEXT DEFAULT '',
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    UNIQUE(user_id, week_start)
);

CREATE INDEX IF NOT EXISTS idx_weekly_reports_user ON weekly_reports(user_id);

-- 3. Monthly Reports Table — Aggregated monthly performance summaries
CREATE TABLE IF NOT EXISTS monthly_reports (
    report_id              TEXT PRIMARY KEY,
    user_id                TEXT NOT NULL,
    month_start            TEXT NOT NULL,  -- YYYY-MM-DD (1st of month)
    month_end              TEXT NOT NULL,  -- YYYY-MM-DD (last day of month)
    total_workouts         INTEGER DEFAULT 0,
    avg_calories           REAL DEFAULT 0.0,
    avg_protein_g          REAL DEFAULT 0.0,
    avg_recovery_score     REAL DEFAULT 0.0,
    avg_fitness_score      REAL DEFAULT 0.0,
    adherence_rate         REAL DEFAULT 0.0,
    strength_improvements  TEXT DEFAULT '',
    body_changes_summary   TEXT DEFAULT '',
    progress_summary       TEXT DEFAULT '',
    created_at             TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    UNIQUE(user_id, month_start)
);

CREATE INDEX IF NOT EXISTS idx_monthly_reports_user ON monthly_reports(user_id);

-- 4. Analytics Snapshots Table — Point-in-time snapshots for UI dashboard
CREATE TABLE IF NOT EXISTS analytics_snapshots (
    snapshot_id             TEXT PRIMARY KEY,
    user_id                 TEXT NOT NULL,
    snapshot_date           TEXT NOT NULL,  -- YYYY-MM-DD
    fitness_score           REAL DEFAULT 0.0,
    total_workouts_ytd      INTEGER DEFAULT 0,
    current_streak_best     INTEGER DEFAULT 0,
    nutrition_compliance_rate REAL DEFAULT 0.0,
    recovery_avg_7day       REAL DEFAULT 0.0,
    body_weight_kg          REAL,
    snapshot_data           TEXT DEFAULT '{}',  -- JSON for extensibility
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    UNIQUE(user_id, snapshot_date)
);

CREATE INDEX IF NOT EXISTS idx_analytics_snapshots_user_date ON analytics_snapshots(user_id, snapshot_date);

-- 5. Progress Trends Table — Tracked metric trends over time
CREATE TABLE IF NOT EXISTS progress_trends (
    trend_id        TEXT PRIMARY KEY,
    user_id         TEXT NOT NULL,
    metric_name     TEXT NOT NULL,  -- 'weight', 'strength', 'consistency', 'recovery', 'nutrition_stability'
    trend_direction TEXT NOT NULL CHECK(trend_direction IN ('increasing', 'decreasing', 'stable')),
    current_value   REAL DEFAULT 0.0,
    previous_value  REAL DEFAULT 0.0,
    delta_value     REAL DEFAULT 0.0,
    percentage_change REAL DEFAULT 0.0,
    moving_avg_7day REAL DEFAULT 0.0,
    moving_avg_30day REAL DEFAULT 0.0,
    period_start    TEXT DEFAULT '',
    period_end      TEXT DEFAULT '',
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    UNIQUE(user_id, metric_name, period_end)
);

CREATE INDEX IF NOT EXISTS idx_progress_trends_user ON progress_trends(user_id);
CREATE INDEX IF NOT EXISTS idx_progress_trends_metric ON progress_trends(metric_name);