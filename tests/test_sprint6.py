"""Sprint 6 Test Suite — Offline AI Coach Engine.

Uses pytest.

Test classes:
  1. TestIntentClassifier     — keyword scoring, tie-breaking, edge cases
  2. TestContextEngine        — context structure, missing-data defaults
  3. TestRecommendationEngine — each rule fires correctly on boundary inputs
  4. TestInsightGenerator     — daily insight, weekly summary, warning alerts
  5. TestAIDBLogging          — session, query, response, recommendation CRUD
  6. TestResponseValidation   — explainability: rule_source always set
"""

import os
import uuid
from datetime import date, timedelta
from pathlib import Path

import pytest

from app.core.exceptions import ValidationError
from app.database.connection import DatabaseManager
from app.database.migrations import MigrationRunner
from app.models.ai import (
    IntentCategory,
    RecommendationPriority,
)
from app.models.domain import User
from app.repositories.ai import (
    AIQueryRepository,
    AIRecommendationRepository,
    AIResponseRepository,
    AISessionRepository,
)
from app.repositories.user import UserRepository
from app.services.ai_coach import AICoachService

# ---------------------------------------------------------------------------
# Test DB setup
# ---------------------------------------------------------------------------

TEST_DB_PATH = Path(__file__).resolve().parent / "test_fitos_s6.db"
MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "app" / "database" / "migrations"

TODAY = date.today().strftime("%Y-%m-%d")
YESTERDAY = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")


@pytest.fixture(scope="function")
def db():
    """Create a fresh isolated test database for each test function."""
    unique_id = uuid.uuid4().hex
    test_db_file = Path(__file__).resolve().parent / f"test_fitos_s6_{unique_id}.db"
    database = DatabaseManager(db_path=str(test_db_file))
    runner = MigrationRunner(migrations_dir=MIGRATIONS_DIR, db=database)
    runner.run_all()
    yield database
    database.close_connection()
    # Cleanup
    for suffix in ("", "-wal", "-shm"):
        p = Path(str(test_db_file) + suffix) if suffix else test_db_file
        if p.exists():
            try:
                os.remove(p)
            except OSError:
                pass


@pytest.fixture(scope="function")
def coach(db):
    """Return an AICoachService wired to the test DB."""
    return AICoachService(
        session_repo=AISessionRepository(db=db),
        query_repo=AIQueryRepository(db=db),
        response_repo=AIResponseRepository(db=db),
        rec_repo=AIRecommendationRepository(db=db),
        user_repo=UserRepository(db=db),
        db=db,
    )


@pytest.fixture(scope="function")
def user_id(db):
    """Seed and return a test user ID."""
    repo = UserRepository(db=db)
    uid = "u-ai-test"
    repo.create_user(User(user_id=uid, name="AI Tester", email="ai@fitos.app"))
    return uid


@pytest.fixture(scope="function")
def session_id(coach, user_id):
    """Create a session and return its ID."""
    sid = "sess-test-1"
    coach.start_session(sid, user_id)
    return sid


# ---------------------------------------------------------------------------
# 1. Intent Classifier Tests
# ---------------------------------------------------------------------------


