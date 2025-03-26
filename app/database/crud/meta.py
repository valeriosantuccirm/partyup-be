import threading
from typing import Any, Dict


class Meta(type):
    """A thread-safe implementation of Singleton using metaclass."""

    _instances: Dict[Any, Any] = {}
    _lock = threading.Lock()  # Ensures thread safety during instance creation

    def __call__(cls, *args, **kwargs) -> Any:
        """Controls the instantiation of the singleton instance."""
        with cls._lock:  # Prevents race conditions in multithreading
            if cls not in cls._instances:
                cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]
