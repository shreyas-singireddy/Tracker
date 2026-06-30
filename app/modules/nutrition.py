"""NutritionModule standardization interface wrapper for FitOS (Sprint 10)."""
from typing import Dict, Any
from app.modules.base import BaseModule
from app.services.nutrition import NutritionService
from app.repositories.nutrition import (
    MealRepository,
    MealEntryRepository,
    NutritionLogRepository
)
from app.repositories.food import FoodRepository
from app.database.connection import db_manager

class NutritionModule(BaseModule):
    """Encapsulates Nutrition domain logic interfaces."""

    def __init__(self):
        self.food_repo = None
        self.meal_repo = None
        self.entry_repo = None
        self.log_repo = None
        self.service = None

    def init(self) -> None:
        self.food_repo = FoodRepository()
        self.meal_repo = MealRepository()
        self.entry_repo = MealEntryRepository()
        self.log_repo = NutritionLogRepository()
        self.service = NutritionService(
            food_repo=self.food_repo,
            meal_repo=self.meal_repo,
            entry_repo=self.entry_repo,
            log_repo=self.log_repo
        )

    def get_services(self) -> Dict[str, Any]:
        return {"NutritionService": self.service}

    def get_repositories(self) -> Dict[str, Any]:
        return {
            "FoodRepository": self.food_repo,
            "MealRepository": self.meal_repo,
            "MealEntryRepository": self.entry_repo,
            "NutritionLogRepository": self.log_repo
        }

    def health_check(self) -> Dict[str, Any]:
        try:
            db_manager.execute_read("SELECT 1 FROM foods LIMIT 1;")
            db_manager.execute_read("SELECT 1 FROM meals LIMIT 1;")
            db_manager.execute_read("SELECT 1 FROM meal_entries LIMIT 1;")
            db_manager.execute_read("SELECT 1 FROM nutrition_logs LIMIT 1;")
            return {"status": "GREEN", "details": "Nutrition module tables are readable."}
        except Exception as e:
            return {"status": "RED", "details": f"Nutrition health check failed: {str(e)}"}
