-- FitOS Core Relational Schema Initialization

-- User Profile Table
CREATE TABLE IF NOT EXISTS user_profiles (
    user_id TEXT PRIMARY KEY,
    birth_date TEXT NOT NULL,
    weight_kg REAL NOT NULL,
    height_cm REAL NOT NULL,
    resting_hr INTEGER,
    max_hr INTEGER,
    fitness_level TEXT CHECK(fitness_level IN ('beginner', 'intermediate', 'advanced')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Exercises Dictionary
CREATE TABLE IF NOT EXISTS exercises (
    exercise_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT CHECK(category IN ('strength', 'cardio', 'mobility')),
    primary_muscles TEXT, -- JSON array of muscles
    form_rules TEXT NOT NULL -- JSON configuration of target angles
);

-- Workout Sessions
CREATE TABLE IF NOT EXISTS workout_sessions (
    session_id TEXT PRIMARY KEY,
    user_id TEXT,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    status TEXT CHECK(status IN ('in_progress', 'completed', 'aborted')),
    calories_burned_kcal REAL DEFAULT 0.0,
    avg_heart_rate INTEGER,
    FOREIGN KEY(user_id) REFERENCES user_profiles(user_id) ON DELETE CASCADE
);

-- Detailed Metrics Time-Series
CREATE TABLE IF NOT EXISTS biometric_telemetry (
    telemetry_id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    timestamp TIMESTAMP NOT NULL,
    heart_rate INTEGER,
    calories_burned_delta REAL,
    active_imu_state TEXT, -- JSON representation of current pose/sensor state
    FOREIGN KEY(session_id) REFERENCES workout_sessions(session_id) ON DELETE CASCADE
);

-- Workout Logs (Sets & Reps)
CREATE TABLE IF NOT EXISTS workout_logs (
    log_id TEXT PRIMARY KEY,
    session_id TEXT,
    exercise_id TEXT,
    set_number INTEGER NOT NULL,
    target_reps INTEGER,
    completed_reps INTEGER NOT NULL,
    average_velocity REAL,
    form_score REAL CHECK(form_score BETWEEN 0.0 AND 1.0),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(session_id) REFERENCES workout_sessions(session_id) ON DELETE CASCADE,
    FOREIGN KEY(exercise_id) REFERENCES exercises(exercise_id) ON DELETE SET NULL
);

-- Semantic Context Storage (RAG for SLM)
CREATE TABLE IF NOT EXISTS user_context_memories (
    memory_id TEXT PRIMARY KEY,
    user_id TEXT,
    category TEXT CHECK(category IN ('injury', 'preference', 'feedback', 'goal')),
    memory_text TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES user_profiles(user_id) ON DELETE CASCADE
);
