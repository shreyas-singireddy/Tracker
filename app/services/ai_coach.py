"""AICoachService — Sprint 6 Offline AI Coach Engine.

This is the ONLY intelligent layer in FitOS.  It coordinates:

    A. Rule-Based NLP Intent Classifier
       - Keyword-hit scoring per IntentCategory
       - Tie-breaking defaults to general_fitness_query

    B. Context Engine
       - Reads Sprint 3-5 data (read-only, never writes to those tables)
       - Produces a unified UserContext snapshot dict

    C. Recommendation Engine (Deterministic Rules Only)
       - Named rule constants → each produces a Recommendation with rule_source
       - No random suggestions; every recommendation is traceable

    D. Insight Generator
       - daily_insight, weekly_summary, warning_alerts, progress_feedback
       - Template strings interpolated with real data — hallucination impossible

    E. DB Logging
       - Persists sessions, queries, responses, recommendations via AI repositories

CRITICAL BUSINESS RULES:
    - AI NEVER modifies data in Sprint 3-5 tables
    - Every AIResponse.rule_source MUST be non-empty
    - Every Recommendation.rule_source MUST be non-empty
    - No ML, no LLM, no external APIs
"""

from datetime import datetime, timedelta
from typing import Any

from app.core.exceptions import ServiceError, ValidationError
from app.core.logging import logger
from app.database.connection import DatabaseManager, db_manager
from app.models.ai import (
    AICoachSession,
    AIQuery,
    AIResponse,
    InsightRule,
    IntentCategory,
    Recommendation,
    RecommendationCategory,
    RecommendationPriority,
)
from app.repositories.ai import (
    AIQueryRepository,
    AIRecommendationRepository,
    AIResponseRepository,
    AISessionRepository,
)
from app.repositories.body_measurement import BodyMeasurementRepository
from app.repositories.food import FoodRepository
from app.repositories.habit import HabitRepository
from app.repositories.habit_log import HabitLogRepository
from app.repositories.nutrition import MealEntryRepository, MealRepository, NutritionLogRepository
from app.repositories.recovery import RecoveryRepository
from app.repositories.sleep import SleepRepository
from app.repositories.user import UserRepository
from app.repositories.workout import WorkoutSessionRepository

# ---------------------------------------------------------------------------
# Rule constants — every rule has a unique ID and a human-readable condition
# ---------------------------------------------------------------------------

RULE_LOW_RECOVERY = InsightRule(
    rule_id="RULE_LOW_RECOVERY",
    category=RecommendationCategory.RECOVERY.value,
    condition="recovery_score < 40",
    message="Your recovery score is critically low ({score:.0f}/100). Take a full rest day today.",
)

RULE_MODERATE_RECOVERY = InsightRule(
    rule_id="RULE_MODERATE_RECOVERY",
    category=RecommendationCategory.WORKOUT.value,
    condition="40 <= recovery_score < 70",
    message="Your recovery score is moderate ({score:.0f}/100). Stick to light training — mobility or easy cardio only.",
)

RULE_LOW_SLEEP = InsightRule(
    rule_id="RULE_LOW_SLEEP",
    category=RecommendationCategory.RECOVERY.value,
    condition="sleep_hours < 6.0",
    message="You slept only {hours:.1f} hours last night. Sleep deprivation impairs muscle repair — rest today.",
)

RULE_PROTEIN_DEFICIT = InsightRule(
    rule_id="RULE_PROTEIN_DEFICIT",
    category=RecommendationCategory.NUTRITION.value,
    condition="daily_protein_g < protein_target_g * 0.8",
    message="Your protein intake ({actual:.0f}g) is below 80% of your target ({target:.0f}g). Add a high-protein meal or snack.",
)

RULE_CALORIE_SURPLUS = InsightRule(
    rule_id="RULE_CALORIE_SURPLUS",
    category=RecommendationCategory.NUTRITION.value,
    condition="daily_calories > calorie_target * 1.15",
    message="Your calorie intake ({actual:.0f} kcal) exceeds your target by more than 15%. Review portion sizes.",
)

RULE_LOW_HABIT_CONSISTENCY = InsightRule(
    rule_id="RULE_LOW_HABIT_CONSISTENCY",
    category=RecommendationCategory.HABIT.value,
    condition="habit_avg_consistency < 50.0",
    message="Your average habit consistency is {pct:.0f}%. Try simplifying one habit to rebuild momentum.",
)

RULE_NO_RECENT_WORKOUTS = InsightRule(
    rule_id="RULE_NO_RECENT_WORKOUTS",
    category=RecommendationCategory.WORKOUT.value,
    condition="workout_sessions_7d == 0",
    message="You have not logged any workouts in the past 7 days. Even a 20-minute session helps maintain progress.",
)