class TestIntentClassifier:
    def test_nutrition_keywords_classify_correctly(self, coach):
        assert coach.classify_intent("I need meal protein calorie advice") == IntentCategory.NUTRITION_QUERY.value

    def test_workout_keywords_classify_correctly(self, coach):
        assert (
            coach.classify_intent("How many sets and reps should I lift today?") == IntentCategory.WORKOUT_QUERY.value
        )

    def test_recovery_keywords_classify_correctly(self, coach):
        assert coach.classify_intent("I didn't sleep well and feel fatigue") == IntentCategory.RECOVERY_QUERY.value

    def test_habit_keywords_classify_correctly(self, coach):
        assert coach.classify_intent("My habit streak was broken today") == IntentCategory.HABIT_QUERY.value

    def test_progress_keywords_classify_correctly(self, coach):
        assert coach.classify_intent("Show me my weight and goal progress") == IntentCategory.PROGRESS_QUERY.value

    def test_general_keywords_classify_correctly(self, coach):
        assert coach.classify_intent("Give me a fitness tip") == IntentCategory.GENERAL_FITNESS_QUERY.value

    def test_empty_string_falls_back_to_general(self, coach):
        assert coach.classify_intent("") == IntentCategory.GENERAL_FITNESS_QUERY.value

    def test_whitespace_only_falls_back_to_general(self, coach):
        assert coach.classify_intent("   ") == IntentCategory.GENERAL_FITNESS_QUERY.value

    def test_unknown_words_fall_back_to_general(self, coach):
        assert coach.classify_intent("xyzzy quux blorp") == IntentCategory.GENERAL_FITNESS_QUERY.value

    def test_single_keyword_classifies_unambiguously(self, coach):
        assert coach.classify_intent("sleep") == IntentCategory.RECOVERY_QUERY.value

    def test_calorie_classifies_as_nutrition(self, coach):
        assert coach.classify_intent("calories") == IntentCategory.NUTRITION_QUERY.value

    def test_classifier_is_case_insensitive(self, coach):
        assert coach.classify_intent("PROTEIN intake MEAL") == IntentCategory.NUTRITION_QUERY.value


# ---------------------------------------------------------------------------
# 2. Context Engine Tests
# ---------------------------------------------------------------------------


class TestContextEngine:
    def test_context_returns_expected_keys(self, coach, user_id):
        ctx = coach.build_user_context(user_id, TODAY)
        expected_keys = {
            "user_id",
            "context_date",
            "recovery_score",
            "readiness_state",
            "sleep_hours",
            "sleep_quality",
            "daily_calories",
            "daily_protein_g",
            "daily_carbs_g",
            "daily_fat_g",
            "calorie_target",
            "protein_target_g",
            "workout_sessions_7d",
            "habit_count",
            "habit_avg_consistency",
            "body_weight_kg",
        }
        assert expected_keys.issubset(ctx.keys())

    def test_context_defaults_are_safe_when_no_data(self, coach, user_id):
        """With no Sprint 3-5 data seeded, context must return safe defaults (no errors)."""
        ctx = coach.build_user_context(user_id, TODAY)
        assert ctx["recovery_score"] is None
        assert ctx["sleep_hours"] is None
        assert ctx["daily_calories"] == 0.0
        assert ctx["daily_protein_g"] == 0.0
        assert ctx["workout_sessions_7d"] == 0
        assert ctx["habit_count"] == 0

    def test_context_user_id_matches(self, coach, user_id):
        ctx = coach.build_user_context(user_id, TODAY)
        assert ctx["user_id"] == user_id

    def test_context_date_matches(self, coach, user_id):
        ctx = coach.build_user_context(user_id, YESTERDAY)
        assert ctx["context_date"] == YESTERDAY


# ---------------------------------------------------------------------------
# 3. Recommendation Engine Tests
# ---------------------------------------------------------------------------


