class LibraryError(Exception):
    """Base exception for task_weaver"""
    pass

class ConfigurationError(LibraryError):
    """Raised when there's a configuration error"""
    pass

class ProcessingError(LibraryError):
    """Raised when processing fails"""
    pass
