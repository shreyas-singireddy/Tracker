import re
from datetime import datetime

from app.core.exceptions import ValidationError


def calculate_age(birth_date_str: str) -> int:
    """Calculates age in years relative to the current date."""
    try:
        birth_date = datetime.strptime(birth_date_str, "%Y-%m-%d")
    except ValueError:
        raise ValidationError(
            message="Invalid birth date format. Must be YYYY-MM-DD.", details=f"Received: {birth_date_str}"
        )

    today = datetime.now()
    age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    return age


def validate_user_profile(birth_date: str, weight_kg: float, height_cm: float):
    """Validates user metrics: age 5-100, weight > 0, height realistic (50 - 300 cm)."""
    age = calculate_age(birth_date)
    if not (5 <= age <= 100):
        raise ValidationError(
            message="User validation failed: Age must be between 5 and 100 years.",
            details=f"Calculated age: {age} from birth date: {birth_date}",
        )

    if weight_kg <= 0:
        raise ValidationError(
            message="User validation failed: Weight must be greater than 0 kg.", details=f"Received weight: {weight_kg}"
        )

    if not (50.0 <= height_cm <= 300.0):
        raise ValidationError(
            message="User validation failed: Height must be realistic (between 50 and 300 cm).",
            details=f"Received height: {height_cm}",
        )


def validate_food_item(calories: float, protein: float, carbs: float, fats: float):
    """Validates food metrics: calories >= 0, macros >= 0, and consistent caloric count."""
    if calories < 0:
        raise ValidationError(
            message="Food validation failed: Calories cannot be negative.", details=f"Calories: {calories}"
        )

    if protein < 0 or carbs < 0 or fats < 0:
        raise ValidationError(
            message="Food validation failed: Macronutrients (protein, carbs, fats) cannot be negative.",
            details=f"Protein: {protein}, Carbs: {carbs}, Fats: {fats}",
        )

    # Macro consistency: 1g Protein = 4 kcal, 1g Carb = 4 kcal, 1g Fat = 9 kcal
    calculated_calories = (protein * 4.0) + (carbs * 4.0) + (fats * 9.0)

    # We allow a maximum rounding variance of 15.0 calories
    tolerance = 15.0
    if calculated_calories > (calories + tolerance):
        raise ValidationError(
            message="Food validation failed: Macronutrient breakdown contradicts total calories.",
            details=f"Stated calories: {calories}, Calculated calories from macros: {calculated_calories} (variance exceeds {tolerance} kcal)",
        )


def validate_timestamp(logged_at_str: str):
    """Validates log timestamp format and guarantees it is not set in the future."""
    # Try different common ISO-like formats
    logged_time = None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S.%f"):
        try:
            # Strip timezone representation if present for simple local comparison
            clean_str = logged_at_str.split("+", maxsplit=1)[0].split("Z", maxsplit=1)[0]
            logged_time = datetime.strptime(clean_str, fmt)
            break
        except ValueError:
            continue

    if not logged_time:
        raise ValidationError(
            message="Log validation failed: Timestamp must be in valid ISO format (YYYY-MM-DD HH:MM:SS).",
            details=f"Received: {logged_at_str}",
        )

    # Check future bounds
    now = datetime.now()
    if logged_time > now:
        raise ValidationError(
            message="Log validation failed: Future timestamps are not allowed.",
            details=f"Logged time: {logged_time}, System time: {now}",
        )


def validate_email(email: str):
    """Validates that a string matches a basic email format."""
    email_regex = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    if not re.match(email_regex, email):
        raise ValidationError(message="Validation failed: Email address is invalid.", details=f"Received: {email}")


# --- Sprint 5: Habit & Recovery Validations ---


def validate_habit_name(name: str):
    """Validates habit name is non-empty."""
    if not name or not name.strip():
        raise ValidationError(message="Habit validation failed: Name cannot be empty.", details=f"Received: {name}")


def validate_habit_frequency(frequency: str):
    """Validates habit frequency is 'daily' or 'weekly'."""
    valid = ("daily", "weekly")
    if frequency not in valid:
        raise ValidationError(
            message="Habit validation failed: Frequency must be 'daily' or 'weekly'.", details=f"Received: {frequency}"
        )


def validate_habit_target_value(target_value: float):
    """Validates habit target is positive."""
    if target_value <= 0:
        raise ValidationError(
            message="Habit validation failed: Target value must be greater than 0.", details=f"Received: {target_value}"
        )


def validate_habit_log_no_duplicate(habit_id: str, user_id: str, log_date: str, repo):
    """Validates that no duplicate log exists for the same habit, user, and date."""
    existing = repo.get_habit_log_by_date(habit_id, user_id, log_date)
    if existing:
        raise ValidationError(
            message="Habit log validation failed: A log already exists for this habit on this date.",
            details=f"Habit: {habit_id}, Date: {log_date}",
        )


def validate_sleep_hours(hours: float):
    """Validates sleep hours are within 0-24 range."""
    if not (0 <= hours <= 24):
        raise ValidationError(
            message="Sleep validation failed: Hours must be between 0 and 24.", details=f"Received: {hours}"
        )


def validate_sleep_quality(quality_score: float):
    """Validates quality score is within 0-10 range."""
    if not (0 <= quality_score <= 10):
        raise ValidationError(
            message="Sleep validation failed: Quality score must be between 0 and 10.",
            details=f"Received: {quality_score}",
        )


def validate_recovery_score(score: float):
    """Validates recovery score is within 0-100 range."""
    if not (0 <= score <= 100):
        raise ValidationError(
            message="Recovery validation failed: Score must be between 0 and 100.", details=f"Received: {score}"
        )
