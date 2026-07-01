"""AnalyticsService — Sprint 7 Analytics & Fitness Intelligence Engine.

Aggregates all fitness data (Workout + Nutrition + Habits + Recovery + AI logs),
generates deterministic Fitness Score (0-100), trend analysis, weekly/monthly reports,
and rule-based insights.

READ-ONLY dependency on Sprint 3-6 systems. NEVER modifies raw data.
"""

from datetime import datetime, timedelta

from app.core.exceptions import ServiceError, ValidationError
from app.core.logging import logger
from app.database.connection import DatabaseManager, db_manager
from app.models.analytics import (
    AnalyticsSnapshot,
    FitnessScore,
    MonthlyReport,
    ProgressTrend,
    WeeklyReport,
)
from app.repositories.analytics import (
    AnalyticsSnapshotRepository,
    FitnessScoreRepository,
    ProgressTrendRepository,
    ReportRepository,
)
from app.repositories.body_measurement import BodyMeasurementRepository
from app.repositories.habit import HabitRepository
from app.repositories.habit_log import HabitLogRepository
from app.repositories.nutrition import NutritionLogRepository
from app.repositories.recovery import RecoveryRepository
from app.repositories.user import UserRepository
from app.repositories.workout import WorkoutSessionRepository

# Fitness Score weights (deterministic)
NUTRITION_WEIGHT = 0.25
WORKOUT_CONSISTENCY_WEIGHT = 0.20
PROGRESSIVE_OVERLOAD_WEIGHT = 0.15
RECOVERY_WEIGHT = 0.15
HABITS_WEIGHT = 0.10
BODY_PROGRESS_WEIGHT = 0.10
AI_ADHERENCE_WEIGHT = 0.05

# Target defaults
DEFAULT_CALORIE_TARGET = 2000.0
DEFAULT_PROTEIN_TARGET = 120.0
DEFAULT_TARGET_WORKOUTS_PER_WEEK = 4
DEFAULT_WATER_INTAKE_CUPS = 8


