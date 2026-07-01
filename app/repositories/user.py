from app.models.domain import User, UserProfile
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository):
    """Repository class managing CRUD operations for the users table."""

    def create_user(self, user: User) -> str:
        """Saves a User object to the database."""
        self.create("users", user.to_dict())
        return user.user_id

    def get_user(self, user_id: str) -> User | None:
        """Fetches a User object by its user_id."""
        row = self.read("users", "user_id", user_id)
        return User.from_dict(row) if row else None

    def update_user(self, user_id: str, updates: dict) -> int:
        """Updates user record details."""
        return self.update("users", "user_id", user_id, updates)

    def delete_user(self, user_id: str) -> int:
        """Deletes a user record."""
        return self.delete("users", "user_id", user_id)


class UserProfileRepository(BaseRepository):
    """Repository class managing CRUD operations for the user_profiles table."""

    def create_profile(self, profile: UserProfile) -> str:
        """Saves a UserProfile object to the database."""
        self.create("user_profiles", profile.to_dict())
        return profile.user_id

    def get_profile(self, user_id: str) -> UserProfile | None:
        """Fetches a UserProfile object by user_id."""
        row = self.read("user_profiles", "user_id", user_id)
        return UserProfile.from_dict(row) if row else None

    def update_profile(self, user_id: str, updates: dict) -> int:
        """Updates profile details."""
        return self.update("user_profiles", "user_id", user_id, updates)

    def delete_profile(self, user_id: str) -> int:
        """Deletes a profile record."""
        return self.delete("user_profiles", "user_id", user_id)
