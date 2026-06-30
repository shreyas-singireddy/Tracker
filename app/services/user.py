from typing import Optional, Tuple
from app.repositories.user import UserRepository, UserProfileRepository
from app.models.domain import User, UserProfile
from app.utils.validators import validate_user_profile, validate_email
from app.core.exceptions import ValidationError, ServiceError
from app.core.logging import logger
from app.database.connection import db_manager


class UserService:
    """Orchestrates user management operations and enforces registration constraints."""

    def __init__(self, user_repo: Optional[UserRepository] = None, profile_repo: Optional[UserProfileRepository] = None):
        self.user_repo = user_repo or UserRepository()
        self.profile_repo = profile_repo or UserProfileRepository()

    def register_user(self, user: User, profile: UserProfile) -> str:
        """Validates metrics and registers a new User account alongside their physical Profile."""
        logger.info(f"Attempting to register user: {user.email}")
        
        # Validations
        validate_email(user.email)
        validate_user_profile(profile.birth_date, profile.weight_kg, profile.height_cm)

        # Check duplicate user
        existing_user = self.user_repo.get_user(user.user_id)
        if existing_user:
            logger.warning(f"Registration rejected: User with ID {user.user_id} already exists.")
            raise ValidationError(
                message="User registration failed: User already exists.",
                details=f"User ID: {user.user_id}"
            )
            
        # SQLite duplicate email check (fails database UNIQUE check otherwise)
        existing_by_email = self.user_repo.db.execute_read_one("SELECT 1 FROM users WHERE email = ?;", (user.email,))
        if existing_by_email:
            logger.warning(f"Registration rejected: Email {user.email} already in use.")
            raise ValidationError(
                message="User registration failed: Email address already registered.",
                details=f"Email: {user.email}"
            )

        # Orchestrated write inside database transaction
        try:
            with db_manager.transaction():
                self.user_repo.create_user(user)
                self.profile_repo.create_profile(profile)
            logger.info(f"User {user.user_id} successfully registered.")
            return user.user_id
        except Exception as e:
            logger.error(f"Failed to register user transaction: {str(e)}")
            raise ServiceError("User registration transaction failed.", details=str(e))

    def get_user_and_profile(self, user_id: str) -> Optional[Tuple[User, UserProfile]]:
        """Retrieves a tuple containing User data and UserProfile data."""
        user = self.user_repo.get_user(user_id)
        profile = self.profile_repo.get_profile(user_id)
        
        if not user or not profile:
            return None
            
        return user, profile

    def update_profile_metrics(self, user_id: str, weight_kg: float, height_cm: float):
        """Updates weight and height metrics for an existing user after validating values."""
        logger.info(f"Updating profile metrics for user: {user_id}")
        
        profile = self.profile_repo.get_profile(user_id)
        if not profile:
            logger.warning(f"Update failed: Profile for user {user_id} not found.")
            raise ValidationError(f"Profile for user {user_id} does not exist.")

        # Validate with existing birth date
        validate_user_profile(profile.birth_date, weight_kg, height_cm)

        updates = {
            "weight_kg": weight_kg,
            "height_cm": height_cm
        }
        self.profile_repo.update_profile(user_id, updates)
        logger.info(f"Profile metrics updated successfully for user {user_id}.")
