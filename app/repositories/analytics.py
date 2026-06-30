from typing import Optional, List
from app.repositories.base import BaseRepository
from app.models.analytics import FitnessScore, WeeklyReport, MonthlyReport, AnalyticsSnapshot, ProgressTrend


class FitnessScoreRepository(BaseRepository):
    """Repository class managing CRUD operations for fitness_scores table."""

    def create_score(self, score: FitnessScore) -> str:
        """Saves a FitnessScore object to the database."""
        self.create("fitness_scores", score.to_dict())
        return score.score_id

    def get_score(self, score_id: str) -> Optional[FitnessScore]:
        """Fetches a FitnessScore by ID."""
        row = self.read("fitness_scores", "score_id", score_id)
        return FitnessScore.from_dict(row) if row else None

    def get_score_by_date(self, user_id: str, log_date: str) -> Optional[FitnessScore]:
        """Fetches a FitnessScore by user and date."""
        query = "SELECT * FROM fitness_scores WHERE user_id = ? AND log_date = ? LIMIT 1;"
        row = self.db.execute_read_one(query, (user_id, log_date))
        return FitnessScore.from_dict(row) if row else None

    def get_user_scores(self, user_id: str) -> List[FitnessScore]:
        """Retrieves all scores for a user, newest first."""
        query = "SELECT * FROM fitness_scores WHERE user_id = ? ORDER BY log_date DESC;"
        rows = self.db.execute_read(query, (user_id,))
        return [FitnessScore.from_dict(row) for row in rows]

    def get_scores_by_date_range(self, user_id: str, start_date: str, end_date: str) -> List[FitnessScore]:
        """Retrieves scores for a user within a date range."""
        query = "SELECT * FROM fitness_scores WHERE user_id = ? AND log_date >= ? AND log_date <= ? ORDER BY log_date ASC;"
        rows = self.db.execute_read(query, (user_id, start_date, end_date))
        return [FitnessScore.from_dict(row) for row in rows]

    def upsert_score(self, score: FitnessScore) -> str:
        """Inserts or replaces a FitnessScore for a user+date pair."""
        data = self._filter_fields_by_schema("fitness_scores", score.to_dict())
        columns = ", ".join(data.keys())
        placeholders = ", ".join("?" for _ in data)
        query = f"INSERT OR REPLACE INTO fitness_scores ({columns}) VALUES ({placeholders});"
        self.db.execute_write(query, tuple(data.values()))
        return score.score_id


class ReportRepository(BaseRepository):
    """Repository class managing CRUD operations for weekly_reports and monthly_reports."""

    # --- Weekly Reports ---

    def create_weekly_report(self, report: WeeklyReport) -> str:
        """Saves a WeeklyReport object to the database."""
        self.create("weekly_reports", report.to_dict())
        return report.report_id

    def get_weekly_report(self, report_id: str) -> Optional[WeeklyReport]:
        """Fetches a WeeklyReport by ID."""
        row = self.read("weekly_reports", "report_id", report_id)
        return WeeklyReport.from_dict(row) if row else None

    def get_weekly_report_by_week(self, user_id: str, week_start: str) -> Optional[WeeklyReport]:
        """Fetches a WeeklyReport by user and week start date."""
        query = "SELECT * FROM weekly_reports WHERE user_id = ? AND week_start = ? LIMIT 1;"
        row = self.db.execute_read_one(query, (user_id, week_start))
        return WeeklyReport.from_dict(row) if row else None

    def get_user_weekly_reports(self, user_id: str) -> List[WeeklyReport]:
        """Retrieves all weekly reports for a user."""
        query = "SELECT * FROM weekly_reports WHERE user_id = ? ORDER BY week_start DESC;"
        rows = self.db.execute_read(query, (user_id,))
        return [WeeklyReport.from_dict(row) for row in rows]

    def upsert_weekly_report(self, report: WeeklyReport) -> str:
        """Inserts or replaces a WeeklyReport."""
        data = self._filter_fields_by_schema("weekly_reports", report.to_dict())
        columns = ", ".join(data.keys())
        placeholders = ", ".join("?" for _ in data)
        query = f"INSERT OR REPLACE INTO weekly_reports ({columns}) VALUES ({placeholders});"
        self.db.execute_write(query, tuple(data.values()))
        return report.report_id

    # --- Monthly Reports ---

    def create_monthly_report(self, report: MonthlyReport) -> str:
        """Saves a MonthlyReport object to the database."""
        self.create("monthly_reports", report.to_dict())
        return report.report_id

    def get_monthly_report(self, report_id: str) -> Optional[MonthlyReport]:
        """Fetches a MonthlyReport by ID."""
        row = self.read("monthly_reports", "report_id", report_id)
        return MonthlyReport.from_dict(row) if row else None

    def get_monthly_report_by_month(self, user_id: str, month_start: str) -> Optional[MonthlyReport]:
        """Fetches a MonthlyReport by user and month start date."""
        query = "SELECT * FROM monthly_reports WHERE user_id = ? AND month_start = ? LIMIT 1;"
        row = self.db.execute_read_one(query, (user_id, month_start))
        return MonthlyReport.from_dict(row) if row else None

    def get_user_monthly_reports(self, user_id: str) -> List[MonthlyReport]:
        """Retrieves all monthly reports for a user."""
        query = "SELECT * FROM monthly_reports WHERE user_id = ? ORDER BY month_start DESC;"
        rows = self.db.execute_read(query, (user_id,))
        return [MonthlyReport.from_dict(row) for row in rows]

    def upsert_monthly_report(self, report: MonthlyReport) -> str:
        """Inserts or replaces a MonthlyReport."""
        data = self._filter_fields_by_schema("monthly_reports", report.to_dict())
        columns = ", ".join(data.keys())
        placeholders = ", ".join("?" for _ in data)
        query = f"INSERT OR REPLACE INTO monthly_reports ({columns}) VALUES ({placeholders});"
        self.db.execute_write(query, tuple(data.values()))
        return report.report_id


