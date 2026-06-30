-- FitOS Sprint 6: Offline AI Coach Engine Schema
-- Adds: ai_sessions, ai_queries, ai_responses, ai_recommendations
-- DOES NOT modify any Sprint 1-5 tables.

-- 1. AI Sessions Table — Groups queries into a conversation session
CREATE TABLE IF NOT EXISTS ai_sessions (
    session_id   TEXT PRIMARY KEY,
    user_id      TEXT NOT NULL,
    started_at   TEXT,                        -- ISO datetime
    ended_at     TEXT,                        -- ISO datetime (nullable until closed)
    query_count  INTEGER DEFAULT 0,
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_ai_sessions_user ON ai_sessions(user_id);

-- 2. AI Queries Table — Stores every raw user question + resolved intent
CREATE TABLE IF NOT EXISTS ai_queries (
    query_id    TEXT PRIMARY KEY,
    session_id  TEXT NOT NULL,
    user_id     TEXT NOT NULL,
    raw_text    TEXT NOT NULL,
    intent      TEXT NOT NULL,               -- IntentCategory value
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(session_id) REFERENCES ai_sessions(session_id) ON DELETE CASCADE,
    FOREIGN KEY(user_id)    REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_ai_queries_session ON ai_queries(session_id);
CREATE INDEX IF NOT EXISTS idx_ai_queries_user    ON ai_queries(user_id);
CREATE INDEX IF NOT EXISTS idx_ai_queries_intent  ON ai_queries(intent);

-- 3. AI Responses Table — Every response with mandatory rule_source (explainability)
--    rule_source MUST NOT be empty — enforced at service layer.
CREATE TABLE IF NOT EXISTS ai_responses (
    response_id   TEXT PRIMARY KEY,
    query_id      TEXT NOT NULL,
    user_id       TEXT NOT NULL,
    response_text TEXT NOT NULL,
    intent        TEXT NOT NULL,
    rule_source   TEXT NOT NULL,             -- MANDATORY: names the rule(s) that produced this response
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(query_id) REFERENCES ai_queries(query_id) ON DELETE CASCADE,
    FOREIGN KEY(user_id)  REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_ai_responses_query ON ai_responses(query_id);
CREATE INDEX IF NOT EXISTS idx_ai_responses_user  ON ai_responses(user_id);

-- 4. AI Recommendations Table — Actionable suggestions with mandatory rule_source
CREATE TABLE IF NOT EXISTS ai_recommendations (
    recommendation_id TEXT PRIMARY KEY,
    user_id           TEXT NOT NULL,
    category          TEXT NOT NULL,         -- 'nutrition'|'workout'|'recovery'|'habit'|'general'
    title             TEXT NOT NULL,
    body              TEXT NOT NULL,
    rule_source       TEXT NOT NULL,         -- MANDATORY: names the triggering rule constant
    priority          TEXT NOT NULL DEFAULT 'medium'
                          CHECK(priority IN ('high', 'medium', 'low')),
    log_date          TEXT,                  -- YYYY-MM-DD date context used for generation
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_ai_recommendations_user     ON ai_recommendations(user_id);
CREATE INDEX IF NOT EXISTS idx_ai_recommendations_category ON ai_recommendations(category);
CREATE INDEX IF NOT EXISTS idx_ai_recommendations_priority ON ai_recommendations(priority);
CREATE INDEX IF NOT EXISTS idx_ai_recommendations_date     ON ai_recommendations(log_date);
