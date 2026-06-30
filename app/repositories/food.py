from typing import Optional, List
from app.repositories.base import BaseRepository
from app.models.domain import FoodItem


class FoodRepository(BaseRepository):
    """Repository class managing CRUD operations for the foods table."""

    def create_food(self, food: FoodItem) -> str:
        """Saves a FoodItem object to the database."""
        self.create("foods", food.to_dict())
        return food.food_id

    def get_food(self, food_id: str) -> Optional[FoodItem]:
        """Fetches a FoodItem object by its food_id."""
        row = self.read("foods", "food_id", food_id)
        return FoodItem.from_dict(row) if row else None

    def update_food(self, food_id: str, updates: dict) -> int:
        """Updates food details."""
        return self.update("foods", "food_id", food_id, updates)

    def delete_food(self, food_id: str) -> int:
        """Deletes a food record."""
        return self.delete("foods", "food_id", food_id)

    def list_foods(self) -> List[FoodItem]:
        """Lists all food items."""
        rows = self.list_all("foods")
        return [FoodItem.from_dict(row) for row in rows]
