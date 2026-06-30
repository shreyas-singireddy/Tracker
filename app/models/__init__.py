# Models package marker
from app.models.domain import (
    User,
    UserProfile,
    Goal,
    FoodItem,
    Exercise,
    MealLog,
    WorkoutLog,
    HabitLog,
    BodyMeasurement
)
from app.models.workout import (
    TrainingSplit,
    WorkoutPlan,
    WorkoutSession,
    ExerciseLog,
    ExerciseSet
)
from app.models.nutrition import (
    MealType,
    Meal,
    MealEntry,
    NutritionLog,
    MacroProfile
)
from app.models.habit_recovery import (
    ReadinessState,
    HabitFrequency,
    Habit,
    SleepLog,
    RecoveryLog,
    RecoveryProfile
)
from app.models.analytics import (
    FitnessScore,
    WeeklyReport,
    MonthlyReport,
    AnalyticsSnapshot,
    ProgressTrend,
    InsightMetric
)
from app.models.ai import (
    IntentCategory,
    RecommendationPriority,
    RecommendationCategory,
    AICoachSession,
    AIQuery,
    AIResponse,
    Recommendation,
    InsightRule
)
