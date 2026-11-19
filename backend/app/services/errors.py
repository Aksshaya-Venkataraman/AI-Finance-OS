class ServiceError(ValueError):
    """Base class for expected business-rule failures (mapped to 4xx responses)."""


class NotFoundError(ServiceError):
    pass


class ConflictError(ServiceError):
    pass


class ValidationFailed(ServiceError):
    def __init__(self, message: str, errors: list[str]) -> None:
        super().__init__(message)
        self.errors = errors