class AnalyticsSnapshotRepository(BaseRepository):
    """Repository class managing CRUD operations for analytics_snapshots table."""

    def create_snapshot(self, snapshot: AnalyticsSnapshot) -> str:
        """Saves an AnalyticsSnapshot to the database."""
        self.create("analytics_snapshots", snapshot.to_dict())
        return snapshot.snapshot_id

    def get_snapshot(self, snapshot_id: str) -> Optional[AnalyticsSnapshot]:
        """Fetches an AnalyticsSnapshot by ID."""
        row = self.read("analytics_snapshots", "snapshot_id", snapshot_id)
        return AnalyticsSnapshot.from_dict(row) if row else None

    def get_snapshot_by_date(self, user_id: str, snapshot_date: str) -> Optional[AnalyticsSnapshot]:
        """Fetches the snapshot for a user on a specific date."""
        query = "SELECT * FROM analytics_snapshots WHERE user_id = ? AND snapshot_date = ? LIMIT 1;"
        row = self.db.execute_read_one(query, (user_id, snapshot_date))
        return AnalyticsSnapshot.from_dict(row) if row else None

    def get_user_snapshots(self, user_id: str) -> List[AnalyticsSnapshot]:
        """Retrieves all snapshots for a user."""
        query = "SELECT * FROM analytics_snapshots WHERE user_id = ? ORDER BY snapshot_date DESC;"
        rows = self.db.execute_read(query, (user_id,))
        return [AnalyticsSnapshot.from_dict(row) for row in rows]

    def upsert_snapshot(self, snapshot: AnalyticsSnapshot) -> str:
        """Inserts or replaces an AnalyticsSnapshot."""
        data = self._filter_fields_by_schema("analytics_snapshots", snapshot.to_dict())
        columns = ", ".join(data.keys())
        placeholders = ", ".join("?" for _ in data)
        query = f"INSERT OR REPLACE INTO analytics_snapshots ({columns}) VALUES ({placeholders});"
        self.db.execute_write(query, tuple(data.values()))
        return snapshot.snapshot_id


class ProgressTrendRepository(BaseRepository):
    """Repository class managing CRUD operations for progress_trends table."""

    def create_trend(self, trend: ProgressTrend) -> str:
        """Saves a ProgressTrend to the database."""
        self.create("progress_trends", trend.to_dict())
        return trend.trend_id

    def get_trend(self, trend_id: str) -> Optional[ProgressTrend]:
        """Fetches a ProgressTrend by ID."""
        row = self.read("progress_trends", "trend_id", trend_id)
        return ProgressTrend.from_dict(row) if row else None

    def get_user_trends(self, user_id: str) -> List[ProgressTrend]:
        """Retrieves all trends for a user."""
        query = "SELECT * FROM progress_trends WHERE user_id = ? ORDER BY created_at DESC;"
        rows = self.db.execute_read(query, (user_id,))
        return [ProgressTrend.from_dict(row) for row in rows]

    def get_trend_by_metric(self, user_id: str, metric_name: str) -> Optional[ProgressTrend]:
        """Retrieves the latest trend for a specific metric."""
        query = "SELECT * FROM progress_trends WHERE user_id = ? AND metric_name = ? ORDER BY created_at DESC LIMIT 1;"
        row = self.db.execute_read_one(query, (user_id, metric_name))
        return ProgressTrend.from_dict(row) if row else None

    def upsert_trend(self, trend: ProgressTrend) -> str:
        """Inserts or replaces a ProgressTrend."""
        data = self._filter_fields_by_schema("progress_trends", trend.to_dict())
        columns = ", ".join(data.keys())
        placeholders = ", ".join("?" for _ in data)
        query = f"INSERT OR REPLACE INTO progress_trends ({columns}) VALUES ({placeholders});"
        self.db.execute_write(query, tuple(data.values()))
        return trend.trend_id