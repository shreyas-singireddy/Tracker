-- FitOS Sprint 2 Schema Expansion

-- 1. Users Table
CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Goals Table
CREATE TABLE IF NOT EXISTS goals (
    goal_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    category TEXT CHECK(category IN ('weight', 'steps', 'calories', 'water', 'sleep')),
    target_value REAL NOT NULL,
    current_value REAL DEFAULT 0.0,
    start_date TEXT NOT NULL,
    target_date TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- 3. Foods Dictionary Table
CREATE TABLE IF NOT EXISTS foods (
    food_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    calories REAL NOT NULL,
    protein REAL DEFAULT 0.0,
    carbs REAL DEFAULT 0.0,
    fats REAL DEFAULT 0.0,
    serving_size_g REAL DEFAULT 100.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Meal Logs Table
CREATE TABLE IF NOT EXISTS meal_logs (
    meal_log_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    food_id TEXT NOT NULL,
    serving_multiplier REAL DEFAULT 1.0,
    logged_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY(food_id) REFERENCES foods(food_id) ON DELETE CASCADE
);

-- 5. Habit Logs Table
CREATE TABLE IF NOT EXISTS habit_logs (
    habit_log_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    habit_name TEXT NOT NULL,
    status TEXT CHECK(status IN ('completed', 'missed')),
    logged_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- 6. Body Measurements Table
CREATE TABLE IF NOT EXISTS body_measurements (
    measurement_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    weight_kg REAL NOT NULL,
    body_fat_percentage REAL,
    chest_cm REAL,
    waist_cm REAL,
    hips_cm REAL,
    logged_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- 7. Extend workout_logs to support user_id and logged_at columns directly
-- We use TRY-CATCH equivalent pattern via SQLite ignore errors, or run safe alters:
-- SQLite ALTER TABLE ADD COLUMN is safe and idempotent if column doesn't exist.
-- (SQLite doesn't support IF NOT EXISTS in ADD COLUMN, but running it in Python can handle it, or we just execute it in the migration).
-- Since the migration script will be executed once per DB init, we run it directly.
-- To ensure compatibility, we'll add the columns to the existing workout_logs table:
ALTER TABLE workout_logs ADD COLUMN user_id TEXT REFERENCES users(user_id) ON DELETE CASCADE;
ALTER TABLE workout_logs ADD COLUMN logged_at TIMESTAMP;
ALTER TABLE workout_logs ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
