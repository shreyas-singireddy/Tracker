# Feature Specification: Fitness Score

## Overview

The Fitness Score is a composite metric (0-100) that summarizes a user's overall fitness progress across multiple domains.

## Components

| Component | Weight | Source |
|-----------|--------|--------|
| Nutrition Score | 20% | NutritionLog |
| Workout Consistency | 25% | WorkoutSession |
| Progressive Overload | 15% | ExerciseSet |
| Recovery Score | 15% | RecoveryLog |
| Habits Score | 10% | HabitLog |
| Body Progress | 10% | BodyMeasurement |
| AI Adherence | 5% | Recommendation |

## Calculation

```python
overall = (
    nutrition * 0.20 +
    consistency * 0.25 +
    overload * 0.15 +
    recovery * 0.15 +
    habits * 0.10 +
    body * 0.10 +
    ai * 0.05
)
```

## Persistence

Stored in `fitness_scores` table with user_id, log_date, and component scores. Snapshots also stored in `analytics_snapshots`.
