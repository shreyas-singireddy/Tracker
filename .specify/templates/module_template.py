"""Template for creating new FitOS modules."""

from typing import Any

from app.modules.base import BaseModule


class NewModule(BaseModule):
    """Template module."""

    def __init__(self):
        self.service = None

    def init(self) -> None:
        pass

    def get_services(self) -> dict[str, Any]:
        return {"NewService": self.service}

    def get_repositories(self) -> dict[str, Any]:
        return {}

    def health_check(self) -> dict[str, Any]:
        return {"status": "GREEN", "details": "Template module healthy."}
