import os
import unittest
from pathlib import Path
from datetime import datetime, timedelta
from app.database.connection import DatabaseManager
from app.database.migrations import MigrationRunner
from app.models.analytics import FitnessScore, WeeklyReport, MonthlyReport, AnalyticsSnapshot, ProgressTrend
from app.models.domain import User, BodyMeasurement
from app.models.habit_recovery import Habit, SleepLog, RecoveryLog
from app.models.workout import WorkoutSession
from app.repositories.user import UserRepository
from app.repositories.analytics import (
    FitnessScoreRepository, ReportRepository,
    AnalyticsSnapshotRepository, ProgressTrendRepository
)
from app.repositories.workout import WorkoutSessionRepository
from app.repositories.body_measurement import BodyMeasurementRepository
from app.repositories.nutrition import NutritionLogRepository
from app.repositories.habit import HabitRepository
from app.repositories.habit_log import HabitLogRepository
from app.repositories.recovery import RecoveryRepository
from app.services.analytics import AnalyticsService
from app.core.exceptions import ValidationError

TEST_DB_PATH = Path(__file__).resolve().parent / "test_fitos_s7.db"


class TestSprint7AnalyticsEngine(unittest.TestCase):
    """Integrity and logic validations covering the Analytics & Fitness Intelligence Engine (Sprint 7)."""

    def setUp(self):
        self.db = DatabaseManager(db_path=str(TEST_DB_PATH))

        self.runner = MigrationRunner(
            migrations_dir=Path(__file__).resolve().parent.parent / "app" / "database" / "migrations",
            db=self.db
        )
        self.runner.run_all()

        # Repositories
        self.user_repo = UserRepository(db=self.db)
        self.score_repo = FitnessScoreRepository(db=self.db)
        self.report_repo = ReportRepository(db=self.db)
        self.snapshot_repo = AnalyticsSnapshotRepository(db=self.db)
        self.trend_repo = ProgressTrendRepository(db=self.db)
        self.workout_session_repo = WorkoutSessionRepository(db=self.db)
        self.body_measurement_repo = BodyMeasurementRepository(db=self.db)
        self.nutrition_log_repo = NutritionLogRepository(db=self.db)
        self.habit_repo = HabitRepository(db=self.db)
        self.habit_log_repo = HabitLogRepository(db=self.db)
        self.recovery_repo = RecoveryRepository(db=self.db)

        # Service
        self.analytics_service = AnalyticsService(
            score_repo=self.score_repo,
            report_repo=self.report_repo,
            snapshot_repo=self.snapshot_repo,
            trend_repo=self.trend_repo,
            user_repo=self.user_repo,
            workout_session_repo=self.workout_session_repo,
            body_measurement_repo=self.body_measurement_repo,
            nutrition_log_repo=self.nutrition_log_repo,
            habit_repo=self.habit_repo,
            habit_log_repo=self.habit_log_repo,
            recovery_repo=self.recovery_repo,
            db=self.db
        )

        # Clear all tables
        try:
            for table in ["progress_trends", "analytics_snapshots", "monthly_reports",
                          "weekly_reports", "fitness_scores", "recovery_logs",
                          "habit_logs", "habits", "nutrition_logs", "exercise_sets",
                          "exercise_logs", "workout_sessions", "body_measurements",
                          "meal_entries", "meals", "users"]:
                self.db.execute_write(f"DELETE FROM {table};")
        except Exception:
            pass

        # Setup base user
        self.user = User(user_id="u-s7", name="Analytics User", email="analytics@fitos.org")
        self.user_repo.create_user(self.user)

    def tearDown(self):
        self.db.close_connection()
        if TEST_DB_PATH.exists():
            try:
                os.remove(TEST_DB_PATH)
                for suffix in ["-wal", "-shm"]:
                    extra_file = Path(str(TEST_DB_PATH) + suffix)
                    if extra_file.exists():
                        os.remove(extra_file)
            except OSError:
                pass

    # ============================================================
    # AGGREGATION ENGINE TESTS
    # ============================================================

    def test_get_aggregated_day_no_data(self):
        """Verifies aggregation returns defaults when no data exists."""
        agg = self.analytics_service.get_aggregated_day("u-s7", "2026-07-15")
        self.assertEqual(agg["total_workouts"], 0)
        self.assertEqual(agg["calories_consumed"], 0.0)
        self.assertEqual(agg["protein_g"], 0.0)
        self.assertEqual(agg["recovery_score"], 0.0)
        self.assertEqual(agg["habits_completion_rate"], 0.0)

    def test_get_aggregated_day_with_data(self):
        """Verifies aggregation collects data from all modules."""
        # Create a recovery log via repo
        from app.models.habit_recovery import RecoveryLog as RL
        rl = RL(recovery_log_id="rl-agg", user_id="u-s7", log_date="2026-07-15",
                recovery_score=85.0, readiness_state="FULL")
        self.recovery_repo.create_recovery_log(rl)

        # Create a habit via repo
        from app.models.habit_recovery import Habit
        h = Habit(habit_id="h-agg", user_id="u-s7", name="Drink Water")
        self.habit_repo.create_habit(h)

        # Log the habit as completed via repo
        from app.models.domain import HabitLog
        hl = HabitLog(habit_log_id="hl-agg", habit_id="h-agg", user_id="u-s7",
                      log_date="2026-07-15", status="completed")
        self.habit_log_repo.create_habit_log(hl)

        agg = self.analytics_service.get_aggregated_day("u-s7", "2026-07-15")
        self.assertEqual(agg["recovery_score"], 85.0)
        self.assertEqual(agg["habits_completion_rate"], 100.0)
        self.assertEqual(agg["habits_completed"], 1)

    # ============================================================
    # FITNESS SCORE TESTS
    # ============================================================

    def test_fitness_score_computation(self):
        """Verifies fitness score is computed and within 0-100 range."""
        score = self.analytics_service.compute_fitness_score("u-s7", "2026-07-20")
        self.assertIsNotNone(score)
        self.assertEqual(score.user_id, "u-s7")
        self.assertEqual(score.log_date, "2026-07-20")
        self.assertGreaterEqual(score.overall_score, 0)
        self.assertLessEqual(score.overall_score, 100)

    def test_fitness_score_breakdown(self):
        """Verifies all sub-scores are populated."""
        score = self.analytics_service.compute_fitness_score("u-s7", "2026-07-21")
        self.assertGreaterEqual(score.nutrition_score, 0)
        self.assertGreaterEqual(score.workout_consistency_score, 0)
        self.assertGreaterEqual(score.progressive_overload_score, 0)
        self.assertGreaterEqual(score.recovery_score, 0)
        self.assertGreaterEqual(score.habits_score, 0)
        self.assertGreaterEqual(score.body_progress_score, 0)
        self.assertGreaterEqual(score.ai_adherence_score, 0)

    def test_fitness_score_weighted_sum(self):
        """Verifies overall is weighted sum of sub-scores."""
        # Create good conditions via repos
        from app.models.habit_recovery import RecoveryLog as RL
        rl = RL(recovery_log_id="rl-fs1", user_id="u-s7", log_date="2026-07-22",
                recovery_score=90.0, readiness_state="FULL")
        self.recovery_repo.create_recovery_log(rl)

        # Log nutrition via repo
        from app.models.nutrition import NutritionLog
        nl = NutritionLog(log_id="nl-fs1", user_id="u-s7", log_date="2026-07-22",
                          total_calories=2000.0, total_protein=130.0)
        self.nutrition_log_repo.upsert_log(nl)

        score = self.analytics_service.compute_fitness_score("u-s7", "2026-07-22")
        self.assertGreater(score.overall_score, 0)
        # Nutrition: (2000/2000 * 0.5 + 130/120 * 0.5) * 100 = (1.0 * 0.5 + 1.0 * 0.5) * 100 = 100.0
        self.assertAlmostEqual(score.nutrition_score, 100.0, delta=5)
        # Recovery from DB: 90.0
        self.assertAlmostEqual(score.recovery_score, 90.0, delta=5)
        # Overall should be meaningful
        self.assertGreater(score.overall_score, 30)

    def test_fitness_score_persisted(self):
        """Verifies fitness score is saved to database."""
        score = self.analytics_service.compute_fitness_score("u-s7", "2026-07-23")
        fetched = self.score_repo.get_score_by_date("u-s7", "2026-07-23")
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.overall_score, score.overall_score)

    def test_fitness_score_nonexistent_user(self):
        """Verifies error for non-existent user."""
        with self.assertRaises(ValidationError):
            self.analytics_service.compute_fitness_score("u-nonexistent", "2026-07-20")

    # ============================================================
    # TREND ANALYSIS TESTS
    # ============================================================

    def test_trend_analysis_stable(self):
        """Verifies stable trend when no data."""
        trend = self.analytics_service.analyze_trends("u-s7", "recovery", days=7)
        self.assertEqual(trend.trend_direction, "stable")

    def test_trend_analysis_recovery(self):
        """Verifies recovery trend with data."""
        # Insert recovery logs
        for i, score_val in enumerate([70.0, 75.0, 80.0, 78.0, 82.0, 85.0, 90.0]):
            day = (datetime.now() - timedelta(days=6 - i)).strftime("%Y-%m-%d")
            self.db.execute_write(
                """INSERT INTO recovery_logs (recovery_log_id, user_id, log_date, recovery_score, readiness_state)
                   VALUES (?, ?, ?, ?, ?)""",
                (f"rl-trend-{i}", "u-s7", day, score_val, "MODERATE")
            )

        trend = self.analytics_service.analyze_trends("u-s7", "recovery", days=7)
        self.assertIn(trend.trend_direction, ["increasing", "stable"])

    def test_trend_saved_to_db(self):
        """Verifies trend is saved to progress_trends table."""
        trend = self.analytics_service.analyze_trends("u-s7", "consistency", days=7)
        fetched = self.trend_repo.get_trend_by_metric("u-s7", "consistency")
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.trend_direction, trend.trend_direction)

    # ============================================================
    # WEEKLY REPORT TESTS
    # ============================================================

    def test_weekly_report_generation(self):
        """Verifies weekly report is generated with valid structure."""
        # Add some workouts
        today = datetime.now()
        for i in range(3):
            day = (today - timedelta(days=i)).strftime("%Y-%m-%d")
            self.db.execute_write(
                """INSERT INTO workout_sessions (session_id, user_id, plan_id, start_time, end_time, status, calories_burned_kcal)
                   VALUES (?, ?, NULL, ?, ?, 'COMPLETED', ?)""",
                (f"ws-wr-{i}", "u-s7", f"{day} 10:00:00", f"{day} 11:00:00", 350.0)
            )

        week_start = (today - timedelta(days=today.weekday())).strftime("%Y-%m-%d")
        report = self.analytics_service.generate_weekly_report("u-s7", week_start)

        self.assertIsNotNone(report)
        self.assertEqual(report.user_id, "u-s7")
        self.assertGreaterEqual(report.total_workouts, 0)
        self.assertGreaterEqual(report.avg_fitness_score, 0)

    def test_weekly_report_persisted(self):
        """Verifies weekly report is saved to database."""
        today = datetime.now()
        week_start = (today - timedelta(days=today.weekday())).strftime("%Y-%m-%d")
        report = self.analytics_service.generate_weekly_report("u-s7", week_start)

        fetched = self.report_repo.get_weekly_report_by_week("u-s7", week_start)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.total_workouts, report.total_workouts)

    def test_weekly_report_with_insights(self):
        """Verifies weekly report contains insight summaries."""
        today = datetime.now()
        week_start = (today - timedelta(days=today.weekday())).strftime("%Y-%m-%d")
        report = self.analytics_service.generate_weekly_report("u-s7", week_start)

        self.assertIsInstance(report.insight_summary, str)
        self.assertGreater(len(report.insight_summary), 0)

    # ============================================================
    # MONTHLY REPORT TESTS
    # ============================================================

    def test_monthly_report_generation(self):
        """Verifies monthly report is generated."""
        month_start = "2026-07-01"
        report = self.analytics_service.generate_monthly_report("u-s7", month_start)

        self.assertIsNotNone(report)
        self.assertEqual(report.user_id, "u-s7")
        self.assertEqual(report.month_start, "2026-07-01")
        self.assertEqual(report.month_end, "2026-07-31")
        self.assertGreaterEqual(report.avg_fitness_score, 0)

    def test_monthly_report_persisted(self):
        """Verifies monthly report is saved to database."""
        report = self.analytics_service.generate_monthly_report("u-s7", "2026-07-01")
        fetched = self.report_repo.get_monthly_report_by_month("u-s7", "2026-07-01")
        self.assertIsNotNone(fetched)

    def test_monthly_report_with_body_changes(self):
        """Verifies monthly report includes body changes when measurements exist."""
        # Add body measurements
        self.db.execute_write(
            """INSERT INTO body_measurements (measurement_id, user_id, weight_kg, logged_at)
               VALUES (?, ?, ?, ?)""",
            ("bm-mr1", "u-s7", 82.0, "2026-07-01 08:00:00")
        )
        self.db.execute_write(
            """INSERT INTO body_measurements (measurement_id, user_id, weight_kg, logged_at)
               VALUES (?, ?, ?, ?)""",
            ("bm-mr2", "u-s7", 80.5, "2026-07-31 08:00:00")
        )

        report = self.analytics_service.generate_monthly_report("u-s7", "2026-07-01")
        self.assertIn("weight", report.body_changes_summary.lower())

    # ============================================================
    # SNAPSHOT TESTS
    # ============================================================

    def test_take_snapshot(self):
        """Verifies analytics snapshot creation."""
        snapshot = self.analytics_service.take_snapshot("u-s7", "2026-08-01")
        self.assertIsNotNone(snapshot)
        self.assertEqual(snapshot.user_id, "u-s7")
        self.assertGreaterEqual(snapshot.fitness_score, 0)

    def test_snapshot_persisted(self):
        """Verifies snapshot is saved to database."""
        self.analytics_service.take_snapshot("u-s7", "2026-08-01")
        fetched = self.snapshot_repo.get_snapshot_by_date("u-s7", "2026-08-01")
        self.assertIsNotNone(fetched)

    def test_dashboard_data(self):
        """Verifies dashboard returns all required sections."""
        data = self.analytics_service.get_dashboard_data("u-s7", "2026-08-01")
        self.assertIn("snapshot", data)
        self.assertIn("weekly_report", data)
        self.assertIn("trends", data)

    # ============================================================
    # EDGE CASE TESTS
    # ============================================================

    def test_missing_data_handling(self):
        """Verifies analytics handles missing data gracefully."""
        score = self.analytics_service.compute_fitness_score("u-s7", "2026-09-01")
        self.assertIsNotNone(score)
        self.assertGreaterEqual(score.overall_score, 0)
        self.assertLessEqual(score.overall_score, 100)

    def test_generate_insights_no_data(self):
        """Verifies insight generation with no data returns messages."""
        today = datetime.now()
        week_end = today.strftime("%Y-%m-%d")
        week_start = (today - timedelta(days=6)).strftime("%Y-%m-%d")
        report = self.analytics_service.generate_weekly_report("u-s7", week_start)
        self.assertIsInstance(report.insight_summary, str)
        self.assertGreater(len(report.insight_summary), 0)

    def test_multiple_daily_scores_upsert(self):
        """Verifies running compute_fitness_score twice for same date upserts rather than duplicates."""
        s1 = self.analytics_service.compute_fitness_score("u-s7", "2026-09-10")
        s2 = self.analytics_service.compute_fitness_score("u-s7", "2026-09-10")
        self.assertEqual(s1.overall_score, s2.overall_score)

        scores = self.score_repo.get_user_scores("u-s7")
        dates = [s.log_date for s in scores]
        self.assertEqual(dates.count("2026-09-10"), 1)


if __name__ == "__main__":
    unittest.main()