import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        errors = response.data
        response.data = {
            "success": False,
            "message": _extract_message(errors),
            "errors": errors,
        }
        return response

    logger.error(
        "Unhandled exception in %s: %s",
        context.get("view"),
        exc,
        exc_info=True,
    )
    return Response(
        {
            "success": False,
            "message": "An unexpected error occurred. Please try again.",
            "errors": {},
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


def _extract_message(errors) -> str:
    if isinstance(errors, list):
        return str(errors[0]) if errors else "Validation error."
    if isinstance(errors, dict):
        for key, value in errors.items():
            message = value[0] if isinstance(value, list) else str(value)
            if key == "non_field_errors":
                return str(message)
            return f"{key}: {message}"
    return "An error occurred."
