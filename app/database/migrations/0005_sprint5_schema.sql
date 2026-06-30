-- FitOS Sprint 5: Habit + Recovery Engine Schema
-- Adds: habits, habit_logs (refined), sleep_logs, recovery_logs, recovery_profiles
-- DOES NOT modify any Sprint 1, 2, 3, or 4 tables.

-- 1. Habits Table — Definable habit templates per user
CREATE TABLE IF NOT EXISTS habits (
    habit_id    TEXT PRIMARY KEY,
    user_id     TEXT NOT NULL,
    name        TEXT NOT NULL,
    description TEXT DEFAULT '',
    frequency   TEXT NOT NULL DEFAULT 'daily' CHECK(frequency IN ('daily', 'weekly')),
    target_value REAL DEFAULT 1.0,
    unit        TEXT DEFAULT 'times',
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Index for fast user lookups
CREATE INDEX IF NOT EXISTS idx_habits_user ON habits(user_id);

-- 2. Habit Entries Table — Structured daily tracking entries per habit (Sprint 5)
-- NOTE: Sprint 2 created a generic 'habit_logs' table. Sprint 5 adds a new
-- structured 'habit_entries' table linked to the habits template table above.
CREATE TABLE IF NOT EXISTS habit_entries (
    habit_log_id TEXT PRIMARY KEY,
    habit_id     TEXT NOT NULL,
    user_id      TEXT NOT NULL,
    log_date     TEXT NOT NULL,  -- YYYY-MM-DD
    value        REAL DEFAULT 1.0,
    status       TEXT NOT NULL DEFAULT 'completed' CHECK(status IN ('completed', 'missed', 'partial')),
    note         TEXT DEFAULT '',
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(habit_id) REFERENCES habits(habit_id) ON DELETE CASCADE,
    FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    UNIQUE(habit_id, user_id, log_date)  -- one log per habit per user per day
);

-- Index for fast user+date lookups
CREATE INDEX IF NOT EXISTS idx_habit_entries_user_date ON habit_entries(user_id, log_date);
CREATE INDEX IF NOT EXISTS idx_habit_entries_habit_date ON habit_entries(habit_id, log_date);

-- 3. Sleep Logs Table — Daily sleep quality tracking
CREATE TABLE IF NOT EXISTS sleep_logs (
    sleep_log_id  TEXT PRIMARY KEY,
    user_id       TEXT NOT NULL,
    log_date      TEXT NOT NULL,  -- YYYY-MM-DD
    hours         REAL NOT NULL CHECK(hours >= 0 AND hours <= 24),
    quality_score REAL NOT NULL CHECK(quality_score >= 0 AND quality_score <= 10),
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    UNIQUE(user_id, log_date)  -- one sleep log per user per date
);

-- Index for fast user lookups
CREATE INDEX IF NOT EXISTS idx_sleep_logs_user_date ON sleep_logs(user_id, log_date);

-- 4. Recovery Logs Table — Daily computed recovery readiness
CREATE TABLE IF NOT EXISTS recovery_logs (
    recovery_log_id           TEXT PRIMARY KEY,
    user_id                   TEXT NOT NULL,
    log_date                  TEXT NOT NULL,  -- YYYY-MM-DD
    recovery_score            REAL NOT NULL CHECK(recovery_score >= 0 AND recovery_score <= 100),
    readiness_state           TEXT NOT NULL CHECK(readiness_state IN ('FULL', 'MODERATE', 'LOW')),
    sleep_quality_component   REAL DEFAULT 0.0,
    sleep_duration_component  REAL DEFAULT 0.0,
    workout_load_component    REAL DEFAULT 0.0,
    rest_days_component       REAL DEFAULT 0.0,
    created_at                TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at                TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    UNIQUE(user_id, log_date)  -- one recovery log per user per date
);

-- Index for fast user lookups
CREATE INDEX IF NOT EXISTS idx_recovery_logs_user_date ON recovery_logs(user_id, log_date);

-- 5. Recovery Profiles Table — Per-user recovery baseline settings
CREATE TABLE IF NOT EXISTS recovery_profiles (
    profile_id           TEXT PRIMARY KEY,
    user_id              TEXT NOT NULL UNIQUE,
    baseline_sleep_hours REAL DEFAULT 8.0 CHECK(baseline_sleep_hours > 0 AND baseline_sleep_hours <= 24),
    created_at           TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at           TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Index for fast user lookup
CREATE INDEX IF NOT EXISTS idx_recovery_profiles_user ON recovery_profiles(user_id);