RULE_GOOD_RECOVERY = InsightRule(
    rule_id="RULE_GOOD_RECOVERY",
    category=RecommendationCategory.WORKOUT.value,
    condition="recovery_score >= 70",
    message="Your recovery score is strong ({score:.0f}/100). Today is a great day for a challenging workout.",
)

RULE_FULL_CONTEXT_POSITIVE = InsightRule(
    rule_id="RULE_FULL_CONTEXT_POSITIVE",
    category=RecommendationCategory.GENERAL.value,
    condition="no negative triggers detected",
    message="All your tracked metrics look healthy today. Keep up the consistent effort!",
)

# Intent keyword map: category → list of trigger keywords (all lowercase)
INTENT_KEYWORDS: dict[str, list[str]] = {
    IntentCategory.NUTRITION_QUERY.value: [
        "eat",
        "eating",
        "food",
        "calorie",
        "calories",
        "protein",
        "carb",
        "carbs",
        "fat",
        "fats",
        "meal",
        "diet",
        "macro",
        "macros",
        "nutrition",
        "intake",
        "deficit",
        "surplus",
        "hungry",
        "snack",
        "supplement",
    ],
    IntentCategory.WORKOUT_QUERY.value: [
        "exercise",
        "workout",
        "workouts",
        "train",
        "training",
        "lift",
        "lifting",
        "run",
        "running",
        "strength",
        "session",
        "sessions",
        "sets",
        "reps",
        "gym",
        "cardio",
        "muscle",
        "push",
        "pull",
        "legs",
        "plan",
    ],
    IntentCategory.RECOVERY_QUERY.value: [
        "sleep",
        "sleeping",
        "recover",
        "recovery",
        "rest",
        "fatigue",
        "sore",
        "soreness",
        "readiness",
        "tired",
        "exhausted",
        "ache",
    ],
    IntentCategory.HABIT_QUERY.value: [
        "habit",
        "habits",
        "streak",
        "streaks",
        "consistency",
        "routine",
        "daily",
        "missed",
        "tracked",
        "completed",
        "log",
        "logging",
    ],
    IntentCategory.PROGRESS_QUERY.value: [
        "progress",
        "weight",
        "goal",
        "goals",
        "trend",
        "improve",
        "improvement",
        "result",
        "results",
        "measure",
        "measurement",
        "body",
        "performance",
        "gain",
        "gains",
        "pr",
        "record",
    ],
    IntentCategory.GENERAL_FITNESS_QUERY.value: [
        "fitness",
        "health",
        "tip",
        "tips",
        "advice",
        "coach",
        "help",
        "suggest",
        "suggestion",
        "today",
        "should",
        "recommend",
        "what",
    ],
}


