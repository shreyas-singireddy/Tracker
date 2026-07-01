# Models package marker
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
from app.models.analytics import (
    AnalyticsSnapshot,
    FitnessScore,
    InsightMetric,
    MonthlyReport,
    ProgressTrend,
    WeeklyReport,
)
from app.models.domain import (
    BodyMeasurement,
    Exercise,
    FoodItem,
    Goal,
    HabitLog,
    MealLog,
    User,
    UserProfile,
    WorkoutLog,
)
from app.models.habit_recovery import Habit, HabitFrequency, ReadinessState, RecoveryLog, RecoveryProfile, SleepLog
from app.models.nutrition import MacroProfile, Meal, MealEntry, MealType, NutritionLog
from app.models.workout import ExerciseLog, ExerciseSet, TrainingSplit, WorkoutPlan, WorkoutSession