class TestRecommendationEngine:
    def _make_ctx(self, **overrides):
        base = {
            "user_id": "u-ai-test",
            "context_date": TODAY,
            "recovery_score": 80.0,
            "readiness_state": "FULL",
            "sleep_hours": 8.0,
            "sleep_quality": 8.0,
            "daily_calories": 2000.0,
            "daily_protein_g": 150.0,
            "daily_carbs_g": 200.0,
            "daily_fat_g": 70.0,
            "calorie_target": 2000.0,
            "protein_target_g": 150.0,
            "workout_sessions_7d": 3,
            "habit_count": 2,
            "habit_avg_consistency": 80.0,
            "body_weight_kg": 80.0,
        }
        base.update(overrides)
        return base

    def test_low_recovery_triggers_rest_recommendation(self, coach, user_id):
        ctx = self._make_ctx(recovery_score=30.0)
        recs = coach.generate_recommendations(user_id, ctx, TODAY)
        rule_ids = [r.rule_source for r in recs]
        assert "RULE_LOW_RECOVERY" in rule_ids

    def test_low_recovery_recommendation_is_high_priority(self, coach, user_id):
        ctx = self._make_ctx(recovery_score=30.0)
        recs = coach.generate_recommendations(user_id, ctx, TODAY)
        low_rec = next(r for r in recs if r.rule_source == "RULE_LOW_RECOVERY")
        assert low_rec.priority == RecommendationPriority.HIGH.value

    def test_moderate_recovery_triggers_light_training(self, coach, user_id):
        ctx = self._make_ctx(recovery_score=55.0)
        recs = coach.generate_recommendations(user_id, ctx, TODAY)
        assert any(r.rule_source == "RULE_MODERATE_RECOVERY" for r in recs)

    def test_good_recovery_triggers_train_hard(self, coach, user_id):
        ctx = self._make_ctx(recovery_score=85.0)
        recs = coach.generate_recommendations(user_id, ctx, TODAY)
        assert any(r.rule_source == "RULE_GOOD_RECOVERY" for r in recs)

    def test_low_sleep_triggers_sleep_recommendation(self, coach, user_id):
        ctx = self._make_ctx(sleep_hours=4.5)
        recs = coach.generate_recommendations(user_id, ctx, TODAY)
        assert any(r.rule_source == "RULE_LOW_SLEEP" for r in recs)

    def test_protein_deficit_triggers_protein_recommendation(self, coach, user_id):
        # protein_actual(50g) < target(150g) * 0.8 = 120g → triggers
        ctx = self._make_ctx(daily_protein_g=50.0, protein_target_g=150.0)
        recs = coach.generate_recommendations(user_id, ctx, TODAY)
        assert any(r.rule_source == "RULE_PROTEIN_DEFICIT" for r in recs)

    def test_protein_at_target_does_not_trigger_deficit(self, coach, user_id):
        ctx = self._make_ctx(daily_protein_g=150.0, protein_target_g=150.0)
        recs = coach.generate_recommendations(user_id, ctx, TODAY)
        assert not any(r.rule_source == "RULE_PROTEIN_DEFICIT" for r in recs)

    def test_calorie_surplus_triggers_alert(self, coach, user_id):
        # 2400 > 2000 * 1.15 = 2300 → triggers
        ctx = self._make_ctx(daily_calories=2400.0, calorie_target=2000.0)
        recs = coach.generate_recommendations(user_id, ctx, TODAY)
        assert any(r.rule_source == "RULE_CALORIE_SURPLUS" for r in recs)

    def test_calorie_at_target_does_not_trigger_surplus(self, coach, user_id):
        ctx = self._make_ctx(daily_calories=2000.0, calorie_target=2000.0)
        recs = coach.generate_recommendations(user_id, ctx, TODAY)
        assert not any(r.rule_source == "RULE_CALORIE_SURPLUS" for r in recs)

    def test_low_habit_consistency_triggers_simplification(self, coach, user_id):
        ctx = self._make_ctx(habit_count=3, habit_avg_consistency=30.0)
        recs = coach.generate_recommendations(user_id, ctx, TODAY)
        assert any(r.rule_source == "RULE_LOW_HABIT_CONSISTENCY" for r in recs)

    def test_zero_workouts_triggers_resume_training(self, coach, user_id):
        ctx = self._make_ctx(workout_sessions_7d=0)
        recs = coach.generate_recommendations(user_id, ctx, TODAY)
        assert any(r.rule_source == "RULE_NO_RECENT_WORKOUTS" for r in recs)

    def test_all_good_triggers_positive_catchall(self, coach, user_id):
        """When no negative rule fires, the positive catchall must be returned."""
        # recovery_score=None skips RULE_GOOD_RECOVERY; sleep_hours=None skips RULE_LOW_SLEEP;
        # protein and calories are both at target; consistency is high; workouts > 0
        ctx = self._make_ctx(
            recovery_score=None,
            readiness_state=None,
            sleep_hours=None,
            workout_sessions_7d=3,
            daily_protein_g=150.0,
            protein_target_g=150.0,
            daily_calories=2000.0,
            calorie_target=2000.0,
            habit_avg_consistency=80.0,
        )
        recs = coach.generate_recommendations(user_id, ctx, TODAY)
        assert any(r.rule_source == "RULE_FULL_CONTEXT_POSITIVE" for r in recs)

    def test_every_recommendation_has_rule_source(self, coach, user_id):
        ctx = self._make_ctx(recovery_score=25.0, sleep_hours=4.0, daily_protein_g=40.0)
        recs = coach.generate_recommendations(user_id, ctx, TODAY)
        for r in recs:
            assert r.rule_source, f"Recommendation {r.recommendation_id} missing rule_source"

    def test_every_recommendation_has_non_empty_body(self, coach, user_id):
        ctx = self._make_ctx(recovery_score=25.0)
        recs = coach.generate_recommendations(user_id, ctx, TODAY)
        for r in recs:
            assert r.body.strip(), f"Recommendation {r.recommendation_id} has empty body"


