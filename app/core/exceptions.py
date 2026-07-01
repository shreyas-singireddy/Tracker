class FitOSError(Exception):
    """Base exception for all FitOS errors."""

    def __init__(self, message: str = "An unexpected error occurred in FitOS", details: str | None = None):
        super().__init__(message)
        self.message = message
        self.details = details

    def __str__(self):
        if self.details:
            return f"{self.message} (Details: {self.details})"
        return self.message


class ConfigurationError(FitOSError):
    """Raised when application configuration is invalid or missing."""


class DatabaseError(FitOSError):
    """Raised when there is an issue with database connection or query execution."""


class RepositoryError(FitOSError):
    """Raised when a data access operation fails in the repository layer."""


class ServiceError(FitOSError):
    """Raised when an operation in the service layer fails."""


class ValidationError(ServiceError):
    """Raised when request validation rules are violated."""
