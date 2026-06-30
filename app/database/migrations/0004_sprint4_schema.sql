-- FitOS Sprint 4: Nutrition Engine Schema
-- Adds: meals, meal_entries, nutrition_logs
-- DOES NOT modify any Sprint 1, 2, or 3 tables.

-- 1. Meals Table — Named meal events per user per date
CREATE TABLE IF NOT EXISTS meals (
    meal_id     TEXT PRIMARY KEY,
    user_id     TEXT NOT NULL,
    meal_type   TEXT NOT NULL CHECK(meal_type IN ('breakfast', 'lunch', 'dinner', 'snack')),
    meal_date   TEXT NOT NULL,  -- YYYY-MM-DD
    name        TEXT,           -- optional label e.g. "Post-workout meal"
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Index for fast user+date lookups
CREATE INDEX IF NOT EXISTS idx_meals_user_date ON meals(user_id, meal_date);

-- 2. Meal Entries Table — Individual food items within a meal
CREATE TABLE IF NOT EXISTS meal_entries (
    entry_id    TEXT PRIMARY KEY,
    meal_id     TEXT NOT NULL,
    food_id     TEXT NOT NULL,
    quantity_g  REAL NOT NULL CHECK(quantity_g > 0),
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(meal_id) REFERENCES meals(meal_id) ON DELETE CASCADE,
    FOREIGN KEY(food_id) REFERENCES foods(food_id) ON DELETE CASCADE
);

-- Index for fast meal-level lookups
CREATE INDEX IF NOT EXISTS idx_meal_entries_meal ON meal_entries(meal_id);

-- 3. Nutrition Logs Table — Daily aggregated macro totals per user
--    Computed by NutritionService; always reproducible from raw meal_entries.
CREATE TABLE IF NOT EXISTS nutrition_logs (
    log_id          TEXT PRIMARY KEY,
    user_id         TEXT NOT NULL,
    log_date        TEXT NOT NULL,  -- YYYY-MM-DD
    total_calories  REAL DEFAULT 0.0,
    total_protein   REAL DEFAULT 0.0,
    total_carbs     REAL DEFAULT 0.0,
    total_fat       REAL DEFAULT 0.0,
    total_fiber     REAL DEFAULT 0.0,
    total_sugar     REAL DEFAULT 0.0,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    UNIQUE(user_id, log_date)  -- exactly one daily log record per user per date
);

-- Index for fast date-range queries
CREATE INDEX IF NOT EXISTS idx_nutrition_logs_user_date ON nutrition_logs(user_id, log_date);
