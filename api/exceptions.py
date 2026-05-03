"""
exceptions.py
-------------
Overrides DRF's default exception handler to produce a consistent
response envelope:

    {
        "success": false,
        "message": "Human-readable summary",
        "errors": { ... }   ← only present for validation errors
    }
"""

import logging
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    # Let DRF handle the basics first
    response = exception_handler(exc, context)

    if response is not None:
        # Reshape the response body
        errors = response.data
        message = _extract_message(errors)

        response.data = {
            "success": False,
            "message": message,
            "errors": errors,
        }
    else:
        # Unhandled exception → 500
        logger.error(
            "Unhandled exception in %s: %s",
            context.get("view"), exc,
            exc_info=True,
        )
        response = Response(
            {
                "success": False,
                "message": "An unexpected error occurred. Please try again.",
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return response


def _extract_message(errors) -> str:
    """Flatten error dict into a readable string for the 'message' field."""
    if isinstance(errors, list):
        return str(errors[0]) if errors else "Validation error."
    if isinstance(errors, dict):
        for key, val in errors.items():
            msg = val[0] if isinstance(val, list) else str(val)
            if key == "non_field_errors":
                return str(msg)
            return f"{key}: {msg}"
    return "An error occurred."
