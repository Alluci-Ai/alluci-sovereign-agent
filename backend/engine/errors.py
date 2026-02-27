class EngineError(Exception):
    """Base class for engine errors."""
    pass

class AdapterError(EngineError):
    """Raised when a tool adapter fails to execute."""
    pass

class AdapterNotFoundError(EngineError):
    """Raised when a requested tool is not registered."""
    pass

class TaskTimeoutError(EngineError):
    """Raised when a task exceeds its execution time limit."""
    pass

class PlanValidationError(EngineError):
    """Raised when the DAG structure is invalid."""
    pass
