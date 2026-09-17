class CCWError(Exception):
    """Base class for expected user-facing errors."""


class WorkForbiddenError(CCWError):
    """Raised whenever a route attempts to use ChatGPT Work."""


class ValidationError(CCWError):
    """Raised when a run or artifact fails validation."""


class StateError(CCWError):
    """Raised when a lifecycle transition is invalid."""
