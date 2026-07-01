from dataclasses import asdict, dataclass
from typing import Any


class MealType:
    """Valid meal type constants."""

    BREAKFAST = "breakfast"
    LUNCH = "lunch"
    DINNER = "dinner"
    SNACK = "snack"

    ALL = (BREAKFAST, LUNCH, DINNER, SNACK)


@dataclass
class Meal:
    """Represents a named meal event (e.g., Breakfast on 2026-06-30) for a user.

    Each meal can contain multiple MealEntry records linking foods with quantities.
    Business logic (totals, macros) lives exclusively in NutritionService.
    """

    meal_id: str
    user_id: str
    meal_type: str  # 'breakfast' | 'lunch' | 'dinner' | 'snack'
    meal_date: str  # YYYY-MM-DD
    name: str | None = None
    created_at: str | None = None
    updated_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Meal":
        return cls(
            meal_id=data["meal_id"],
            user_id=data["user_id"],
            meal_type=data["meal_type"],
            meal_date=data["meal_date"],
            name=data.get("name"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )


@dataclass
class MealEntry:
    """A single food item recorded within a Meal, with its consumed quantity in grams.

    Macros are NOT stored here — they are always derived dynamically from FoodItem
    values, ensuring totals are always reproducible from raw logs.
    """

    entry_id: str
    meal_id: str
    food_id: str
    quantity_g: float  # grams consumed
    created_at: str | None = None
    updated_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MealEntry":
        return cls(
            entry_id=data["entry_id"],
            meal_id=data["meal_id"],
            food_id=data["food_id"],
            quantity_g=float(data["quantity_g"]),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )


@dataclass
class NutritionLog:
    """A persisted daily macro summary for a user.

    Computed and upserted by NutritionService.save_daily_nutrition_log().
    Always reproducible by re-running the calculation over meal_entries for that date.
    """

    log_id: str
    user_id: str
    log_date: str  # YYYY-MM-DD
    total_calories: float = 0.0
    total_protein: float = 0.0
    total_carbs: float = 0.0
    total_fat: float = 0.0
    total_fiber: float = 0.0
    total_sugar: float = 0.0
    created_at: str | None = None
    updated_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "NutritionLog":
        return cls(
            log_id=data["log_id"],
            user_id=data["user_id"],
            log_date=data["log_date"],
            total_calories=float(data.get("total_calories", 0.0)),
            total_protein=float(data.get("total_protein", 0.0)),
            total_carbs=float(data.get("total_carbs", 0.0)),
            total_fat=float(data.get("total_fat", 0.0)),
            total_fiber=float(data.get("total_fiber", 0.0)),
            total_sugar=float(data.get("total_sugar", 0.0)),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )


@dataclass
class MacroProfile:
    """A computed-only (non-persisted) result object holding macro totals.

    Returned by NutritionService calculation methods. Never inserted into the DB.
    All fields are scaled from raw FoodItem values by quantity consumed.
    """

    calories: float = 0.0
    protein_g: float = 0.0
    carbs_g: float = 0.0
    fat_g: float = 0.0
    fiber_g: float = 0.0
    sugar_g: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def __add__(self, other: "MacroProfile") -> "MacroProfile":
        """Allows summing MacroProfile instances across meals."""
        return MacroProfile(
            calories=self.calories + other.calories,
            protein_g=self.protein_g + other.protein_g,
            carbs_g=self.carbs_g + other.carbs_g,
            fat_g=self.fat_g + other.fat_g,
            fiber_g=self.fiber_g + other.fiber_g,
            sugar_g=self.sugar_g + other.sugar_g,
        )
