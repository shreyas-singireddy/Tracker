from app.models.domain import BodyMeasurement
from app.repositories.base import BaseRepository


class BodyMeasurementRepository(BaseRepository):
    """Repository class managing CRUD operations for the body_measurements table."""

    def create_measurement(self, measurement: BodyMeasurement) -> str:
        """Saves a BodyMeasurement object to the database."""
        self.create("body_measurements", measurement.to_dict())
        return measurement.measurement_id

    def get_measurement(self, measurement_id: str) -> BodyMeasurement | None:
        """Fetches a BodyMeasurement object by measurement_id."""
        row = self.read("body_measurements", "measurement_id", measurement_id)
        return BodyMeasurement.from_dict(row) if row else None

    def get_user_measurements(self, user_id: str) -> list[BodyMeasurement]:
        """Retrieves all measurements associated with a specific user."""
        query = "SELECT * FROM body_measurements WHERE user_id = ? ORDER BY logged_at DESC;"
        rows = self.db.execute_read(query, (user_id,))
        return [BodyMeasurement.from_dict(row) for row in rows]

    def update_measurement(self, measurement_id: str, updates: dict) -> int:
        """Updates measurement details."""
        return self.update("body_measurements", "measurement_id", measurement_id, updates)

    def delete_measurement(self, measurement_id: str) -> int:
        """Deletes a measurement record."""
        return self.delete("body_measurements", "measurement_id", measurement_id)
