"""BaseModule — Abstract Base Class for module standardization in FitOS.

Every domain module (Workout, Nutrition, Habit, Recovery, AI, Analytics)
must inherit from BaseModule and implement its lifecycle contracts.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseModule(ABC):
    """Lifecycle and contract interface for modular FitOS systems."""

    @abstractmethod
    def init(self) -> None:
        """Initializes dependencies, loads config, and runs module migrations/seeds."""
        pass

    @abstractmethod
    def get_services(self) -> Dict[str, Any]:
        """Exposes the business service layer classes within this module boundary."""
        pass

    @abstractmethod
    def get_repositories(self) -> Dict[str, Any]:
        """Exposes the raw data access repository classes within this module boundary."""
        pass

    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """Runs diagnostics on database access and module state.
        
        Returns:
            Dict containing 'status' (GREEN/YELLOW/RED) and detailed diagnosics.
        """
        pass