# ---------------------------------------------------------------------------
# 4. Insight Generator Tests
# ---------------------------------------------------------------------------


class TestInsightGenerator:
    def test_daily_insight_returns_string(self, coach, user_id):
        result = coach.generate_daily_insight(user_id, TODAY)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_daily_insight_contains_date(self, coach, user_id):
        result = coach.generate_daily_insight(user_id, TODAY)
        assert TODAY in result

    def test_daily_insight_contains_nutrition_section(self, coach, user_id):
        result = coach.generate_daily_insight(user_id, TODAY)
        assert "Nutrition" in result

    def test_daily_insight_contains_workout_section(self, coach, user_id):
        result = coach.generate_daily_insight(user_id, TODAY)
        assert "Workout" in result

    def test_weekly_summary_returns_string(self, coach, user_id):
        result = coach.generate_weekly_summary(user_id, TODAY)
        assert isinstance(result, str)
        assert "Weekly Summary" in result

    def test_weekly_summary_contains_workout_count(self, coach, user_id):
        result = coach.generate_weekly_summary(user_id, TODAY)
        assert "Workouts" in result

    def test_warning_alerts_empty_when_all_ok(self, coach):
        ctx = {
            "recovery_score": 85.0,
            "sleep_hours": 8.0,
            "daily_protein_g": 150.0,
            "protein_target_g": 150.0,
        }
        alerts = coach.generate_warning_alerts(ctx)
        assert alerts == []

    def test_warning_alert_for_low_recovery(self, coach):
        ctx = {
            "recovery_score": 30.0,
            "sleep_hours": 8.0,
            "daily_protein_g": 150.0,
            "protein_target_g": 150.0,
        }
        alerts = coach.generate_warning_alerts(ctx)
        assert any("RULE_LOW_RECOVERY" in a for a in alerts)

    def test_warning_alert_for_low_sleep(self, coach):
        ctx = {
            "recovery_score": None,
            "sleep_hours": 4.0,
            "daily_protein_g": 150.0,
            "protein_target_g": 150.0,
        }
        alerts = coach.generate_warning_alerts(ctx)
        assert any("RULE_LOW_SLEEP" in a for a in alerts)

    def test_warning_alerts_contain_rule_id(self, coach):
        ctx = {
            "recovery_score": 20.0,
            "sleep_hours": 3.0,
            "daily_protein_g": 40.0,
            "protein_target_g": 150.0,
        }
        alerts = coach.generate_warning_alerts(ctx)
        for alert in alerts:
            assert "RULE_" in alert, "Every alert must reference a rule ID"

    def test_progress_feedback_returns_string(self, coach, user_id):
        result = coach.generate_progress_feedback(user_id, TODAY)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_invalid_date_raises_in_weekly_summary(self, coach, user_id):
        with pytest.raises(ValidationError):
            coach.generate_weekly_summary(user_id, "30-06-2026")


# ---------------------------------------------------------------------------
# 5. DB Logging Tests
# ---------------------------------------------------------------------------


