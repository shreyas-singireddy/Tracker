from typing import Optional, List
from app.repositories.food import FoodRepository
from app.models.domain import FoodItem
from app.utils.validators import validate_food_item
from app.core.exceptions import ValidationError, ServiceError
from app.core.logging import logger


class FoodService:
    """Orchestrates food dictionary logging and validates nutritional calorie/macronutrient balances."""

    def __init__(self, food_repo: Optional[FoodRepository] = None):
        self.food_repo = food_repo or FoodRepository()

    def add_food_item(self, food: FoodItem) -> str:
        """Validates macronutrient consistency and registers a new food item in the catalog."""
        logger.info(f"Adding food item: {food.name}")
        
        # Validations
        if not food.name.strip():
            raise ValidationError("Food item name cannot be empty.")
            
        validate_food_item(food.calories, food.protein, food.carbs, food.fats)

        if food.serving_size_g <= 0:
            raise ValidationError("Serving size must be greater than 0 grams.")

        # Ensure name uniqueness (Data Integrity Rule)
        existing_foods = self.food_repo.db.execute_read_one("SELECT 1 FROM foods WHERE name = ?;", (food.name,))
        if existing_foods:
            logger.warning(f"Registration rejected: Food item name '{food.name}' already exists.")
            raise ValidationError(
                message="Food item creation failed: Name already exists in catalog.",
                details=f"Name: {food.name}"
            )

        try:
            return self.food_repo.create_food(food)
        except Exception as e:
            logger.error(f"Failed to add food item: {str(e)}")
            raise ServiceError("Food item creation failed.", details=str(e))

    def get_food_item(self, food_id: str) -> Optional[FoodItem]:
        """Retrieves a single food item definition."""
        return self.food_repo.get_food(food_id)

    def list_food_items(self) -> List[FoodItem]:
        """Retrieves all food items in the database dictionary."""
        return self.food_repo.list_foods()
