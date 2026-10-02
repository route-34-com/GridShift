"""Errors that map to an HTTP status and a message for the user."""


class AppError(Exception):
    """A refusal with an HTTP status and a plain-language message; audit entries written before it are kept."""

    keeps_writes = True

    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message
