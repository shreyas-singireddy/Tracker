"""System Bootloader for registering and initializing modules, migrations, and dependencies."""

from app.core.exceptions import ServiceError
from app.core.logging import logger
from app.database.migrations import migration_runner
from app.modules.ai import AIModule
from app.modules.analytics import AnalyticsModule
from app.modules.habit import HabitModule
from app.modules.nutrition import NutritionModule
from app.modules.recovery import RecoveryModule
from app.modules.workout import WorkoutModule
from app.registry.module_registry import module_registry


class Bootloader:
    """Orchestrates system startup sequences for database migrations and module registries."""

    @staticmethod
    def boot() -> None:
        """Runs the sequential startup boot check."""
        logger.info("BOOTLOADER: Starting FitOS system boot sequence...")

        # 1. Run migrations
        try:
            logger.info("BOOTLOADER: Initializing database tables & migrations...")
            migration_runner.run_all()
        except Exception as e:
            logger.critical(f"BOOTLOADER: Database migration failed: {e!s}")
            raise ServiceError("System boot failure: migration error", details=str(e))

        # 2. Register Modules (skip if already registered to handle Streamlit re-runs gracefully)
        if not module_registry.get_all_modules():
            logger.info("BOOTLOADER: Registering module architectures...")
            module_registry.register("workout", WorkoutModule())
            module_registry.register("nutrition", NutritionModule())
            module_registry.register("habit", HabitModule())
            module_registry.register("recovery", RecoveryModule(), dependencies=["workout"])

            # AI and Analytics depend on prior domains
            module_registry.register("ai", AIModule(), dependencies=["workout", "nutrition", "habit", "recovery"])
            module_registry.register(
                "analytics", AnalyticsModule(), dependencies=["workout", "nutrition", "habit", "recovery"]
            )
        else:
            logger.info("BOOTLOADER: Modules already registered in singleton instance.")

        # 3. Initialize Modules in resolved load order
        try:
            module_registry.initialize_all()
        except Exception as e:
            logger.critical(f"BOOTLOADER: Module load sequence failed: {e!s}")
            raise ServiceError("System boot failure: dependency initialization cycle", details=str(e))

        # 4. Perform Startup Health Check
        health = module_registry.health_check_all()
        logger.info(f"BOOTLOADER: System health status is {health['status']}")

        if health["status"] == "RED":
            logger.critical(f"BOOTLOADER: RED alert status during health check: {health}")
            raise ServiceError("System boot failed due to critical RED status.", details=str(health))

        logger.info("BOOTLOADER: FitOS system booted successfully and is fully operational.")