class TestAIDBLogging:
    def test_start_session_persists_to_db(self, coach, user_id, db):
        sid = "sess-persist-1"
        coach.start_session(sid, user_id)
        repo = AISessionRepository(db=db)
        session = repo.get_session(sid)
        assert session is not None
        assert session.user_id == user_id

    def test_start_session_unknown_user_raises(self, coach):
        with pytest.raises(ValidationError):
            coach.start_session("sess-ghost", "u-ghost")

    def test_process_query_persists_query_and_response(self, coach, user_id, session_id, db):
        q_id = "q-persist-1"
        r_id = "r-persist-1"
        coach.process_query(session_id, q_id, r_id, user_id, "How should I eat today?", TODAY)

        q_repo = AIQueryRepository(db=db)
        r_repo = AIResponseRepository(db=db)

        q = q_repo.get_query(q_id)
        r = r_repo.get_response(r_id)

        assert q is not None and q.raw_text == "How should I eat today?"
        assert r is not None and r.query_id == q_id

    def test_process_query_persists_recommendations(self, coach, user_id, session_id, db):
        q_id = "q-rec-1"
        r_id = "r-rec-1"
        coach.process_query(session_id, q_id, r_id, user_id, "Give me tips", TODAY)
        rec_repo = AIRecommendationRepository(db=db)
        recs = rec_repo.get_recommendations_by_date(user_id, TODAY)
        assert len(recs) > 0

    def test_process_query_increments_session_count(self, coach, user_id, session_id, db):
        repo = AISessionRepository(db=db)
        coach.process_query(session_id, "q-cnt-1", "r-cnt-1", user_id, "workout tip", TODAY)
        coach.process_query(session_id, "q-cnt-2", "r-cnt-2", user_id, "nutrition tip", TODAY)
        updated = repo.get_session(session_id)
        assert updated.query_count == 2

    def test_get_session_history_returns_pairs(self, coach, user_id, session_id):
        coach.process_query(session_id, "q-hist-1", "r-hist-1", user_id, "sleep advice", TODAY)
        history = coach.get_session_history(session_id)
        assert len(history) == 1
        q, r = history[0]
        assert q.query_id == "q-hist-1"
        assert r is not None and r.response_id == "r-hist-1"

    def test_get_recommendations_by_date(self, coach, user_id, session_id):
        coach.process_query(session_id, "q-date-1", "r-date-1", user_id, "any advice", TODAY)
        recs = coach.get_recommendations(user_id, log_date=TODAY)
        assert len(recs) > 0

    def test_get_recommendations_by_category(self, coach, user_id, session_id):
        coach.process_query(session_id, "q-cat-1", "r-cat-1", user_id, "any advice", TODAY)
        all_recs = coach.get_recommendations(user_id)
        categories = {r.category for r in all_recs}
        # At least one category exists
        assert len(categories) > 0


# ---------------------------------------------------------------------------
# 6. Response Validation Tests
# ---------------------------------------------------------------------------


class TestResponseValidation:
    def test_response_always_has_rule_source(self, coach, user_id, session_id):
        _, response, _ = coach.process_query(session_id, "q-val-1", "r-val-1", user_id, "give me advice", TODAY)
        assert response.rule_source, "rule_source must never be empty"

    def test_response_rule_source_contains_rule_id(self, coach, user_id, session_id):
        _, response, _ = coach.process_query(session_id, "q-val-2", "r-val-2", user_id, "recovery advice", TODAY)
        assert "RULE_" in response.rule_source

    def test_response_text_is_non_empty(self, coach, user_id, session_id):
        _, response, _ = coach.process_query(session_id, "q-val-3", "r-val-3", user_id, "fitness tips", TODAY)
        assert response.response_text.strip()

    def test_empty_query_raises_validation_error(self, coach, user_id, session_id):
        with pytest.raises(ValidationError):
            coach.process_query(session_id, "q-e", "r-e", user_id, "", TODAY)

    def test_whitespace_query_raises_validation_error(self, coach, user_id, session_id):
        with pytest.raises(ValidationError):
            coach.process_query(session_id, "q-w", "r-w", user_id, "   ", TODAY)

    def test_missing_session_raises_validation_error(self, coach, user_id):
        with pytest.raises(ValidationError):
            coach.process_query("no-such-session", "q-ms", "r-ms", user_id, "test", TODAY)

    def test_missing_user_raises_validation_error(self, coach, session_id):
        with pytest.raises(ValidationError):
            coach.process_query(session_id, "q-mu", "r-mu", "u-ghost", "test", TODAY)

    def test_every_recommendation_in_response_has_rule_source(self, coach, user_id, session_id):
        _, _, recs = coach.process_query(session_id, "q-all-1", "r-all-1", user_id, "all advice please", TODAY)
        for rec in recs:
            assert rec.rule_source, f"Recommendation {rec.recommendation_id} is missing rule_source"
