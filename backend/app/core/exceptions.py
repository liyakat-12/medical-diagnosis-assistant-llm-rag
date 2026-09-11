from __future__ import annotations

from fastapi import HTTPException, status


class AppError(HTTPException):
    def __init__(self, status_code: int, detail: str):
        super().__init__(status_code=status_code, detail=detail)


def unauthorized(message: str = "Please sign in to use the assistant.") -> AppError:
    return AppError(status.HTTP_401_UNAUTHORIZED, message)


def forbidden(message: str = "You do not have access to this resource.") -> AppError:
    return AppError(status.HTTP_403_FORBIDDEN, message)


def not_found(message: str = "Not found.") -> AppError:
    return AppError(status.HTTP_404_NOT_FOUND, message)


def conflict(message: str) -> AppError:
    return AppError(status.HTTP_409_CONFLICT, message)


def bad_request(message: str) -> AppError:
    return AppError(status.HTTP_400_BAD_REQUEST, message)
