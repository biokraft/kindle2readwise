"""Exceptions for the Kindle2Readwise application."""


class Kindle2ReadwiseError(Exception):
    """Base class for all application errors."""

    pass


class ValidationError(Kindle2ReadwiseError):
    """Error raised when validation fails."""

    pass


class ProcessingError(Kindle2ReadwiseError):
    """Error raised when processing fails."""

    pass
