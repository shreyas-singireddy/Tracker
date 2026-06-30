"""System Registry Layer for module registration, dependency resolution, and health monitoring.

Provides:
- ModuleRegistry: central singleton to register/initialize modules
- ServiceRegistry: registry for global service lookups
- DependencyGraph: topological sorter & circular dependency detector
"""

from typing import Dict, List, Any, Optional
from app.modules.base import BaseModule
from app.core.logging import logger
from app.core.exceptions import ValidationError

class ServiceRegistry:
    """Registry class for globally registering and looking up service instances."""
    _services: Dict[str, Any] = {}

    @classmethod
    def register(cls, name: str, service: Any) -> None:
        logger.info(f"REGISTRY: Registering service '{name}'")
        cls._services[name] = service

    @classmethod
    def get(cls, name: str) -> Any:
        if name not in cls._services:
            raise KeyError(f"Service '{name}' not found in registry.")
        return cls._services[name]

    @classmethod
    def clear(cls) -> None:
        cls._services.clear()


class DependencyGraph:
    """Graph structure to validate dependencies and resolve load ordering."""

    def __init__(self, adj_list: Dict[str, List[str]]):
        self.adj_list = adj_list

    def detect_circular_dependencies(self) -> bool:
        """Returns True if a circular dependency is detected."""
        visited = set()
        rec_stack = set()

        def dfs(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in self.adj_list.get(node, []):
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
                    
            rec_stack.remove(node)
            return False

        for node in self.adj_list:
            if node not in visited:
                if dfs(node):
                    return True
        return False

    def get_load_order(self) -> List[str]:
        """Performs topological sort to determine correct load order of modules."""
        if self.detect_circular_dependencies():
            raise ValidationError("Circular dependency detected in system modules graph!")

        visited = set()
        order = []

        def dfs(node: str):
            visited.add(node)
            for neighbor in self.adj_list.get(node, []):
                if neighbor not in visited:
                    dfs(neighbor)
            order.append(node)

        for node in self.adj_list:
            if node not in visited:
                dfs(node)

        return order


class ModuleRegistry:
    """Central registry handling registration, initialization, and lifecycle monitoring of modules."""

    def __init__(self):
        self._modules: Dict[str, BaseModule] = {}
        self._dependencies: Dict[str, List[str]] = {}
        self._initialized = False

    def register(self, name: str, module: BaseModule, dependencies: Optional[List[str]] = None) -> None:
        """Registers a module and its associated dependencies."""
        if name in self._modules:
            raise ValidationError(f"Module '{name}' is already registered.")
        
        self._modules[name] = module
        self._dependencies[name] = dependencies or []
        logger.info(f"REGISTRY: Module '{name}' registered successfully.")

    def initialize_all(self) -> List[str]:
        """Resolves dependencies, checks cycles, and initializes modules in sorted order."""
        if self._initialized:
            logger.warning("REGISTRY: Modules already initialized.")
            return list(self._modules.keys())

        # Validate that all declared dependencies are registered
        for name, deps in self._dependencies.items():
            for dep in deps:
                if dep not in self._modules:
                    raise ValidationError(
                        f"Module '{name}' depends on unregistered module '{dep}'!"
                    )

        # Topological sorting
        graph = DependencyGraph(self._dependencies)
        load_order = graph.get_load_order()

        logger.info(f"REGISTRY: Resolved load order: {load_order}")

        for name in load_order:
            logger.info(f"REGISTRY: Initializing module '{name}'...")
            module = self._modules[name]
            module.init()
            
            # Register module services globally
            for s_name, s_instance in module.get_services().items():
                ServiceRegistry.register(s_name, s_instance)
                
        self._initialized = True
        logger.info("REGISTRY: All modules initialized successfully.")
        return load_order

    def get_module(self, name: str) -> BaseModule:
        if name not in self._modules:
            raise KeyError(f"Module '{name}' not found.")
        return self._modules[name]

    def get_all_modules(self) -> Dict[str, BaseModule]:
        return self._modules

    def health_check_all(self) -> Dict[str, Any]:
        """Aggregates health checks from all registered modules."""
        status = "GREEN"
        checks = {}

        for name, module in self._modules.items():
            try:
                res = module.health_check()
                checks[name] = res
                if res.get("status") == "RED":
                    status = "RED"
                elif res.get("status") == "YELLOW" and status != "RED":
                    status = "YELLOW"
            except Exception as e:
                checks[name] = {"status": "RED", "details": f"Health check threw exception: {str(e)}"}
                status = "RED"

        return {"status": status, "modules": checks}


# Global registry instance
module_registry = ModuleRegistry()
