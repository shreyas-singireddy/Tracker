-- FitOS Sprint 3 Schema Migration

-- 1. Create Workout Plans Table
CREATE TABLE IF NOT EXISTS workout_plans (
    plan_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    split_name TEXT NOT NULL, -- e.g. Push, Pull, Legs
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- 2. Migrate workout_sessions to updated constraints ('NOT_STARTED', 'ACTIVE', 'PAUSED', 'COMPLETED')
-- Create temporary table with the expanded schema structure
CREATE TABLE workout_sessions_temp (
    session_id TEXT PRIMARY KEY,
    user_id TEXT,
    plan_id TEXT,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    status TEXT CHECK(status IN ('NOT_STARTED', 'ACTIVE', 'PAUSED', 'COMPLETED')) DEFAULT 'NOT_STARTED',
    calories_burned_kcal REAL DEFAULT 0.0,
    avg_heart_rate INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY(plan_id) REFERENCES workout_plans(plan_id) ON DELETE SET NULL
);

-- Copy existing session records with status translation mapping
INSERT INTO workout_sessions_temp (
    session_id, user_id, start_time, end_time, status, calories_burned_kcal, avg_heart_rate
)
SELECT
    session_id, user_id, start_time, end_time,
    CASE 
        WHEN status = 'in_progress' THEN 'ACTIVE'
        WHEN status = 'completed' THEN 'COMPLETED'
        ELSE 'COMPLETED'
    END,
    calories_burned_kcal, avg_heart_rate
FROM workout_sessions;

-- Drop old table
DROP TABLE workout_sessions;

-- Rename temp table
ALTER TABLE workout_sessions_temp RENAME TO workout_sessions;

-- 3. Create Exercise Logs Table
CREATE TABLE IF NOT EXISTS exercise_logs (
    exercise_log_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    exercise_id TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(session_id) REFERENCES workout_sessions(session_id) ON DELETE CASCADE,
    FOREIGN KEY(exercise_id) REFERENCES exercises(exercise_id) ON DELETE CASCADE
);

-- 4. Create Exercise Sets Table
CREATE TABLE IF NOT EXISTS exercise_sets (
    set_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    exercise_log_id TEXT NOT NULL,
    set_number INTEGER NOT NULL,
    weight REAL NOT NULL,
    reps INTEGER NOT NULL,
    rpe REAL, -- Rate of Perceived Exertion
    is_completed INTEGER DEFAULT 0 CHECK(is_completed IN (0, 1)),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(session_id) REFERENCES workout_sessions(session_id) ON DELETE CASCADE,
    FOREIGN KEY(exercise_log_id) REFERENCES exercise_logs(exercise_log_id) ON DELETE CASCADE
);
