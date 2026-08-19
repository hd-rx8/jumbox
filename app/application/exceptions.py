from __future__ import annotations


class ApplicationError(Exception):
    """Base exception for application-layer failures."""


class AuthenticationError(ApplicationError):
    """Raised when authentication fails."""


class ConflictError(ApplicationError):
    """Raised when a resource already exists."""


class NotFoundError(ApplicationError):
    """Raised when a resource cannot be found."""


class SessionNotFoundError(NotFoundError):
    """Raised when a transfer session cannot be found."""


class ItemNotFoundError(NotFoundError):
    """Raised when a transfer item cannot be found."""


class SessionExpiredError(ApplicationError):
    """Raised when an operation is attempted on an expired session."""


class PermissionDeniedError(ApplicationError):
    """Raised when user is not authorized to perform the action."""