class AICoachService:
    """Offline AI Coach — rule-based intelligence layer (Sprint 6).

    Injected via constructor with all required repositories.
    No defaults that silently create production DB connections in tests.
    """

    def __init__(
        self,
        session_repo: AISessionRepository | None = None,
        query_repo: AIQueryRepository | None = None,
        response_repo: AIResponseRepository | None = None,
        rec_repo: AIRecommendationRepository | None = None,
        user_repo: UserRepository | None = None,
        workout_session_repo: WorkoutSessionRepository | None = None,
        nutrition_log_repo: NutritionLogRepository | None = None,
        meal_entry_repo: MealEntryRepository | None = None,
        meal_repo: MealRepository | None = None,
        food_repo: FoodRepository | None = None,
        recovery_repo: RecoveryRepository | None = None,
        sleep_repo: SleepRepository | None = None,
        habit_repo: HabitRepository | None = None,
        habit_log_repo: HabitLogRepository | None = None,
        body_measurement_repo: BodyMeasurementRepository | None = None,
        db: DatabaseManager | None = None,
    ):
        _db = db or db_manager
        self.session_repo = session_repo or AISessionRepository(db=_db)
        self.query_repo = query_repo or AIQueryRepository(db=_db)
        self.response_repo = response_repo or AIResponseRepository(db=_db)
        self.rec_repo = rec_repo or AIRecommendationRepository(db=_db)
        self.user_repo = user_repo or UserRepository(db=_db)
        self.workout_session_repo = workout_session_repo or WorkoutSessionRepository(db=_db)
        self.nutrition_log_repo = nutrition_log_repo or NutritionLogRepository(db=_db)
        self.meal_entry_repo = meal_entry_repo or MealEntryRepository(db=_db)
        self.meal_repo = meal_repo or MealRepository(db=_db)
        self.food_repo = food_repo or FoodRepository(db=_db)
        self.recovery_repo = recovery_repo or RecoveryRepository(db=_db)
        self.sleep_repo = sleep_repo or SleepRepository(db=_db)
        self.habit_repo = habit_repo or HabitRepository(db=_db)
        self.habit_log_repo = habit_log_repo or HabitLogRepository(db=_db)
        self.body_measurement_repo = body_measurement_repo or BodyMeasurementRepository(db=_db)

    # -----------------------------------------------------------------------
    # A. Rule-Based NLP Intent Classifier
    # -----------------------------------------------------------------------

    def classify_intent(self, raw_text: str) -> str:
        """Classifies user query text into an IntentCategory via keyword scoring.

        Algorithm:
            1. Tokenise lowercased text into words.
            2. Count keyword hits per category.
            3. Return the category with the highest score.
            4. Ties (including zero-score) → general_fitness_query.

        Returns an IntentCategory value string.
        """
        if not raw_text or not raw_text.strip():
            return IntentCategory.GENERAL_FITNESS_QUERY.value

        tokens = set(raw_text.lower().split())
        scores: dict[str, int] = {}

        for category, keywords in INTENT_KEYWORDS.items():
            scores[category] = sum(1 for kw in keywords if kw in tokens)

        max_score = max(scores.values())
        if max_score == 0:
            return IntentCategory.GENERAL_FITNESS_QUERY.value

        # Filter to winners; on tie prefer general_fitness_query
        winners = [cat for cat, score in scores.items() if score == max_score]
        if len(winners) == 1:
            return winners[0]

        # Tie-breaking: prefer by priority order
        priority_order = [
            IntentCategory.RECOVERY_QUERY.value,
            IntentCategory.NUTRITION_QUERY.value,
            IntentCategory.WORKOUT_QUERY.value,
            IntentCategory.HABIT_QUERY.value,
            IntentCategory.PROGRESS_QUERY.value,
            IntentCategory.GENERAL_FITNESS_QUERY.value,
        ]
        for intent in priority_order:
            if intent in winners:
                return intent

        return IntentCategory.GENERAL_FITNESS_QUERY.value

    # -----------------------------------------------------------------------
    # B. Context Engine
    # -----------------------------------------------------------------------

    def build_user_context(self, user_id: str, context_date: str) -> dict[str, Any]:
        """Aggregates read-only data from Sprints 3-5 into a unified context snapshot.

        Returns a dict with safe defaults so downstream logic never raises KeyError.
        AI NEVER modifies Sprint 3-5 tables -- read-only access only.
        """
        ctx: dict[str, Any] = {
            "user_id": user_id,
            "context_date": context_date,
            "recovery_score": None,
            "readiness_state": None,
            "sleep_hours": None,
            "sleep_quality": None,
            "daily_calories": 0.0,
            "daily_protein_g": 0.0,
            "daily_carbs_g": 0.0,
            "daily_fat_g": 0.0,
            "calorie_target": 2000.0,  # heuristic default
            "protein_target_g": 150.0,  # heuristic default
            "workout_sessions_7d": 0,
            "habit_count": 0,
            "habit_avg_consistency": 0.0,
            "body_weight_kg": None,
        }

        # --- Recovery & Sleep (Sprint 5) ---
        try:
            rec_log = self.recovery_repo.get_recovery_log_by_date(user_id, context_date)
            if rec_log:
                ctx["recovery_score"] = rec_log.recovery_score
                ctx["readiness_state"] = rec_log.readiness_state
        except Exception as e:
            logger.warning(f"Context: could not fetch recovery log: {e}")

        try:
            sleep_log = self.sleep_repo.get_sleep_log_by_date(user_id, context_date)
            if sleep_log:
                ctx["sleep_hours"] = sleep_log.hours
                ctx["sleep_quality"] = sleep_log.quality_score
        except Exception as e:
            logger.warning(f"Context: could not fetch sleep log: {e}")

        # --- Nutrition (Sprint 4) ---
        try:
            nut_log = self.nutrition_log_repo.get_log_by_date(user_id, context_date)
            if nut_log:
                ctx["daily_calories"] = nut_log.total_calories
                ctx["daily_protein_g"] = nut_log.total_protein
                ctx["daily_carbs_g"] = nut_log.total_carbs
                ctx["daily_fat_g"] = nut_log.total_fat
            else:
                # Fall back to real-time calculation from meal entries
                meals = self.meal_repo.get_meals_by_date(user_id, context_date)
                for meal in meals:
                    entries = self.meal_entry_repo.get_meal_entries(meal.meal_id)
                    for entry in entries:
                        food = self.food_repo.get_food(entry.food_id)
                        if food and food.serving_size_g > 0:
                            scale = entry.quantity_g / food.serving_size_g
                            ctx["daily_calories"] += food.calories * scale
                            ctx["daily_protein_g"] += food.protein * scale
                            ctx["daily_carbs_g"] += food.carbs * scale
                            ctx["daily_fat_g"] += food.fats * scale
        except Exception as e:
            logger.warning(f"Context: could not fetch nutrition data: {e}")

        # --- Body weight for protein target (Sprint 2 BodyMeasurement) ---
        try:
            measurements = self.body_measurement_repo.get_user_measurements(user_id)
            if measurements:
                # Most recent measurement
                most_recent = max(measurements, key=lambda m: m.logged_at)
                ctx["body_weight_kg"] = most_recent.weight_kg
                ctx["protein_target_g"] = most_recent.weight_kg * 1.6  # 1.6g/kg heuristic
                ctx["calorie_target"] = most_recent.weight_kg * 30.0  # ~30 kcal/kg heuristic
        except Exception as e:
            logger.warning(f"Context: could not fetch body measurement: {e}")

        # --- Workout load (Sprint 3) ---
        try:
            log_dt = datetime.strptime(context_date, "%Y-%m-%d")
            seven_days_ago = (log_dt - timedelta(days=7)).strftime("%Y-%m-%d")
            query = (
                "SELECT COUNT(*) as cnt FROM workout_sessions "
                "WHERE user_id = ? AND status = 'COMPLETED' "
                "AND start_time >= ? AND start_time < ?;"
            )
            rows = self.workout_session_repo.db.execute_read(query, (user_id, seven_days_ago, context_date))
            if rows:
                ctx["workout_sessions_7d"] = int(rows[0].get("cnt", 0) or 0)
        except Exception as e:
            logger.warning(f"Context: could not fetch workout sessions: {e}")

        # --- Habit consistency (Sprint 5) ---
        try:
            habits = self.habit_repo.get_user_habits(user_id)
            ctx["habit_count"] = len(habits)
            if habits:
                # Compute average consistency over last 30 days for each habit
                log_dt = datetime.strptime(context_date, "%Y-%m-%d")
                start_date = (log_dt - timedelta(days=29)).strftime("%Y-%m-%d")
                consistency_scores: list[float] = []
                for habit in habits:
                    logs = self.habit_log_repo.get_habit_logs_by_date_range(user_id, start_date, context_date)
                    completed = sum(1 for log in logs if log.habit_id == habit.habit_id and log.status == "completed")
                    consistency_scores.append((completed / 30.0) * 100.0)
                ctx["habit_avg_consistency"] = (
                    sum(consistency_scores) / len(consistency_scores) if consistency_scores else 0.0
                )
        except Exception as e:
            logger.warning(f"Context: could not fetch habit data: {e}")

        return ctx

    # -----------------------------------------------------------------------
    # C. Recommendation Engine (Deterministic Rules Only)
    # -----------------------------------------------------------------------

    def generate_recommendations(
        self, user_id: str, context: dict[str, Any], context_date: str
    ) -> list[Recommendation]:
        """Evaluates all named rules against the user context and returns triggered recommendations.

        Every Recommendation.rule_source names the InsightRule.rule_id that triggered it.
        No recommendations are generated without a named rule. No random suggestions.
        """
        import uuid

        recs: list[Recommendation] = []
        triggered_any = False

        recovery_score = context.get("recovery_score")
        sleep_hours = context.get("sleep_hours")
        protein_actual = context.get("daily_protein_g", 0.0)
        protein_target = context.get("protein_target_g", 150.0)
        cal_actual = context.get("daily_calories", 0.0)
        cal_target = context.get("calorie_target", 2000.0)
        habit_consist = context.get("habit_avg_consistency", 0.0)
        sessions_7d = context.get("workout_sessions_7d", 0)

        # RULE_LOW_RECOVERY
        if recovery_score is not None and recovery_score < 40:
            recs.append(
                Recommendation(
                    recommendation_id=str(uuid.uuid4()),
                    user_id=user_id,
                    category=RULE_LOW_RECOVERY.category,
                    title="Take a Full Rest Day",
                    body=RULE_LOW_RECOVERY.message.format(score=recovery_score),
                    rule_source=RULE_LOW_RECOVERY.rule_id,
                    priority=RecommendationPriority.HIGH.value,
                    log_date=context_date,
                )
            )
            triggered_any = True

        # RULE_MODERATE_RECOVERY (only if LOW not triggered)
        elif recovery_score is not None and 40 <= recovery_score < 70:
            recs.append(
                Recommendation(
                    recommendation_id=str(uuid.uuid4()),
                    user_id=user_id,
                    category=RULE_MODERATE_RECOVERY.category,
                    title="Light Training Day",
                    body=RULE_MODERATE_RECOVERY.message.format(score=recovery_score),
                    rule_source=RULE_MODERATE_RECOVERY.rule_id,
                    priority=RecommendationPriority.MEDIUM.value,
                    log_date=context_date,
                )
            )
            triggered_any = True

        # RULE_GOOD_RECOVERY
        elif recovery_score is not None and recovery_score >= 70:
            recs.append(
                Recommendation(
                    recommendation_id=str(uuid.uuid4()),
                    user_id=user_id,
                    category=RULE_GOOD_RECOVERY.category,
                    title="Great Day to Train Hard",
                    body=RULE_GOOD_RECOVERY.message.format(score=recovery_score),
                    rule_source=RULE_GOOD_RECOVERY.rule_id,
                    priority=RecommendationPriority.LOW.value,
                    log_date=context_date,
                )
            )
            triggered_any = True

        # RULE_LOW_SLEEP
        if sleep_hours is not None and sleep_hours < 6.0:
            recs.append(
                Recommendation(
                    recommendation_id=str(uuid.uuid4()),
                    user_id=user_id,
                    category=RULE_LOW_SLEEP.category,
                    title="Prioritise Sleep Tonight",
                    body=RULE_LOW_SLEEP.message.format(hours=sleep_hours),
                    rule_source=RULE_LOW_SLEEP.rule_id,
                    priority=RecommendationPriority.HIGH.value,
                    log_date=context_date,
                )
            )
            triggered_any = True

        # RULE_PROTEIN_DEFICIT
        if protein_actual < protein_target * 0.8:
            recs.append(
                Recommendation(
                    recommendation_id=str(uuid.uuid4()),
                    user_id=user_id,
                    category=RULE_PROTEIN_DEFICIT.category,
                    title="Increase Protein Intake",
                    body=RULE_PROTEIN_DEFICIT.message.format(actual=protein_actual, target=protein_target),
                    rule_source=RULE_PROTEIN_DEFICIT.rule_id,
                    priority=RecommendationPriority.MEDIUM.value,
                    log_date=context_date,
                )
            )
            triggered_any = True

        # RULE_CALORIE_SURPLUS
        if cal_target > 0 and cal_actual > cal_target * 1.15:
            recs.append(
                Recommendation(
                    recommendation_id=str(uuid.uuid4()),
                    user_id=user_id,
                    category=RULE_CALORIE_SURPLUS.category,
                    title="Caloric Surplus Alert",
                    body=RULE_CALORIE_SURPLUS.message.format(actual=cal_actual),
                    rule_source=RULE_CALORIE_SURPLUS.rule_id,
                    priority=RecommendationPriority.MEDIUM.value,
                    log_date=context_date,
                )
            )
            triggered_any = True

        # RULE_LOW_HABIT_CONSISTENCY
        if context.get("habit_count", 0) > 0 and habit_consist < 50.0:
            recs.append(
                Recommendation(
                    recommendation_id=str(uuid.uuid4()),
                    user_id=user_id,
                    category=RULE_LOW_HABIT_CONSISTENCY.category,
                    title="Simplify Your Habits",
                    body=RULE_LOW_HABIT_CONSISTENCY.message.format(pct=habit_consist),
                    rule_source=RULE_LOW_HABIT_CONSISTENCY.rule_id,
                    priority=RecommendationPriority.MEDIUM.value,
                    log_date=context_date,
                )
            )
            triggered_any = True

        # RULE_NO_RECENT_WORKOUTS
        if sessions_7d == 0:
            recs.append(
                Recommendation(
                    recommendation_id=str(uuid.uuid4()),
                    user_id=user_id,
                    category=RULE_NO_RECENT_WORKOUTS.category,
                    title="Resume Your Training",
                    body=RULE_NO_RECENT_WORKOUTS.message,
                    rule_source=RULE_NO_RECENT_WORKOUTS.rule_id,
                    priority=RecommendationPriority.HIGH.value,
                    log_date=context_date,
                )
            )
            triggered_any = True

        # Positive catch-all when no negative rule fires
        if not triggered_any:
            recs.append(
                Recommendation(
                    recommendation_id=str(uuid.uuid4()),
                    user_id=user_id,
                    category=RULE_FULL_CONTEXT_POSITIVE.category,
                    title="Everything Looks Great!",
                    body=RULE_FULL_CONTEXT_POSITIVE.message,
                    rule_source=RULE_FULL_CONTEXT_POSITIVE.rule_id,
                    priority=RecommendationPriority.LOW.value,
                    log_date=context_date,
                )
            )

        return recs

    # -----------------------------------------------------------------------
    # D. Insight Generator
    # -----------------------------------------------------------------------

    def generate_daily_insight(self, user_id: str, context_date: str) -> str:
        """Generates a human-readable daily insight string from real context data.

        Template-based — hallucination is impossible because every value is
        read directly from the DB via build_user_context().
        """
        ctx = self.build_user_context(user_id, context_date)
        parts: list[str] = [f"=== Daily Fitness Insight — {context_date} ==="]

        # Recovery
        if ctx["recovery_score"] is not None:
            state = ctx["readiness_state"] or "unknown"
            parts.append(
                f"Recovery: {ctx['recovery_score']:.0f}/100 ({state}) | Sleep: {ctx['sleep_hours']:.1f}h"
                if ctx["sleep_hours"] is not None
                else f"Recovery: {ctx['recovery_score']:.0f}/100 ({state})"
            )
        else:
            parts.append("Recovery: No data logged for today.")

        # Nutrition
        parts.append(
            f"Nutrition: {ctx['daily_calories']:.0f} kcal | "
            f"Protein: {ctx['daily_protein_g']:.0f}g | "
            f"Carbs: {ctx['daily_carbs_g']:.0f}g | "
            f"Fat: {ctx['daily_fat_g']:.0f}g"
        )

        # Workouts
        parts.append(f"Workouts (last 7 days): {ctx['workout_sessions_7d']} session(s)")

        # Habits
        if ctx["habit_count"] > 0:
            parts.append(
                f"Habits: {ctx['habit_count']} tracked | Average consistency: {ctx['habit_avg_consistency']:.1f}%"
            )

        # Top recommendation
        recs = self.generate_recommendations(user_id, ctx, context_date)
        if recs:
            top = sorted(
                recs,
                key=lambda r: {"high": 0, "medium": 1, "low": 2}.get(r.priority, 2),
            )[0]
            parts.append(f"\n💡 Top Tip: {top.title} — {top.body}")

        return "\n".join(parts)

    def generate_weekly_summary(self, user_id: str, end_date: str) -> str:
        """Generates a text weekly summary aggregated over the 7 days ending on end_date.

        All values come from real DB data. No fabricated metrics.
        """
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError:
            raise ValidationError(f"Invalid date format: {end_date}")

        start_dt = end_dt - timedelta(days=6)
        days = [(start_dt + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]

        recovery_scores: list[float] = []
        sleep_hours_list: list[float] = []
        calorie_list: list[float] = []
        protein_list: list[float] = []

        for d in days:
            try:
                rec = self.recovery_repo.get_recovery_log_by_date(user_id, d)
                if rec:
                    recovery_scores.append(rec.recovery_score)
            except Exception:
                pass

            try:
                slp = self.sleep_repo.get_sleep_log_by_date(user_id, d)
                if slp:
                    sleep_hours_list.append(slp.hours)
            except Exception:
                pass

            try:
                nut = self.nutrition_log_repo.get_log_by_date(user_id, d)
                if nut:
                    calorie_list.append(nut.total_calories)
                    protein_list.append(nut.total_protein)
            except Exception:
                pass

        # Workout count for the week
        try:
            query = (
                "SELECT COUNT(*) as cnt FROM workout_sessions "
                "WHERE user_id = ? AND status = 'COMPLETED' "
                "AND start_time >= ? AND start_time <= ?;"
            )
            rows = self.workout_session_repo.db.execute_read(query, (user_id, days[0], end_date))
            workout_count = int(rows[0].get("cnt", 0)) if rows else 0
        except Exception:
            workout_count = 0

        avg_recovery = sum(recovery_scores) / len(recovery_scores) if recovery_scores else 0.0
        avg_sleep = sum(sleep_hours_list) / len(sleep_hours_list) if sleep_hours_list else 0.0
        avg_calories = sum(calorie_list) / len(calorie_list) if calorie_list else 0.0
        avg_protein = sum(protein_list) / len(protein_list) if protein_list else 0.0

        lines = [
            f"=== Weekly Summary: {days[0]} → {end_date} ===",
            f"Workouts completed: {workout_count}",
            f"Avg recovery score: {avg_recovery:.1f}/100",
            f"Avg sleep: {avg_sleep:.1f}h/night",
            f"Avg daily calories: {avg_calories:.0f} kcal",
            f"Avg daily protein: {avg_protein:.0f}g",
        ]
        return "\n".join(lines)

    def generate_warning_alerts(self, context: dict[str, Any]) -> list[str]:
        """Returns a list of plain-text warning messages for critical conditions.

        Only generates output when a named rule threshold is breached.
        """
        alerts: list[str] = []

        recovery_score = context.get("recovery_score")
        sleep_hours = context.get("sleep_hours")
        protein_actual = context.get("daily_protein_g", 0.0)
        protein_target = context.get("protein_target_g", 150.0)

        if recovery_score is not None and recovery_score < 40:
            alerts.append(
                f"⚠️  [{RULE_LOW_RECOVERY.rule_id}] Recovery score critical: {recovery_score:.0f}/100. Rest required."
            )

        if sleep_hours is not None and sleep_hours < 6.0:
            alerts.append(f"⚠️  [{RULE_LOW_SLEEP.rule_id}] Sleep deficit: {sleep_hours:.1f}h (<6h minimum).")

        if protein_actual < protein_target * 0.8:
            alerts.append(
                f"⚠️  [{RULE_PROTEIN_DEFICIT.rule_id}] Protein intake low: "
                f"{protein_actual:.0f}g vs {protein_target:.0f}g target."
            )

        return alerts

    def generate_progress_feedback(self, user_id: str, context_date: str) -> str:
        """Returns a brief progress feedback message based on recent DB trends.

        Compares today's nutrition log vs 7-day average. No predictive ML.
        """
        ctx_today = self.build_user_context(user_id, context_date)

        try:
            end_dt = datetime.strptime(context_date, "%Y-%m-%d")
            start_dt = end_dt - timedelta(days=7)
            cal_list: list[float] = []
            for i in range(7):
                d = (start_dt + timedelta(days=i)).strftime("%Y-%m-%d")
                nut = self.nutrition_log_repo.get_log_by_date(user_id, d)
                if nut:
                    cal_list.append(nut.total_calories)
            avg_7d = sum(cal_list) / len(cal_list) if cal_list else 0.0
        except Exception:
            avg_7d = 0.0

        today_cal = ctx_today.get("daily_calories", 0.0)

        if avg_7d == 0:
            return "Not enough historical data for progress comparison yet."

        delta = today_cal - avg_7d
        direction = "above" if delta > 0 else "below"
        return (
            f"Progress Feedback ({context_date}): Today's calorie intake is "
            f"{abs(delta):.0f} kcal {direction} your 7-day average ({avg_7d:.0f} kcal)."
        )

    # -----------------------------------------------------------------------
    # E. Public Session & Query API
    # -----------------------------------------------------------------------

    def start_session(self, session_id: str, user_id: str) -> AICoachSession:
        """Creates and persists a new AICoachSession for a user.

        Validates user existence before creating the session.
        """
        if not self.user_repo.get_user(user_id):
            raise ValidationError(f"Cannot start session: user {user_id} does not exist.")

        now = datetime.now().isoformat(timespec="seconds")
        session = AICoachSession(
            session_id=session_id,
            user_id=user_id,
            started_at=now,
            query_count=0,
        )
        try:
            self.session_repo.create_session(session)
            logger.info(f"AI session started: {session_id} for user {user_id}")
            return session
        except Exception as e:
            raise ServiceError("Failed to create AI session.", details=str(e))

    def process_query(
        self,
        session_id: str,
        query_id: str,
        response_id: str,
        user_id: str,
        raw_text: str,
        context_date: str | None = None,
    ) -> tuple[AIQuery, AIResponse, list[Recommendation]]:
        """Full pipeline: validate → classify → build context → recommend → respond → persist.

        Steps:
            1. Validate: non-empty text, session exists, user exists
            2. Classify intent via NLP keyword scoring
            3. Build user context from Sprint 3-5 data (read-only)
            4. Generate recommendations via deterministic rules
            5. Build response text + rule_source (explainability enforced)
            6. Persist query, response, and recommendations to DB
            7. Increment session query count

        Returns (AIQuery, AIResponse, List[Recommendation]).
        """
        if not raw_text or not raw_text.strip():
            raise ValidationError("Query cannot be empty.")

        if not self.session_repo.get_session(session_id):
            raise ValidationError(f"Session {session_id} does not exist. Call start_session first.")

        if not self.user_repo.get_user(user_id):
            raise ValidationError(f"User {user_id} does not exist.")

        date_str = context_date or datetime.now().strftime("%Y-%m-%d")

        # 1. Classify intent
        intent = self.classify_intent(raw_text)

        # 2. Build context
        context = self.build_user_context(user_id, date_str)

        # 3. Generate recommendations
        recommendations = self.generate_recommendations(user_id, context, date_str)

        # 4. Build response text & rule_source
        response_text, rule_source = self._build_response(intent, context, recommendations)

        # Explainability contract: rule_source must never be empty
        assert rule_source, "INTERNAL: rule_source must not be empty."

        # 5. Persist query
        ai_query = AIQuery(
            query_id=query_id,
            session_id=session_id,
            user_id=user_id,
            raw_text=raw_text.strip(),
            intent=intent,
        )
        self.query_repo.create_query(ai_query)

        # 6. Persist response
        ai_response = AIResponse(
            response_id=response_id,
            query_id=query_id,
            user_id=user_id,
            response_text=response_text,
            intent=intent,
            rule_source=rule_source,
        )
        self.response_repo.create_response(ai_response)

        # 7. Persist recommendations
        for rec in recommendations:
            try:
                self.rec_repo.create_recommendation(rec)
            except Exception as e:
                logger.warning(f"Failed to persist recommendation {rec.recommendation_id}: {e}")

        # 8. Increment session query count
        self.session_repo.increment_query_count(session_id)

        logger.info(
            f"Query processed: session={session_id}, intent={intent}, "
            f"rule_source='{rule_source}', recs={len(recommendations)}"
        )
        return ai_query, ai_response, recommendations

    def get_recommendations(
        self,
        user_id: str,
        category: str | None = None,
        log_date: str | None = None,
    ) -> list[Recommendation]:
        """Returns stored recommendations for a user, optionally filtered."""
        if log_date:
            return self.rec_repo.get_recommendations_by_date(user_id, log_date)
        if category:
            return self.rec_repo.get_recommendations_by_category(user_id, category)
        return self.rec_repo.get_user_recommendations(user_id)

    def get_session_history(self, session_id: str) -> list[tuple[AIQuery, AIResponse | None]]:
        """Returns all (query, response) pairs for a session in chronological order."""
        queries = self.query_repo.get_session_queries(session_id)
        result = []
        for q in queries:
            resp = self.response_repo.get_response_for_query(q.query_id)
            result.append((q, resp))
        return result

    # -----------------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------------

    def _build_response(
        self,
        intent: str,
        context: dict[str, Any],
        recommendations: list[Recommendation],
    ) -> tuple[str, str]:
        """Builds a response text and rule_source string from intent + recommendations.

        The rule_source is always a comma-separated list of rule_ids from triggered
        recommendations, guaranteeing full explainability.

        Returns (response_text, rule_source).
        """
        rule_ids = [r.rule_source for r in recommendations if r.rule_source]
        rule_source = ", ".join(rule_ids) if rule_ids else "RULE_FULL_CONTEXT_POSITIVE"

        intent_intro = {
            IntentCategory.NUTRITION_QUERY.value: "Here's your nutrition guidance:",
            IntentCategory.WORKOUT_QUERY.value: "Here's your workout guidance:",
            IntentCategory.RECOVERY_QUERY.value: "Here's your recovery guidance:",
            IntentCategory.HABIT_QUERY.value: "Here's your habit guidance:",
            IntentCategory.PROGRESS_QUERY.value: "Here's your progress overview:",
            IntentCategory.GENERAL_FITNESS_QUERY.value: "Here's your fitness coaching summary:",
        }.get(intent, "Here's your fitness coaching summary:")

        # Filter recommendations relevant to the intent category
        intent_to_category = {
            IntentCategory.NUTRITION_QUERY.value: RecommendationCategory.NUTRITION.value,
            IntentCategory.WORKOUT_QUERY.value: RecommendationCategory.WORKOUT.value,
            IntentCategory.RECOVERY_QUERY.value: RecommendationCategory.RECOVERY.value,
            IntentCategory.HABIT_QUERY.value: RecommendationCategory.HABIT.value,
        }
        target_category = intent_to_category.get(intent)
        relevant = (
            [r for r in recommendations if r.category == target_category] if target_category else recommendations
        ) or recommendations  # fallback to all if category produces nothing

        # Build response body
        lines = [intent_intro, ""]
        for rec in relevant[:3]:  # Show top 3 most relevant
            lines.append(f"• {rec.title}: {rec.body}")

        # Append quick stats
        lines += [
            "",
            f"[Recovery: {context['recovery_score']:.0f}/100]"
            if context.get("recovery_score") is not None
            else "[Recovery: No data]",
            f"[Nutrition: {context['daily_calories']:.0f} kcal | Protein: {context['daily_protein_g']:.0f}g]",
            f"[Workouts (7d): {context['workout_sessions_7d']}]",
        ]

        return "\n".join(lines), rule_source