class AnalyticsService:
    """Core analytics engine — aggregation, fitness score, trends, reports, insights."""

    def __init__(
        self,
        score_repo: FitnessScoreRepository | None = None,
        report_repo: ReportRepository | None = None,
        snapshot_repo: AnalyticsSnapshotRepository | None = None,
        trend_repo: ProgressTrendRepository | None = None,
        user_repo: UserRepository | None = None,
        workout_session_repo: WorkoutSessionRepository | None = None,
        body_measurement_repo: BodyMeasurementRepository | None = None,
        nutrition_log_repo: NutritionLogRepository | None = None,
        habit_repo: HabitRepository | None = None,
        habit_log_repo: HabitLogRepository | None = None,
        recovery_repo: RecoveryRepository | None = None,
        db: DatabaseManager | None = None,
    ):
        self.score_repo = score_repo or FitnessScoreRepository()
        self.report_repo = report_repo or ReportRepository()
        self.snapshot_repo = snapshot_repo or AnalyticsSnapshotRepository()
        self.trend_repo = trend_repo or ProgressTrendRepository()
        self.user_repo = user_repo or UserRepository()
        self.workout_session_repo = workout_session_repo or WorkoutSessionRepository()
        self.body_measurement_repo = body_measurement_repo or BodyMeasurementRepository()
        self.nutrition_log_repo = nutrition_log_repo or NutritionLogRepository()
        self.habit_repo = habit_repo or HabitRepository()
        self.habit_log_repo = habit_log_repo or HabitLogRepository()
        self.recovery_repo = recovery_repo or RecoveryRepository()
        self.db = db or db_manager

    # ================================================================== #
    # SECTION A: DATA AGGREGATION ENGINE
    # ================================================================== #

    def get_aggregated_day(self, user_id: str, log_date: str) -> dict:
        """Builds a unified dataset for a single day, pulling from all modules."""
        # Workout data
        sessions = self._get_workout_sessions_for_date(user_id, log_date)
        total_workouts = len(sessions)
        total_calories_burned = sum(s.calories_burned_kcal for s in sessions)

        # Nutrition data
        nutrition_log = self.nutrition_log_repo.get_log_by_date(user_id, log_date)
        calories_consumed = nutrition_log.total_calories if nutrition_log else 0.0
        protein_g = nutrition_log.total_protein if nutrition_log else 0.0

        # Recovery data
        recovery = self.recovery_repo.get_recovery_log_by_date(user_id, log_date)
        recovery_score = recovery.recovery_score if recovery else 0.0

        # Habits data
        habits = self.habit_repo.get_user_habits(user_id)
        habits_completed = 0
        habits_total = len(habits) or 1
        for h in habits:
            log = self.habit_log_repo.get_habit_log_by_date(h.habit_id, user_id, log_date)
            if log and log.status == "completed":
                habits_completed += 1
        habits_completion_rate = (habits_completed / habits_total) * 100.0

        # Body measurement
        measurement = None
        try:
            measurements = self.body_measurement_repo.get_user_measurements(user_id)
            if measurements:
                # Find closest measurement to log_date
                measurement = measurements[0]
        except Exception:
            pass

        return {
            "date": log_date,
            "total_workouts": total_workouts,
            "calories_burned": total_calories_burned,
            "calories_consumed": round(calories_consumed, 2),
            "protein_g": round(protein_g, 2),
            "recovery_score": round(recovery_score, 2),
            "habits_completion_rate": round(habits_completion_rate, 2),
            "habits_completed": habits_completed,
            "habits_total": habits_total,
            "body_weight_kg": measurement.weight_kg if measurement else None,
        }

    def _get_workout_sessions_for_date(self, user_id: str, log_date: str) -> list:
        """Gets completed workout sessions for a specific date."""
        try:
            next_date = (datetime.strptime(log_date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
            query = """
                SELECT * FROM workout_sessions
                WHERE user_id = ? AND status = 'COMPLETED'
                  AND start_time >= ? AND start_time < ?
                ORDER BY start_time ASC;
            """
            from app.models.workout import WorkoutSession

            rows = self.db.execute_read(query, (user_id, log_date, next_date))
            return [WorkoutSession.from_dict(r) for r in rows]
        except Exception as e:
            logger.warning(f"Failed to get workout sessions for {log_date}: {e}")
            return []

    # ================================================================== #
    # SECTION B: FITNESS SCORE ENGINE (0-100)
    # ================================================================== #

    def compute_fitness_score(self, user_id: str, log_date: str) -> FitnessScore:
        """Computes the daily deterministic Fitness Score (0-100) with sub-score breakdown."""
        logger.info(f"Computing fitness score for user {user_id} on {log_date}")

        if not self.user_repo.get_user(user_id):
            raise ValidationError(f"User with ID {user_id} does not exist.")

        agg = self.get_aggregated_day(user_id, log_date)

        # 1. Nutrition Score (25%) — based on calorie + protein target achievement
        cal_ratio = min(agg["calories_consumed"] / DEFAULT_CALORIE_TARGET, 1.0)
        protein_ratio = min(agg["protein_g"] / DEFAULT_PROTEIN_TARGET, 1.0)
        nutrition_score = ((cal_ratio * 0.5) + (protein_ratio * 0.5)) * 100.0

        # 2. Workout Consistency (20%) — based on whether user worked out
        consistency_score = 100.0 if agg["total_workouts"] > 0 else 0.0

        # 3. Progressive Overload (15%) — based on calories burned if worked out
        if agg["total_workouts"] > 0 and agg["calories_burned"] > 0:
            overload_ratio = min(agg["calories_burned"] / 500.0, 1.0)
            overload_score = overload_ratio * 100.0
        else:
            overload_score = 0.0

        # 4. Recovery Score (15%) — direct from recovery system
        recovery_score = agg["recovery_score"]

        # 5. Habits Score (10%) — based on habit completion rate
        habits_score = agg["habits_completion_rate"]

        # 6. Body Progress (10%) — based on weight trend if available
        body_progress_score = self._compute_body_progress(user_id)

        # 7. AI Adherence (5%) — placeholder (Sprint 6 AI logs not fully implemented)
        ai_adherence_score = 50.0  # Neutral default until Sprint 6 provides data

        # Overall weighted score
        overall = (
            (nutrition_score * NUTRITION_WEIGHT)
            + (consistency_score * WORKOUT_CONSISTENCY_WEIGHT)
            + (overload_score * PROGRESSIVE_OVERLOAD_WEIGHT)
            + (recovery_score * RECOVERY_WEIGHT)
            + (habits_score * HABITS_WEIGHT)
            + (body_progress_score * BODY_PROGRESS_WEIGHT)
            + (ai_adherence_score * AI_ADHERENCE_WEIGHT)
        )
        overall = round(max(0.0, min(100.0, overall)), 2)

        score = FitnessScore(
            score_id=f"fs-{user_id}-{log_date}",
            user_id=user_id,
            log_date=log_date,
            overall_score=overall,
            nutrition_score=round(nutrition_score, 2),
            workout_consistency_score=round(consistency_score, 2),
            progressive_overload_score=round(overload_score, 2),
            recovery_score=round(recovery_score, 2),
            habits_score=round(habits_score, 2),
            body_progress_score=round(body_progress_score, 2),
            ai_adherence_score=round(ai_adherence_score, 2),
        )

        try:
            self.score_repo.upsert_score(score)
        except Exception as e:
            logger.error(f"Failed to save fitness score: {e}")
            raise ServiceError("Failed to save fitness score.", details=str(e))

        return score

    def _compute_body_progress(self, user_id: str) -> float:
        """Computes body progress score based on weight trend."""
        try:
            measurements = self.body_measurement_repo.get_user_measurements(user_id)
            if len(measurements) < 2:
                return 50.0  # Neutral

            # Compare first and last measurement weight
            first = measurements[-1]
            last = measurements[0]
            if first.weight_kg and last.weight_kg:
                weight_change = first.weight_kg - last.weight_kg
                # Weight loss (negative) = positive for most users, up to +10%
                if weight_change < 0:
                    progress = min(abs(weight_change) / first.weight_kg * 500, 100.0)
                else:
                    progress = max(50.0 - (weight_change / first.weight_kg * 500), 0.0)
                return round(progress, 2)
            return 50.0
        except Exception:
            return 50.0

    # ================================================================== #
    # SECTION C: TREND ANALYSIS ENGINE
    # ================================================================== #

    def analyze_trends(self, user_id: str, metric_name: str, days: int = 30) -> ProgressTrend:
        """Computes trend analysis for a specific metric using moving avg, delta, and percentage change."""
        logger.info(f"Analyzing trend for user {user_id}, metric {metric_name}, days {days}")

        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=days - 1)).strftime("%Y-%m-%d")

        # Gather data based on metric
        if metric_name == "weight":
            values = self._get_weight_series(user_id, start_date, end_date)
        elif metric_name == "recovery":
            values = self._get_recovery_series(user_id, start_date, end_date)
        elif metric_name == "consistency":
            values = self._get_workout_consistency_series(user_id, start_date, end_date)
        elif metric_name == "nutrition_stability":
            values = self._get_nutrition_series(user_id, start_date, end_date)
        elif metric_name == "strength":
            values = self._get_strength_series(user_id, start_date, end_date)
        else:
            raise ValidationError(f"Unknown metric: {metric_name}")

        if not values:
            # Return neutral trend
            return self._save_trend(user_id, metric_name, "stable", 0.0, 0.0, start_date, end_date)

        current_values = [v for _, v in values]
        current_avg = sum(current_values) / len(current_values)
        prev_avg = current_avg  # fallback

        # Split data into two halves for comparison
        mid = len(values) // 2
        if mid > 0:
            first_half = [v for _, v in values[:mid]]
            second_half = [v for _, v in values[mid:]]
            if first_half and second_half:
                current_avg = sum(second_half) / len(second_half)
                prev_avg = sum(first_half) / len(first_half)

        # Moving averages
        all_values = [v for _, v in values]
        ma_7 = self._moving_average(all_values, min(7, len(all_values)))
        ma_30 = self._moving_average(all_values, min(30, len(all_values)))

        # Delta and percentage
        delta = round(current_avg - prev_avg, 2)
        pct_change = round((delta / prev_avg * 100.0) if prev_avg > 0 else 0.0, 2)

        # Determine direction
        if abs(delta) < 0.5:
            direction = "stable"
        elif delta > 0:
            direction = "increasing"
        else:
            direction = "decreasing"

        return self._save_trend(
            user_id,
            metric_name,
            direction,
            round(current_avg, 2),
            round(prev_avg, 2),
            start_date,
            end_date,
            delta,
            pct_change,
            round(ma_7, 2),
            round(ma_30, 2),
        )

    def _get_weight_series(self, user_id: str, start_date: str, end_date: str) -> list[tuple[str, float]]:
        """Returns time-ordered (date, weight_kg) pairs."""
        try:
            measurements = self.body_measurement_repo.get_user_measurements(user_id)
            return [
                (m.logged_at[:10], m.weight_kg)
                for m in measurements
                if m.logged_at[:10] >= start_date and m.logged_at[:10] <= end_date
            ]
        except Exception:
            return []

    def _get_recovery_series(self, user_id: str, start_date: str, end_date: str) -> list[tuple[str, float]]:
        """Returns time-ordered (date, recovery_score) pairs."""
        try:
            logs = self.recovery_repo.get_recovery_logs_by_date_range(user_id, start_date, end_date)
            return [(l.log_date, l.recovery_score) for l in logs]
        except Exception:
            return []

    def _get_workout_consistency_series(self, user_id: str, start_date: str, end_date: str) -> list[tuple[str, float]]:
        """Returns daily workout count as (date, count) pairs."""
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            series = []
            current = start_dt
            while current <= end_dt:
                date_str = current.strftime("%Y-%m-%d")
                sessions = self._get_workout_sessions_for_date(user_id, date_str)
                series.append((date_str, float(len(sessions))))
                current += timedelta(days=1)
            return series
        except Exception:
            return []

    def _get_nutrition_series(self, user_id: str, start_date: str, end_date: str) -> list[tuple[str, float]]:
        """Returns daily calorie intake as (date, calories) pairs."""
        try:
            logs = self.nutrition_log_repo.get_user_logs(user_id)
            return [
                (l.log_date, l.total_calories)
                for l in logs
                if start_date <= l.log_date <= end_date and l.total_calories > 0
            ]
        except Exception:
            return []

    def _get_strength_series(self, user_id: str, start_date: str, end_date: str) -> list[tuple[str, float]]:
        """Returns max weight lifted across exercises as a proxy strength metric."""
        try:
            query = """
                SELECT ws.start_time, MAX(es.weight) as max_weight
                FROM workout_sessions ws
                JOIN exercise_sets es ON ws.session_id = es.session_id
                WHERE ws.user_id = ? AND ws.status = 'COMPLETED'
                  AND ws.start_time >= ? AND ws.start_time < ?
                GROUP BY ws.session_id
                ORDER BY ws.start_time ASC;
            """
            next_date = (datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
            rows = self.db.execute_read(query, (user_id, start_date, next_date))
            return [(r["start_time"][:10], float(r["max_weight"])) for r in rows]
        except Exception:
            return []

    def _moving_average(self, values: list[float], window: int) -> float:
        """Computes simple moving average of the last N values."""
        if not values or window <= 0:
            return 0.0
        recent = values[-window:]
        return sum(recent) / len(recent)

    def _save_trend(
        self,
        user_id: str,
        metric_name: str,
        direction: str,
        current: float,
        previous: float,
        start: str,
        end: str,
        delta: float = 0.0,
        pct: float = 0.0,
        ma7: float = 0.0,
        ma30: float = 0.0,
    ) -> ProgressTrend:
        """Saves and returns a ProgressTrend record."""
        import uuid

        trend = ProgressTrend(
            trend_id=str(uuid.uuid4()),
            user_id=user_id,
            metric_name=metric_name,
            trend_direction=direction,
            current_value=current,
            previous_value=previous,
            delta_value=delta,
            percentage_change=pct,
            moving_avg_7day=ma7,
            moving_avg_30day=ma30,
            period_start=start,
            period_end=end,
        )
        try:
            self.trend_repo.upsert_trend(trend)
        except Exception as e:
            logger.warning(f"Failed to save trend: {e}")
        return trend

    # ================================================================== #
    # SECTION D: WEEKLY & MONTHLY REPORT ENGINE
    # ================================================================== #

    def generate_weekly_report(self, user_id: str, week_start: str) -> WeeklyReport:
        """Generates a structured weekly report from raw logs."""
        logger.info(f"Generating weekly report for user {user_id}, week {week_start}")

        if not self.user_repo.get_user(user_id):
            raise ValidationError(f"User with ID {user_id} does not exist.")

        week_start_dt = datetime.strptime(week_start, "%Y-%m-%d")
        week_end_dt = week_start_dt + timedelta(days=6)
        week_end = week_end_dt.strftime("%Y-%m-%d")

        # Aggregate daily data
        scores = []
        total_calories = 0.0
        total_protein = 0.0
        total_recovery = 0.0
        recovery_days = 0
        total_workouts = 0

        current = week_start_dt
        while current <= week_end_dt:
            date_str = current.strftime("%Y-%m-%d")
            score = self.compute_fitness_score(user_id, date_str)
            scores.append(score)

            agg = self.get_aggregated_day(user_id, date_str)
            total_workouts += agg["total_workouts"]
            total_calories += agg["calories_consumed"]
            total_protein += agg["protein_g"]
            if agg["recovery_score"] > 0:
                total_recovery += agg["recovery_score"]
                recovery_days += 1
            current += timedelta(days=1)

        days = 7
        avg_calories = round(total_calories / days, 2) if days > 0 else 0.0
        avg_protein = round(total_protein / days, 2) if days > 0 else 0.0
        avg_recovery = round(total_recovery / recovery_days, 2) if recovery_days > 0 else 0.0
        avg_fitness = round(sum(s.overall_score for s in scores) / len(scores), 2) if scores else 0.0

        # Best habit streak (from Sprint 5)
        best_streak = 0
        try:
            habits = self.habit_repo.get_user_habits(user_id)
            for h in habits:
                # Simple calculation: check consecutive days from the logs
                logs = self.habit_log_repo.get_habit_logs(h.habit_id)
                user_logs = sorted(
                    [l for l in logs if l.user_id == user_id and l.status == "completed"],
                    key=lambda x: x.log_date,
                    reverse=True,
                )
                if user_logs:
                    streak = 0
                    check_date = datetime.strptime(user_logs[0].log_date, "%Y-%m-%d")
                    for l in user_logs:
                        ld = datetime.strptime(l.log_date, "%Y-%m-%d")
                        if ld == check_date:
                            streak += 1
                            check_date -= timedelta(days=1)
                        else:
                            break
                    best_streak = max(best_streak, streak)
        except Exception:
            pass

        # Adherence rate: days with at least one workout or completed habit
        adherence_days = sum(1 for s in scores if s.workout_consistency_score > 0 or s.habits_score > 50)
        adherence_rate = round((adherence_days / days) * 100.0, 2)

        # Generate insights
        insights = self._generate_insights(
            user_id,
            week_start,
            week_end,
            avg_fitness,
            avg_calories,
            avg_protein,
            avg_recovery,
            adherence_rate,
            total_workouts,
        )
        insight_summary = " | ".join(insights[:3]) if insights else "No significant trends this week."

        report = WeeklyReport(
            report_id=f"wr-{user_id}-{week_start}",
            user_id=user_id,
            week_start=week_start,
            week_end=week_end,
            total_workouts=total_workouts,
            avg_calories=avg_calories,
            avg_protein_g=avg_protein,
            avg_recovery_score=avg_recovery,
            habit_streaks_best=best_streak,
            avg_fitness_score=avg_fitness,
            adherence_rate=adherence_rate,
            insight_summary=insight_summary,
        )

        try:
            self.report_repo.upsert_weekly_report(report)
        except Exception as e:
            logger.error(f"Failed to save weekly report: {e}")
            raise ServiceError("Failed to save weekly report.", details=str(e))

        return report

    def generate_monthly_report(self, user_id: str, month_start: str) -> MonthlyReport:
        """Generates a structured monthly report."""
        logger.info(f"Generating monthly report for user {user_id}, month {month_start}")

        if not self.user_repo.get_user(user_id):
            raise ValidationError(f"User with ID {user_id} does not exist.")

        month_start_dt = datetime.strptime(month_start, "%Y-%m-%d")
        # Compute last day of month
        next_month = month_start_dt.replace(day=28) + timedelta(days=4)
        month_end_dt = next_month - timedelta(days=next_month.day)
        month_end = month_end_dt.strftime("%Y-%m-%d")

        # Aggregate daily data
        scores = []
        total_calories = 0.0
        total_protein = 0.0
        total_recovery = 0.0
        recovery_days = 0
        total_workouts = 0

        current = month_start_dt
        while current <= month_end_dt:
            date_str = current.strftime("%Y-%m-%d")
            score = self.compute_fitness_score(user_id, date_str)
            scores.append(score)

            agg = self.get_aggregated_day(user_id, date_str)
            total_workouts += agg["total_workouts"]
            total_calories += agg["calories_consumed"]
            total_protein += agg["protein_g"]
            if agg["recovery_score"] > 0:
                total_recovery += agg["recovery_score"]
                recovery_days += 1
            current += timedelta(days=1)

        days = len(scores)
        avg_calories = round(total_calories / days, 2) if days > 0 else 0.0
        avg_protein = round(total_protein / days, 2) if days > 0 else 0.0
        avg_recovery = round(total_recovery / recovery_days, 2) if recovery_days > 0 else 0.0
        avg_fitness = round(sum(s.overall_score for s in scores) / len(scores), 2) if scores else 0.0

        adherence_days = sum(1 for s in scores if s.workout_consistency_score > 0 or s.habits_score > 50)
        adherence_rate = round((adherence_days / days) * 100.0, 2) if days > 0 else 0.0

        # Compute strength improvements
        strength_info = self._compute_strength_improvements(user_id, month_start, month_end)

        # Body changes
        body_info = ""
        try:
            measurements = self.body_measurement_repo.get_user_measurements(user_id)
            if len(measurements) >= 2:
                first = measurements[-1]
                last = measurements[0]
                weight_diff = round(last.weight_kg - first.weight_kg, 1)
                if weight_diff < 0:
                    body_info = f"Weight decreased by {abs(weight_diff)} kg"
                elif weight_diff > 0:
                    body_info = f"Weight increased by {weight_diff} kg"
                else:
                    body_info = "Weight remained stable"
        except Exception:
            pass

        # Progress summary
        progress_summary = f"Avg Fitness Score: {avg_fitness}/100 | "
        progress_summary += f"Adherence: {adherence_rate}% | "
        progress_summary += f"Workouts: {total_workouts} | "
        progress_summary += f"Avg Recovery: {avg_recovery}"

        report = MonthlyReport(
            report_id=f"mr-{user_id}-{month_start}",
            user_id=user_id,
            month_start=month_start,
            month_end=month_end,
            total_workouts=total_workouts,
            avg_calories=avg_calories,
            avg_protein_g=avg_protein,
            avg_recovery_score=avg_recovery,
            avg_fitness_score=avg_fitness,
            adherence_rate=adherence_rate,
            strength_improvements=strength_info,
            body_changes_summary=body_info,
            progress_summary=progress_summary,
        )

        try:
            self.report_repo.upsert_monthly_report(report)
        except Exception as e:
            logger.error(f"Failed to save monthly report: {e}")
            raise ServiceError("Failed to save monthly report.", details=str(e))

        return report

    def _compute_strength_improvements(self, user_id: str, month_start: str, month_end: str) -> str:
        """Computes strength improvements summary from exercise sets."""
        try:
            next_date = (datetime.strptime(month_end, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
            query = """
                SELECT e.name, MAX(es.weight) as max_weight, MIN(es.weight) as min_weight
                FROM workout_sessions ws
                JOIN exercise_logs el ON ws.session_id = el.session_id
                JOIN exercise_sets es ON el.exercise_log_id = es.exercise_log_id
                JOIN exercises e ON el.exercise_id = e.exercise_id
                WHERE ws.user_id = ? AND ws.status = 'COMPLETED'
                  AND ws.start_time >= ? AND ws.start_time < ?
                  AND es.is_completed = 1
                GROUP BY e.exercise_id
                HAVING max_weight > min_weight
                ORDER BY (max_weight - min_weight) DESC
                LIMIT 3;
            """
            rows = self.db.execute_read(query, (user_id, month_start, next_date))
            if not rows:
                return "No significant strength improvements recorded."
            improvements = [f"{r['name']}: +{round(r['max_weight'] - r['min_weight'], 1)}kg" for r in rows]
            return " | ".join(improvements)
        except Exception as e:
            logger.warning(f"Failed to compute strength improvements: {e}")
            return ""

    # ================================================================== #
    # SECTION E: RULE-BASED INSIGHT GENERATION
    # ================================================================== #

    def generate_insights(self, user_id: str, week_start: str, week_end: str) -> list[str]:
        """Generates rule-based insights comparing current week to previous week."""
        logger.info(f"Generating insights for user {user_id}, {week_start} to {week_end}")

        if not self.user_repo.get_user(user_id):
            raise ValidationError(f"User with ID {user_id} does not exist.")

        return self._generate_insights(user_id, week_start, week_end, 0.0, 0.0, 0.0, 0.0, 0.0, 0)

    def _generate_insights(
        self,
        user_id: str,
        week_start: str,
        week_end: str,
        avg_fitness: float,
        avg_calories: float,
        avg_protein: float,
        avg_recovery: float,
        adherence: float,
        total_workouts: int,
    ) -> list[str]:
        """Internal — generates text insights from metrics."""
        insights = []

        # Recovery insight
        if avg_recovery >= 80:
            insights.append(f"Great recovery this week! Average score: {avg_recovery}/100")
        elif avg_recovery < 50 and avg_recovery > 0:
            insights.append(f"Your recovery averaged {avg_recovery}/100 — consider more rest days")

        # Nutrition insight
        if avg_protein > 0 and avg_protein < DEFAULT_PROTEIN_TARGET * 0.7:
            insights.append(f"Protein intake below target ({avg_protein}g avg) on multiple days")
        elif avg_protein >= DEFAULT_PROTEIN_TARGET:
            insights.append(f"Excellent protein intake! Averaged {avg_protein}g/day")

        if avg_calories > 0 and avg_calories < DEFAULT_CALORIE_TARGET * 0.6:
            insights.append(f"Calorie intake low — averaged {avg_calories} kcal/day")
        elif avg_calories >= DEFAULT_CALORIE_TARGET:
            insights.append(f"Good calorie intake — {avg_calories} kcal/day avg")

        # Workout consistency insight
        if total_workouts >= DEFAULT_TARGET_WORKOUTS_PER_WEEK:
            insights.append(f"Workout consistency on track — {total_workouts} sessions this week")
        elif total_workouts > 0:
            insights.append(f"Workout consistency dropped — only {total_workouts} sessions this week")
        else:
            insights.append("No workouts logged this week")

        # Adherence insight
        if adherence >= 80:
            insights.append(f"Strong adherence rate: {adherence}%")
        elif adherence < 50 and adherence > 0:
            insights.append(f"Adherence rate low at {adherence}% — try to stay consistent on weekends")

        # Fitness score insight
        if avg_fitness >= 80:
            insights.append(f"Excellent overall fitness score: {avg_fitness}/100")
        elif avg_fitness < 40 and avg_fitness > 0:
            insights.append(f"Fitness score could improve ({avg_fitness}/100) — focus on consistency")

        return insights

    # ================================================================== #
    # SECTION F: SNAPSHOT & DASHBOARD DATA
    # ================================================================== #

    def take_snapshot(self, user_id: str, snapshot_date: str) -> AnalyticsSnapshot:
        """Creates a point-in-time analytics snapshot for dashboard use."""
        logger.info(f"Taking analytics snapshot for user {user_id} on {snapshot_date}")

        if not self.user_repo.get_user(user_id):
            raise ValidationError(f"User with ID {user_id} does not exist.")

        # Compute fitness score for today
        score = self.compute_fitness_score(user_id, snapshot_date)

        # Year-to-date workout count
        ytd_start = f"{snapshot_date[:4]}-01-01"
        try:
            query = """
                SELECT COUNT(*) as count FROM workout_sessions
                WHERE user_id = ? AND status = 'COMPLETED'
                  AND start_time >= ? AND start_time < ?
            """
            next_date = (datetime.strptime(snapshot_date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
            rows = self.db.execute_read(query, (user_id, ytd_start, next_date))
            total_workouts_ytd = rows[0].get("count", 0) if rows else 0
        except Exception:
            total_workouts_ytd = 0

        # Best streak
        best_streak = 0
        try:
            habits = self.habit_repo.get_user_habits(user_id)
            for h in habits:
                logs = self.habit_log_repo.get_habit_logs(h.habit_id)
                user_logs = sorted(
                    [l for l in logs if l.user_id == user_id and l.status == "completed"],
                    key=lambda x: x.log_date,
                    reverse=True,
                )
                if user_logs:
                    streak = 0
                    cd = datetime.strptime(user_logs[0].log_date, "%Y-%m-%d")
                    for l in user_logs:
                        ld = datetime.strptime(l.log_date, "%Y-%m-%d")
                        if ld == cd:
                            streak += 1
                            cd -= timedelta(days=1)
                        else:
                            break
                    best_streak = max(best_streak, streak)
        except Exception:
            pass

        # 7-day recovery average
        seven_days_ago = (datetime.strptime(snapshot_date, "%Y-%m-%d") - timedelta(days=6)).strftime("%Y-%m-%d")
        recovery_avg = 0.0
        try:
            recovery_logs = self.recovery_repo.get_recovery_logs_by_date_range(user_id, seven_days_ago, snapshot_date)
            if recovery_logs:
                recovery_avg = round(sum(r.recovery_score for r in recovery_logs) / len(recovery_logs), 2)
        except Exception:
            pass

        # Nutrition compliance
        nutrition_compliance = 0.0
        try:
            nutrition_logs = self.nutrition_log_repo.get_user_logs(user_id)
            recent = [l for l in nutrition_logs if l.log_date >= seven_days_ago]
            if recent:
                compliant = sum(1 for l in recent if l.total_calories >= DEFAULT_CALORIE_TARGET * 0.8)
                nutrition_compliance = round((compliant / len(recent)) * 100.0, 2)
        except Exception:
            pass

        # Body weight
        body_weight = None
        try:
            measurements = self.body_measurement_repo.get_user_measurements(user_id)
            if measurements:
                body_weight = measurements[0].weight_kg
        except Exception:
            pass

        import json

        snapshot = AnalyticsSnapshot(
            snapshot_id=f"ss-{user_id}-{snapshot_date}",
            user_id=user_id,
            snapshot_date=snapshot_date,
            fitness_score=score.overall_score,
            total_workouts_ytd=total_workouts_ytd,
            current_streak_best=best_streak,
            nutrition_compliance_rate=nutrition_compliance,
            recovery_avg_7day=recovery_avg,
            body_weight_kg=body_weight,
            snapshot_data=json.dumps(
                {
                    "workout_consistency": score.workout_consistency_score,
                    "habits_score": score.habits_score,
                    "overload_score": score.progressive_overload_score,
                }
            ),
        )

        try:
            self.snapshot_repo.upsert_snapshot(snapshot)
        except Exception as e:
            logger.error(f"Failed to save snapshot: {e}")
            raise ServiceError("Failed to save analytics snapshot.", details=str(e))

        return snapshot

    def get_dashboard_data(self, user_id: str, snapshot_date: str) -> dict:
        """Returns a ready-to-use dashboard dataset for UI rendering."""
        snapshot = self.snapshot_repo.get_snapshot_by_date(user_id, snapshot_date)
        if not snapshot:
            snapshot = self.take_snapshot(user_id, snapshot_date)

        # Get weekly report
        week_start_dt = datetime.strptime(snapshot_date, "%Y-%m-%d") - timedelta(
            days=datetime.strptime(snapshot_date, "%Y-%m-%d").weekday()
        )
        week_start = week_start_dt.strftime("%Y-%m-%d")
        weekly = self.report_repo.get_weekly_report_by_week(user_id, week_start)
        if not weekly:
            weekly = self.generate_weekly_report(user_id, week_start)

        # Get trends
        trends = {}
        for metric in ["weight", "recovery", "consistency", "nutrition_stability", "strength"]:
            try:
                trend = self.analyze_trends(user_id, metric, days=30)
                trends[metric] = {
                    "direction": trend.trend_direction,
                    "change": trend.percentage_change,
                    "current": trend.current_value,
                    "ma7": trend.moving_avg_7day,
                    "ma30": trend.moving_avg_30day,
                }
            except Exception:
                pass

        return {
            "snapshot": snapshot.to_dict() if snapshot else {},
            "weekly_report": weekly.to_dict() if weekly else {},
            "trends": trends,
        }
